import base64
import hashlib
from cryptography.fernet import Fernet
from extension.backend.config import settings

def _get_fernet() -> Fernet:
    # Ensure key is 32 url-safe base64-encoded bytes
    # Hash the config key to ensure it's the correct length
    key_hash = hashlib.sha256(settings.ENCRYPTION_KEY.encode("utf-8")).digest()
    b64_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(b64_key)

def encrypt_token(token: str) -> str:
    if not token:
        return token
    f = _get_fernet()
    return f.encrypt(token.encode("utf-8")).decode("utf-8")

def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return encrypted_token
    # If the token is not encrypted (legacy or plain), Fernet throws an InvalidToken exception.
    # We try to decrypt, but if it fails, we assume it's unencrypted and return as-is.
    f = _get_fernet()
    try:
        return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except Exception:
        return encrypted_token
