import pandas as pd
import re
from typing import Tuple

def _is_all_blank(series: pd.Series) -> bool:
    s = series.fillna("").astype(str).str.strip()
    return (s == "").all()

def unique_ratio(values: pd.Series) -> float:
    vals = values.fillna("").astype(str).str.strip()
    total = len(vals)
    if total == 0:
        return 0.0
    return vals.nunique() / total

_NAME_LIKE = re.compile(r"^[가-힣]{2,4}$")
_ADMIN_SUFFIX = ("시", "군", "구", "동", "읍", "면", "리")

def _is_korean_person_name_token(x: str) -> bool:
    x = str(x).strip()
    if not _NAME_LIKE.match(x):
        return False
    if x.endswith(_ADMIN_SUFFIX):
        return False
    return True

SENSITIVE_PATTERNS = [
    re.compile(r"\d{6}[-]?\d{7}"),    
    re.compile(r"\d{2,3}-\d{3,4}-\d{4}"),
    re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
]

def detect_sensitive_pattern_ratio(values: pd.Series) -> float:
    vals = values.fillna("").astype(str)
    total = len(vals)
    if total == 0:
        return 0.0

    match_count = 0
    for v in vals:
        vv = str(v)
        if _is_korean_person_name_token(vv):
            match_count += 1
            continue
        for p in SENSITIVE_PATTERNS:
            if p.search(vv):
                match_count += 1
                break
    return match_count / total

def _looks_pseudonymized(values: pd.Series) -> bool:
    vals = values.fillna("").astype(str).str.strip()
    vals = vals[vals != ""]
    if len(vals) == 0:
        return True

    sample = vals.sample(n=min(20, len(vals)), random_state=0)
    hex_re = re.compile(r"^[0-9a-fA-F]{8,}$")  # token-ish
    for v in sample:
        if re.match(r"^[가-힣]00$", v):
            continue
        if hex_re.match(v):
            continue
        return False
    return True

def _date_floor_ok(values: pd.Series, decade: bool) -> bool:
    vals = values.fillna("").astype(str).str.strip()
    vals = vals[vals != ""]
    if len(vals) == 0:
        return True

    sample = vals.sample(n=min(20, len(vals)), random_state=0)
    for v in sample:
        if not re.match(r"^\d{4}-01-01$", v):
            return False
        if decade:
            y = int(v[:4])
            if y % 10 != 0:
                return False
    return True

def check_column_compliance(
    original: pd.Series,
    anon: pd.Series,
    semantic: str,
    action: str,
    diagnosis_allowed: bool = False
) -> Tuple[str, str]:
    semantic = str(semantic or "").lower().strip()
    action = str(action or "").lower().strip()

    if action == "drop":
        if not _is_all_blank(anon):
            return "FAIL", "Expected drop, but values remain"
        return "PASS", ""

    if action == "keep_if_permitted_else_drop":
        if diagnosis_allowed:
            return "PASS", ""
        if not _is_all_blank(anon):
            return "FAIL", "Not permitted, but values remain"
        return "PASS", ""

    if action == "pseudonymize":
        ur = unique_ratio(anon)
        if ur < 0.7:
            return "WARN", f"Low uniqueness after pseudonymization: {ur:.2f}"
        if not _looks_pseudonymized(anon):
            return "WARN", "Values do not resemble pseudonyms"
        return "PASS", ""

    if action in ("date_floor_year", "date_floor_decade"):
        decade = (action == "date_floor_decade")
        if not _date_floor_ok(anon, decade=decade):
            return "FAIL", "Date not generalized as expected (YYYY-01-01)"
        return "PASS", ""

    pattern_ratio = detect_sensitive_pattern_ratio(anon)
    if pattern_ratio > 0.1:
        return "FAIL", f"Sensitive patterns remain in {pattern_ratio*100:.1f}%"
    return "PASS", ""

def compute_validation_metrics(
    df_orig,
    df_anon,
    log_info,
    diagnosis_allowed,
    validation_result,
    duration_sec
):
    total_cols = len(df_orig.columns)
    total_cells = df_orig.shape[0] * total_cols
    total_fail = len(validation_result.get("fail", []))
    total_warn = len(validation_result.get("warn", []))

    expected_actions = {k: str(v.get("action", "")).lower().strip() for k, v in log_info.items()}
    actual_cols = set(df_anon.columns)

    mismatch_count = 0
    for col, exp_action in expected_actions.items():
        if exp_action == "drop" and col in actual_cols and not (df_anon[col].fillna("").astype(str).str.strip() == "").all():
            mismatch_count += 1
    policy_consistency = 1 - (mismatch_count / len(expected_actions)) if expected_actions else 1.0

    pattern_matches = 0
    checked = 0
    for col in df_anon.columns:
        s = df_anon[col].dropna().astype(str)
        if len(s) == 0:
            continue
        sample = s.sample(n=min(20, len(s)), random_state=0)
        checked += len(sample)
        for x in sample:
            if _is_korean_person_name_token(x):
                pattern_matches += 1
                continue
            for pat in SENSITIVE_PATTERNS:
                if pat.search(str(x)):
                    pattern_matches += 1
                    break
    pattern_residual_ratio = pattern_matches / checked if checked > 0 else 0.0

    high_risk_keywords = ["ssn", "passport", "driver", "license", "name", "patient_id", "id", "birth", "death", "phone", "email", "address", "zipcode"]
    ok_actions = {"drop", "pseudonymize", "date_floor_year", "date_floor_decade", "region_generalize", "mask_zip_leading", "drop_zip_detail"}

    total_hr = 0
    missed_hr = 0
    for col, meta in log_info.items():
        sem = str(meta.get("semantic", "")).lower()
        action = str(meta.get("action", "")).lower()
        if any(k in sem for k in high_risk_keywords):
            total_hr += 1
            if action not in ok_actions:
                missed_hr += 1
    high_risk_handling_rate = 1 - (missed_hr / total_hr) if total_hr else 1.0

    return pd.DataFrame([{
        "총 컬럼 수": total_cols,
        "총 셀 수": total_cells,
        "실패 메시지 수": total_fail,
        "경고 메시지 수": total_warn,
        "정책 일관성 준수율": round(policy_consistency, 4),
        "패턴 잔존율": round(pattern_residual_ratio, 4),
        "고위험 컬럼 처리율": round(high_risk_handling_rate, 4),
        "총 처리 시간 (초)": round(float(duration_sec), 2),
    }])
