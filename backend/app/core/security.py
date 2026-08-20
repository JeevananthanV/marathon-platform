import hmac
import hashlib


def verify_hmac_sha256(payload: str, secret: str, expected_signature: str) -> bool:
    """Verify HMAC SHA256 signature for webhooks and payment verification."""
    generated_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_signature, expected_signature)
