#!/usr/bin/env python3
"""
Scan a Spring Boot codebase for HTTP endpoints and audit-logging coverage.

Stdlib only. No dependencies, no network access. Never writes to the repo.

    python scripts/scan.py <path-to-repo> [--json] [--include-tests] [--out FILE]

Output is a markdown report on stdout.

Granularity is the endpoint, not the file. A file that mentions AuditService in a
comment is not an audited file. Every row carries a file and line, so "not
audited" is a claim you can check.
"""

import argparse
import json
import os
import re
import sys

# --- Patterns ---

MAPPING = re.compile(
    r'@(GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping|RequestMapping)\b')
METHOD_FOR_REQUESTMAPPING = re.compile(r'RequestMethod\.(\w+)')

# Audit markers, matched against the method body and its annotations only.
AUDIT = re.compile(
    r'@AuditLog|@Audited|@Auditable|AuditService|AuditRecorder|AuditLogger|'
    r'AuditRepository|AuditEvent|AuditTrail|AuditPublisher|auditLog\.|auditService\.|'
    r'audit\.record', re.IGNORECASE)

# Signs of audit happening somewhere central rather than per endpoint.
CENTRAL = [
    ('aspect', re.compile(r'@Aspect\b')),
    ('filter', re.compile(r'extends\s+OncePerRequestFilter\b|implements\s+Filter\b')),
    ('interceptor', re.compile(r'implements\s+HandlerInterceptor\b')),
    ('advice', re.compile(r'@RestControllerAdvice\b|@ControllerAdvice\b')),
    ('base class', re.compile(r'class\s+\w+\s+extends\s+(?:Base)?(?:Audited)?Controller\b')),
]

FEIGN = re.compile(r'@FeignClient\b')
SCHEDULED = re.compile(r'@Scheduled\b')

SKIP_DIRS = {'.git', 'target', 'build', 'node_modules', '.idea', 'out', 'bin', '.mvn'}

# Ranked by blast radius. First match wins.
CATEGORIES = [
    ('money movement', 40, (
        'transfer', 'payment', 'pay', 'payout', 'refund', 'debit', 'credit', 'withdraw',
        'deposit', 'balance', 'ledger', 'settle', 'invoice', 'billing', 'charge',
        'premium', 'claim', 'policy', 'loan', 'emi', 'disburse', 'order', 'checkout',
        'subscription', 'renewal', 'transaction', 'txn',
    )),
    ('customer identity', 30, (
        'kyc', 'customer', 'account', 'profile', 'user', 'auth', 'login', 'logout',
        'token', 'credential', 'password', 'otp', 'consent', 'role', 'permission',
        'admin', 'register', 'signup', 'mfa', 'session',
    )),
    ('documents', 20, (
        'document', 'upload', 'download', 'attachment', 'export', 'import', 'file',
        'report', 'statement', 'pdf', 'share',
    )),
]

METHOD_WEIGHT = {'DELETE': 15, 'PUT': 10, 'PATCH': 10, 'POST': 10, 'GET': 0, 'ANY': 5}


# --- Java source handling ---

def strip_comments(src):
    """Blank // and /* */ comments, keeping string literals and every offset."""
    out, i, n, state = [], 0, len(src), None
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if state is None:
            if c == '/' and nxt == '/':
                state, i = 'line', i + 2
                out.append('  ')
                continue
            if c == '/' and nxt == '*':
                state, i = 'block', i + 2
                out.append('  ')
                continue
            if src.startswith('"""', i):
                state = 'textblock'
                out.append('"""')
                i += 3
                continue
            if c == '"':
                state = 'str'
            elif c == "'":
                state = 'char'
            out.append(c)
            i += 1
            continue
        if state == 'line':
            if c == '\n':
                state = None
                out.append(c)
            else:
                out.append(' ')
            i += 1
            continue
        if state == 'block':
            if c == '*' and nxt == '/':
                state = None
                out.append('  ')
                i += 2
                continue
            out.append(c if c == '\n' else ' ')
            i += 1
            continue
        if state == 'textblock':
            if src.startswith('"""', i):
                state = None
                out.append('"""')
                i += 3
                continue
            out.append(c if c == '\n' else ' ')
            i += 1
            continue
        if c == '\\' and i + 1 < n:
            out.append(c)
            out.append(src[i + 1])
            i += 2
            continue
        if (state == 'str' and c == '"') or (state == 'char' and c == "'"):
            state = None
        out.append(c)
        i += 1
    return ''.join(out)


def mask_strings(src):
    """Blank the *contents* of literals so '/{id}' is not mistaken for a block."""
    out = list(src)
    i, n, state = 0, len(src), None
    while i < n:
        c = src[i]
        if state is None:
            if src.startswith('"""', i):
                state = 'textblock'
                i += 3
                continue
            if c == '"':
                state = 'str'
            elif c == "'":
                state = 'char'
            i += 1
            continue
        if state == 'textblock':
            if src.startswith('"""', i):
                state = None
                i += 3
                continue
            if c != '\n':
                out[i] = ' '
            i += 1
            continue
        if c == '\\' and i + 1 < n:
            out[i] = out[i + 1] = ' '
            i += 2
            continue
        if (state == 'str' and c == '"') or (state == 'char' and c == "'"):
            state = None
            i += 1
            continue
        if c != '\n':
            out[i] = ' '
        i += 1
    return ''.join(out)


def line_of(src, pos):
    return src.count('\n', 0, pos) + 1


def match_brace(src, open_pos):
    depth = 0
    for i in range(open_pos, len(src)):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1


def string_args(text):
    return [m.group(1) for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', text)]


def annotation_args(src, end_pos):
    """Return the raw '( ... )' text following an annotation name, or ''."""
    rest = src[end_pos:]
    stripped = rest.lstrip()
    if not stripped.startswith('('):
        return ''
    start = src.index('(', end_pos)
    depth = 0
    for i in range(start, len(src)):
        if src[i] == '(':
            depth += 1
        elif src[i] == ')':
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    return ''


def class_ranges(code):
    """Yield (name, body_start, body_end, decl_start) for each type declaration."""
    pattern = re.compile(
        r'(?m)^[ \t]*(?:@\w+(?:\([^)]*\))?[ \t]*\n[ \t]*)*'
        r'(?:public[ \t]+|final[ \t]+|abstract[ \t]+|static[ \t]+)*'
        r'(?:class|record)[ \t]+(\w+)')
    for m in pattern.finditer(code):
        brace = code.find('{', m.end())
        if brace == -1:
            continue
        end = match_brace(code, brace)
        if end == -1:
            continue
        yield m.group(1), brace, end, m.start()


def header_before(src, pos, window=1200):
    chunk = src[max(0, pos - window):pos]
    cut = max(chunk.rfind(';'), chunk.rfind('}'), chunk.rfind('{'))
    return chunk[cut + 1:] if cut != -1 else chunk


# --- Classification ---

def classify(path, java_method, http_method):
    """Category by path and method name.

    Exact token match with a naive plural stripped (`documents` hits `document`).
    Keys of 5+ chars also match inside compound method names (`deleteDocument`
    hits `delete`); short keys never substring-match, so `payload` misses `pay`.
    """
    hay = '{} {}'.format(path, java_method).lower()
    words = set()
    for token in re.split(r'[^a-z0-9]+', hay):
        if not token:
            continue
        words.add(token)
        if token.endswith('s'):
            words.add(token[:-1])

    for name, weight, keys in CATEGORIES:
        if any(k in words for k in keys):
            return name, weight + METHOD_WEIGHT.get(http_method, 0)
        if any(len(k) >= 5 and k in w for w in words for k in keys):
            return name, weight + METHOD_WEIGHT.get(http_method, 0)
    return 'other', 10 + METHOD_WEIGHT.get(http_method, 0)


def risk_label(score):
    if score >= 40:
        return 'high'
    if score >= 25:
        return 'medium'
    return 'low'


# --- Scan ---

def walk_java(root, include_tests):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        norm = dirpath.replace(os.sep, '/') + '/'
        is_test = '/src/test/' in norm or '/test/java/' in norm
        if is_test and not include_tests:
            continue
        for fn in sorted(filenames):
            if fn.endswith('.java'):
                yield os.path.join(dirpath, fn)


def scan(root, include_tests=False):
    endpoints, central, feign_files, scheduled_files = [], [], [], []
    files_read = 0

    for path in walk_java(root, include_tests):
        try:
            with open(path, encoding='utf-8', errors='replace') as f:
                raw = f.read()
        except OSError:
            continue
        files_read += 1

        src = strip_comments(raw)
        code = mask_strings(src)
        rel = os.path.relpath(path, root).replace(os.sep, '/')

        if FEIGN.search(code):
            feign_files.append({'file': rel, 'audited': bool(AUDIT.search(src))})
        if SCHEDULED.search(code):
            scheduled_files.append(rel)

        for kind, pattern in CENTRAL:
            for m in pattern.finditer(code):
                window = src[m.start():m.start() + 2500]
                head = header_before(src, m.start(), 400)
                central.append({
                    'kind': kind,
                    'file': rel,
                    'line': line_of(src, m.start()),
                    'audit_aware': bool(AUDIT.search(window) or AUDIT.search(head)),
                })

        ranges = list(class_ranges(code))
        if not ranges:
            continue

        for m in MAPPING.finditer(code):
            ann = m.group(1)
            args = annotation_args(code, m.end())
            args_src = annotation_args(src, m.end())

            owner = None
            for name, bstart, bend, dstart in ranges:
                if bstart <= m.start() <= bend and (owner is None or bstart > owner[1]):
                    owner = (name, bstart, bend, dstart)
            if owner is None:
                continue  # class-level mapping, read as the base path below
            cls, cstart, cend, dstart = owner

            cheader = code[max(0, dstart - 800):cstart]
            cheader_src = src[max(0, dstart - 800):cstart]
            is_rest = '@RestController' in cheader
            if not (is_rest or '@Controller' in cheader):
                continue

            body_open = code.find('{', m.end())
            semi = code.find(';', m.end())
            if body_open == -1 or (semi != -1 and semi < body_open) or body_open > cend:
                continue  # abstract method: nothing to inspect
            body_end = match_brace(code, body_open)
            if body_end == -1:
                continue

            signature = code[m.end():body_open]
            body = src[body_open:body_end + 1]

            java_method = '?'
            for cand in re.finditer(r'(\w+)\s*\(', signature):
                word = cand.group(1)
                if word in {'new', 'if', 'for', 'while', 'switch', 'catch', 'return',
                            'throw', 'super', 'this'}:
                    continue
                if signature[:cand.start(1)].rstrip().endswith('@'):
                    continue
                java_method = word
                break

            http_method = ann[:-7].upper() if ann != 'RequestMapping' else None
            if http_method is None:
                mm = METHOD_FOR_REQUESTMAPPING.search(args)
                http_method = mm.group(1) if mm else 'ANY'

            base = ''
            cm = re.search(r'@RequestMapping\b\s*(\((?:[^()]|\([^()]*\))*\))?', cheader_src)
            if cm and cm.group(1):
                found = string_args(cm.group(1))
                if found:
                    base = found[0]
            sub = string_args(args_src)
            sub_path = sub[0] if sub else ''
            full = '/' + '/'.join(p.strip('/') for p in (base, sub_path) if p.strip('/'))
            if full == '/':
                full = base or '/'

            ann_header = header_before(src, m.start(), 600)
            covered, evidence = False, 'no audit call in the method, no audit annotation on it'
            if re.search(r'@(?:Audit|Audited|Auditable|Loggable)\b', ann_header):
                covered, evidence = True, 'audit annotation on the method'
            else:
                hit = AUDIT.search(body)
                if hit:
                    covered = True
                    evidence = 'audit call at line {}'.format(
                        line_of(src, body_open + hit.start()))

            category, score = classify(full, java_method, http_method)
            notes = []
            if not is_rest and re.search(r'public\s+String\s+\w+\s*\(', signature):
                # A @Controller returning String renders a view only if it returns a
                # template name. Returning a constant is a text body.
                literal = re.search(r'return\s+"([^"]*)"\s*;', body)
                is_view = bool(literal) and re.fullmatch(r'[a-z][a-z0-9/_-]*', literal.group(1))
                if is_view and '@ResponseBody' not in cheader + signature:
                    category, score = 'page render', 5
                    notes.append('returns a template name - confirm this is an audit event')
                else:
                    notes.append('returns a String body, not a template - ranked as data')

            endpoints.append({
                'endpoint': full,
                'method': http_method,
                'operation': java_method,
                'audited': covered,
                'evidence': evidence,
                'file': rel,
                'line': line_of(src, m.start()),
                'controller': cls,
                'category': category,
                'score': score,
                'risk': risk_label(score),
                'notes': notes,
            })

    return {
        'files_read': files_read,
        'endpoints': endpoints,
        'central': central,
        'feign': feign_files,
        'scheduled': scheduled_files,
    }


# --- Report ---

def report(result, root):
    eps = result['endpoints']
    gaps = sorted([e for e in eps if not e['audited']],
                  key=lambda e: (-e['score'], e['endpoint']))
    done = sorted([e for e in eps if e['audited']],
                  key=lambda e: (-e['score'], e['endpoint']))
    central = result['central']
    aware = [c for c in central if c['audit_aware']]
    controllers = sorted({(e['controller'], e['file']) for e in eps})

    o = []
    o.append('# Audit coverage report\n')
    o.append('Scanned: `{}`\n'.format(root))
    o.append('## Summary\n')
    o.append('- Java files read: **{}**'.format(result['files_read']))
    o.append('- Controllers: **{}**'.format(len(controllers)))
    o.append('- Endpoints found: **{}**'.format(len(eps)))
    o.append('- With audit logging in the method: **{}**'.format(len(done)))
    o.append('- **Without audit logging: {}**'.format(len(gaps)))

    if aware:
        o.append('- Central audit infrastructure detected: **yes** — the "no" rows below '
                 'are unconfirmed until you check it covers them')
    elif central:
        o.append('- Central infrastructure found, but none of it mentions auditing')
    else:
        o.append('- Central audit infrastructure detected: **none**')
    o.append('')

    if aware:
        o.append('> **Central audit exists.** Read the pointcut, `addPathPatterns` / '
                 '`excludePathPatterns`, or filter URL pattern before reporting any row '
                 'below as a gap. An endpoint covered there is covered.\n')

    o.append('## Central audit infrastructure\n')
    if central:
        o.append('| Kind | Where | Audit-aware |')
        o.append('|---|---|---|')
        for c in central:
            o.append('| {} | `{}`:{} | {} |'.format(
                c['kind'], c['file'], c['line'], 'yes' if c['audit_aware'] else 'no'))
    else:
        o.append('None found. No `@Aspect`, filter, interceptor or controller advice in the '
                 'scanned sources, so each endpoint has to audit for itself.')
    o.append('')

    if gaps:
        o.append('## Endpoints without audit logging, worst first\n')
        o.append('| Endpoint | Method | Operation | Audited? | Risk |')
        o.append('|---|---|---|---|---|')
        for e in gaps:
            mark = 'no' if not aware else 'unconfirmed'
            o.append('| `{}` | {} | `{}()` | {} | {} ({}, score {}) |'.format(
                e['endpoint'], e['method'], e['operation'], mark,
                e['risk'], e['category'], e['score']))
        o.append('')
        o.append('Where each row lives:\n')
        o.append('| Endpoint | File | Line | Note |')
        o.append('|---|---|---|---|')
        for e in gaps:
            o.append('| `{}` {} | `{}` | {} | {} |'.format(
                e['endpoint'], e['method'], e['file'], e['line'],
                '; '.join(e.get('notes') or []) or '-'))
        o.append('')

    if done:
        o.append('## Endpoints that already audit\n')
        o.append('| Endpoint | Method | Operation | Evidence |')
        o.append('|---|---|---|---|')
        for e in done:
            o.append('| `{}` | {} | `{}()` | {} |'.format(
                e['endpoint'], e['method'], e['operation'], e['evidence']))
        o.append('')

    if result['feign']:
        o.append('## Outbound calls (Feign clients) — check these are audited too\n')
        for f in result['feign']:
            o.append('- `{}` — {}'.format(
                f['file'], 'audited' if f['audited'] else 'NOT audited'))
        o.append('')

    if result['scheduled']:
        o.append('## Scheduled jobs — state changes with no caller\n')
        for f in result['scheduled']:
            o.append('- `{}`'.format(f))
        o.append('')

    o.append('## How to read this\n')
    o.append('"Audited" means the method itself calls an audit sink or carries an audit '
             'annotation. It does not mean the record is complete — check it against '
             '`references/checklist.md`.')
    o.append('')
    o.append('A row marked "unconfirmed" is not a gap yet. Verify central coverage first, '
             'then report it.')
    o.append('')
    return '\n'.join(o)


def main():
    ap = argparse.ArgumentParser(description='Spring Boot audit-coverage scanner')
    ap.add_argument('path', help='repository root to scan')
    ap.add_argument('--json', action='store_true', help='emit JSON instead of markdown')
    ap.add_argument('--include-tests', action='store_true', help='scan src/test too')
    ap.add_argument('--out', help='also write the report to this file')
    args = ap.parse_args()

    if not os.path.isdir(args.path):
        print('Not a directory: {}'.format(args.path), file=sys.stderr)
        return 2

    result = scan(args.path, args.include_tests)
    if not result['endpoints']:
        print('No controller endpoints found under {}.'.format(args.path), file=sys.stderr)
        print('Point the scanner at the module containing the @RestController classes.',
              file=sys.stderr)
        return 1

    output = (json.dumps(result, indent=2) if args.json else report(result, args.path))

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(output + '\n')
    print(output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
