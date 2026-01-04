# Tabular-Anonymization

**Tabular-Anonymization** is a GUI-based toolkit for **policy-driven anonymization and verification**
of structured tabular data (CSV / Excel), intended for handling **healthcare research information**.

This repository provides:
- **Application**: GUI that runs anonymization → verification sequentially and produces a single report
- **Anonymizer**: policy-based anonymization (low/high level rules, semantic-aware field handling)
- **Verifier**: post-hoc verification and reporting to confirm whether anonymization rules were applied as intended

---

## Repository layout

- `tabular_application/`  
  **GUI application** (recommended entry point): run anonymization and verification in one workflow.

- `tabular_anonymizer/`  
  **Standalone anonymizer GUI**: apply low/high anonymization policies to CSV/Excel and export anonymized files.

- `tabular_verifier/`  
  **Standalone verifier GUI**: validate anonymization outputs and generate compliance-style reports (including k-group summaries when configured).

- `data/`  
  Demo assets and sample data (e.g., `patients.csv`) and UI screenshots.

---

## Quick start

### 0) Requirements
- python 3.11+
- Git (optional, only if you clone the repository)

### 1) Install
```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd Tabular-Anonymization
pip install -r requirements.txt
```

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

---

## Demo data

A sample dataset is included under the `data/` directory (e.g., `patients.csv`).  
Additional demo data based on Synthea is referenced in `data/download.md`.
