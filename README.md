# Marathon Registration & Marketing Automation Platform

A high-performance, mobile-first marathon event registration and marketing automation engine built with Next.js, FastAPI, PostgreSQL, Razorpay, Zoho CRM, WhatsApp Cloud API, and n8n.

---

## 🏗️ Architecture Overview

- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, responsive mobile-first architecture.
- **Backend**: FastAPI (Python 3.11+), Pydantic v2 Settings, SQLAlchemy 2.0 (Async), Alembic migrations.
- **Database**: PostgreSQL (with asyncpg driver in production, aiosqlite for local testing).
- **Integrations (Modular & Decoupled)**:
  - **Razorpay**: Order creation, server-side signature verification & idempotent webhook processing.
  - **Zoho CRM**: Automatic Contact & Deal upsert with OAuth2 token manager.
  - **WhatsApp Cloud API**: Instant registration ticket and digital bib issuance.
  - **n8n Automation Engine**: Outgoing webhook triggers for scheduled race drip reminders (T-30, T-7, T-1, T+1).

---

## 📁 Project Structure

```
marathon-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/       # API endpoints (health, categories, registrations, payments, webhooks)
│   │   ├── core/                   # Config, security, logging
│   │   ├── db/                     # Async session & base metadata
│   │   ├── integrations/           # Third-party adapters (Razorpay, Zoho, WhatsApp, n8n)
│   │   ├── models/                 # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/               # Registration & payment business logic
│   │   └── main.py                 # FastAPI application factory & middleware
│   ├── alembic/                    # Database migrations
│   ├── tests/                      # Automated test suite (pytest)
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Backend environment template
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router pages
│   │   ├── components/             # Reusable UI & section components
│   │   ├── hooks/                  # Custom React hooks (useUTM, useRazorpay)
│   │   ├── lib/api.ts              # Type-safe API client
│   │   └── types/                  # TypeScript interfaces
│   ├── package.json
│   ├── tailwind.config.ts
│   └── .env.example
│
├── n8n/                            # n8n marketing workflow JSON exports
│   └── workflows/
├── docker-compose.yml              # Local multi-container development stack
└── README.md
```

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- PostgreSQL (or Docker)

### 2. Backend Setup

```bash
cd backend

# 1. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env

# 4. Run database migrations
python -m alembic upgrade head

# 5. Start the backend development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be running at: `http://localhost:8000`
- Swagger UI / OpenAPI docs: `http://localhost:8000/api/v1/docs`
- Health Check: `http://localhost:8000/api/health`

### 3. Frontend Setup

```bash
cd frontend

# 1. Configure environment variables
cp .env.example .env.local

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

Frontend will be running at: `http://localhost:3000`

---

## 🧪 Testing

To run the backend automated test suite:

```bash
cd backend
python -m pytest
```

---

## 🛡️ Security & Integrity

- **Environment Secrets**: All secrets and API credentials are kept strictly in `.env` files and ignored in `.gitignore`.
- **Payment Verification**: Razorpay payment signatures are strictly verified server-side with HMAC-SHA256.
- **Webhook Idempotency**: Webhook events are deduplicated against unique transaction and order records.
- **Input Validation**: All requests are rigorously validated with Pydantic schemas and sanitized.
