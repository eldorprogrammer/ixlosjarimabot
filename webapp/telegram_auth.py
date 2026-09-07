"""
Telegram MiniApp (WebApp) dan kelgan initData ni tekshirish (HMAC orqali).
https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
"""
import hashlib
import hmac
import json
from urllib.parse import parse_qsl


def validate_init_data(init_data: str, bot_token: str):
    """initData satrini tekshiradi. To'g'ri bo'lsa (True, user_dict) qaytaradi, aks holda (False, None)."""
    if not init_data:
        return False, None
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return False, None

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return False, None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return False, None

    user = {}
    if "user" in pairs:
        try:
            user = json.loads(pairs["user"])
        except json.JSONDecodeError:
            pass
    return True, user
