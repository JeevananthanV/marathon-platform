# Production Deployment & Operations Runbook

This runbook covers the end-to-end deployment, container orchestration, SSL/TLS configuration, database backup/recovery, and monitoring for the Marathon Registration & Marketing Automation Platform.

---

## 1. System Requirements & Architecture

### Recommended Server Specifications
- **Operating System:** Ubuntu 22.04 LTS / 24.04 LTS
- **CPU:** 2 vCPUs minimum (4 vCPUs recommended for >10,000 peak registrations)
- **RAM:** 4 GB minimum (8 GB recommended)
- **Disk Storage:** 40 GB NVMe SSD with automated log rotation
- **Network:** 1 Gbps port with static public IPv4

### Container Topology
```
                  Internet / Users (HTTPS:443)
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │       Nginx Alpine Reverse Proxy & SPA      │
        │   (Port 80/443, SSL/TLS, Caching, Headers)  │
        └──────────────────────┬──────────────────────┘
                               │
                Proxy /api/* to http://backend:8000
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │         FastAPI Backend Application         │
        │  (Python 3.12, Uvicorn, Non-root User)     │
        └──────────────────────┬──────────────────────┘
                               │
                   SQLAlchemy 2.0 AsyncPG
                               │
                               ▼
        ┌─────────────────────────────────────────────┐
        │         PostgreSQL 16 Relational DB         │
        │      (Persistent Volume: pgdata)            │
        └─────────────────────────────────────────────┘
```

---

## 2. Docker & Server Preparation

### Install Docker & Compose on Ubuntu
```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl apt-transport-https ca-certificates gnupg lsb-release

# 2. Add Docker official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 3. Add repository and install Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 4. Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker
```

---

## 3. Environment Configuration

### Configure Production Variables
```bash
# Clone the repository
git clone https://github.com/your-org/marathon-platform.git /opt/marathon
cd /opt/marathon

# Copy production template
cp backend/.env.production.example backend/.env.production
cp frontend/.env.production.example frontend/.env.production
```

Edit `backend/.env.production`:
- Set strong `POSTGRES_PASSWORD`.
- Set production domain in `CORS_ORIGINS`.
- Configure `INTEGRATIONS_MOCK_MODE=true` initially for staging verification, and `false` for live production.

---

## 4. Build & Deployment Execution

### Start Full Stack in Production Mode
```bash
# Validate Compose configuration
docker compose -f docker-compose.yml -f docker-compose.prod.yml config

# Build and start containers in detached mode
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Inspect Container Health & Status
```bash
docker compose ps
```
Expected output:
```
NAME                 IMAGE                   STATUS                    PORTS
marathon_db          postgres:16-alpine      Up (healthy)              0.0.0.0:5432->5432/tcp
marathon_backend     marathon-backend        Up (healthy)              0.0.0.0:8000->8000/tcp
marathon_frontend    marathon-frontend       Up (healthy)              0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

---

## 5. SSL/TLS Certificate Setup (Certbot & Let's Encrypt)

### Option A: Certbot on Host
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL Certificate
sudo certbot certonly --standalone -d marathon.yourdomain.com -d www.marathon.yourdomain.com

# Mount certificates into frontend container in docker-compose.prod.yml:
# - /etc/letsencrypt:/etc/letsencrypt:ro
```

### Automatic Certificate Renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Add cron job for bi-monthly renewal
sudo crontab -e
# 0 3 1,15 * * certbot renew --quiet && docker compose -f /opt/marathon/docker-compose.yml exec frontend nginx -s reload
```

---

## 6. Database Backup & Disaster Recovery

### Automated Daily PostgreSQL Backup
Create backup script at `/opt/marathon/scripts/db_backup.sh`:
```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/marathon/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="$BACKUP_DIR/marathon_db_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

# Dump and compress database
docker compose -f /opt/marathon/docker-compose.yml exec -T db pg_dump -U marathon_admin marathon_db | gzip > "$FILENAME"

# Retain only last 30 days of backups
find "$BACKUP_DIR" -type f -name "marathon_db_*.sql.gz" -mtime +30 -delete

echo "Database backup completed: $FILENAME"
```
Make executable and schedule in cron:
```bash
chmod +x /opt/marathon/scripts/db_backup.sh
# Cron: Daily at 02:00 UTC
# 0 2 * * * /opt/marathon/scripts/db_backup.sh >> /var/log/marathon_backup.log 2>&1
```

### Point-in-Time Restore Procedure
```bash
# 1. Uncompress backup file
gunzip -c /opt/marathon/backups/marathon_db_YYYYMMDD_HHMMSS.sql.gz > /tmp/restore.sql

# 2. Restore into database container
docker compose -f /opt/marathon/docker-compose.yml exec -T db psql -U marathon_admin -d marathon_db < /tmp/restore.sql

# 3. Clean up temporary uncompressed file
rm /tmp/restore.sql
```

---

## 7. Monitoring & Operational Inspection

### Health Check Inspection
- Backend Health: `curl -f http://localhost:8000/api/health`
- Operations Metrics: `curl -f http://localhost:8000/api/v1/admin/overview`
- Frontend Health: `curl -f http://localhost/healthz`

### Live Log Streaming
```bash
# Stream all logs
docker compose logs -f --tail=100

# Stream backend logs only
docker compose logs -f backend

# Stream payment and integration errors
docker compose logs backend | grep -i -E "error|failed|payment"
```

### Resource Utilization
```bash
docker stats --no-stream
```

---

## 8. Rollback & Troubleshooting Procedures

### Zero-Downtime Rollback to Previous Version
```bash
# Rollback git commit
git checkout <previous-stable-tag>

# Rebuild and restart containers
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Common Issues & Resolution

| Issue | Root Cause | Resolution |
| :--- | :--- | :--- |
| **Backend container exiting with code 1** | Database not yet ready | The backend uses `depends_on: db: condition: service_healthy` to guarantee DB readiness. |
| **502 Bad Gateway from Nginx** | Backend Uvicorn process starting up | Check backend logs: `docker compose logs backend`. Ensure health check passes. |
| **CORS Rejected on Checkout** | Origin missing from `CORS_ORIGINS` | Add exact production domain (including `https://`) in `backend/.env.production`. |
| **Razorpay Signature Mismatch** | Incorrect `RAZORPAY_KEY_SECRET` | Verify matching Secret in Razorpay Dashboard and backend environment file. |

---

## 9. Security Audit Checklist

- [x] **Non-root user execution**: Backend runs as `marathonuser` (UID 1001).
- [x] **Secret protection**: No credentials or `.env` files copied into Docker images.
- [x] **Port isolation**: Database port `5432` only accessible within Docker bridge network in production.
- [x] **Security headers**: `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`, and strict CSP configured in Nginx.
- [x] **Log rotation**: Container log size capped at 20–50MB with 3–5 file retention to prevent disk exhaustion.
- [x] **Deterministic Mock Mode**: Default `INTEGRATIONS_MOCK_MODE=true` ensures 0 unauthorized third-party charges or external network requests.
- [x] **Safe migrations**: `start.sh` executes only `alembic upgrade head` (never destructive drops).
