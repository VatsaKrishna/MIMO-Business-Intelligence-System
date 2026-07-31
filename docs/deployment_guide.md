# MBIS v3.0 Deployment & Webhook Setup Guide

This guide walks you through deploying **MIMO Business Intelligence System (MBIS v3.0)** to Render and connecting Cashfree Webhooks.

---

## 1. Prerequisites

- **GitHub Repository**: Accessible at `https://github.com/VatsaKrishna/MIMO-Business-Intelligence-System`
- **Render Account**: Register at [Render.com](https://render.com)
- **Google Service Account**: Credentials saved in `credentials.json`
- **Cashfree API Merchant Credentials**: Client ID and Client Secret from Cashfree Merchant Dashboard

---

## 2. Render Web Service Deployment

1. Log into your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** $\rightarrow$ **Web Service**.
3. Select your repository: `MIMO-Business-Intelligence-System`.
4. Configure service settings:
   - **Name**: `mbis-webhook`
   - **Environment**: `Python 3`
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn webhook:app --host 0.0.0.0 --port $PORT`

5. Navigate to the **Environment** tab and add the following 4 Environment Variables:

| Environment Variable | Value Description |
| :--- | :--- |
| `CASHFREE_CLIENT_ID` | Your Cashfree Merchant Client ID |
| `CASHFREE_CLIENT_SECRET` | Your Cashfree Merchant Secret Key |
| `SPREADSHEET_KEY` | `1QHfXru9IrOXWp0x8QVWTgA7WnCGe7rMlwjO-HdWjuds` |
| `GOOGLE_CREDENTIALS_JSON` | Copy and paste the entire JSON text from your local `credentials.json` |

6. Click **Deploy Web Service**.

---

## 3. Cashfree Webhook Configuration

1. Log into your **Cashfree Merchant Dashboard**.
2. Navigate to **Developers** $\rightarrow$ **Webhooks**.
3. Click **Add Webhook Endpoint**.
4. Enter Endpoint Details:
   - **Webhook URL**: `https://mbis-webhook.onrender.com/cashfree/webhook`
   - **HTTP Method**: `POST`
5. Select Events to Subscribe:
   - `PAYMENT_SUCCESS_WEBHOOK`
   - `PAYMENT_FAILED_WEBHOOK`
   - `REFUND_WEBHOOK`
6. Save & Enable the Webhook.

---

## 4. Windows Task Scheduler Automation Setup

To automate periodic batch syncs of Cashfree Settlements to Google Sheets:

1. Open **Windows Task Scheduler** on your computer.
2. Click **Create Basic Task...** in the right pane.
3. Task Name: `MBIS Settlement Sync`.
4. **Trigger**: Select **Daily** (e.g. at 8:00 AM) or **Hourly**.
5. **Action**: Select **Start a program**.
6. Program/script: Browse and select `c:\Users\HP\PycharmProjects\PythonProject\run_mbis_sync.bat`.
7. Start in (optional): `c:\Users\HP\PycharmProjects\PythonProject`.
8. Click **Finish**.

Executions and logs will be saved to `logs/sync.log`.
