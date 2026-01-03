# Tabular Anonymizer

**Tabular Anonymizer** is a GUI-based framework for **policy-driven anonymization and validation**
of structured tabular data (CSV / Excel), designed for medical and clinical research workflows.

The framework provides:
- a **Transformer** for semantic-aware anonymization
- a **Verifier** for log-driven compliance checking
- an **All-in-one application** for end-to-end execution

## Installation
``` bash
git clone https://github.com/labhai/Tabular-Anonymization
cd Tabular-Anonymizer
```

### Required packages:
**Environment**
- OS: Windows
- Python: 3.12 (recommended)
  ```bash
  pip install pandas numpy tkinter
  ```
  or
  ```bash
  pip3 install -r requirements.txt
  ```

## Example
Anonymizer & Validator
```bash
python app.py
```

How to use:
![Anonymization_Pipeline](https://github.com/labhai/Tabular-Anonymization/blob/main/data/tabular-application.png)

Anonymizer
```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd /Tabular-Anonymization
python tabular-anonymizer/tabular_anonymizer.py
```

Validator
```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd /Tabular-Anonymization
python tabular-verifier/tabular_anonymization_verifier.py
```

## Test Dataset (Demo Data)
To test the Anonymizer and Validator, a sample tabular data (Synthea_TM) is provided. You can use `patients.csv` data in `data` folder or download the demo dataset from the following link: https://github.com/synthetichealth/synthea-sample-data/tree/main/downloads