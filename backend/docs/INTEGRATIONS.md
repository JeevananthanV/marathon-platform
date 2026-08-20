# Marathon Registration Platform — Integration Architecture & Guide (Phase 4A)

This document provides a comprehensive reference for the marketing automation and external service integrations architecture:
1. **Zoho CRM** (Lead & Runner Deal Synchronization)
2. **WhatsApp Business Cloud API** (Digital Pass & Race Update Messaging)
3. **n8n Automation Engine** (Event Webhook Orchestration & Scheduled Reminders)
4. **Meta Conversions API (CAPI)** (Server-Side Ad Attribution & Conversion Tracking)

---

## 1. Integration Architecture & Design Principles

```
                    ┌────────────────────────┐
                    │  FastAPI Registration  │
                    │    & Payment Engine    │
                    └───────────┬────────────┘
                                │
               Payment Verified │ (HMAC SHA-256)
                                ▼
            ┌────────────────────────────────────────┐
            │      IntegrationDispatcherService      │
            │  (Asynchronous, Non-Blocking, Idempotent) │
            └───────────────────┬────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┬────────────────────────┐
       ▼                        ▼                        ▼                        ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Zoho CRM   │         │ WhatsApp API │         │     n8n      │         │  Meta CAPI   │
│ Client/Mock  │         │ Client/Mock  │         │ Client/Mock  │         │ Client/Mock  │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │                        │
       └────────────────────────┴──────────┬─────────────┴────────────────────────┘
                                           ▼
                            ┌─────────────────────────────┐
                            │   Database IntegrationLog   │
                            │ (Status, Payloads, Retries) │
                            └─────────────────────────────┘
```

### Core Architecture Rules:
1. **Decoupled & Non-Blocking**: External API slowdowns, timeouts, or transient 500 errors NEVER rollback or fail a confirmed runner registration or payment.
2. **Idempotency**: All dispatch events utilize unique idempotency keys derived from `registration_id` (e.g. `zoho_deal_{reg_id}`, `wa_pass_{reg_id}`, `n8n_confirm_{reg_id}`). Repeated webhook receipts or manual retries will never send duplicate WhatsApp tickets or duplicate leads.
3. **Structured Audit Trail**: Every outgoing request payload, API response, retry attempt, and error code is recorded in the `integration_logs` table.
4. **Data Privacy & Secret Masking**: API keys, auth tokens, and runner phone/email contacts are automatically masked in structured server logs.

---

## 2. Credentials & Source Reference

| Integration | Environment Variable | Source / Where to Obtain | Description |
| :--- | :--- | :--- | :--- |
| **Zoho CRM** | `ZOHO_CLIENT_ID` | [Zoho Developer Console](https://api-console.zoho.com/) | Client ID of Server-based or Self-Client app. |
| | `ZOHO_CLIENT_SECRET` | Zoho Developer Console | Client Secret paired with Client ID. |
| | `ZOHO_REFRESH_TOKEN` | Zoho OAuth Generator | Permanent refresh token to generate access tokens. |
| | `ZOHO_API_DOMAIN` | Zoho Developer Console | API endpoint (Default: `https://www.zohoapis.com` or `https://www.zohoapis.in`). |
| **WhatsApp** | `WHATSAPP_ACCESS_TOKEN` | [Meta for Developers](https://developers.facebook.com/) ➔ WhatsApp ➔ API Setup | Permanent System User Token with `whatsapp_business_messaging` permission. |
| | `WHATSAPP_PHONE_NUMBER_ID` | Meta for Developers ➔ WhatsApp ➔ API Setup | Unique Phone Number ID for the verified business sender number. |
| | `WHATSAPP_BUSINESS_ACCOUNT_ID` | Meta Business Manager ➔ WhatsApp Accounts | WhatsApp Business Account (WABA) ID. |
| | `WHATSAPP_API_VERSION` | Meta Graph API Version | Current Graph API version (Default: `v20.0`). |
| **n8n** | `N8N_BASE_URL` | Self-hosted instance or n8n Cloud | Base URL for webhooks (e.g. `http://localhost:5678` or `https://n8n.yourdomain.com`). |
| | `N8N_WEBHOOK_SECRET` | n8n Webhook Node Settings | Optional HMAC shared secret header for webhook validation. |
| **Meta CAPI** | `META_PIXEL_ID` | [Meta Events Manager](https://eventsmanager.facebook.com/) | Dataset / Pixel ID used on the marathon landing page. |
| | `META_ACCESS_TOKEN` | Meta Events Manager ➔ Settings ➔ Conversions API | Conversions API System User access token. |
| | `META_API_VERSION` | Meta Graph API Version | Default: `v20.0`. |

---

## 3. Development / Mock Mode vs Production Mode

### Development & Test Mode (`INTEGRATIONS_MOCK_MODE=true`):
- Active by default in `.env` and automated tests.
- Uses mock integration adapters (`MockZohoClient`, `MockWhatsAppClient`, `MockN8nClient`, `MockMetaCAPIClient`).
- **No external API calls are made.**
- Deterministic mock IDs are generated (e.g. `mock_zoho_lead_...`, `wamid.mock_...`, `n8n_exec_mock_...`, `fb_mock_trace_...`).
- Phone numbers and emails are masked in structured logs.
- Enables complete end-to-end integration and registration testing completely offline.

### Production Mode (`INTEGRATIONS_MOCK_MODE=false`):
- Activated by setting `INTEGRATIONS_MOCK_MODE=false` in production environment when live credentials are provided.
- Dispatches live HTTPS requests to Zoho REST APIs, Meta Graph API for WhatsApp Cloud, n8n webhook nodes, and Meta CAPI endpoints.

---

## 4. Failure & Retry Strategy

1. **Transient Network Errors**:
   - When an external API call fails, the `IntegrationDispatcherService` catches the exception and logs an `IntegrationLog` with `status="FAILED"`.
   - The user's payment and registration confirmation remain **`CONFIRMED`**.
2. **Automated Recovery / Retry Job**:
   - Failed integration attempts can be queried via `SELECT * FROM integration_logs WHERE status = 'FAILED' AND retry_count < 3`.
   - Idempotency guarantees that retrying an integration does not produce duplicate downstream effects.
