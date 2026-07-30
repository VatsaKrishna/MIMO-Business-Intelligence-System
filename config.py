# ==========================================
# MBIS CONFIGURATION MANAGER
# ==========================================

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project Metadata
PROJECT_NAME = "MBIS"
PROJECT_VERSION = "3.0"

# Cashfree API Credentials & Webhook Secrets
CASHFREE_CLIENT_ID = os.getenv("CASHFREE_CLIENT_ID")
CASHFREE_CLIENT_SECRET = os.getenv("CASHFREE_CLIENT_SECRET")
CASHFREE_WEBHOOK_SECRET = os.getenv("CASHFREE_WEBHOOK_SECRET", CASHFREE_CLIENT_SECRET)

# Google Sheets Configuration
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
SPREADSHEET_KEY = os.getenv("SPREADSHEET_KEY", "1QHfXru9IrOXWp0x8QVWTgA7WnCGe7rMlwjO-HdWjuds")
SPREADSHEET_TITLE = os.getenv("SPREADSHEET_TITLE", "MIMO Business Intelligence System")

# System Defaults & Feature Flags
DEVELOPMENT_MODE = False
SIMULATED_ORDERS = 25
DEFAULT_CURRENCY = "INR"
EMAIL_REPORTS = False
POWERBI_EXPORT = False

# ==========================================
# END CONFIGURATION
# ==========================================