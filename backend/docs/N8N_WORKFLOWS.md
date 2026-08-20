# n8n Workflow Automation Architecture & Deployment Guide

This guide details the integration of **n8n** with the Marathon Platform as an external workflow and event orchestration engine.

---

## 1. Architectural Principles

1. **Source of Truth**: The FastAPI backend and PostgreSQL database remain the single source of truth for all registrations, payments, participant records, and BIB number allocations.
2. **Decoupled Orchestration**: n8n coordinates external asynchronous jobs (WhatsApp reminders, CRM syncs, email dispatches, reporting) triggered by backend events.
3. **Non-Blocking Safety**: If n8n is offline, down, or unreachable, registrations and payments still complete with 100% success.
4. **Secret Authentication**: Webhooks communicating between backend and n8n are protected by `X-N8N-Webhook-Secret`.

---

## 2. Configuration & Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `N8N_ENABLED` | `true` | Enables or disables n8n webhook dispatches |
| `N8N_MOCK_MODE` | `true` | Enables local deterministic mock mode (zero external HTTP traffic) |
| `N8N_BASE_URL` | `http://localhost:5678` | Base URL of the n8n server instance |
| `N8N_WEBHOOK_SECRET` | `marathon_n8n_secret_2026` | Shared secret header required on all automation endpoints |

---

## 3. Workflow Blueprints Directory

All pre-configured, importable workflow blueprints reside in [`workflows/n8n/`](file:///c:/Users/Raghavi/Desktop/MARATHON/backend/workflows/n8n/):

| Blueprint | Trigger | Description |
| :--- | :--- | :--- |
| `registration-confirmed.json` | Webhook (`/webhook/registration-confirmed`) | Validates secret, triggers WhatsApp confirmation and Zoho CRM sync. |
| `payment-captured.json` | Webhook (`/webhook/payment-captured`) | Validates secret, triggers payment confirmation notification. |
| `bib-assigned.json` | Webhook (`/webhook/bib-assigned`) | Validates secret, triggers digital entry pass & BIB dispatch. |
| `reminder-7-days.json` | Cron (`0 9 * * *`) + Webhook | Fetches CONFIRMED runners, dispatches 7-day pre-race reminders. |
| `reminder-1-day.json` | Cron (`0 10 * * *`) + Webhook | Fetches CONFIRMED runners, dispatches 1-day instructions. |
| `reminder-event-day.json` | Cron (`0 4 * * *`) + Webhook | Fetches CONFIRMED runners, dispatches race-morning reporting details. |

---

## 4. Running n8n Locally

### Option A: Via Docker Compose (Recommended)
```bash
docker-compose -f docker-compose.n8n.yml up -d
```
Open **http://localhost:5678** in your browser to access the n8n editor.

### Option B: Via npm / npx
```bash
npx n8n
```

---

## 5. Importing Workflows into n8n

1. Log in to your local n8n console (`http://localhost:5678`).
2. Click on **Workflows** in the sidebar.
3. Click **Add Workflow** -> Click the **...** menu -> **Import from File**.
4. Select any JSON blueprint from `backend/workflows/n8n/`.
5. Set the workflow to **Active**.
