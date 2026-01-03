import re
import pandas as pd
from common_hash import stable_token

_HANGUL_NAME_RE = re.compile(r"^[가-힣]{2,4}$")

def pseudonymize_name_series(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str)

    out = []
    for v in s:
        vv = v.strip()
        if vv == "":
            out.append("")
            continue
        if _HANGUL_NAME_RE.match(vv):
            out.append(vv[0] + "00")
        else:
            out.append(stable_token(vv))
    return pd.Series(out, index=s.index)
