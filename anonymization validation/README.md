# Tabular Verifier
This repository provides a comprehensive Tabular validation pipeline to ensure anonymization integrity.
- Verifies anonymized files against original data
- Supports validation
- Results are appended to a single CSV report
- Uses anonymization logs to ensure policy compliance
- Designed for large-scale anonymization quality checks

## Run the Validator
```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd /anonymization\ validation
python tabular_anonymization_verifier.py
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

### Example
   - Original: `test/patients.csv`
   - Anonymized: `test/patients_anonymized.csv`
   - Report: `test/anonymization_report_*.csv`