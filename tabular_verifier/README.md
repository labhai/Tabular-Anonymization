# Tabular Anonymization Verifier (`tabular_anonymization_verifier.py`)

`tabular_anonymization_verifier.py` validates whether anonymization rules were applied correctly by comparing:
- original structured files (CSV / Excel)
- anonymized structured files (`*_anonymized.*`)
- anonymization logs (`*_anonymized_log.json`)

It performs **column-level compliance checks** based on the anonymization log (`log_info`) and generates a **single cumulative CSV report**.

> This script is GUI-based (tkinter). You select original files, and the verifier automatically resolves the corresponding anonymized file + log file.

---

## Directory contains

This directory contains a standalone GUI dedicated to verification and reporting.

- `tabular_anonymization_verifier.py`  
  Standalone verifier GUI entry point. Inspects anonymized outputs, evaluates policy compliance, and exports verification reports.

- `validation_low.py`, `validation_high.py`  
  Policy-specific verification routines for low- and high-level anonymization.

- `validation_common.py`  
  Shared verification helpers used across verification modules.

---

##  What this script does

### 1) File pairing rule (origin ↔ anonymized ↔ log)

Given an original file:

- Original: `xxx.csv` (or `xxx.xlsx`, `xxx.xls`)
- Anonymized: `xxx_anonymized.csv` (same extension as original)
- Log: `xxx_anonymized_log.json`

If the anonymized folder is not provided, the verifier looks for anonymized/log files in the original file’s directory.

---

### 2) Column-level compliance verification (log-driven)

For each original column, the verifier checks the corresponding anonymized column(s) using `log_info`:

- If the anonymized dataset contains the same column name, it is used directly.
- If the anonymized dataset does not contain the exact column name, the verifier also supports “expanded” columns that start with:
  - `"<original_col>_"`  
  (e.g., the original column `address` may map to anonymized columns like `address_region`, `address_detail`, etc.)

Each anonymized column is validated according to the **expected action** stored in `log_info`:

#### A) `drop`
- **Expected**: anonymized column values must be blank
- **Fail condition**: any non-blank values remain

#### B) `keep_if_permitted_else_drop` (diagnosis policy)
- If diagnosis retention is **NOT permitted**:
  - treated as `drop` (must be blank)
- If diagnosis retention **IS permitted**:
  - retention is allowed (not forced to blank)

#### C) `pseudonymize`
- Checks whether values look pseudonymized and remain sufficiently diverse
- Produces **WARN** if:
  - uniqueness ratio is low, or
  - values do not resemble pseudonyms

#### D) `date_floor_year` / `date_floor_decade`
- Checks whether dates are generalized into a floor form:
  - expected format resembles `YYYY-01-01`
- For decade flooring, the year is expected to be aligned to the decade boundary

#### E) Other actions
- For remaining transformation actions, the verifier performs a generic **sensitive-pattern residual check**:
  - If sensitive patterns remain in more than **10%** of values, the column **FAILS**
  - Otherwise, it is treated as **PASS**

---

### 3) Policy consistency check (drop mismatch)

Beyond per-column checks, the verifier computes **policy consistency**:

- If a column is expected to be `drop` but the anonymized column exists and contains non-blank values,
  it counts as a policy mismatch.

It reports a **policy consistency rate** in the final report.

---

### 4) Sensitive pattern residual ratio (global)

The verifier estimates a dataset-level **pattern residual ratio** by scanning the anonymized dataset for known sensitive patterns (e.g., ID-like tokens, phone/email-like patterns, etc.).  
This contributes to the PASS/WARN/FAIL decision thresholds.

---

### 5) High-risk field handling rate

The verifier scans `log_info` for semantics that look high-risk (e.g., SSN/passport/license/phone/email/address/zipcode/birth/death, etc.), then checks whether the applied action is one of the acceptable protective actions.

It reports a **high-risk handling rate**.

---

### 6) k-anonymity risk indicators (QI-based)

The verifier selects quasi-identifier (QI) columns based on semantics in `log_info`, including:

- age, gender, race, ethnicity, marital_status, address, zipcode, visit_date

Using these QI columns, it computes:
- group sizes of identical QI tuples
- the fraction of records that fall into:
  - groups with `k < 2`
  - groups with `k < 5`

These are reported as:
- `k < 2 비율(%)`
- `k < 5 비율(%)`

---

## PASS / WARN / FAIL decision rule

The verifier produces a final decision per file:

- **PASS**
  - meets threshold conditions, and
  - no “mandatory review” flags, and
  - no “recommended review” flags

- **FAIL**
  - any threshold condition fails, or
  - mandatory review is triggered (any FAIL messages exist)

- **WARN**
  - threshold conditions pass, but review flags are triggered (e.g., warn ratio is high)

Thresholds:
- High-level mode:
  - policy consistency ≥ 0.80
  - pattern residual ≤ 0.10
  - high-risk handling rate ≥ 1.0
- Low-level mode:
  - policy consistency ≥ 0.60
  - pattern residual ≤ 0.10
  - high-risk handling rate ≥ 1.0

Review flags:
- mandatory review: any FAIL exists
- recommended review:
  - high-level: WARN ratio ≥ 0.30
  - low-level:  WARN ratio ≥ 0.50

---

## Usage

Run from repository root:

```bash
python "tabular_verifier/tabular_anonymization_verifier.py"
```

Then, in the GUI:
1. Select original files (CSV / Excel)
2. (Optional) Select anonymized folder (defaults to original folder)
3. (Optional) Select report folder (defaults to original folder)
4. Start validation

How to use:
![Verifier_Pipeline](https://github.com/labhai/Tabular-Anonymization/blob/main/data/tabular-verifier.png)

---

## Output

### 1) CSV report

A CSV report is saved under the selected report directory (or the original directory if not specified):

- `anonymization_report_YYYYMMDD_HHMMSS.csv`

Rows are appended per processed file within a single run.

### 2) Report columns

| Column | Description |
|---|---|
| `파일명` | Original filename |
| `익명화 결과` | `PASS` / `WARN` / `FAIL` |
| `정책 일관성 준수율(%)` | Drop-policy consistency rate |
| `패턴 잔존율(%)` | Sensitive-pattern residual ratio |
| `고위험 필드 처리율(%)` | High-risk field handling rate |
| `PASS 비율(%)` | Ratio of PASS messages (per-column checks) |
| `WARN 비율(%)` | Ratio of WARN messages |
| `FAIL 비율(%)` | Ratio of FAIL messages |
| `추가 검토 여부` | Whether manual review is recommended |
| `필수 검토 여부` | Whether manual review is mandatory |
| `k < 2 비율(%)` | Fraction of records in QI-groups with size < 2 |
| `k < 5 비율(%)` | Fraction of records in QI-groups with size < 5 |
| `처리 시간(초)` | Validation duration per file |