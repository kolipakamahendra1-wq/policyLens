# Security and Encryption Standard
Policy ID: SEC-CRYPTO
Domain: encryption

## 1 Encryption at rest
Data stores containing Confidential or Restricted data must be encrypted at rest using AES-256 with keys managed in KMS. (risk: high; evidence: encryption)

## 2 Encryption in transit
All network traffic carrying customer data must use TLS 1.2 or higher. (risk: high; evidence: encryption)

## 3 Secrets
Secrets and credentials must be stored in a secrets manager and never committed to source control. (risk: high; evidence: encryption)
