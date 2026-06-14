# Security Evaluation — RBAC System

## Threat Model

### Assets
- User credentials and identity data
- Role and permission assignments controlling access to resources
- Audit logs (tamper-evidence, forensic value)
- System configuration and secrets

### Threat Actors
- **Unauthenticated external attacker**: credential stuffing, brute force, enumeration
- **Authenticated low-privilege user**: privilege escalation, horizontal access to other users' data
- **Compromised token**: JWT theft, replay attacks
- **Malicious insider / compromised Admin**: unauthorized privilege assignment, log manipulation
- **Automated bots**: DoS, spray attacks

### Trust Boundaries
- Internet → Django API (CORS, rate limiting)
- JWT boundary: client holds short-lived access token; refresh token rotates and is blacklisted on logout
- DB boundary: ORM parameterized queries only

---

## OWASP Top 10 Mapping

| # | OWASP Risk | Mitigation in this system |
|---|---|---|
| A01 | **Broken Access Control** | Custom DRF RBAC permission classes (`HasRBACPermission`, per-endpoint `rbac_permission()`) enforce `resource.action` granular checks. Principle of least privilege in default role assignments. ProtectedRoute guards in frontend. |
| A02 | **Cryptographic Failures** | Argon2 password hashing (memory-hard, resistant to GPU cracking). JWT signed with HS256 SECRET_KEY stored in env. HTTPS-ready settings (`SECURE_SSL_REDIRECT`, HSTS) to be enabled in production. No plaintext secrets committed. |
| A03 | **Injection** | Django ORM with parameterized queries used exclusively — no raw SQL. DRF serializers validate and coerce all input. No shell commands constructed from user input. |
| A04 | **Insecure Design** | Explicit permission matrix with default-deny; new users get only the minimal `User` role. Audit logging on all auth and resource-access events. Token blacklisting on logout enforces session termination. |
| A05 | **Security Misconfiguration** | Secrets via `django-environ` / `.env` file. `DEBUG=False` enforced in production. Security headers set: `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`, `SECURE_REFERRER_POLICY`. CORS restricted to listed origins. Django `check` framework validates config. |
| A06 | **Vulnerable & Outdated Components** | Pinned dependencies in `requirements.txt` and `package.json`. Monitor with `pip-audit` / `npm audit`. |
| A07 | **Identification & Authentication Failures** | Account lockout after N failed attempts (configurable). JWT access tokens are short-lived (15 min default). Refresh tokens rotate and are blacklisted on logout via `rest_framework_simplejwt.token_blacklist`. Password strength enforced via Django validators. Email uniqueness enforced. |
| A08 | **Software & Data Integrity Failures** | JWT signature verification on every request. No deserialization of untrusted objects. Dependency integrity via pinned versions. |
| A09 | **Security Logging & Monitoring Failures** | `AuditMiddleware` logs every authenticated API request. Auth events (login, failure, lockout, logout, register) explicitly logged with IP, user, timestamp. Admin/Auditor report endpoints expose login failure patterns and denied-access summaries. |
| A10 | **Server-Side Request Forgery** | No outbound HTTP requests made by the server from user-supplied URLs. |

---

## Additional Security Controls

### Rate Limiting
- Login endpoint: 5 requests/minute per IP (`LoginRateThrottle`)
- Registration endpoint: 10 requests/minute per IP (`RegisterRateThrottle`)
- General authenticated endpoints: 1000/day
- Anonymous endpoints: 100/day

### CSRF Considerations
This system uses JWT in the `Authorization: Bearer` header (not cookies), which **is not vulnerable to CSRF** by design. CSRF tokens are not required for API calls. If the frontend is ever migrated to cookie-based auth, `SameSite=Strict` and CSRF middleware must be re-enabled.

### Security Headers
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
```
In production, add:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

---

## Ethical Considerations

### Privacy of Audit Logs and PII
Audit logs contain **personally identifiable information** (email addresses, IP addresses) and **behavioral data** (every API call made by authenticated users). This creates obligations:

- **Legitimate purpose**: Logs must only be collected for security monitoring, incident response, and compliance. They should not be used to surveil employees for performance management or other non-security purposes.
- **Data minimization**: The current schema captures the minimum necessary: identity, timestamp, action, result, and IP. Free-form `details` fields should not be used to capture request/response bodies containing sensitive data (passwords, health data, etc.).
- **Access control on logs**: Audit endpoints are restricted to `Admin` and `Auditor` roles. The Auditor role is read-only and cannot modify data.

### Retention Policy
Audit logs should not be retained indefinitely. Recommended practices:
- **90–365 days** for operational security monitoring
- **7 years** only if required by specific compliance frameworks (HIPAA, PCI-DSS, SOX)
- Implement a scheduled `cleanup_old_logs` management command after determining the appropriate retention period
- Logs containing IP addresses may be subject to GDPR/CCPA data retention rules

### Transparency
Users whose actions are logged should be informed via a privacy policy or terms of service that access events are recorded for security purposes.

### Potential Misuse and Safeguards
| Risk | Safeguard |
|---|---|
| Admin uses audit logs to monitor specific users without cause | Limit `audit.read` to a dedicated Auditor role separate from Admin; require a second-person approval for targeted log reviews in high-sensitivity deployments |
| Admin assigns themselves additional permissions | Log all role/permission assignment events with `assigned_by`; consider requiring two-person integrity for Admin role changes |
| Audit logs altered to hide evidence | Logs are append-only via the API (no PATCH/DELETE on AccessLog via REST); database-level immutability (e.g., append-only DB user, write-once storage) should be added for high-assurance deployments |
| IP address data used for geolocation beyond security scope | Establish a policy document specifying IP data is used only for security rate limiting and anomaly detection |

### Principle of Least Privilege in Default Roles
- **User**: Can only read and update their own profile. Cannot see other users, roles, permissions, or logs.
- **Auditor**: Read-only access to users, roles, permissions, and audit data. Cannot modify any data.
- **Admin**: Full access, but all actions are logged with the `assigned_by` field for accountability.

---

## Production Hardening Checklist

- [ ] Set `DEBUG=False` and regenerate `SECRET_KEY`
- [ ] Enable `SECURE_SSL_REDIRECT=True`
- [ ] Set `SESSION_COOKIE_SECURE=True` and `CSRF_COOKIE_SECURE=True`
- [ ] Enable `SECURE_HSTS_SECONDS=31536000`
- [ ] Use PostgreSQL in production (not SQLite)
- [ ] Run behind a reverse proxy (nginx) with TLS termination
- [ ] Set `CORS_ALLOWED_ORIGINS` to production frontend domain only
- [ ] Run `pip-audit` and `npm audit` in CI pipeline
- [ ] Configure a log retention and archival policy
- [ ] Set up alerting on `result=denied` spikes and lockout events
- [ ] Rotate `SECRET_KEY` if it is ever suspected to be leaked (this invalidates all JWTs)
