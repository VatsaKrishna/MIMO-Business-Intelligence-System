import base64
from datetime import datetime
import hashlib
import hmac
import json
import os
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
import gspread

import config

app = FastAPI()


def get_gspread_client() -> gspread.Client:
    """Authenticates and returns gspread Client using filename or raw JSON env var."""
    if config.GOOGLE_CREDENTIALS_JSON:
        creds_dict = json.loads(config.GOOGLE_CREDENTIALS_JSON)
        return gspread.service_account_from_dict(creds_dict)
    if os.path.exists(config.CREDENTIALS_FILE):
        return gspread.service_account(filename=config.CREDENTIALS_FILE)
    raise FileNotFoundError(
        f"Neither '{config.CREDENTIALS_FILE}' nor 'GOOGLE_CREDENTIALS_JSON' env var was found."
    )


# 1. Google Sheets Authentication
gc = get_gspread_client()

# 2. Open Spreadsheet by Key
spreadsheet = gc.open_by_key(config.SPREADSHEET_KEY)

# 3. Select the Raw Transactions worksheet
raw_sheet = spreadsheet.worksheet("Raw Transactions")


def verify_signature(raw_body: bytes, timestamp: str, signature: str) -> bool:
    """Verifies Cashfree webhook signature using HMAC-SHA256."""
    secret = config.CASHFREE_WEBHOOK_SECRET or config.CASHFREE_CLIENT_SECRET
    if not timestamp or not signature or not secret:
        return False

    message = timestamp.encode("utf-8") + raw_body
    secret_bytes = secret.encode("utf-8")

    computed_hmac = hmac.new(secret_bytes, message, hashlib.sha256).digest()
    computed_signature = base64.b64encode(computed_hmac).decode("utf-8")

    return hmac.compare_digest(computed_signature, signature)


@app.get("/")
def home() -> dict:
    """Health check homepage endpoint."""
    return {"message": "MBIS Webhook Server Running!"}


@app.get("/cashfree/webhook")
def cashfree_webhook_get() -> dict:
    """Verification GET endpoint for Cashfree Webhook registration."""
    return {"status": "SUCCESS", "message": "Webhook endpoint reachable"}


@app.post("/cashfree/webhook")
async def cashfree_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    x_webhook_timestamp: Optional[str] = Header(None)
) -> dict:
    """Process incoming Cashfree payment and refund webhooks securely."""
    raw_body = await request.body()

    # In live mode (or when signature headers are provided), verify authenticity
    if not config.DEVELOPMENT_MODE and (x_webhook_signature or x_webhook_timestamp):
        if not verify_signature(raw_body, x_webhook_timestamp or "", x_webhook_signature or ""):
            print("❌ Invalid Webhook Signature - Request Rejected")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}

    print("\n========== WEBHOOK RECEIVED ==========")
    print(payload)
    print("======================================\n")

    event_type = payload.get("type")
    data = payload.get("data", {})

    # -----------------------------
    # SUCCESS PAYMENT
    # -----------------------------
    if event_type == "PAYMENT_SUCCESS_WEBHOOK":
        order = data.get("order", {})
        payment = data.get("payment", {})
        customer = data.get("customer_details", {})

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            payment.get("cf_payment_id"),
            payment.get("payment_amount"),
            payment.get("payment_group"),
            payment.get("payment_status"),
            customer.get("customer_phone"),
            order.get("order_id"),
            customer.get("customer_id")
        ]

        raw_sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"✅ Payment Logged: {order.get('order_id')}")

    # -----------------------------
    # FAILED PAYMENT
    # -----------------------------
    elif event_type == "PAYMENT_FAILED_WEBHOOK":
        order = data.get("order", {})
        payment = data.get("payment", {})
        customer = data.get("customer_details", {})

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            payment.get("cf_payment_id"),
            payment.get("payment_amount"),
            payment.get("payment_group"),
            "FAILED",
            customer.get("customer_phone"),
            order.get("order_id"),
            customer.get("customer_id")
        ]

        raw_sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"❌ Failed Payment Logged: {order.get('order_id')}")

    # -----------------------------
    # REFUND
    # -----------------------------
    elif event_type == "REFUND_WEBHOOK":
        order = data.get("order", {})
        refund = data.get("refund", {})
        customer = data.get("customer_details", {})

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            refund.get("cf_refund_id"),
            refund.get("refund_amount"),
            "Refund",
            "REFUNDED",
            customer.get("customer_phone"),
            order.get("order_id"),
            customer.get("customer_id")
        ]

        raw_sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"💸 Refund Logged: {order.get('order_id')}")

    else:
        print(f"⚠ Ignored Event: {event_type}")

    return {"status": "SUCCESS"}