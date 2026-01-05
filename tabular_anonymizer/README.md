# Tabular Anonymizer (`tabular_anonymizer.py`)

`tabular_anonymizer.py` applies **policy-driven anonymization** to structured tabular data
(CSV / Excel) using **semantic field inference** and produces:

- anonymized tabular files
- per-file anonymization logs (`*_anonymized_log.json`) for audit and validation

The anonymizer is GUI-based and supports **batch anonymization** in a single run.


## Directory contains

This directory contains a standalone GUI focused solely on anonymization without verification.

- `tabular_anonymizer.py`  
  Standalone anonymizer GUI entry point. Supports selecting one or more input files and applying low- or high-level anonymization policies.

- `anonymizer.py`  
  Implements the standalone anonymization pipeline.

- `policy_low.py`, `policy_high.py`  
  Define low- and high-level anonymization policies.

- `transforms.py`  
  Anonymization transformation primitives.

- `semantics.py`  
  Semantic field inference for applying appropriate transformations per field type.

- `name_masking.py`  
  Name-specific masking utilities.

- `common_hash.py`  
  Hashing utilities for pseudonymization and tokenization.


## What this script does

### 1) Input handling
The anonymizer accepts one or more structured files:

- CSV (`.csv`)
- Excel (`.xlsx`, `.xls`)

Files may contain heterogeneous schemas; anonymization is applied **per file**.

---

### 2) Semantic field inference

Before anonymization, each field name is tokenized and matched against a predefined
semantic alias dictionary to infer its semantic role.

Examples of inferred semantics:
- direct identifiers: `name`, `ssn`, `passport`, `email`, `phone`
- quasi-identifiers: `age`, `gender`, `zipcode`, `address`, `visit_date`
- clinical fields: `diagnosis`, `diagnosis_code`
- non-sensitive fields: `lab_value`, `measurement`, `score`, etc.

Semantic inference is **header-based only** (no value-based inspection at this stage).

The inferred semantic for each field is recorded in the anonymization log.

---

### 3) Anonymization level selection

The anonymizer supports two anonymization levels:

#### Low-level anonymization
- Designed for **internal research use**
- Preserves more analytical utility
- Typical actions:
  - partial generalization
  - pseudonymization
  - date flooring (year-level)
  - selective retention of quasi-identifiers

#### High-level anonymization
- Designed for **external sharing**
- Maximizes privacy protection
- Typical actions:
  - aggressive dropping of identifiers
  - stronger generalization
  - decade-level date flooring
  - suppression of high-risk quasi-identifiers

The selected level determines the policy mapping applied to each semantic field.

| Semantic Field | Description | Low-level Anonymization | High-level Anonymization |
|---------------|------------|----------------------------------------|---------------------------------------------|
| `id` | Generic identifier (patient / visit / record ID) | `pseudonymize` | `drop` |
| `patient_id` | Patient identifier | `pseudonymize` | `drop` |
| `insurance_id` | Insurance identifier | `pseudonymize` | `drop` |
| `encounter_id` | Visit / encounter identifier | `pseudonymize` | `drop` |
| `ssn` | Social security / resident number | `drop` | `drop` |
| `driver_license` | Driver’s license number | `drop` | `drop` |
| `passport` | Passport number | `drop` | `drop` |
| `name` | Person name | `pseudonymize` | `drop` |
| `birthdate` | Date of birth | `date_floor_year` | `date_floor_decade` |
| `deathdate` | Date of death | `date_floor_year` | `date_floor_decade` |
| `visit_date` | Visit or admission date | `date_floor_year` | `date_floor_year` |
| `age` | Age | `keep` | `drop` |
| `gender` | Sex / gender | `keep` | `drop` |
| `marital_status` | Marital status | `keep` | `normalize_marital_prefix` |
| `race` | Race | `keep` | `keep` |
| `ethnicity` | Ethnicity | `keep` | `keep` |
| `address` | Free-text address | `region_generalize` (district-level) | `region_generalize` (city-level) |
| `zipcode` | Postal code | `mask_zip_leading` | `mask_zip_leading` |
| `location` | GPS / coordinate data | `drop` | `drop` |
| `diagnosis` | Diagnosis name or code | `keep_if_permitted_else_drop` | `keep_if_permitted_else_drop` |
| `measurement` | Lab results / numeric measurements | `keep` | `keep` |
| `finance` | Financial or billing information | `drop` | `drop` |
| `comment` | Free-text comment | `drop` | `drop` |
| `note` | Clinical or administrative notes | `drop` | `drop` |
| `other` | Non-sensitive miscellaneous fields | `keep` | `keep` |

---

### 4) field-wise transformation

The Tabular Anonymizer applies **semantic-aware anonymization techniques** at the
field level. Each transformation corresponds to a well-established privacy
preservation method (e.g., deletion, pseudonymization, generalization).

### Supported transformations and their privacy classifications

#### `drop`
- **Privacy technique**: Deletion
- Replaces all values with blanks
- Irreversible anonymization method
- Used for direct identifiers or fields not permitted to be retained

#### `keep_if_permitted_else_drop`
- **Privacy technique**: Conditional Deletion
- Retains values only if explicitly permitted by policy or runtime options
  (e.g., diagnosis permission)
- Otherwise treated identically to `drop`

#### `pseudonymize`
- **Privacy technique**: Pseudonymization
- Replaces original values with deterministic pseudonyms
- Preserves linkability across records while hiding original values
- As this is not deletion, pseudonymized fields may still be considered
  personal data under certain regulations

#### `date_floor_year`, `date_floor_decade`
- **Privacy technique**: Temporal Generalization
- Converts dates to coarse-grained representations
  (e.g., `YYYY-01-01`, decade-aligned years)
- Reduces temporal re-identification risk while preserving analytical utility

#### `generalize`
- **Privacy technique**: Generalization / Bucketing
- Maps detailed values to broader categories
  (e.g., age → age group, address → region)
- Directly contributes to improved k-anonymity

#### `keep`
- **Privacy technique**: No anonymization (Non-sensitive field)
- Retains original values for fields assessed as non-sensitive

### Summary table

| Action | Privacy technique |
|---|---|
| `drop` | Deletion |
| `keep_if_permitted_else_drop` | Conditional Deletion |
| `pseudonymize` | Pseudonymization |
| `date_floor_*` | Temporal Generalization |
| `generalize` | Generalization / Bucketing |
| `keep` | No anonymization |

All applied actions are explicitly recorded in the log.

---

### 5) Diagnosis field handling (policy-controlled)

Diagnosis-related fields are handled specially:

- If **diagnosis retention is NOT permitted**:
  - diagnosis fields are treated as `drop`
- If **diagnosis retention IS permitted**:
  - diagnosis fields may be retained or weakly transformed
  - this decision is recorded in the log

---

### 6) Output generation

For each input file:

- An anonymized file is written:
  - `<original_stem>_anonymized.<ext>`
- A corresponding log file is written:
  - `<original_stem>_anonymized_log.json`

The anonymized file preserves:
- row count
- field order (except for dropped/expanded fields)


## Anonymization log (`*_anonymized_log.json`)

Each log file records:

- original filename
- anonymization level (`low` / `high`)
- diagnosis permission flag
- per-field entries:
  - original field name
  - inferred semantic
  - applied action
  - any action-specific parameters


## Usage

Run from repository root:

```bash
python "tabular_anonymizer/tabular_anonymizer.py"
```

Then, in the GUI:
1. Select one or more CSV / Excel files
2. Select anonymization level (low / high)
3. (Optional) Enable diagnosis retention
4. (Optional) Select output directory
5. Start anonymization

How to use:
![Anonymizer_Pipeline](https://github.com/labhai/Tabular-Anonymization/blob/main/data/tabular-transformer.png)


## Output

For an input file: `patients.csv`
The anonymizer produces: `patients_anonymized.csv` , `patients_anonymized_log.json`

These filenames are used by the verifier for automatic matching.

### Supported inputs

- CSV (`*.csv`)
- Excel (`*.xlsx`, `*.xls`)

### Multiple file selection

The GUI supports selecting multiple CSV or Excel files at once through a multi-file picker.

When multiple input files are selected:

- Each file is processed independently using the same selected policy (low or high) and configuration
- Anonymized outputs are generated per input file
- Verification reports include the original file name so that users can trace results for each file individually
