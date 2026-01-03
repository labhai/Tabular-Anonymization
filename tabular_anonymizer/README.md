# Tabular Anonymization Transformer (`tabular_anonymizer.py`)

`tabular_anonymizer.py` applies **policy-driven anonymization** to structured tabular data
(CSV / Excel) using **semantic column inference** and produces:

- anonymized tabular files
- per-file anonymization logs (`*_anonymized_log.json`) for audit and validation

The transformer is GUI-based and supports **batch anonymization** in a single run.

---

## What this script does

### 1) Input handling
The transformer accepts one or more structured files:

- CSV (`.csv`)
- Excel (`.xlsx`, `.xls`)

Files may contain heterogeneous schemas; anonymization is applied **per file**.

---

### 2) Semantic column inference

Before anonymization, each column name is tokenized and matched against a predefined
semantic alias dictionary to infer its semantic role.

Examples of inferred semantics:
- direct identifiers: `name`, `ssn`, `passport`, `email`, `phone`
- quasi-identifiers: `age`, `gender`, `zipcode`, `address`, `visit_date`
- clinical fields: `diagnosis`, `diagnosis_code`
- non-sensitive fields: `lab_value`, `measurement`, `score`, etc.

Semantic inference is **header-based only** (no value-based inspection at this stage).

The inferred semantic for each column is recorded in the anonymization log.

---

### 3) Anonymization level selection

The transformer supports two anonymization levels:

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

---

### 4) Column-wise transformation

For each column, the transformer selects an action based on:
- inferred semantic
- anonymization level
- runtime options (e.g., diagnosis permission)

Supported transformation actions include:

- `drop`
  - replace all values with blank
- `keep_if_permitted_else_drop`
  - used for diagnosis-related fields
- `pseudonymize`
  - deterministic pseudonym generation
- `date_floor_year`
- `date_floor_decade`
- `generalize`
  - e.g., coarse bucketing
- `keep`
  - for non-sensitive fields

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
- column order (except for dropped/expanded columns)

---

## Anonymization log (`*_anonymized_log.json`)

Each log file records:

- original filename
- anonymization level (`low` / `high`)
- diagnosis permission flag
- per-column entries:
  - original column name
  - inferred semantic
  - applied action
  - any action-specific parameters

---

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

---

## Output

For an input file: `patients.csv`
The transformer produces: `patients_anonymized.csv` , `patients_anonymized_log.json`

These filenames are used by the verifier for automatic matching.