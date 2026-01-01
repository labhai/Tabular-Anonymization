import re
import pandas as pd

def _tokenize(col: str) -> list[str]:
    s = str(col or "")
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"[^0-9a-zA-Z가-힣]+", " ", s.lower())
    return [t for t in s.split() if t]

SEMANTIC_ALIASES = {
    "ssn": ["ssn", "resident", "rrn", "주민", "주민번호", "주민등록"],
    "passport": ["passport", "여권"],
    "driver_license": ["driverlicense", "driver_license", "license", "운전면허"],
    "name": ["name", "full_name", "patient_name", "성명", "이름", "환자명"],
    "phone": ["phone", "tel", "mobile", "cell", "연락처", "전화"],
    "email": ["email", "e-mail", "메일"],
    "address": ["address", "addr", "주소"],
    "zipcode": ["zip", "zipcode", "postal", "우편", "우편번호"],
    "birthdate": ["birth", "dob", "birthdate", "생년월일", "출생"],
    "deathdate": ["death", "deathdate", "사망"],
    "visit_date": ["visitdate", "visit_date", "admit", "discharge", "encounterdate", "date"],
    "patient_id": ["patientid", "patient_id", "mrn", "chart", "등록번호", "환자번호", "id"],
    "gender": ["gender", "sex", "성별"],
    "age": ["age", "나이", "연령"],
    "marital_status": ["marital", "marriage", "marital_status", "혼인", "결혼"],
    "diagnosis": ["diagnosis", "dx", "icd", "진단"],
}

def guess_semantic_field(col_name: str, series: pd.Series | None = None) -> str:
    tokens = _tokenize(col_name)

    priority = [
        "ssn", "passport", "driver_license",
        "patient_id",
        "name",
        "birthdate", "deathdate",
        "phone", "email",
        "address", "zipcode",
        "diagnosis",
        "gender", "age",
        "marital_status",
        "visit_date",
    ]

    for sem in priority:
        kws = SEMANTIC_ALIASES.get(sem, [])
        for kw in kws:
            kw_tokens = _tokenize(kw)
            if not kw_tokens:
                continue
            if all(t in tokens for t in kw_tokens):
                return sem

    return "other"
