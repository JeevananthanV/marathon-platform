# 🏃 Marathon Registration & Marketing Automation Platform

[![Repository](https://img.shields.io/badge/GitHub-JeevananthanV%2Fmarathon--platform-blue?logo=github)](https://github.com/JeevananthanV/marathon-platform)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com)

A high-performance, mobile-first marathon event registration and marketing automation engine built with Next.js, FastAPI, PostgreSQL, Razorpay, Zoho CRM, WhatsApp Cloud API, and n8n.

---

## 🔗 Repository Links

| Detail | Link |
|---|---|
| **GitHub Repository** | [https://github.com/JeevananthanV/marathon-platform](https://github.com/JeevananthanV/marathon-platform) |
| **Author** | [Jeevananthan V](https://github.com/JeevananthanV) |
| **API Docs (Swagger)** | `http://localhost:8000/api/v1/docs` |
| **API Health Check** | `http://localhost:8000/api/health` |
| **Frontend Portal** | `http://localhost:3000` |

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
├── n8n/                            # Workflow JSONs for drip campaigns & webhooks
├── docs/                           # Architecture decision records & API specs
├── docker-compose.yml              # Local multi-container development environment
└── docker-compose.prod.yml         # Production multi-container deployment
```

---

## 🚀 Quickstart & Setup

### Clone Repository

```bash
git clone https://github.com/JeevananthanV/marathon-platform.git
cd marathon-platform
```

### 1. Docker Compose (Recommended)

To launch the complete stack with local PostgreSQL:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

docker-compose up --build
```

- Frontend: `http://localhost:3000`
- Backend API Docs: `http://localhost:8000/api/v1/docs`

---

### 2. Manual Backend Setup

```bash
cd backend

# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env

# 4. Apply migrations
alembic upgrade head

# 5. Start dev server
uvicorn app.main:app --reload --port 8000
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

---

## 👨‍💻 Author

**Jeevananthan V** — [@JeevananthanV](https://github.com/JeevananthanV)

## License

MIT
