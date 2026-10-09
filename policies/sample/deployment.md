# Deployment Policy
Policy ID: ENG-DEPLOY
Domain: deployment

## 1 Pipelines
Production deployments must go through the approved CI/CD pipeline with automated tests. (risk: medium; evidence: deployment)

## 2 Rollback
Every production release must have a documented rollback plan. (risk: medium; evidence: deployment)

## 3 Progressive delivery
Changes to customer-facing services should use canary or staged rollout where possible.
