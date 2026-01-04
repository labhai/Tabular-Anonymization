# Tabular Anonymizer and Verifier Application (`app.py`)

`app.py` provides an **integrated, end-to-end GUI application** that combines
the **Tabular Anonymizer** and the **Tabular Anonymization Verifier**
into a single workflow.

This application is designed to simplify operational use by ensuring that
anonymization and validation are executed **consistently, sequentially, and audibly**
without manual intervention between steps.

---

## Directory contains
This directory contains the recommended entry point for most users.  
The application provides a single GUI workflow that runs anonymization and verification sequentially and exports both anonymized data and verification reports.

- `app.py`  
  Main GUI entry point. Allows users to select one or more input files, choose the anonymization policy level, execute anonymization and verification end-to-end, and export outputs and reports.

- `anonymizer.py`  
  Implements application-side anonymization orchestration, including loading input files, applying transformations, and writing anonymized outputs.

- `validation_low.py`, `validation_high.py`  
  Verification logic for low- and high-level policies. Performs rule-by-rule checks and produces aggregated PASS/WARN/FAIL summaries.

- `validation_common.py`  
  Shared verification utilities used by both low- and high-level verification modules.

- `policy_low.py`, `policy_high.py`  
  Define the anonymization rules and policy configurations used by the application workflow.

- `transforms.py`  
  Core transformation primitives such as masking, replacement, generalization, dropping, and hashing.

- `semantics.py`  
  Semantic field inference utilities for identifying field types (e.g., name-like, identifier-like, contact-related).

- `name_masking.py`  
  Specialized masking logic for person name–like fields using rule-based patterns.

- `common_hash.py`  
  Shared hashing and tokenization utilities used when irreversible pseudonymization is required by a policy.

---

## What this application does

The application performs the following steps in a single run:

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

### Supported inputs

- CSV (`*.csv`)
- Excel (`*.xlsx`, `*.xls`)

### Multiple file selection

The GUI supports selecting multiple CSV or Excel files at once through a multi-file picker.

When multiple input files are selected:

- Each file is processed independently using the same selected policy (low or high) and configuration
- Anonymized outputs are generated per input file
- Verification reports include the original file name so that users can trace results for each file individually

### Report fields

| Field | Description |
|---|---|
| `파일명` | Original filename |
| `익명화 결과` | `PASS` / `WARN` / `FAIL` |
| `정책 일관성 준수율(%)` | Drop-policy consistency rate |
| `패턴 잔존율(%)` | Sensitive-pattern residual ratio |
| `고위험 필드 처리율(%)` | High-risk field handling rate |
| `PASS 비율(%)` | Ratio of PASS messages (per-field checks) |
| `WARN 비율(%)` | Ratio of WARN messages |
| `FAIL 비율(%)` | Ratio of FAIL messages |
| `추가 검토 여부` | Whether manual review is recommended |
| `필수 검토 여부` | Whether manual review is mandatory |
| `k < 2 비율(%)` | Fraction of records in QI-groups with size < 2 |
| `k < 5 비율(%)` | Fraction of records in QI-groups with size < 5 |
| `처리 시간(초)` | Validation duration per file |
