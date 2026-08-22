import os
from datetime import date as PyDate
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")


def calculate_gst_cents(amount_cents: int) -> int:
    """Calculates 9% Singapore GST inclusive tax in integer cents."""
    total = Decimal(str(amount_cents))
    gst = (total * Decimal("9")) / Decimal("109")
    return int(gst.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not configured.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db_schema():
    """Initializes tables on demand without blocking startup."""
    if DATABASE_URL:
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS receipts (
                            id SERIAL PRIMARY KEY,
                            merchant VARCHAR(255) NOT NULL,
                            date DATE NOT NULL,
                            amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                            gst_cents INTEGER NOT NULL DEFAULT 0 CHECK (gst_cents >= 0),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cur.execute("""
                        ALTER TABLE receipts 
                        ADD COLUMN IF NOT EXISTS gst_cents INTEGER NOT NULL DEFAULT 0 CHECK (gst_cents >= 0);
                    """)
                conn.commit()
        except Exception as e:
            print(f"Database schema check notice: {e}")


app = FastAPI(
    title="Receipts Engine",
    description="Receipts ingestion, GST calculations, and HTML interface",
    version="1.0.0"
)


# --- Schemas ---

class ReceiptCreate(BaseModel):
    merchant: str = Field(..., min_length=1, max_length=255, json_schema_extra={"example": "FairPrice Supermarket"})
    date: PyDate = Field(..., json_schema_extra={"example": "2026-08-22"})
    amount_cents: int = Field(..., gt=0, description="Total inclusive amount in integer cents", json_schema_extra={"example": 2500})


class ReceiptResponse(BaseModel):
    id: int
    merchant: str
    date: str
    amount_cents: int
    gst_cents: int


class ReceiptListResponse(BaseModel):
    count: int
    total_amount_cents: int
    total_gst_cents: int
    data: List[ReceiptResponse]


# --- Endpoints ---

@app.get("/health", tags=["System"])
def health():
    return {"ok": True, "database_connected": bool(DATABASE_URL)}


@app.post("/receipts", response_model=ReceiptResponse, status_code=201, tags=["Receipts"])
def create_receipt(receipt: ReceiptCreate):
    init_db_schema()
    gst = calculate_gst_cents(receipt.amount_cents)
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO receipts (merchant, date, amount_cents, gst_cents)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, merchant, date, amount_cents, gst_cents;
                    """,
                    (receipt.merchant.strip(), receipt.date, receipt.amount_cents, gst)
                )
                row = cur.fetchone()
                conn.commit()
                row["date"] = str(row["date"])
                return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insert error: {str(e)}")


@app.get("/receipts", response_model=ReceiptListResponse, tags=["Receipts"])
def list_receipts(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    init_db_schema()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, merchant, date, amount_cents, gst_cents 
                    FROM receipts 
                    ORDER BY id DESC 
                    LIMIT %s OFFSET %s;
                    """,
                    (limit, offset)
                )
                rows = cur.fetchall()

                formatted_rows = []
                for r in rows:
                    formatted_rows.append({
                        "id": r["id"],
                        "merchant": r["merchant"],
                        "date": str(r["date"]),
                        "amount_cents": int(r["amount_cents"]),
                        "gst_cents": int(r["gst_cents"])
                    })

                cur.execute("""
                    SELECT 
                        COUNT(*) as total_count,
                        COALESCE(SUM(amount_cents), 0) as sum_amount,
                        COALESCE(SUM(gst_cents), 0) as sum_gst
                    FROM receipts;
                """)
                summary = cur.fetchone()

                return {
                    "count": int(summary["total_count"]),
                    "total_amount_cents": int(summary["sum_amount"]),
                    "total_gst_cents": int(summary["sum_gst"]),
                    "data": formatted_rows
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database fetch error: {str(e)}")


# --- Day 5 Frontend HTML ---

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Receipts & GST Ledger</title>
    <style>
        :root {
            --bg: #0d1117;
            --panel: #161b22;
            --border: #30363d;
            --text: #e6edf3;
            --text-muted: #8b949e;
            --accent: #238636;
            --accent-hover: #2ea043;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.5;
            padding: 30px 20px;
        }
        .container { max-width: 860px; margin: 0 auto; }
        header { margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }
        h1 { font-size: 24px; font-weight: 600; }
        p.subtitle { color: var(--text-muted); font-size: 14px; }
        
        .grid { display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 24px; }
        @media(min-width: 768px) {
            .grid { grid-template-columns: 320px 1fr; }
        }

        .card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 18px;
        }
        .card h2 { font-size: 16px; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-family: var(--font-mono); }
        
        .form-group { margin-bottom: 14px; }
        label { display: block; font-size: 13px; margin-bottom: 5px; color: var(--text-muted); }
        input {
            width: 100%;
            padding: 8px 12px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text);
            font-size: 14px;
        }
        input:focus { outline: none; border-color: #58a6ff; }
        button {
            width: 100%;
            background: var(--accent);
            color: #ffffff;
            border: none;
            padding: 9px 16px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
        }
        button:hover { background: var(--accent-hover); }

        .stats-strip {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 16px;
        }
        .stat-box {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 10px;
            text-align: center;
        }
        .stat-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono); }
        .stat-val { font-size: 18px; font-weight: 600; font-family: var(--font-mono); }

        table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
        th { text-align: left; padding: 10px; border-bottom: 1px solid var(--border); color: var(--text-muted); font-family: var(--font-mono); font-size: 12px; }
        td { padding: 10px; border-bottom: 1px solid #21262d; }
        td.mono { font-family: var(--font-mono); }
        td.num { text-align: right; }
        th.num { text-align: right; }
        .empty-msg { text-align: center; padding: 24px; color: var(--text-muted); }
        .status-msg { font-size: 13px; margin-top: 10px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Receipts & 9% GST Engine</h1>
            <p class="subtitle">FastAPI + Neon Postgres • Live Production</p>
        </header>

        <div class="grid">
            <div class="card">
                <h2>Add Receipt</h2>
                <form id="receiptForm">
                    <div class="form-group">
                        <label for="merchant">Merchant</label>
                        <input type="text" id="merchant" required placeholder="e.g. FairPrice, Grab, 7-Eleven">
                    </div>
                    <div class="form-group">
                        <label for="date">Transaction Date</label>
                        <input type="date" id="date" required>
                    </div>
                    <div class="form-group">
                        <label for="amount">Total Amount ($)</label>
                        <input type="number" step="0.01" min="0.01" id="amount" required placeholder="e.g. 25.00">
                    </div>
                    <button type="submit" id="submitBtn">Save Receipt</button>
                    <div id="statusMsg" class="status-msg"></div>
                </form>
            </div>

            <div class="card">
                <h2>Ledger Summary</h2>
                <div class="stats-strip">
                    <div class="stat-box">
                        <div class="stat-label">Count</div>
                        <div class="stat-val" id="statCount">0</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Total Spend</div>
                        <div class="stat-val" id="statTotal">$0.00</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">9% GST</div>
                        <div class="stat-val" id="statGst">$0.00</div>
                    </div>
                </div>

                <h2>All Transactions</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Merchant</th>
                                <th class="num">GST (9%)</th>
                                <th class="num">Total</th>
                            </tr>
                        </thead>
                        <tbody id="ledgerBody">
                            <tr><td colspan="4" class="empty-msg">Loading records...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('date').value = new Date().toISOString().split('T')[0];

        function formatCents(cents) {
            return '$' + (cents / 100).toFixed(2);
        }

        async function fetchLedger() {
            try {
                const res = await fetch('/receipts');
                const data = await res.json();
                
                document.getElementById('statCount').textContent = data.count || 0;
                document.getElementById('statTotal').textContent = formatCents(data.total_amount_cents || 0);
                document.getElementById('statGst').textContent = formatCents(data.total_gst_cents || 0);

                const tbody = document.getElementById('ledgerBody');
                if (!data.data || data.data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="empty-msg">No receipts recorded yet.</td></tr>';
                    return;
                }

                tbody.innerHTML = data.data.map(r => `
                    <tr>
                        <td class="mono">${r.date}</td>
                        <td><strong>${r.merchant}</strong></td>
                        <td class="mono num" style="color: #8b949e;">${formatCents(r.gst_cents)}</td>
                        <td class="mono num"><strong>${formatCents(r.amount_cents)}</strong></td>
                    </tr>
                `).join('');
            } catch (err) {
                console.error('Fetch error:', err);
                document.getElementById('ledgerBody').innerHTML = '<tr><td colspan="4" class="empty-msg" style="color: #f85149;">Failed to load records.</td></tr>';
            }
        }

        document.getElementById('receiptForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById('submitBtn');
            const statusMsg = document.getElementById('statusMsg');
            
            const merchant = document.getElementById('merchant').value.trim();
            const date = document.getElementById('date').value;
            const amountVal = parseFloat(document.getElementById('amount').value);
            const amount_cents = Math.round(amountVal * 100);

            if (!merchant || !date || isNaN(amount_cents) || amount_cents <= 0) {
                statusMsg.textContent = 'Please provide valid inputs.';
                statusMsg.style.color = '#f85149';
                return;
            }

            submitBtn.disabled = true;
            submitBtn.textContent = 'Saving...';
            statusMsg.textContent = '';

            try {
                const res = await fetch('/receipts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ merchant, date, amount_cents })
                });

                if (!res.ok) {
                    const error = await res.json();
                    throw new Error(error.detail || 'Failed to save');
                }

                statusMsg.textContent = 'Receipt added successfully!';
                statusMsg.style.color = '#2ea043';
                document.getElementById('merchant').value = '';
                document.getElementById('amount').value = '';
                
                await fetchLedger();
            } catch (err) {
                statusMsg.textContent = 'Error: ' + err.message;
                statusMsg.style.color = '#f85149';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Save Receipt';
            }
        });

        fetchLedger();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, tags=["UI"])
def index():
    return HTMLResponse(content=HTML_TEMPLATE, status_code=200)
