# Tabular Anonymizer and Verifier All-in-One Application (`app.py`)

`app.py` provides an **integrated, end-to-end GUI application** that combines
the **Tabular Anonymization Transformer** and the **Tabular Anonymization Verifier**
into a single workflow.

This application is designed to simplify operational use by ensuring that
anonymization and validation are executed **consistently, sequentially, and audibly**
without manual intervention between steps.

---

## What this application does

The all-in-one application performs the following steps in a single run:

1. Anonymizes structured tabular data (CSV / Excel)
2. Generates anonymized outputs and per-file anonymization logs
3. Immediately validates anonymization results against original data
4. Produces a cumulative CSV validation report

All steps are executed using the **same anonymization configuration**, eliminating
configuration drift between anonymization and validation.

---

## Usage

Run from repository root:

```bash
python app.py
```

Then, in the GUI:
1. Select one or more CSV / Excel files
2. Select anonymization level (low / high)
3. (Optional) Enable diagnosis retention
4. (Optional) Select output directory
5. Start anonymization
6. Start validation

How to use:
![Verifier_Pipeline](https://github.com/labhai/Tabular-Anonymization/blob/main/data/tabular-application.png)


## Output

input: `patients.csv`
output:
- anonymized data: `patients_anonymized.csv`
- validation report: `anonymization_report_YYYYMMDD_HHMMSS.csv`

### Report columns

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
