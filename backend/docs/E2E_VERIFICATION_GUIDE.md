# End-to-End Multi-Channel Integration & Verification Guide (Phase 4F)

This document provides complete instructions, architecture flows, testing scenarios, failure isolation guarantees, and execution commands for the full marathon registration and marketing automation platform.

---

## 1. Clean Test Environment Architecture

The system operates in **Mock Mode** by default (`INTEGRATIONS_MOCK_MODE=true`), preventing real network requests to third-party services:

| Component | Default Mode | Behavior in Mock Mode |
| :--- | :--- | :--- |
| **Database** | Isolated SQLite / Test DB | All data is created and cleaned between tests using transactional fixtures |
| **Razorpay** | Test Mode (`rzp_test_...`) | Generates test orders and validates cryptographically using HMAC-SHA256 |
| **Zoho CRM** | Mock Client (`ZOHO_MOCK_MODE=true`) | Simulates OAuth2 token caching, search-before-create, and returns `mock_zoho_rec_<id>` |
| **WhatsApp** | Mock Client (`WHATSAPP_MOCK_MODE=true`) | Renders 6 official Meta templates and returns `mock_wamid_<id>` without cellular dispatch |
| **n8n Automation**| Mock Client (`N8N_MOCK_MODE=true`) | Dispatches automation payloads and validates `X-N8N-Webhook-Secret` auth |
| **Meta CAPI** | Mock Client (`META_CAPI_MOCK_MODE=true`)| Hashes customer PII with SHA-256 and returns `MOCK_META_EVENT_<event>_<id>` |

---

## 2. Complete Synthetic Runner Journey (Steps 1–20)

```
1. Facebook Ad Click (utm_source=facebook&utm_medium=paid_social&utm_campaign=marathon_2026&utm_content=10k_ad)
        ↓
2. Landing Page View (Tracked via Meta CAPI PageView event)
        ↓
3. 10K Category Selected (Tracked via Meta CAPI ViewContent event)
        ↓
4. Registration Initiated (Name: Demo Runner, Email: demo.runner@example.com, Phone: +919999999999)
        ↓
5. Meta CAPI Lead Event generated & logged
        ↓
6. Razorpay Order Created (Status: PENDING)
        ↓
7. Razorpay Test Mode Checkout Initiated (Meta CAPI InitiateCheckout event)
        ↓
8. Payment Succeeded (Signature verified via HMAC-SHA256)
        ↓
9. Atomic BIB Allocation (e.g. 10K-1001) & Registration CONFIRMED
        ↓
10. Digital Race Pass Generated (QR code, BIB, category, runner details)
        ↓
11. Zoho CRM Synchronization (Lead/Deal created with deterministic mock ID)
        ↓
12. WhatsApp Registration Confirmation & Digital Pass delivered (Mock Mode)
        ↓
13. n8n Automation Engine Dispatched (registration.confirmed, payment.captured, bib.assigned)
        ↓
14. Meta CAPI Purchase Event tracked (Value: ₹699, Currency: INR, Deduplication Event ID)
        ↓
15. Meta CAPI CompleteRegistration Event tracked (Hashed PII)
        ↓
16. 7-Day Pre-Marathon Reminder Simulated (/api/v1/automation/simulate-event)
        ↓
17. 1-Day Pre-Marathon Instructions Simulated (/api/v1/automation/simulate-event)
        ↓
18. Event-Day Instructions & BIB Reminder Simulated (/api/v1/automation/simulate-event)
        ↓
19. Administrative Overview Queryable (/api/v1/admin/overview)
        ↓
20. Cross-Table Consistency Verified across Registrations, Participants, Payments, and Integration Logs
```

---

## 3. Failure Isolation Guarantees

Every third-party integration is wrapped in non-blocking try/except blocks. **A failure in Zoho CRM, WhatsApp, n8n, or Meta CAPI NEVER impacts the customer checkout experience or database state:**

- **Scenario A (Meta CAPI Fails / 500)**: Payment succeeds, Registration remains `CONFIRMED`, error is recorded with `status="FAILED"` in `integration_logs`, and can be retried via `retry_failed_meta_events()`.
- **Scenario B (Zoho CRM Fails / Timeout)**: Payment succeeds, Registration remains `CONFIRMED`, failure logged and retried via `retry_failed_zoho_sync()`.
- **Scenario C (WhatsApp Fails / Network Error)**: Payment succeeds, Registration remains `CONFIRMED`, digital pass is accessible via web, and message can be redelivered via `retry_failed_whatsapp_messages()`.
- **Scenario D (n8n Engine Unavailable)**: Core registration and checkout remain 100% operational.

---

## 4. Idempotency & Security Hardening

- **Deduplication**: Repeated payment verification or webhook calls return the existing confirmation without double-charging or duplicate BIB allocations.
- **Zoho Search-Before-Create**: Identifies existing participants by email and updates their record without creating duplicate deals.
- **Meta Event ID Matching**: Client and server send deterministic `event_id` strings (`purchase_{registration_code}_{payment_id}`) to prevent double-counting conversions.
- **Signature Authentication**: Rejects tampered Razorpay payment and webhook signatures with HTTP 400.
- **SQL Injection / XSS Sanitization**: Input fields are validated by Pydantic v2 schemas and sanitized before storage.
- **Secret Protection**: API endpoints never leak credentials (`RAZORPAY_KEY_SECRET`, `ZOHO_CLIENT_SECRET`, `WHATSAPP_ACCESS_TOKEN`, `META_ACCESS_TOKEN`, `N8N_WEBHOOK_SECRET`).

---

## 5. Operations Visibility & Safe Demo Reset

### Operations Overview
```bash
GET /api/v1/admin/overview
```
Returns total registrations, confirmed count, revenue, category slot usage, and integration health metrics.

### Participant Audit
```bash
GET /api/v1/admin/registrations
```
Returns complete participant information, payment status, UTM attribution, and integration audit log counts.

### Safe Demo Reset
```bash
POST /api/v1/admin/demo-reset
```
*Note: This endpoint is strictly forbidden in production environments (`DEBUG=false` and `INTEGRATIONS_MOCK_MODE=false`).* It safely removes demo registrations, participants, payments, and integration logs, resetting category counters to 0.

---

## 6. How to Run Locally

### Start Backend (FastAPI)
```bash
cd backend
.\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/health`

### Start Frontend (React + Vite)
```bash
cd frontend
npm run dev
```
- Web Application: `http://localhost:5173`

### Run Complete Automated Test Suite (89 Tests)
```bash
cd backend
.\venv\Scripts\python -m pytest -v
```
