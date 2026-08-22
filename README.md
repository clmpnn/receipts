# Receipts & 9% GST Engine

A high-performance receipt ingestion, tax computation, and expense ledger engine built with Python, FastAPI, and Serverless PostgreSQL (Neon).

Live Demo: [https://receipts-sigma-five.vercel.app/](https://receipts-sigma-five.vercel.app/)

---

## Capabilities & Architecture

- **Exact Currency & Tax Math:** Computes the 9% Singapore GST inclusive tax component:
  $$\text{GST} = \text{round}\left(\text{Amount} \times \frac{9}{109}\right)$$
  using `decimal.Decimal` with `ROUND_HALF_UP` commercial rounding to prevent floating-point drift.
- **Persistent Serverless Ledger:** Stores transaction records in a Neon PostgreSQL database with parameterized SQL queries preventing SQL injection.
- **Integrated Frontend:** Zero-build HTML5/CSS/JavaScript dashboard served directly from FastAPI via `HTMLResponse`.
- **Live Aggregations:** Computes real-time running ledger counts, spend totals, and tax totals using SQL aggregates.

---

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **Database:** PostgreSQL (Neon Serverless with SSL pooling)
- **Database Driver:** `psycopg2-binary`
- **Deployment:** Vercel Serverless Functions

---

## Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/clmpnn/receipts.git
cd receipts
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```text
DATABASE_URL="postgresql://<user>:<password>@<neon-host>-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
```

### 5. Run the development server
```bash
python -m uvicorn main:app --reload
```
Open `http://127.0.0.1:8000/` for the web interface or `http://127.0.0.1:8000/docs` for the interactive OpenAPI documentation.

---

## API Reference

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web dashboard UI |
| `GET` | `/health` | Healthcheck and database connection status |
| `POST` | `/receipts` | Create a new receipt and calculate 9% GST |
| `GET` | `/receipts` | Retrieve paginated receipts with aggregate summaries |
