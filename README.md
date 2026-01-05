# Tabular Anonymization

This is a GUI-based toolkit for **policy-driven anonymization and verification**
of structured tabular data (CSV / Excel), intended for handling **healthcare research information**.

## What is Tabular data?
This project handles tabular healthcare research information, typically stored in CSV or Excel formats.
Such data represents structured records where each row corresponds to an individual entity (e.g., a patient, visit, or supply item), and each column represents an attribute such as identifiers, demographics, dates, diagnoses, or administrative information.

## Why Anonymization Is Necessary
Healthcare tabular data often contains personally identifiable information (PII) or quasi-identifiers, such as:

- patient IDs or record numbers
- names or initials
- dates (birth, visit, admission, discharge)
- demographic attributes (age, sex, region)

Even if explicit identifiers are removed, individuals may still be re-identified by linkage attacks using combinations of attributes (e.g., age + sex + visit date).

Anonymization is therefore required to:
- comply with privacy regulations (e.g., IRB, GDPR, HIPAA-style principles)
- reduce re-identification risk before data sharing or analysis
- enable safe secondary use of healthcare data for research and development

## Repository Structure

### `tabular_application`  
  **GUI application** (recommended entry point): run anonymization and verification in one workflow.

### `tabular_anonymizer`  
  **Standalone anonymizer GUI**: apply low/high anonymization policies to CSV/Excel and export anonymized files.

### `tabular_verifier`  
  **Standalone verifier GUI**: validate anonymization outputs and generate compliance-style reports (including k-group summaries when configured).

### `data`  
  Demo assets and sample data (e.g., `patients.csv`) and UI screenshots.


## Download Tabular Anonymization

```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd Tabular-Anonymization
```

## Requirements and Installation

### Requirements
- python 3.11+
- Git (optional, only if you clone the repository)

### Installation
```bash
pip install -r requirements.txt
```

## Example (Quickstart)

### 2) Run (recommended): GUI application
```bash
python tabular_application/app.py
```

### 3) Run (optional): Standalone modules
Standalone anonymizer
``` bash
python tabular_anonymizer/tabular_anonymizer.py
```

Standalone verifier
```bash
python tabular_verifier/tabular_anonymization_verifier.py
```

## Test Dataset (Demo Data)

A sample dataset is included under the `data/` directory (e.g., `patients.csv`).  
Additional demo data based on Synthea is referenced in `data/download.md`.
