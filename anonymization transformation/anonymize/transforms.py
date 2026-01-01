import re
import pandas as pd

from .common_hash import stable_token
from .name_masking import pseudonymize_name_series

def _blank_series_like(series: pd.Series) -> pd.Series:
    return pd.Series([""] * len(series), index=series.index)

def pseudonymize_generic_series(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str)
    return s.apply(lambda v: "" if str(v).strip() == "" else stable_token(str(v)))

def floor_to_year(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, errors="coerce")
    years = dt.dt.year
    out = years.astype("Int64").astype(str)
    out = out.where(dt.notna(), "")
    out = out.apply(lambda y: f"{y}-01-01" if y not in ("", "<NA>", "<na>") else "")
    return out

def floor_to_decade(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, errors="coerce")
    years = dt.dt.year
    decade = (years // 10) * 10
    out = decade.astype("Int64").astype(str)
    out = out.where(dt.notna(), "")
    out = out.apply(lambda y: f"{y}-01-01" if y not in ("", "<NA>", "<na>") else "")
    return out

def normalize_marital_prefix(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.lower().str.strip()
    out = []
    for v in s:
        if v == "":
            out.append("")
            continue
        if v.startswith("mr") or " mr" in v:
            out.append("married")
        elif v.startswith("mrs") or " mrs" in v:
            out.append("married")
        elif v.startswith("miss") or v.startswith("ms") or " ms" in v:
            out.append("single")
        else:
            out.append("")
    return pd.Series(out, index=s.index)

def region_generalize(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str)
    out = []
    for v in s:
        vv = v.strip()
        if vv == "":
            out.append("")
            continue
        toks = vv.replace("\n", " ").replace(",", " ").split()
        if len(toks) >= 2:
            out.append(" ".join(toks[:2]))
        else:
            out.append(toks[0])
    return pd.Series(out, index=s.index)

def mask_zip_leading(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.strip()
    out = []
    for v in s:
        if v == "":
            out.append("")
            continue
        digits = re.sub(r"\D", "", v)
        if digits == "":
            out.append("")
            continue
        digits = digits.zfill(5)[:5]
        out.append(digits[:3] + "00")
    return pd.Series(out, index=s.index)

def drop_zip_detail(series: pd.Series) -> pd.Series:
    return mask_zip_leading(series)

def transform_series(
    series: pd.Series,
    action: str,
    diagnosis_allowed: bool = False,
    semantic: str | None = None,
) -> pd.Series:
    s = series.fillna("").astype(str)
    action = str(action or "").strip()

    if action == "drop":
        return _blank_series_like(s)

    if action == "keep":
        return s

    if action == "keep_if_permitted_else_drop":
        return s if diagnosis_allowed else _blank_series_like(s)

    if action == "pseudonymize":
        if (semantic or "").lower().strip() == "name":
            return pseudonymize_name_series(s)
        return pseudonymize_generic_series(s)

    if action == "date_floor_year":
        return floor_to_year(s)

    if action == "date_floor_decade":
        return floor_to_decade(s)

    if action == "normalize_marital_prefix":
        return normalize_marital_prefix(s)

    if action == "region_generalize":
        return region_generalize(s)

    if action in ("mask_zip_leading", "drop_zip_detail"):
        return mask_zip_leading(s)

    return _blank_series_like(s)
