# Meta Conversions API (CAPI) Architecture & Integration Guide

This guide documents the server-side **Meta Conversions API (CAPI)** implementation for the Marathon Platform.

---

## 1. Funnel Event Mapping

| Event Name | Trigger Stage | Key Payload Fields | Deduplication Event ID |
| :--- | :--- | :--- | :--- |
| `PageView` | Visitor loads landing page | `session_id`, `url` | `pageview_{session_id}_{timestamp}` |
| `ViewContent` | Visitor views/selects race category | `category_code`, `title`, `price_inr` | `viewcontent_{code}_{session_id}` |
| `Lead` | Participant submits Step 1-2 details | `email`, `phone`, `name`, `category` | `lead_{registration_code}` |
| `InitiateCheckout` | Participant opens Razorpay modal | `category_code`, `price_inr`, `utm_source` | `initiate_checkout_{registration_code}` |
| `Purchase` | Payment is verified / webhook captured | `value`, `currency="INR"`, `order_id`, `bib_number` | `purchase_{registration_code}_{payment_id}` |
| `CompleteRegistration` | Registration status marked CONFIRMED | `registration_code`, `bib_number`, `status` | `complete_registration_{registration_code}` |

---

## 2. Customer Matching & SHA-256 Hashing

Per Meta Graph API specifications, all Personally Identifiable Information (PII) is normalized and hashed using **SHA-256** prior to transmission:

- **Email (`em`)**: Lowercased, stripped of whitespace -> SHA-256.
- **Phone (`ph`)**: Non-digits removed, leading `91` country code ensured -> SHA-256.
- **First Name (`fn`) / Last Name (`ln`)**: Lowercased, stripped -> SHA-256.
- **City (`ct`) / State (`st`)**: Lowercased, stripped -> SHA-256.
- **Country (`country`)**: Normalized to `in` -> SHA-256.
- **Technical Context**: `client_ip_address`, `client_user_agent`, `fbc`, `fbp` are sent unhashed as expected by Meta.

---

## 3. Configuration & Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `META_CAPI_ENABLED` | `true` | Enables or disables Meta CAPI dispatches |
| `META_CAPI_MOCK_MODE` | `true` | Enables local mock mode (zero external HTTP traffic) |
| `META_PIXEL_ID` | `""` | Your Meta Pixel ID from Meta Events Manager |
| `META_ACCESS_TOKEN` | `""` | Server-side Conversions API System User token |
| `META_API_VERSION` | `v20.0` | Meta Graph API version |
| `META_TEST_EVENT_CODE` | `""` | Optional test code for Meta Events Manager Test Events tab |

---

## 4. Deduplication Strategy (Browser Pixel + Server CAPI)

To achieve 100% conversion accuracy without double-counting, the frontend Pixel and backend CAPI use identical `eventID` parameters:

```
Browser: fbq('track', 'Purchase', {...}, { eventID: 'purchase_MX26-000001_pay_123' })
Server:  POST https://graph.facebook.com/v20.0/... with event_id: 'purchase_MX26-000001_pay_123'
```
Meta automatically deduplicates matching `eventID` records within a 48-hour window.

---

## 5. Non-Blocking Payment Safety

Meta CAPI dispatches run asynchronously inside safe `try/except` blocks:
- If Meta's API times out, returns HTTP 500/429, or is unreachable, the event is logged as `FAILED` in `integration_logs`.
- **Payment verification and registration confirmation ALWAYS succeed immediately.**
- Failed events can be re-dispatched via `retry_failed_meta_events()`.
