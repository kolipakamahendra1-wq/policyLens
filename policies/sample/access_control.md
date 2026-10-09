# Access Control Policy
Policy ID: SEC-ACCESS
Domain: access_control

## 1 Purpose
This policy defines how access to systems and data is granted, reviewed and revoked.

## 2.1 Least privilege
Access to production systems must be granted through IAM roles scoped to least privilege. (risk: high; evidence: iam)
Shared or generic accounts are prohibited for human users.

## 2.2 Authentication
Administrative access must require multi-factor authentication (MFA). (risk: high; evidence: iam)

## 2.3 Access reviews
Access to systems that store customer data must be reviewed at least quarterly by the data owner. (risk: medium; evidence: iam)
