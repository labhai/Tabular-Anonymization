## Prepare demo input folders

Before running the application, prepare demo tabular input files and place them in the `data/` directory.  
The demo files in this directory are provided solely for testing anonymization and verification workflows.

The files `tabular-application.png`, `tabular-transformer.png`, and `tabular-verifier.png` are used only for the main `README.md` and can be safely removed from this directory.

Expected structure:

```text
data/
├─ conditions.csv
├─ patients.csv
├─ supplies.csv
└─ README.md
```

Multiple CSV or Excel files may be placed in this directory.  
The application supports selecting **one or more files simultaneously** during execution.

---

## Sample file examples

- `conditions.csv`  
  A sample tabular dataset representing condition-related information for patients.

- `patients.csv`  
  A sample tabular dataset representing condition-related healthcare research information.

- `supplies.csv`  
  A sample tabular dataset representing supplies information.

Larger or additional datasets should be downloaded separately, as described below.

---

## Synthea (synthetic healthcare data)

**Link**  
- https://github.com/synthetichealth/synthea-sample-data/tree/main/downloads

**Synthea brief description**  
- Synthea is an open-source synthetic patient data generator that produces realistic but non-identifiable healthcare records.
- It is widely used for developing, testing, and validating healthcare data processing pipelines without relying on real patient data.

**How to generate or download data**

1. Visit the Synthea sample data GitHub repository.
2. Download one of the pre-generated sample datasets (the archives include CSV files).
3. Extract the CSV files. Placement into the `data/` directory is optional.
4. When using multiple CSV files together, ensure that all file names are unique.

---

## Notes

- When multiple files are selected, anonymization and verification are applied **independently to each file**.
- Verification reports reference the original input file names to ensure traceability.