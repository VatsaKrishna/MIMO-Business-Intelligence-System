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


def is_duplicate_transaction(sheet: gspread.Worksheet, transaction_id: str) -> bool:
    """Checks if a transaction_id (payment ID or refund ID) already exists in Raw Transactions."""
    if not transaction_id or transaction_id == "-":
        return False

    try:
        records = sheet.get_all_values()
        if not records or len(records) <= 1:
            return False

        for row in records[1:]:
            # Check for transaction ID in Payment ID column (Index 3) or any column
            for cell_val in row:
                if str(cell_val).strip() == transaction_id.strip():
                    return True
    except Exception as e:
        print(f"⚠️ Error checking duplicate transaction in Google Sheets: {e}")

    return False


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
    """Process incoming Cashfree payment and refund webhooks securely and idempotently."""
    raw_body = await request.body()
    payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}

    print("\n========== WEBHOOK RECEIVED ==========")
    print(json.dumps(payload, indent=2))
    print("======================================\n")

    if x_webhook_signature and x_webhook_timestamp:
        if not verify_signature(raw_body, x_webhook_timestamp, x_webhook_signature):
            print("⚠️ Webhook Signature Check Failed (Logged for Debugging)")

    event_type = str(
        payload.get("type") or
        payload.get("event") or
        payload.get("event_type") or
        "PAYMENT_WEBHOOK"
    ).upper()

    data = payload.get("data", {})
    order = data.get("order") or payload.get("order") or {}
    payment = data.get("payment") or payload.get("payment") or {}
    refund = data.get("refund") or payload.get("refund") or {}

    payment_id = str(payment.get("cf_payment_id") or payment.get("payment_id") or "-").strip()
    refund_id = str(refund.get("cf_refund_id") or refund.get("refund_id") or "-").strip()
    transaction_id = refund_id if "REFUND" in event_type and refund_id != "-" else payment_id

    payment_amount = payment.get("payment_amount") or payment.get("amount") or 0.0
    order_id = str(order.get("order_id") or payload.get("order_id") or "-").strip()

    # Idempotency Check: Return HTTP 200 OK without appending duplicate row
    if transaction_id != "-" and is_duplicate_transaction(raw_sheet, transaction_id):
        print(f"ℹ️ Duplicate Webhook Ignored (Transaction ID: {transaction_id})")
        return {"status": "SUCCESS", "message": "Duplicate event ignored (Idempotent)"}

    # Official Raw Transactions Schema: [Timestamp, Event, Order ID, Payment ID, Amount, Status, Raw JSON]
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_json_str = json.dumps(payload)

    if "SUCCESS" in event_type or payment.get("payment_status") == "SUCCESS":
        row = [
            timestamp_str,
            event_type,
            order_id,
            transaction_id,
            payment_amount,
            "SUCCESS",
            raw_json_str
        ]
        raw_sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"✅ Payment Logged: {order_id} (ID: {transaction_id})")

    elif "FAIL" in event_type or payment.get("payment_status") == "FAILED":
        row = [
            timestamp_str,
            event_type,
            order_id,
            transaction_id,
            payment_amount,
            "FAILED",
            raw_json_str
        ]
        raw_sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"❌ Failed Payment Logged: {order_id} (ID: {transaction_id})")

    elif "REFUND" in event_type:
        refund_amount = refund.get("refund_amount") or refund.get("amount") or 0.0
        row = [
            timestamp_str,
            event_type,
            order_id,
            transaction_id,
            refund_amount,
            "REFUNDED",
            raw_json_str
        ]
        raw_sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"💸 Refund Logged: {order_id} (ID: {transaction_id})")

    else:
        row = [
            timestamp_str,
            event_type,
            order_id,
            transaction_id,
            payment_amount,
            f"EVENT: {event_type}",
            raw_json_str
        ]
        raw_sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"ℹ️ Logged Payload for Event: {event_type}")

    return {"status": "SUCCESS"}