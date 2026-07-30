import json
import os
import random
import sys
import time
from datetime import datetime, timedelta

from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import GSpreadException
import requests

import config

# ==========================================
# MBIS CONSTANTS & CONFIGURATION
# ==========================================

CLIENT_ID = config.CASHFREE_CLIENT_ID
CLIENT_SECRET = config.CASHFREE_CLIENT_SECRET
PROJECT_NAME = config.PROJECT_NAME
PROJECT_VERSION = config.PROJECT_VERSION


# ==========================================
# GOOGLE SHEETS FORMATTING HELPERS
# ==========================================

def format_currency(sheet_id: int, row: int) -> dict:
    """Format target cell as INR Currency."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row - 1,
                "endRowIndex": row,
                "startColumnIndex": 3,
                "endColumnIndex": 4
            },
            "cell": {
                "userEnteredFormat": {
                    "numberFormat": {
                        "type": "CURRENCY",
                        "pattern": "₹#,##0.00"
                    }
                }
            },
            "fields": "userEnteredFormat.numberFormat"
        }
    }


def format_number(sheet_id: int, row: int) -> dict:
    """Format target cell as Integer Number."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row - 1,
                "endRowIndex": row,
                "startColumnIndex": 3,
                "endColumnIndex": 4
            },
            "cell": {
                "userEnteredFormat": {
                    "numberFormat": {
                        "type": "NUMBER",
                        "pattern": "0"
                    }
                }
            },
            "fields": "userEnteredFormat.numberFormat"
        }
    }


def format_percent(sheet_id: int, row: int) -> dict:
    """Format target cell as Percentage."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row - 1,
                "endRowIndex": row,
                "startColumnIndex": 3,
                "endColumnIndex": 4
            },
            "cell": {
                "userEnteredFormat": {
                    "numberFormat": {
                        "type": "PERCENT",
                        "pattern": "0.00%"
                    }
                }
            },
            "fields": "userEnteredFormat.numberFormat"
        }
    }


def format_section(sheet_id: int, row: int, red: float, green: float, blue: float) -> dict:
    """Format section header row background and text."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row - 1,
                "endRowIndex": row,
                "startColumnIndex": 0,
                "endColumnIndex": 4
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {
                        "red": red,
                        "green": green,
                        "blue": blue
                    },
                    "textFormat": {
                        "bold": True,
                        "fontSize": 11,
                        "foregroundColor": {
                            "red": 1,
                            "green": 1,
                            "blue": 1
                        }
                    }
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)"
        }
    }


def format_kpi_color(sheet_id: int, row: int, color: dict) -> dict:
    """Apply dynamic text color to KPI cell."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row,
                "endRowIndex": row + 1,
                "startColumnIndex": 3,
                "endColumnIndex": 4
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": color
                    }
                }
            },
            "fields": "userEnteredFormat.textFormat.foregroundColor,userEnteredFormat.textFormat.bold"
        }
    }


def clear_demo_rows(worksheet, id_column_index: int, demo_prefix: str) -> None:
    """Deletes every row whose ID starts with the demo prefix."""
    records = worksheet.get_all_values()
    if not records:
        return

    rows_to_keep = [records[0]]

    for row in records[1:]:
        if len(row) <= id_column_index:
            rows_to_keep.append(row)
            continue

        if not row[id_column_index].startswith(demo_prefix):
            rows_to_keep.append(row)

    worksheet.clear()
    worksheet.update(rows_to_keep)


def generate_demo_business(demo_orders_count: int, demo_history_days_count: int) -> list:
    """Generate simulated settlement records for offline development."""
    print("\n🟠 Developer Simulator")
    print("Creating demo business data...")

    settlements_list = []

    for i in range(demo_orders_count):
        payment_amount = round(random.uniform(5, 250), 2)
        service_charge = round(payment_amount * 0.015, 2)
        service_tax = round(service_charge * 0.18, 2)
        amount_settled = round(payment_amount - service_charge - service_tax, 2)

        print("payment_amount =", payment_amount)
        print("service_charge =", service_charge)
        print("service_tax =", service_tax)
        print("calculated amount_settled =", amount_settled)

        random_days = random.randint(0, max(demo_history_days_count - 1, 0))
        random_seconds = random.randint(8 * 3600, 21 * 3600)
        random_datetime = (
            datetime.now()
            - timedelta(days=random_days)
            + timedelta(seconds=random_seconds)
        )

        settlement_item = {
            "settlement_date": random_datetime.isoformat(),
            "payment_amount": payment_amount,
            "amount_settled": amount_settled,
            "service_charge": service_charge,
            "service_tax": service_tax,
            "status": "PAID",
            "cf_settlement_id": f"DEMO{i + 1:04d}",
            "settlement_utr": f"DEMOUTR{i + 1:04d}"
        }

        settlements_list.append(settlement_item)

    return settlements_list


# =====================================
# DASHBOARD ROW REFERENCES
# =====================================

# Daily KPIs
DAILY_HEADER_ROW = 8
DAILY_REVENUE_ROW = 9
DAILY_ORDERS_ROW = 10
DAILY_PAYMENTS_ROW = 11
DAILY_REFUNDS_ROW = 12
DAILY_REFUND_RATE_ROW = 13
DAILY_SUCCESS_RATE_ROW = 14
DAILY_SERVICE_CHARGE_ROW = 15
DAILY_GST_ROW = 16
DAILY_SETTLED_ROW = 17

# Weekly KPIs
WEEKLY_HEADER_ROW = 19
WEEKLY_REVENUE_ROW = 20
WEEKLY_ORDERS_ROW = 21
WEEKLY_PAYMENTS_ROW = 22
WEEKLY_REFUNDS_ROW = 23
WEEKLY_REFUND_RATE_ROW = 24
WEEKLY_SUCCESS_RATE_ROW = 25
WEEKLY_SERVICE_CHARGE_ROW = 26
WEEKLY_GST_ROW = 27
WEEKLY_SETTLED_ROW = 28

# Monthly KPIs
MONTHLY_HEADER_ROW = 30
MONTHLY_REVENUE_ROW = 31
MONTHLY_ORDERS_ROW = 32
MONTHLY_PAYMENTS_ROW = 33
MONTHLY_REFUNDS_ROW = 34
MONTHLY_REFUND_RATE_ROW = 35
MONTHLY_SUCCESS_RATE_ROW = 36
MONTHLY_SERVICE_CHARGE_ROW = 37
MONTHLY_GST_ROW = 38
MONTHLY_SETTLED_ROW = 39

# Business Overview
SUMMARY_HEADER_ROW = 41
TOTAL_SETTLEMENTS_ROW = 42
AVERAGE_SETTLEMENT_ROW = 43
HIGHEST_SETTLEMENT_ROW = 44
LOWEST_SETTLEMENT_ROW = 45
TOTAL_PAYMENTS_ROW = 46
TOTAL_REFUNDS_ROW = 47

# Settlement Health
HEALTH_HEADER_ROW = 50
COMPLETION_ROW = 51
PENDING_ROW = 52
SYSTEM_STATUS_ROW = 53


# ==========================================
# MAIN EXECUTION
# ==========================================

start_time = time.time()
today_dt = datetime.now()

# 1. Google Sheets Authentication
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

if config.GOOGLE_CREDENTIALS_JSON:
    creds_dict = json.loads(config.GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
elif os.path.exists(config.CREDENTIALS_FILE):
    creds = Credentials.from_service_account_file(
        config.CREDENTIALS_FILE,
        scopes=scope
    )
else:
    raise FileNotFoundError(
        f"Neither '{config.CREDENTIALS_FILE}' nor 'GOOGLE_CREDENTIALS_JSON' env var was found."
    )

client = gspread.authorize(creds)

try:
    spreadsheet = client.open_by_key(config.SPREADSHEET_KEY)
except GSpreadException:
    spreadsheet = client.open(config.SPREADSHEET_TITLE)

settlements_sheet = spreadsheet.worksheet("Settlements")
dashboard_sheet = spreadsheet.worksheet("Dashboard")
config_sheet = spreadsheet.worksheet("Configuration")

# Read Configuration Values from Google Sheet
demo_orders = int(config_sheet.acell("B3").value or 25)
demo_history_days = int(config_sheet.acell("B4").value or 30)
developer_mode_value = str(config_sheet.acell("B2").value)
DEVELOPMENT_MODE = developer_mode_value.upper() == "TRUE"

# Clear previous demo rows if any
clear_demo_rows(
    settlements_sheet,
    id_column_index=1,
    demo_prefix="DEMO"
)

print("=" * 55)
print(f"{PROJECT_NAME} Version {PROJECT_VERSION}")
print("=" * 55)

if DEVELOPMENT_MODE:
    print("🟠 Developer Mode Enabled")
else:
    print("🟢 Live Mode Enabled")

print("=" * 55)

# Read Existing IDs for De-duplication
existing_records = settlements_sheet.get_all_values()
existing_ids = set()

for row in existing_records[1:]:
    if len(row) > 1:
        existing_ids.add(str(row[1]).strip())

# Fetch Settlements Data
if DEVELOPMENT_MODE:
    settlements = generate_demo_business(demo_orders, demo_history_days)
else:
    start_of_month = today_dt.replace(day=1, hour=0, minute=0, second=0)
    start_date = start_of_month.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date = today_dt.strftime("%Y-%m-%dT23:59:59Z")

    url = "https://api.cashfree.com/pg/settlements"
    headers = {
        "Content-Type": "application/json",
        "x-api-version": "2023-08-01",
        "x-client-id": CLIENT_ID,
        "x-client-secret": CLIENT_SECRET
    }
    body = {
        "product": "PG",
        "pagination": {"limit": 1000},
        "filters": {
            "start_date": start_date,
            "end_date": end_date
        }
    }

    response = requests.post(url=url, headers=headers, json=body)
    print("✅ Cashfree API Connected")

    if response.status_code != 200:
        print("API request failed")
        print(response.status_code)
        print(response.text)
        sys.exit(1)

    data = response.json()
    settlements = data.get("data", [])

# =====================================================
# METRICS ENGINE
# =====================================================

rows = []
daily_revenue = 0
weekly_revenue = 0
monthly_revenue = 0

daily_settled = 0
weekly_settled = 0
monthly_settled = 0

daily_orders = 0
weekly_orders = 0
monthly_orders = 0

daily_charges = 0
weekly_charges = 0
monthly_charges = 0

daily_payments = 0
weekly_payments = 0
monthly_payments = 0

daily_refunds = 0
weekly_refunds = 0
monthly_refunds = 0

daily_failed_payments = 0
weekly_failed_payments = 0
monthly_failed_payments = 0

total_transactions = 0
total_payments = 0
total_refunds = 0

today = today_dt.date()
start_of_week = today - timedelta(days=today.weekday())
start_of_month = today.replace(day=1)

payment_rows = []
payment_amounts = []
settled_amounts = []
service_charges = []
service_taxes = []

for settlement in settlements:
    remarks = settlement.get("remarks")
    settlement_id = str(settlement.get("cf_settlement_id")).strip()
    settlement_date_str = settlement.get("settlement_date")

    if settlement_date_str:
        settlement_date = datetime.fromisoformat(settlement_date_str).date()
    else:
        continue

    settlement_utr = settlement["settlement_utr"]
    status = settlement["status"]

    payment_amount = float(settlement.get("payment_amount", 0))
    settled_amount = float(settlement.get("amount_settled") or 0)
    service_charge = float(settlement.get("service_charge", 0))
    service_tax = float(settlement.get("service_tax") or 0)

    if status == "PAID":
        if settled_amount > 0:
            settlement_status = "✅ Settled"
        elif remarks and "Insufficient amount to settle" in remarks:
            settlement_status = "⏭ Skipped"
        else:
            settlement_status = "⏳ Pending Settlement"
    elif status == "FAILED":
        settlement_status = "❌ Failed"
    elif status == "CANCELLED":
        settlement_status = "🚫 Cancelled"
    elif status == "REFUNDED":
        settlement_status = "💸 Refunded"
    else:
        settlement_status = "⚠ Unknown"

    # Overall Metrics
    total_transactions += 1
    if settlement_status == "💸 Refunded":
        total_refunds += 1
    else:
        total_payments += 1

    if not remarks:
        if settlement_status == "✅ Settled":
            remarks = "Settlement completed successfully."
        elif settlement_status == "⏭ Skipped":
            remarks = "Settlement skipped."
        elif settlement_status == "⏳ Pending Settlement":
            remarks = "Awaiting settlement."
        elif settlement_status == "❌ Failed":
            remarks = "Settlement failed."
        elif settlement_status == "🚫 Cancelled":
            remarks = "Settlement cancelled."
        elif settlement_status == "💸 Refunded":
            remarks = "Settlement refunded."
        else:
            remarks = "-"

    if settlement_date == today and settlement_status == "❌ Failed":
        daily_failed_payments += 1

    if settlement_date >= start_of_week and settlement_status == "❌ Failed":
        weekly_failed_payments += 1

    if settlement_date >= start_of_month and settlement_status == "❌ Failed":
        monthly_failed_payments += 1

    # Daily KPIs
    if settlement_date == today:
        if settlement_status == "💸 Refunded":
            daily_refunds += 1
        else:
            daily_payments += 1
            daily_revenue += payment_amount
            daily_orders += 1
            daily_settled += settled_amount
            daily_charges += service_charge

    # Weekly KPIs
    if settlement_date >= start_of_week:
        if settlement_status == "💸 Refunded":
            weekly_refunds += 1
        else:
            weekly_payments += 1
            weekly_revenue += payment_amount
            weekly_orders += 1
            weekly_settled += settled_amount
            weekly_charges += service_charge

    # Monthly KPIs
    if settlement_date >= start_of_month:
        if settlement_status == "💸 Refunded":
            monthly_refunds += 1
        else:
            monthly_payments += 1
            monthly_revenue += payment_amount
            monthly_orders += 1
            monthly_settled += settled_amount
            monthly_charges += service_charge

    payment_amounts.append(payment_amount)
    settled_amounts.append(settled_amount)
    service_charges.append(service_charge)
    service_taxes.append(service_tax)

    # Health evaluation per row
    if settled_amount == payment_amount:
        settlement_health = "🟢 Excellent"
    elif settled_amount >= payment_amount * 0.95:
        settlement_health = "🟢 Healthy"
    elif settled_amount > 0:
        settlement_health = "🟡 Partial"
    else:
        settlement_health = "🔴 Unsettled"

    if settlement_id in existing_ids:
        continue

    formatted_date = settlement.get("settlement_date")[:10]
    row = [
        formatted_date,
        settlement.get("cf_settlement_id"),
        settlement.get("payment_amount"),
        settled_amount,
        settlement.get("service_charge"),
        settlement.get("service_tax"),
        settlement.get("settlement_utr"),
        settlement_status,
        remarks,
        settlement_health
    ]
    payment_row = [
        settlement.get("settlement_date"),
        f"TXN{settlement_id}",
        payment_amount,
        random.choice(["UPI", "Card", "Net Banking"]),
        "SUCCESS",
        f"9{random.randint(100000000, 999999999)}",
        f"ORDER{settlement_id}",
        payment_amount,
        f"CUST{random.randint(1000, 9999)}"
    ]

    payment_rows.append(payment_row)
    rows.append(row)

# Dynamic Performance Rates
daily_refund_rate = round(
    (daily_refunds / max(daily_payments + daily_refunds, 1)) * 100, 2
)
weekly_refund_rate = round(
    (weekly_refunds / max(weekly_payments + weekly_refunds, 1)) * 100, 2
)
monthly_refund_rate = round(
    (monthly_refunds / max(monthly_payments + monthly_refunds, 1)) * 100, 2
)

daily_success_rate = round(
    (daily_payments / max(daily_payments + daily_failed_payments, 1)) * 100, 2
)
weekly_success_rate = round(
    (weekly_payments / max(weekly_payments + weekly_failed_payments, 1)) * 100, 2
)
monthly_success_rate = round(
    (monthly_payments / max(monthly_payments + monthly_failed_payments, 1)) * 100, 2
)

print("\n==============================")
print("METRICS ENGINE")
print("==============================")
print(f"Today's Revenue: ₹{daily_revenue:.2f}")
print(f"Today's Orders : {daily_orders}")
print(f"This Week Revenue: ₹{weekly_revenue:.2f}")
print(f"This Week Orders : {weekly_orders}")
print(f"This Month Revenue: ₹{monthly_revenue:.2f}")
print(f"This Month Orders : {monthly_orders}")
print("==============================\n")

current_date = today_dt.strftime("%d %b %Y")
current_time = today_dt.strftime("%I:%M %p")

if len(payment_amounts) > 0:
    total_revenue = sum(payment_amounts)
    total_settled = sum(settled_amounts)
    number_of_orders = len(payment_amounts)
    highest_order = max(payment_amounts)
    lowest_order = min(payment_amounts)
    average_order = round(total_revenue / number_of_orders, 2)
    pending_amount = round(total_revenue - total_settled, 2)
    settlement_completion = round((total_settled / total_revenue) * 100, 2)
    pending_percentage = round((pending_amount / total_revenue) * 100, 2)
else:
    total_revenue = 0
    total_settled = 0
    number_of_orders = 0
    highest_order = 0
    lowest_order = 0
    average_order = 0
    pending_amount = 0
    settlement_completion = 0
    pending_percentage = 0

if number_of_orders == 0:
    system_status = "⚪ No Settlement Activity"
elif settlement_completion >= 95:
    system_status = "✅ Healthy"
elif settlement_completion >= 80:
    system_status = "⚠ Needs Attention"
else:
    system_status = "❌ Critical"

if DEVELOPMENT_MODE:
    system_status = "🟠 SYSTEM STATUS"
    environment = "SIMULATION MODE"
    api_status = "Disabled"
    simulator_status = "Active"
else:
    system_status = "🟢 SYSTEM STATUS"
    environment = "LIVE ENVIRONMENT"
    api_status = "Connected"
    simulator_status = "Disabled"

overall_refund_rate = (
    total_refunds / total_transactions * 100
    if total_transactions else 0
)

dashboard_data = [
    ["📊 MIMO EXECUTIVE DASHBOARD"],
    [""],
    ["🟢 SYSTEM STATUS", "", "", environment],
    ["Cashfree API", "", "", api_status],
    ["Business Simulator", "", "", simulator_status],
    ["🕒 Last Sync", "", "", f"{current_date}\n{current_time}"],
    [""],

    # TODAY KPIs
    ["📅 DAILY PERFORMANCE", "", "", ""],
    ["Revenue", "", "", daily_revenue],
    ["Orders", "", "", daily_orders],
    ["Payments", "", "", daily_payments],
    ["Refunds", "", "", daily_refunds],
    ["Refund Rate", "", "", f"{daily_refund_rate:.2f}%"],
    ["Success Rate", "", "", f"{daily_success_rate:.2f}%"],
    ["Service Charges", "", "", round(daily_charges, 2)],
    ["GST", "", "", round(daily_charges * 0.18, 2)],
    ["Amount Settled", "", "", daily_settled],
    [""],

    # WEEK KPIs
    ["📈 WEEKLY PERFORMANCE", "", "", ""],
    ["Revenue", "", "", weekly_revenue],
    ["Orders", "", "", weekly_orders],
    ["Payments", "", "", weekly_payments],
    ["Refunds", "", "", weekly_refunds],
    ["Refund Rate", "", "", f"{weekly_refund_rate:.2f}%"],
    ["Success Rate", "", "", f"{weekly_success_rate:.2f}%"],
    ["Service Charges", "", "", round(weekly_charges, 2)],
    ["GST", "", "", round(weekly_charges * 0.18, 2)],
    ["Amount Settled", "", "", weekly_settled],
    [""],

    # MONTH KPIs
    ["📊 MONTHLY PERFORMANCE", "", "", ""],
    ["Revenue", "", "", monthly_revenue],
    ["Orders", "", "", monthly_orders],
    ["Payments", "", "", monthly_payments],
    ["Refunds", "", "", monthly_refunds],
    ["Refund Rate", "", "", f"{monthly_refund_rate:.2f}%"],
    ["Success Rate", "", "", f"{monthly_success_rate:.2f}%"],
    ["Service Charges", "", "", round(monthly_charges, 2)],
    ["GST", "", "", round(monthly_charges * 0.18, 2)],
    ["Amount Settled", "", "", monthly_settled],
    [""],

    ["📦 BUSINESS OVERVIEW", "", "", ""],
    ["Total Transactions", "", "", total_transactions],
    ["Total Payments", "", "", total_payments],
    ["Total Refunds", "", "", total_refunds],
    ["Overall Refund Rate", "", "", f"{overall_refund_rate:.2f}%"],
    ["Number of Settlements", "", "", number_of_orders],
    ["Average Transaction Value", "", "", average_order],
    ["Highest Transaction", "", "", highest_order],
    ["Lowest Transaction", "", "", lowest_order],
    [""],

    ["📈 SETTLEMENT HEALTH", "", "", ""],
    ["Settlement Completion %", "", "", f"{settlement_completion}%"],
    ["Settlement Cost %", "", "", f"{pending_percentage}%"],
    ["System Status", "", "", system_status],

    [""],
    ["────────────────────────────────────────────────────────────"],
    ["MBIS v3.0 (Development Preview)"],
    ["Developed by", "", "", "Vatsa Krishna Raj"],
    ["© 2026 Vision Printt Technologies LLP"]
]

dashboard_sheet.freeze(rows=1)
dashboard_sheet.columns_auto_resize(0, 2)
dashboard_sheet.clear()

dashboard_sheet.update(
    values=dashboard_data,
    range_name="A1"
)

dashboard_sheet.format(
    "D52",
    {
        "textFormat": {
            "foregroundColor": {"red": 1, "green": 0, "blue": 0},
            "bold": True
        }
    }
)

# KPI COLOR LOGIC
if monthly_revenue > 0:
    revenue_color = {"red": 0.18, "green": 0.62, "blue": 0.31}
else:
    revenue_color = {"red": 0.50, "green": 0.50, "blue": 0.50}

if monthly_orders > 0:
    orders_color = {"red": 0.12, "green": 0.47, "blue": 0.95}
else:
    orders_color = {"red": 0.50, "green": 0.50, "blue": 0.50}

if monthly_settled > 0:
    settled_color = {"red": 0.18, "green": 0.62, "blue": 0.31}
else:
    settled_color = {"red": 0.50, "green": 0.50, "blue": 0.50}

if settlement_completion >= 70:
    completion_color = {"red": 0.18, "green": 0.62, "blue": 0.31}
elif settlement_completion >= 50:
    completion_color = {"red": 1, "green": 0.60, "blue": 0}
else:
    completion_color = {"red": 0.85, "green": 0.26, "blue": 0.21}

if pending_percentage <= 20:
    cost_color = {"red": 0.18, "green": 0.62, "blue": 0.31}
elif pending_percentage <= 40:
    cost_color = {"red": 1, "green": 0.60, "blue": 0}
elif pending_percentage <= 60:
    cost_color = {"red": 1, "green": 0.60, "blue": 0}
else:
    cost_color = {"red": 0.85, "green": 0.26, "blue": 0.21}

if monthly_success_rate >= 95:
    success_rate_color = {"red": 0.18, "green": 0.62, "blue": 0.31}
elif monthly_success_rate >= 80:
    success_rate_color = {"red": 1, "green": 0.60, "blue": 0}
else:
    success_rate_color = {"red": 0.85, "green": 0.26, "blue": 0.21}

if monthly_refund_rate <= 5:
    refund_rate_color = {"red": 0.18, "green": 0.62, "blue": 0.31}
elif monthly_refund_rate <= 10:
    refund_rate_color = {"red": 1, "green": 0.60, "blue": 0}
else:
    refund_rate_color = {"red": 0.85, "green": 0.26, "blue": 0.21}

# Send Batch Format Request
spreadsheet.batch_update({
    "requests": [
        format_kpi_color(dashboard_sheet.id, MONTHLY_REVENUE_ROW, revenue_color),
        format_kpi_color(dashboard_sheet.id, MONTHLY_SUCCESS_RATE_ROW, success_rate_color),
        format_kpi_color(dashboard_sheet.id, MONTHLY_REFUND_RATE_ROW, refund_rate_color),
        format_kpi_color(dashboard_sheet.id, COMPLETION_ROW, completion_color),
        format_kpi_color(dashboard_sheet.id, PENDING_ROW, cost_color),
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": MONTHLY_ORDERS_ROW,
                    "endRowIndex": MONTHLY_ORDERS_ROW + 1,
                    "startColumnIndex": 3,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": orders_color
                        }
                    }
                },
                "fields": "userEnteredFormat.textFormat"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": MONTHLY_SETTLED_ROW,
                    "endRowIndex": MONTHLY_SETTLED_ROW + 1,
                    "startColumnIndex": 3,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": settled_color
                        }
                    }
                },
                "fields": "userEnteredFormat.textFormat"
            }
        },
        format_number(dashboard_sheet.id, DAILY_ORDERS_ROW),
        format_number(dashboard_sheet.id, WEEKLY_ORDERS_ROW),
        format_number(dashboard_sheet.id, MONTHLY_ORDERS_ROW),
        format_number(dashboard_sheet.id, TOTAL_PAYMENTS_ROW),
        format_number(dashboard_sheet.id, TOTAL_REFUNDS_ROW),
        format_number(dashboard_sheet.id, TOTAL_SETTLEMENTS_ROW),
        {
            "mergeCells": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 4
                },
                "mergeType": "MERGE_ALL"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "fontSize": 16,
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1}
                        },
                        "backgroundColor": {"red": 0.09, "green": 0.29, "blue": 0.55}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": 18,
                    "endRowIndex": 19,
                    "startColumnIndex": 0,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.22, "green": 0.63, "blue": 0.29},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1}
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": 29,
                    "endRowIndex": 30,
                    "startColumnIndex": 0,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.09, "green": 0.29, "blue": 0.55},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1}
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": 40,
                    "endRowIndex": 41,
                    "startColumnIndex": 0,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.48, "green": 0.29, "blue": 0.69},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1}
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": 50,
                    "endRowIndex": 51,
                    "startColumnIndex": 0,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.40, "green": 0.40, "blue": 0.40},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1}
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": 7,
                    "endRowIndex": 8,
                    "startColumnIndex": 0,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.48, "green": 0.29, "blue": 0.69},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1}
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "startRowIndex": 5,
                    "endRowIndex": 21,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True}
                    }
                },
                "fields": "userEnteredFormat.textFormat.bold"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1
                },
                "properties": {"pixelSize": 240},
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": dashboard_sheet.id,
                    "dimension": "COLUMNS",
                    "startIndex": 3,
                    "endIndex": 4
                },
                "properties": {"pixelSize": 160},
                "fields": "pixelSize"
            }
        },
        format_currency(dashboard_sheet.id, DAILY_REVENUE_ROW),
        format_currency(dashboard_sheet.id, DAILY_SERVICE_CHARGE_ROW),
        format_currency(dashboard_sheet.id, DAILY_GST_ROW),
        format_currency(dashboard_sheet.id, DAILY_SETTLED_ROW),

        format_currency(dashboard_sheet.id, WEEKLY_REVENUE_ROW),
        format_currency(dashboard_sheet.id, WEEKLY_SERVICE_CHARGE_ROW),
        format_currency(dashboard_sheet.id, WEEKLY_GST_ROW),
        format_currency(dashboard_sheet.id, WEEKLY_SETTLED_ROW),

        format_currency(dashboard_sheet.id, MONTHLY_REVENUE_ROW),
        format_currency(dashboard_sheet.id, MONTHLY_SERVICE_CHARGE_ROW),
        format_currency(dashboard_sheet.id, MONTHLY_GST_ROW),
        format_currency(dashboard_sheet.id, MONTHLY_SETTLED_ROW),

        format_currency(dashboard_sheet.id, AVERAGE_SETTLEMENT_ROW),
        format_currency(dashboard_sheet.id, HIGHEST_SETTLEMENT_ROW),
        format_currency(dashboard_sheet.id, LOWEST_SETTLEMENT_ROW),
    ]
})

if rows:
    settlements_sheet.append_rows(rows)

print("\n==============================")
print("SYNC SUMMARY")
print("==============================")
print(f"Payments Synced     : {len(payment_rows)}")
print(f"Settlements Synced  : {len(rows)}")
print("Dashboard Updated   : ✓")
print("\n✔ MBIS Sync Complete")

execution_time = time.time() - start_time
print(f"⏱ Execution Time    {execution_time:.2f}s")
