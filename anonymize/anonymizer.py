import pandas as pd

from .semantics import guess_semantic_field
from .transforms import transform_series

from policy.policy_low import policy_low
from policy.policy_high import policy_high

from validation.validation_low import validate_low
from validation.validation_high import validate_high

def _get_policy(mode: str):
    return policy_high if str(mode).lower().strip() == "high" else policy_low

def anonymize_dataframe(
    df: pd.DataFrame,
    mode: str = "low",
    diagnosis_allowed: bool = False,
):
    policy = _get_policy(mode)

    out_cols: dict[str, pd.Series] = {}
    log_info: dict[str, dict] = {}

    for col in df.columns:
        sem = guess_semantic_field(str(col), df[col])
        action = policy.get(sem, "keep")

        out_cols[col] = transform_series(
            df[col],
            action,
            diagnosis_allowed=diagnosis_allowed,
            semantic=sem,
        )
        log_info[col] = {"semantic": sem, "action": action}

    out_df = pd.DataFrame(out_cols)

    if str(mode).lower().strip() == "high":
        validation_msg = validate_high(df, out_df, log_info, diagnosis_allowed)
    else:
        validation_msg = validate_low(df, out_df, log_info, diagnosis_allowed)

    return out_df, log_info, validation_msg

def anonymize_csv(
    input_path: str,
    output_path: str,
    mode: str = "low",
    diagnosis_allowed: bool = False,
    encoding: str | None = None,
):
    df = pd.read_csv(input_path, encoding=encoding) if encoding else pd.read_csv(input_path)
    out_df, log_info, validation_msg = anonymize_dataframe(
        df, mode=mode, diagnosis_allowed=diagnosis_allowed
    )
    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return out_df, log_info, validation_msg
