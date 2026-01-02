import pandas as pd
from .validation_common import check_column_compliance

def _is_nan_colname(col):
    if col is None:
        return True
    if isinstance(col, float) and pd.isna(col):
        return True
    s = str(col).strip()
    return (s == "" or s.lower() == "nan")

def _safe_get_anon_column(df_anon: pd.DataFrame, orig_col_name):
    if orig_col_name in df_anon.columns:
        return {orig_col_name: df_anon[orig_col_name]}
    prefix = str(orig_col_name) + "_"
    matched = {c: df_anon[c] for c in df_anon.columns if str(c).startswith(prefix)}
    return matched if matched else None

def validate_low(df_orig, df_anon, log_info, diagnosis_allowed: bool):
    result_msgs = []
    for col in df_orig.columns:
        if _is_nan_colname(col):
            result_msgs.append("WARN - 이름 없는 컬럼은 검사에서 제외되었습니다.")
            continue

        orig = df_orig[col]
        anon_cols = _safe_get_anon_column(df_anon, col)

        if anon_cols is None:
            result_msgs.append(f"WARN - '{col}' 컬럼이 익명화 결과에 존재하지 않습니다(삭제/분해 여부 확인).")
            continue

        for anon_name, anon_series in anon_cols.items():
            meta = log_info.get(anon_name, log_info.get(col, {}))
            semantic = meta.get("semantic", "")
            action = meta.get("action", "")
            status, msg = check_column_compliance(orig, anon_series, semantic, action, diagnosis_allowed)
            result_msgs.append(f"{status} - {col} → {anon_name}: {msg}")

    return {
        "pass": [m for m in result_msgs if m.startswith("PASS")],
        "warn": [m for m in result_msgs if m.startswith("WARN")],
        "fail": [m for m in result_msgs if m.startswith("FAIL")],
    }
