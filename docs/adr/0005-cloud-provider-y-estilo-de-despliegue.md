# ADR-0005: AWS Cloud Provider & Deployment Strategy

**Date:** 29 May 2026  
**Status:** ACCEPTED  
**Authors:** G04 — BIOMED UMSS  

---

## Context

BIOMED UMSS requires scalable, compliant infrastructure:
- Asynchronous processing of cytogenetic images
- HIPAA Security Rule (§164.312) + 21 CFR Part 11 compliance
- Sub-500ms API latency for real-time karyotype validation
- Audit trail integrity with hash chains

---

## Decision

### **Selected: AWS**

#### Cloud Provider Rationale
- HIPAA-eligible with Business Associate Agreement (BAA)
- Regional availability: `us-east-1` (Ohio) primary; `us-east-2` (Virginia) DR
- Data residency: Complies with Bolivian sovereignty requirements

#### Architecture Mapping

| Layer | AWS Service | Justification |
|---|---|---|
| **API Gateway** | API Gateway + ALB | Horizontal scaling, WAF |
| **Backend** | ECS (Fargate) | Containerized FastAPI, no infra management |
| **Queue** | SQS | Async task distribution (Celery compatible) |
| **ML Inference** | SageMaker | Pre-trained model hosting, auto-scaling |
| **Database** | RDS PostgreSQL | ACID compliance, encrypted (AES-256) |
| **File Storage** | S3 | Versioning, lifecycle policies, encryption |
| **Logging** | CloudWatch | Audit logs, 5-year retention |
| **Auth** | Cognito + IAM | MFA, role-based access (RBAC) |

#### Deployment Strategy

```
Load Balancer (ALB)
    ↓
ECS Fargate Cluster:
  ├─ FastAPI Backend (2-10 replicas)
  ├─ Celery Workers (1-5 replicas)
  └─ SageMaker Endpoint (auto-scaling)
    ↓
RDS PostgreSQL (Multi-AZ)
S3 (versioned)
CloudWatch + X-Ray (audit)
```

**CI/CD:** CodePipeline + GitHub Actions  
**Deployment:** Blue-green (ECS)

---

## Consequences

### ✅ Positive
- **Scalability:** 1→50+ concurrent users without code changes
- **Compliance:** Automated HIPAA audit logging
- **Reliability:** 99.95% SLA (multi-AZ RDS + ALB redundancy)
- **Operations:** No on-site DevOps needed
- **Cost Flexibility:** Pay-per-use; $0 if idle

### ⚠️ Negative / Mitigations
- **Vendor lock-in:** Mitigated with Terraform IaC
- **Cost unpredictability:** Mitigated with budget alerts + reserved instances
- **Latency:** us-east-1 ~200ms from Bolivia; acceptable for medical use
- **Compliance burden:** Mitigated with automated scanning (AWS Config, Security Hub)

### 💰 Estimated Costs
- Development: $200–500/month
- Production (baseline): $2,000–3,500/month
- DR/Backup: +$500/month

---

## Alternatives Considered

| Option | Pros | Cons | Decision |
|---|---|---|---|
| **Google Cloud** | Strong ML/AI | Weak HIPAA LATAM support | ❌ Rejected |
| **Azure** | HIPAA-eligible | 50% more expensive | ❌ Rejected |
| **On-Premise** | Full control | $150K CapEx, 2 FTE DevOps | ❌ Rejected |

---

## Trade-offs Analyzed

### Trade-off 1: Auto-scaling vs Cost Control
- **Decision:** 20% reserved + 80% on-demand
- **Rationale:** Peaks at 2 PM UTC (10x baseline load)
- **Risk:** Bills spike 30% in busy weeks → Mitigated with budget alerts

### Trade-off 2: Encryption vs Performance
- **Decision:** Always encrypt (AES-256 RDS, TLS 1.2)
- **Latency overhead:** <2% (acceptable; compliance is non-negotiable)

### Trade-off 3: Multi-region Redundancy vs Cost
- **Decision:** Primary us-east-1; snapshot backup us-east-2 (not live-live)
- **RTO:** 4 hours (acceptable for non-critical medical use)
- **Rationale:** Live-live would 2× costs

---

## References

- AWS Well-Architected Framework (Security Pillar)
- HIPAA Security Rule (45 CFR §164.312)
- 21 CFR Part 11 (Electronic Records)
- ADR-0002 (Async Pipeline)
- ADR-0003 (CHN Anonymization)
- FSD §4.2 (Infrastructure Requirements)

---

**Status:** ACCEPTED for release/2.0.0 Final Defense
