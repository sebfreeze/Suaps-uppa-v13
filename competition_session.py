import hashlib
import hmac
import time


SESSION_SECONDS = 4 * 60 * 60


def issue_role_token(role, secret, now=None, ttl=SESSION_SECONDS):
    if not secret:
        return ""
    now = int(time.time() if now is None else now)
    expiry = now + int(ttl)
    payload = f"{role}|{expiry}"
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}|{signature}"


def validate_role_token(token, secrets_by_role, now=None):
    if not token:
        return None
    try:
        role, expiry_text, signature = str(token).rsplit("|", 2)
        expiry = int(expiry_text)
    except Exception:
        return None
    now = int(time.time() if now is None else now)
    if expiry <= now:
        return None
    secret = secrets_by_role.get(role, "")
    if not secret:
        return None
    payload = f"{role}|{expiry}"
    expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return role if hmac.compare_digest(signature, expected) else None
