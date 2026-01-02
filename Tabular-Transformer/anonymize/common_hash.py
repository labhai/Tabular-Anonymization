import os
import hmac
import hashlib

def get_salt() -> bytes:
    s = os.environ.get("ANON_SALT", "").strip()
    if not s:
        s = "DEFAULT_DEV_SALT_CHANGE_ME"
    return s.encode("utf-8")

def stable_token(value: str, n_hex: int = 12) -> str:
    v = (value or "").strip()
    if v == "":
        return ""
    digest = hmac.new(get_salt(), v.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:n_hex]
