# MBIS v3.0 Architecture Guide

This document describes the technical architecture, data flows, and security model of the **MIMO Business Intelligence System (MBIS v3.0)**.

---

## 1. System Architecture

MBIS combines a **Real-Time Webhook Receiver** (FastAPI) and a **Batch Sync & Reporting Engine** (Python CLI) integrated with Google Sheets as the visual dashboard layer.

```
+---------------------+               +----------------------+
|  Cashfree Webhooks  | ------------> | webhook.py (FastAPI) |
+---------------------+               +----------+-----------+
                                                 | (Append Row)
                                                 v
+---------------------+               +----------------------+
| Cashfree REST API   | <------------ | main.py (Batch Engine|
+---------------------+               +----------+-----------+
                                                 | (Update Dashboard)
                                                 v
                                      +----------------------+
                                      | Google Sheets (MBIS) |
                                      +----------------------+
```

---

## 2. Key Modules

### [config.py](file:///c:/Users/HP/PycharmProjects/PythonProject/config.py)
Centralized configuration manager loading environment variables from `.env` or system environment (Render).

### [webhook.py](file:///c:/Users/HP/PycharmProjects/PythonProject/webhook.py)
FastAPI application receiving payment webhooks, verifying HMAC-SHA256 signatures, and appending raw transactions to Google Sheets.

### [main.py](file:///c:/Users/HP/PycharmProjects/PythonProject/main.py)
Batch synchronization and metrics calculation engine that updates the Executive Dashboard.

---

## 3. Security Model

- **HMAC-SHA256 Verification**: Webhooks verify the `x-webhook-signature` header against Cashfree secrets.
- **Dual Credentials Management**: Supports local `credentials.json` files as well as cloud `GOOGLE_CREDENTIALS_JSON` environment variables.
- **SSL Fallback**: Built-in certificate fallback for Windows local environments.
