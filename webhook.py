from fastapi import FastAPI, Request
import gspread
from datetime import datetime

app = FastAPI()

# 1. Google Sheets Authentication
gc = gspread.service_account(filename="credentials.json")

# 2. Open Spreadsheet by Key
spreadsheet = gc.open_by_key("1QHfXru9IrOXWp0x8QVWTgA7WnCGe7rMlwjO-HdWjuds")

# 3. Select the Raw Transactions worksheet
raw_sheet = spreadsheet.worksheet("Raw Transactions")


@app.get("/")
def home():
    return {"message": "MBIS Webhook Server Running!"}


# Allow both GET and POST so Cashfree verification checks pass cleanly
@app.get("/cashfree/webhook")
def cashfree_webhook_get():
    return {"status": "SUCCESS", "message": "Webhook endpoint reachable"}


@app.post("/cashfree/webhook")
async def cashfree_webhook(request: Request):

    payload = await request.json()

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