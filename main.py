from contextlib import asynccontextmanager
from datetime import date as PyDate
from decimal import Decimal, ROUND_HALF_UP
import os
from fastapi import FastAPI, HTTPException
import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

DATABASE_URL = os.getenv("DATABASE_URL")


def calculate_gst_cents(amount_cents: int) -> int:
  """Calculates the 9% Singapore GST inclusive tax component in integer cents.

  Formula: GST = (Total * 9) / 109 with half-up rounding.
  """
  total = Decimal(str(amount_cents))
  gst = (total * Decimal("9")) / Decimal("109")
  return int(gst.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def get_db():
  if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. Run:"
        " $env:DATABASE_URL='...'"
    )
  return psycopg.connect(DATABASE_URL, row_factory=dict_row)


@asynccontextmanager
async def lifespan(app: FastAPI):
  if DATABASE_URL:
    try:
      with get_db() as conn:
        with conn.cursor() as cur:
          # Ensure table exists with all necessary columns
          cur.execute("""
                        CREATE TABLE IF NOT EXISTS receipts (
                            id SERIAL PRIMARY KEY,
                            merchant VARCHAR(255) NOT NULL,
                            date DATE NOT NULL,
                            amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                            gst_cents INTEGER NOT NULL DEFAULT 0 CHECK (gst_cents >= 0)
                        );
                    """)
        conn.commit()
    except Exception as e:
      print(f"Startup DB Error: {e}")
  yield


app = FastAPI(title="Receipts Engine", lifespan=lifespan)


class ReceiptCreate(BaseModel):
  merchant: str = Field(
      ...,
      min_length=1,
      max_length=255,
      json_schema_extra={"example": "Guardian Pharmacy"},
  )
  date: PyDate = Field(..., json_schema_extra={"example": "2026-08-22"})
  amount_cents: int = Field(
      ...,
      gt=0,
      description="Total inclusive amount in integer cents",
      json_schema_extra={"example": 4850},
  )


@app.get("/health")
def health():
  return {"ok": True, "database_connected": bool(DATABASE_URL)}


@app.post("/receipts", status_code=201)
def create_receipt(receipt: ReceiptCreate):
  # Compute GST so gst_cents is never null
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
            (
                receipt.merchant.strip(),
                receipt.date,
                receipt.amount_cents,
                gst,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        row["date"] = str(row["date"])
        return row
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/receipts")
def list_receipts():
  try:
    with get_db() as conn:
      with conn.cursor() as cur:
        cur.execute(
            "SELECT id, merchant, date, amount_cents, gst_cents FROM receipts"
            " ORDER BY id ASC;"
        )
        rows = cur.fetchall()

        formatted_rows = []
        for r in rows:
          formatted_rows.append({
              "id": r["id"],
              "merchant": r["merchant"],
              "date": str(r["date"]),
              "amount_cents": int(r["amount_cents"]),
              "gst_cents": int(r["gst_cents"]),
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
            "data": formatted_rows,
        }
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")