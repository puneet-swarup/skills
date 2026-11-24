# Implementation patterns

Four ways to add audit logging to a Spring Boot service. Pick the lightest one that
fits the codebase. Do not introduce a framework where an aspect will do.

---

## Pattern 1 — Annotation plus AOP (recommended default)

The least invasive way to audit an existing controller. The endpoint gains one
annotation; the capture logic lives in one place.

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Audited {
    String action();
    boolean includePayload() default false;
}
```

```java
@Aspect
@Component
public class AuditAspect {

    private final AuditPublisher publisher;

    @Around("@annotation(audited)")
    public Object capture(ProceedingJoinPoint pjp, Audited audited) throws Throwable {
        AuditRecord record = AuditRecord.start(audited.action(), currentPrincipal());
        try {
            Object result = pjp.proceed();
            record.succeeded();
            return result;
        } catch (Throwable t) {
            record.failed(t);
            throw t;
        } finally {
            publisher.publish(record);   // async, never blocks
        }
    }
}
```

Why it works: the audit is out of band. The transaction commits or rolls back on its
own schedule; the record is published on a separate executor.

---

## Pattern 2 — Feign interceptor for outbound calls

Inbound auditing tells you what the service received. It does not tell you what it sent
to another service. If the codebase uses Feign, add a request interceptor.

```java
@Bean
public RequestInterceptor auditFeignInterceptor(AuditPublisher publisher) {
    return template -> publisher.publishOutbound(
        template.method() + " " + template.path(),
        template.headers()
    );
}
```

Capture method, path, status and correlation id. Never capture the body wholesale —
payloads carry tokens and personal data.

---

## Pattern 3 — Servlet filter for a catch-all baseline

Use when you need coverage of every request including ones that never reach a
controller (security rejections, 404s, malformed requests).

```java
@Component
public class AuditFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest req,
                                    HttpServletResponse res,
                                    FilterChain chain) throws ServletException, IOException {
        String correlationId = UUID.randomUUID().toString();
        MDC.put("correlationId", correlationId);
        try {
            chain.doFilter(req, res);
        } finally {
            publisher.publish(AuditRecord.of(req, res, correlationId));
            MDC.remove("correlationId");
        }
    }
}
```

A filter gives you "something happened" evidence. It does not know the business meaning
of the operation — that still needs Pattern 1 on the endpoints that matter.

---

## Pattern 4 — Domain events for business-level audit

When the auditable fact is a business event ("policy issued", "claim approved") rather
than an HTTP call, publish a domain event and audit the listener.

```java
public record PolicyIssued(String policyId, String actor, Instant at) {}

@Component
class PolicyIssuedAuditor {
    @EventListener
    void on(PolicyIssued e) {
        publisher.publish(AuditRecord.of(e));
    }
}
```

This survives refactoring of the HTTP layer and reads well in an audit review, because
the record says what the business did rather than which URL was called.

---

## Choosing

| Situation | Pattern |
|---|---|
| Existing controllers, need targeted audit | 1 |
| Microservices calling each other | 2 |
| Need proof every request was seen | 3 |
| Regulated business events | 4 |

Patterns compose. A mature service typically runs 3 for the baseline, 1 for the
business operations, and 2 for outbound calls.

## Sinks

Keep the sink behind an interface so it can change without touching call sites:
database (JPA/JDBC), message queue (Kafka), append-only file, or memory for tests.
The audit record should never be written inside the business transaction — an audit
write that rolls back with the business change is not an audit trail.
