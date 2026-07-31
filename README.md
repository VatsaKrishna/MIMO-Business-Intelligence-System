# MBIS - MIMO Business Intelligence System (v3.0)

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.140-green.svg)](https://fastapi.tiangolo.com/)
[![Render](https://img.shields.io/badge/Render-Deployed-purple.svg)](https://render.com/)

MBIS is an automated Business Intelligence system built for MIMO to streamline Cashfree settlement reporting, real-time payment tracking, and executive decision-making.

---

## 🌟 Key Features

- **Automated Settlement Import**: Pulls Cashfree settlements directly via REST API.
- **Real-Time Webhook Processing**: Deployed on Render (`https://mbis-webhook.onrender.com`) to record payments instantly.
- **HMAC-SHA256 Security**: Verifies webhook signatures to ensure data authenticity.
- **Executive Dashboard**: Generates formatted, color-coded Google Sheets executive dashboards.
- **Financial KPIs**: Calculates daily, weekly, and monthly revenue, service charges, GST, refund rates, and settlement health.
- **Developer Simulator**: Built-in simulator for offline development and UI testing.
- **Windows Task Scheduler Ready**: Automated background synchronization via `run_mbis_sync.bat`.

---

## 🏗 System Architecture

```
Cashfree Webhooks ──> Render (FastAPI webhook.py) ──> Google Sheets (Raw Transactions)
Cashfree API      ──> Windows Task Scheduler (main.py) ──> Google Sheets (Executive Dashboard)
```

---

## 🛠 Tech Stack

- **Language**: Python 3.13
- **Framework**: FastAPI / Uvicorn
- **Integrations**: Cashfree API, Google Sheets API (`gspread`)
- **Deployment**: Render Web Services
- **OS Automation**: Windows Task Scheduler

---

## 📖 Documentation

- [Deployment Guide](docs/deployment_guide.md)
- [Architecture Guide](docs/architecture_guide.md)

---

## 👤 Author

**Vatsa Krishna Raj**  
Business Analytics | Automation | Python | Power BI | SQL  
Developed for MIMO (Vision Printt Technologies LLP).
