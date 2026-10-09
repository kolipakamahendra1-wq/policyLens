# Logging and Monitoring Policy
Policy ID: SEC-LOG
Domain: logging

## 1 Audit logging
Services that access customer data must emit audit logs recording who accessed which record and when. (risk: medium; evidence: logging)

## 2 Log retention
Audit logs must be retained for at least 1 year in a central log store. (risk: medium; evidence: logging)

## 3 Sensitive data in logs
Logs must not contain passwords, tokens or full payment card numbers. (risk: high; evidence: logging)
