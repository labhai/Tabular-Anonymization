# Tabular Anonymizer
This repository provides a comprehensive Tabular anonymization pipeline to anonymize data.
- Supports **CSV / XLSX / XLS** input formats
- **Low-level** and **High-level** anonymization modes (selectable)
- Automatic identifier / quasi-identifier inference based on column names (semantic guessing)
- Policy-driven transformations (hashing, masking, generalization, suppression, etc.)
- Optional diagnosis retention (only when explicitly permitted)
- Batch processing of multiple files in a single run
- Generates:
  - Anonymized data file
  - JSON-based transformation log for auditability

## Run the Anonymizer
```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd /anonymization\ transformation
python tabular_anonymizer.py
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

### Example Workflow
   - Input: `data/patients.csv`
   - Output: `data/patients_anonymized.csv`