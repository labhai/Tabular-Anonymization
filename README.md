# Tabular Anonymization

This is a GUI-based toolkit for **policy-driven anonymization and verification**
of structured tabular data (CSV / Excel), intended for handling **healthcare research information**.

## What is Tabular data?
**Tabular data** refers to structured healthcare research information typically stored in CSV or Excel file formats.
In such datasets, each row represents an individual entity—such as a patient, a clinical visit, or a supply item—while each column corresponds to a specific attribute, including identifiers, demographic characteristics, dates, diagnoses, or administrative variables.

Due to its simplicity and flexibility, tabular data is widely used in clinical research, hospital information systems, and administrative reporting.

## Why Anonymization Is Necessary
Healthcare tabular datasets frequently contain direct identifiers and quasi-identifiers, such as patient or record IDs, names or initials, dates (e.g., birth, visit, admission, or discharge), and demographic attributes (e.g., age, sex, or region).

Because tabular data can be easily copied, merged, and cross-referenced with external datasets, insufficient anonymization may lead to unintended disclosure of sensitive personal information.
Even when explicit identifiers are removed, individuals may still be re-identified through linkage attacks that exploit unique combinations of remaining attributes (e.g., age, sex, and visit date).

Anonymization is therefore essential to:

- comply with privacy and research ethics regulations (e.g., IRB requirements, GDPR, HIPAA-style principles)
- reduce the risk of re-identification prior to data sharing or secondary analysis
- enable safe reuse of healthcare data for research and development

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
- OS: Window 10/11
- python 3.11+
- Git (optional, only if you clone the repository)

### Installation
```bash
pip install -r requirements.txt
```

## Example (Quickstart)

### 1) Run (recommended): GUI application
```bash
python tabular_application/app.py
```

### 2) Run (optional): Standalone modules
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
