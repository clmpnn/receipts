# System Verification & Test Plan: 9% Singapore GST Receipts Engine

**Project:** Receipts & GST Expense Ledger  
**Author:** Claudia  
**Repository:** [https://github.com/clmpnn/receipts](https://github.com/clmpnn/receipts)  
**Standard:** ISO/IEC/IEEE 29119 Software Testing & IRAS e-Tax Guide (2026 Edition)  
**Revision:** 1.0.0 (Day 11 Artifact)

---

## 1. Scope & Objective

This document defines the formal software quality assurance (SQA) and test verification plan for the **Receipts & 9% GST Engine**. The objective is to verify that all ingestion, validation, financial calculation, and ledger operations adhere strictly to statutory Singapore Inland Revenue Authority (IRAS) guidelines, prevent data corruption, and ensure zero floating-point cent drift across high-throughput operations.

---

## 2. Requirements Traceability Matrix (RTM)

The matrix below maps statutory and architectural requirements directly to their automated test implementations in `test_gst.py`.

| Requirement ID | Statutory / Functional Requirement | Risk Category | Verification Method | Associated Pytest Function | Expected Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-TAX-01** | **Exact IRAS Tax Fraction (9/109):** Extract 9% inclusive GST without applying standard percentage multiplication. | High (Tax Audit Failure) | Automated Unit Test | `test_exact_division` | `calculate_gst_cents(1090) == 90` |
| **REQ-RND-02** | **Commercial Half-Up Rounding:** Round half-cent increments strictly upward ($0.005 $\rightarrow$ \$0.01) rather than banker's rounding. | Critical (Cent Drift) | Automated Unit Test | `test_half_cent_rounding_up`, `test_standard_retail_rounding` | `calculate_gst_cents(7) == 1`, `calculate_gst_cents(2500) == 206` |
| **REQ-RND-03** | **Downward Rounding Threshold:** Fractional cents strictly under 0.5 must round downward. | High (Over-taxation) | Automated Unit Test | `test_half_cent_rounding_down`, `test_single_cent` | `calculate_gst_cents(6) == 0`, `calculate_gst_cents(1) == 0` |
| **REQ-EDG-04** | **Odd Cent Invariance:** Verify adjacent odd cent totals that fall within the same fractional bracket produce identical tax. | Medium (Customer Dispute) | Automated Unit Test | `test_odd_cents_rounding_boundary_low`, `test_odd_cents_rounding_boundary_high` | `calculate_gst_cents(105) == 9` and `calculate_gst_cents(115) == 9` |
| **REQ-ZRO-05** | **Zero-Rated Supplies (GST Act S21(3)):** International services and exports are taxed at 0% GST output. | Critical (Legal Compliance) | Automated Unit Test | `test_zero_rated_item_flag` | `calculate_gst_cents(2500, is_zero_rated=True) == 0` |
| **REQ-VAL-06** | **Negative Value Boundary:** Negative transaction totals represent data corruption and must raise an exception. | High (Ledger Integrity) | Automated Exception Test | `test_negative_amount_raises_value_error` | `pytest.raises(ValueError)` |
| **REQ-VAL-07** | **Zero Total Base Case:** Zero transaction amount must evaluate to zero tax without exception. | Low (Edge Boundary) | Automated Unit Test | `test_zero_amount` | `calculate_gst_cents(0) == 0` |
| **REQ-SCAL-08** | **High Value Integer Scalability:** Compute enterprise transactions up to \$100,000 without integer overflow or float truncation. | High (Enterprise Accuracy) | Automated Unit Test | `test_large_enterprise_amount` | `calculate_gst_cents(10000000) == 825688` |

---

## 3. Mathematical Proofs & Edge-Case Boundary Analyses

### 3.1 Statutory Inclusive Tax Formula
Under Singapore Goods and Services Tax (GST) legislation, retail prices are tax-inclusive. The output tax is derived via the IRAS tax fraction:
$$\text{GST} = \text{Amount} \times \frac{R}{100 + R} = \text{Amount} \times \frac{9}{109}$$

### 3.2 Half-Cent Boundary Analysis
Python's built-in `round()` executes IEEE 754 round-half-to-even (banker's rounding). This fails statutory compliance on boundary numbers (e.g. `round(2.5) == 2`). 

The engine uses `decimal.Decimal` with explicit `ROUND_HALF_UP`:
* For $A = 6\text{ cents}$:
  $$6 \times \frac{9}{109} = \frac{54}{109} \approx 0.4954128\text{ cents} \xrightarrow{\text{Half-Up}} 0\text{ cents}$$
* For $A = 7\text{ cents}$:
  $$7 \times \frac{9}{109} = \frac{63}{109} \approx 0.5779816\text{ cents} \xrightarrow{\text{Half-Up}} 1\text{ cent}$$
* For $A = 2500\text{ cents}$ (\$25.00):
  $$2500 \times \frac{9}{109} = \frac{22500}{109} \approx 206.422018\text{ cents} \xrightarrow{\text{Half-Up}} 206\text{ cents (\$2.06)}$$

---

## 4. Continuous Integration & Pipeline Verification

Every test case defined in this document is automatically executed on **Ubuntu Linux (Python 3.11)** via GitHub Actions (`.github/workflows/test.yml`) on every pull request and push to `main`. 

A regression or broken assertion halts deployment to the production environment on Vercel.
