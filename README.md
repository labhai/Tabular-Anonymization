# Tabular Anonymizer
This repository provides a comprehensive Tabular anonymization and validation pipeline, along with verification tools to ensure anonymization integrity.

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

## Usage
![Anonymization_Pipeline](data\tabular-application.png)

## Example
Anonymizer & Validator
```bash
python app.py
```

Anonymizer
```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd /Tabular-Transformer
python tabular_transformer.py
```

Validator
```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd /Tabular-Verifier
python tabular_anonymization_verifier.py
```

## Test Dataset (Demo Data)
To test the Anonymizer and Validator, a sample tabular data (Synthea_TM) is provided. You can use `patients.csv` data in `data` folder or download the demo dataset from the following link: https://github.com/synthetichealth/synthea-sample-data/tree/main/downloads