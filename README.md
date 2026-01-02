# Tabular Anonymizer
This repository provides a comprehensive Tabular anonymization and validation pipeline, along with verification tools to ensure anonymization integrity.

## Installation
``` bash
git clone https://github.com/labhai/Tabular-Anonymization
```

### Required packages:
  ```bash
  pip install pandas numpy openpyxl
  ```

## Usage of application

Anonymizer & Validator
```bash
cd Tabular_Anonymizer
python app.py
```

Anonymizer
```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd /anonymization\ transformation
python tabular_anonymizer.py
```

Validator
```bash
git clone https://github.com/labhai/Tabular-Anonymization
cd /anonymization\ validation
python tabular_anonymization_verifier.py
```

## Example


## Test Dataset (Demo Data)
To test the Anonymizer and Validator, a sample tabular data (Synthea_TM) is provided. You can use `patients.csv` data in `data` folder or download the demo dataset from the following link: https://github.com/synthetichealth/synthea-sample-data/tree/main/downloads