# Marathon Registration & Marketing Automation Platform — Setup Guide

Welcome to the **Marathon Registration & Marketing Automation Platform** setup guide. This enterprise-grade platform combines Next.js 14, FastAPI (Python 3.11+), PostgreSQL, Razorpay, Zoho CRM, WhatsApp Cloud API, and n8n automation.

- **GitHub Repository**: [https://github.com/JeevananthanV/marathon-platform](https://github.com/JeevananthanV/marathon-platform)
- **Author**: Jeevananthan V

---

## 📋 System Prerequisites

- **Docker & Docker Compose** (Recommended for fastest local run)
- Or manually:
  - **Python**: 3.11+
  - **Node.js**: v18.17+ (or v20+)
  - **PostgreSQL**: 15+

---

## 📥 1. Clone the Repository

```bash
git clone https://github.com/JeevananthanV/marathon-platform.git
cd marathon-platform
```

---

## 🐳 2. Quickstart with Docker Compose (Recommended)

1. Copy environment variable templates:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

2. Build and run containers:
```bash
docker-compose up --build
```

- **Frontend Application**: `http://localhost:3000`
- **FastAPI OpenAPI Docs**: `http://localhost:8000/api/v1/docs`
- **API Health Check**: `http://localhost:8000/api/health`

---

## ⚙️ 3. Manual Local Setup

### Backend (FastAPI)

1. Navigate to backend and create virtual environment:
```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1
# Linux/macOS
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure `backend/.env`:
```env
PROJECT_NAME="Marathon Platform"
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/marathon_db
SECRET_KEY=marathon_super_secret_key_32chars_min
RAZORPAY_KEY_ID=rzp_test_xxxx
RAZORPAY_KEY_SECRET=your_razorpay_secret
WHATSAPP_TOKEN=your_meta_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
ZOHO_CLIENT_ID=your_zoho_id
ZOHO_CLIENT_SECRET=your_zoho_secret
N8N_WEBHOOK_URL=http://localhost:5678/webhook/marathon-drip
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Launch backend server:
```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend (Next.js 14)

1. Navigate to frontend:
```bash
cd ../frontend
```

2. Configure `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_xxxx
```

3. Install dependencies and start development server:
```bash
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🧪 4. Running Automated Tests

```bash
cd backend
python -m pytest
```

---

## 🛠️ Troubleshooting

- **Database Connection Refused**: Ensure PostgreSQL is running on port 5432 or use `docker-compose up db`.
- **Razorpay Signature Mismatch**: Verify `RAZORPAY_KEY_SECRET` matches your test webhook secret exactly.
