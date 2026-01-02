# Tabular Anonymizer
This repository provides a robust, policy-driven tabular data anonymization framework designed for research, clinical, and institutional data pipelines.
It supports reproducible, auditable anonymization of structured datasets while balancing privacy protection and downstream data utility.

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
cd /Tabular-Transformer
python tabular_transformer.py
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

## Usage
![Transformer_Pipeline](..\data\tabular-transformer.png)

### Example
   - Input: `data/patients.csv`
   - Output: `data/patients_anonymized.csv`