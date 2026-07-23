# 🚢 Deployment Guide

> *"Resilient. Scalable. Always on."*

---

## 1. Deployment Architecture

```
                         Internet
                            │
                    ┌───────┴───────┐
                    │   Cloudflare   │
                    │  (DNS + DDoS)  │
                    └───────┬───────┘
                            │
                    ┌───────┴───────┐
                    │    Nginx LB    │
                    │  (SSL term)    │
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
      ┌────────────┐ ┌────────────┐ ┌────────────┐
      │  Dashboard │ │ API Server │ │ Scraper    │
      │  (Vercel)  │ │ (K8s Pods) │ │ Fleet (K8s)│
      └────────────┘ └──────┬─────┘ └────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
      ┌────────────┐ ┌────────────┐ ┌────────────┐
      │ PostgreSQL │ │   Redis    │ │  RabbitMQ  │
      │ (RDS/Aurora)│ │ (ElastiCache)│ │ (Amazon MQ)│
      └────────────┘ └────────────┘ └────────────┘
```

### Hosting Options

| Tier | Cost/mo | Description |
|---|---|---|
| **Dev** (single VPS) | ~$50 | Docker Compose on 1 box. 8 vCPU, 16GB RAM, 200GB SSD |
| **Prod** (K8s cluster) | ~$300-500 | 3-node K8s (4 vCPU, 8GB each) + managed DB |
| **Enterprise** (multi-region) | ~$2K+ | Multi-AZ K8s, read replicas, global CDN |

---

## 2. Docker Compose (Dev / Single Server)

```yaml
# deploy/docker-compose.yml
version: '3.9'

services:
  # ─── Infrastructure ───
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: nabu
      POSTGRES_USER: nabu
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nabu"]
      interval: 10s

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redisdata:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: nabu
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    ports:
      - "5672:5672"   # AMQP
      - "15672:15672" # Management UI
    volumes:
      - rabbitmqdata:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmqctl", "status"]
      interval: 10s

  # ─── Scraper Workers (Go) ───
  scraper-twitter:
    build:
      context: ../
      dockerfile: deploy/Dockerfile.scraper
    command: ["nabu-scraper", "--source", "twitter"]
    environment:
      NABU_CONFIG: /etc/nabu/nabu.yaml
    volumes:
      - ./config:/etc/nabu
    depends_on:
      rabbitmq: { condition: service_healthy }
    restart: unless-stopped
    deploy:
      replicas: 3

  scraper-telegram:
    build:
      context: ../
      dockerfile: deploy/Dockerfile.scraper
    command: ["nabu-scraper", "--source", "telegram"]
    environment:
      NABU_CONFIG: /etc/nabu/nabu.yaml
    volumes:
      - ./config:/etc/nabu
      - telegram_sessions:/sessions
    depends_on:
      rabbitmq: { condition: service_healthy }
    restart: unless-stopped
    deploy:
      replicas: 2

  scraper-blockchain:
    build:
      context: ../
      dockerfile: deploy/Dockerfile.scraper
    command: ["nabu-scraper", "--source", "blockchain"]
    environment:
      NABU_CONFIG: /etc/nabu/nabu.yaml
    volumes:
      - ./config:/etc/nabu
    depends_on:
      rabbitmq: { condition: service_healthy }
    restart: unless-stopped
    deploy:
      replicas: 3

  scraper-web:
    build:
      context: ../
      dockerfile: deploy/Dockerfile.scraper
    command: ["nabu-scraper", "--source", "web"]
    environment:
      NABU_CONFIG: /etc/nabu/nabu.yaml
    volumes:
      - ./config:/etc/nabu
    depends_on:
      rabbitmq: { condition: service_healthy }
    restart: unless-stopped
    deploy:
      replicas: 2

  # ─── Intelligence Workers (Python) ───
  intelligence-worker:
    build:
      context: ../
      dockerfile: deploy/Dockerfile.intelligence
    environment:
      NABU_CONFIG: /etc/nabu/nabu.yaml
      LLM_API_KEYS: ${LLM_API_KEYS}
    volumes:
      - ./config:/etc/nabu
    depends_on:
      rabbitmq: { condition: service_healthy }
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    restart: unless-stopped
    deploy:
      replicas: 4

  # ─── API Server ───
  api:
    build:
      context: ../
      dockerfile: deploy/Dockerfile.api
    ports:
      - "8443:8443"
    environment:
      NABU_CONFIG: /etc/nabu/nabu.yaml
      DB_URL: postgresql://nabu:${DB_PASSWORD}@postgres:5432/nabu
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      RABBITMQ_URL: amqp://nabu:${RABBITMQ_PASSWORD}@rabbitmq:5672
    volumes:
      - ./config:/etc/nabu
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    restart: unless-stopped
    deploy:
      replicas: 2

  # ─── Dashboard (Next.js) ───
  dashboard:
    build:
      context: ../dashboard
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: https://nabu.internal:8443/api/v1
      NABU_API_KEY: ${DASHBOARD_API_KEY}
    depends_on:
      - api
    restart: unless-stopped

  # ─── Monitoring ───
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheusdata:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafanadata:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3001:3000"

volumes:
  pgdata:
  redisdata:
  rabbitmqdata:
  telegram_sessions:
  prometheusdata:
  grafanadata:
```

---

## 3. Kubernetes (Production)

### Namespace & Secrets

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nabu

---
apiVersion: v1
kind: Secret
metadata:
  name: nabu-secrets
  namespace: nabu
type: Opaque
stringData:
  db-password: ${DB_PASSWORD}
  redis-password: ${REDIS_PASSWORD}
  rabbitmq-password: ${RABBITMQ_PASSWORD}
  llm-api-keys: '{"anthropic":"sk-ant-...","openai":"sk-...","deepseek":"sk-..."}'
  twitter-keys: '[...]'
  dashboard-api-key: ${DASHBOARD_API_KEY}
```

### API Server Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nabu-api
  namespace: nabu
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nabu-api
  template:
    metadata:
      labels:
        app: nabu-api
    spec:
      containers:
      - name: api
        image: nabu/api:latest
        ports:
        - containerPort: 8443
        env:
        - name: NABU_CONFIG
          value: /etc/nabu/nabu.yaml
        - name: DB_URL
          valueFrom:
            secretKeyRef:
              name: nabu-secrets
              key: db-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: nabu-secrets
              key: redis-url
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: "2"
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8443
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8443
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Auto-scaling for Scrapers

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: scraper-twitter-hpa
  namespace: nabu
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: scraper-twitter
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: rabbitmq_queue_twitter_depth
      target:
        type: AverageValue
        averageValue: 50
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 4. Environment Variables

```bash
# .env.example

# Database
DB_PASSWORD=changeme
DB_URL=postgresql://nabu:${DB_PASSWORD}@localhost:5432/nabu

# Redis
REDIS_PASSWORD=changeme
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379

# RabbitMQ
RABBITMQ_PASSWORD=changeme
RABBITMQ_URL=amqp://nabu:${RABBITMQ_PASSWORD}@localhost:5672

# LLM API Keys (JSON object)
LLM_API_KEYS='{"anthropic":"sk-ant-...","openai":"sk-...","deepseek":"sk-..."}'

# Scraper Credentials
TWITTER_BEARER_TOKS='["AAAA...1","AAAA...2"]'
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=abc123def456
DISCORD_BOT_TOKEN=MTExMjIz...

# Proxy Configuration
PROXY_POOL_URL=http://proxy-manager:8080/pool/next

# Dashboard
DASHBOARD_API_KEY=nbu_dash_abc123
NEXT_PUBLIC_API_URL=https://nabu.internal:8443/api/v1

# JWT Secret (for API auth)
JWT_SECRET=super-secret-key-rotate-monthly

# Optional: Webhook for alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
TELEGRAM_ALERT_BOT_TOKEN=...
```

---

## 5. Monitoring Stack

### Prometheus Metrics Endpoints

| Component | Endpoint | Port |
|---|---|---|
| API Server | `/metrics` | 8443 |
| Scraper Workers | `/metrics` | 9090 (per pod) |
| Intelligence Workers | `/metrics` | 9091 |
| PostgreSQL | `postgres_exporter` | 9187 |
| Redis | `redis_exporter` | 9121 |
| RabbitMQ | plugin | 15692 |

### Grafana Dashboards

| Dashboard | Description |
|---|---|
| **Nabu Overview** | All services, event rates, queue depths, error rates |
| **Scraper Health** | Per-source metrics, rate limits, proxy health |
| **Opportunity Pipeline** | Events in → analyzed → scored → persisted |
| **LLM Cost Tracker** | Tokens used, cost per model, per analysis |
| **Mining Machine Activity** | Wallet actions, tasks completed, gas spent |

### Critical Alerts (PagerDuty / Slack)

| Alert | Condition | Severity |
|---|---|---|
| `ScraperDown` | No scraper heartbeat for 60s | Critical |
| `QueueBacklog` | Any queue depth > 10,000 for 5min | High |
| `HighErrorRate` | Error rate > 5% for 10min | High |
| `LLMProviderDown` | All LLM providers fail in 5min window | Critical |
| `DBSlowQueries` | P95 query time > 500ms for 5min | Medium |
| `NoNewOpportunities` | Zero new opps in 1 hour | Warning |

---

## 6. Backup & Disaster Recovery

| Data | Frequency | Retention | Method |
|---|---|---|---|
| PostgreSQL | Every 6h | 30 days | `pg_dump` → S3 |
| Redis | Snapshot every 1h | 24h | `BGSAVE`, RDB to S3 |
| Configuration | Git | Forever | GitOps (config in repo) |
| Scraper Sessions | Every 24h | 7 days | Tar → S3 |

### Recovery Time Objective

| Failure | RTO | RPO |
|---|---|---|
| Single pod crash | < 30s | Zero (stateless) |
| Database failure | < 15min | < 5min |
| Full region outage | < 2h | < 1h |
| Catastrophic data loss | < 24h | < 6h |

---

## 7. CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy Nabu

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Go tests
        run: make test-go
      - name: Run Python tests
        run: make test-python
      - name: Run Dashboard tests
        run: cd dashboard && npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker images
        run: |
          docker build -t nabu/api:${GITHUB_SHA} -f deploy/Dockerfile.api .
          docker build -t nabu/scraper:${GITHUB_SHA} -f deploy/Dockerfile.scraper .
          docker build -t nabu/dashboard:${GITHUB_SHA} -f dashboard/Dockerfile .
      - name: Push to registry
        run: |
          docker push nabu/api:${GITHUB_SHA}
          docker push nabu/scraper:${GITHUB_SHA}
          docker push nabu/dashboard:${GITHUB_SHA}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to K8s
        run: |
          kubectl set image deployment/nabu-api api=nabu/api:${GITHUB_SHA}
          kubectl set image deployment/scraper-twitter scraper=nabu/scraper:${GITHUB_SHA}
          kubectl set image deployment/dashboard dashboard=nabu/dashboard:${GITHUB_SHA}
          kubectl rollout status deployment/nabu-api
```
