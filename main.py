from datetime import date as PyDate
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Receipts Engine")


class ReceiptCreate(BaseModel):
  merchant: str = Field(..., min_length=1, json_schema_extra={"example": "FairPrice"})
  date: PyDate = Field(..., json_schema_extra={"example": "2026-08-22"})
  amount_cents: int = Field(..., gt=0, json_schema_extra={"example": 2500})


receipts_db: list[dict] = []


@app.get("/health")
def health():
  return {"ok": True}


@app.post("/receipts", status_code=201)
def create_receipt(receipt: ReceiptCreate):
  record = receipt.model_dump()
  record["id"] = len(receipts_db) + 1
  receipts_db.append(record)
  return record


@app.get("/receipts")
def list_receipts():
  return {"count": len(receipts_db), "data": receipts_db}