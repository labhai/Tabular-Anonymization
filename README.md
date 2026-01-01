# Tabular Anonymizer
This repository provides a comprehensive Tabular anonymization and validation pipeline, along with verification tools to ensure anonymization integrity.

## Features

### Anonymization (`tabular_anonymizer.py`)
- Supports **CSV / XLSX / XLS** input formats
- **Low-level** and **High-level** anonymization modes (selectable)
- Automatic identifier / quasi-identifier inference based on column names (semantic guessing)
- Policy-driven transformations (hashing, masking, generalization, suppression, etc.)
- Optional diagnosis retention (only when explicitly permitted)
- Batch processing of multiple files in a single run
- Generates:
  - Anonymized data file
  - JSON-based transformation log for auditability

### Validation (`tabular_anonymization_verifier.py`)
- Verifies anonymized files against original data
- Supports validation
- Results are appended to a single CSV report
- Uses anonymization logs to ensure policy compliance
- Designed for large-scale anonymization quality checks

### All-in-one (`tabular_anonymizer_application.py`)
- Provides an integrated anonymization and validation pipeline within a single GUI
- Executes anonymization followed immediately by validation in a single workflow
- Supports batch processing of multiple CSV / Excel files
- Ensures consistent policy application by reusing the same anonymization configuration for validation
- Generates anonymized datasets and appends validation results to a cumulative CSV report
- Designed to reduce operational errors and simplify end-to-end anonymization QA for large-scale tabular datasets

### Repository Structure
```
tabular_anonymizer/
├─ anonymization transformation/
│  ├─ tabular_anonymizer.py
│  ├─ anonymize/
│  │  ├─ semantic_detection.py
│  │  └─ transform_functions.py
│  └─ policy/
│     ├─ low_level_policy.py
│     └─ high_level_policy.py
│
├─ anonymization validation/
│  ├─ tabular_anonymization_verifier.py
│  └─ validation/
│     ├─ validate_low.py
│     └─ validate_high.py
│
└─ anonymization application/
   ├─ tabular_anonymizer_application.py
   ├─ anonymize/
   │  ├─ semantic_detection.py
   │  └─ transform_functions.py
   ├─ policy/
   │  ├─ low_level_policy.py
   │  └─ high_level_policy.py
   └─ validation/
      ├─ validate_low.py
      └─ validate_high.py
```

## Requirements

- Python 3.8+
- Required packages:
  ```bash
  pip install pandas numpy openpyxl
  ```

## Installation and Usage
This project is GUI-driven (not CLI-based).
Because directory names contain spaces, always wrap paths in quotes when executing.

Clone or extract the repository:
``` bash
git clone <repository-url>
cd tabular_anonymizer
```
No additional build steps are required.

### 1. Run the Anonymizer
```bash
python "anonymization transformation/tabular_anonymizer.py"
```
**GUI Options**
- **Input files:** Select one or more CSV / Excel files
- **Output directory:** Optional (defaults to input file location)
- **Anonymization mode**
    - Low-level
    - High-level
- **Allow diagnosis fields** (optional, policy-controlled)

**Output file**
```
patients.csv
```
The following will be generated:
```
patients_anonymized.csv
patients_anonymized_log.json
```
- The anonymized file contains transformed data
- The JSON log records:
    - Detected semantic fields
    - Applied anonymization policies
    - Column-level transformations

### 2. Run the Validator
```bash
python "anonymization validation/tabular_anonymization_verifier.py"
```

**GUI Options**
- **Original files:** Select original CSV / Excel files

**Output file**
A CSV file is generated:
```
anonymization_report_YYYYMMDD_HHMMSS.csv
```
- When validating multiple files in one run:
    - Results are appended row-wise into the same CSV
- Typical report contents:
    - File name
    - Anonymization mode
    - Identifier handling status
    - Policy compliance indicators
    - Warning / failure flag

## Example Workflow
``` 
demo/
├─ test/
│  └─ patients.csv
├─ anonymized/
└─ reports/
```
### 1. Run anonymizer
   - Input: `test/patients.csv`
   - Output: `test/patients_anonymized.csv`

### 2. Run Validator
   - Original: `test/patients.csv`
   - Anonymized: `test/patients_anonymized.csv`
   - Report: `test/anonymization_report_*.csv`