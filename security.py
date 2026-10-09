"""Authentication helpers for the private Racket-Go administration page.

No default credentials are supplied. Configuration stays in environment
variables or Streamlit secrets, never in the product catalogue.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets as secure_random
import time
from collections.abc import Mapping, Sequence


_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000
_SALT_BYTES = 16
_HASH_KEY = "RACKET_GO_ADMIN_PASSWORD_HASH"
_PASSWORD_KEY = "RACKET_GO_ADMIN_PASSWORD"


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash suitable for the admin hash setting."""
    if not isinstance(password, str):
        raise TypeError("Le mot de passe doit être une chaîne de caractères.")
    salt = secure_random.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _ITERATIONS
    )
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a generated hash; malformed or unsupported hashes fail closed."""
    if not isinstance(password, str) or not isinstance(stored_hash, str):
        return False
    parts = stored_hash.split("$")
    if len(parts) != 4:
        return False
    algorithm, iterations, salt_hex, digest_hex = parts
    # Restrict the work factor and field sizes before invoking PBKDF2. A broken
    # configuration must not cause unbounded CPU work during authentication.
    if algorithm != _ALGORITHM or iterations != str(_ITERATIONS):
        return False
    if re.fullmatch(r"[0-9a-fA-F]{32}", salt_hex) is None:
        return False
    if re.fullmatch(r"[0-9a-fA-F]{64}", digest_hex) is None:
        return False
    try:
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), _ITERATIONS
        )
        expected = bytes.fromhex(digest_hex)
    except (ValueError, UnicodeError):
        return False
    return hmac.compare_digest(digest, expected)


def get_admin_credentials(
    secrets: Mapping[str, object] | None = None,
) -> tuple[str | None, str | None]:
    """Return (password hash, password), preferring each environment binding.

    Pass Streamlit's secrets mapping explicitly from the application. This
    module neither imports Streamlit nor reads configuration files itself.
    Empty bindings are treated as absent; non-string secret values are ignored.
    """

    def configured_value(key: str) -> str | None:
        value = os.environ.get(key)
        if value:
            return value
        if secrets is not None:
            value = secrets.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    return configured_value(_HASH_KEY), configured_value(_PASSWORD_KEY)


def credentials_configured(secrets: Mapping[str, object] | None = None) -> bool:
    """Report whether an administrator credential has been supplied."""
    stored_hash, stored_password = get_admin_credentials(secrets)
    return stored_hash is not None or stored_password is not None


def authenticate(password: str, secrets: Mapping[str, object] | None = None) -> bool:
    """Authenticate with the configured hash, or a password if no hash exists."""
    if not isinstance(password, str):
        return False
    stored_hash, stored_password = get_admin_credentials(secrets)
    if stored_hash is not None:
        return verify_password(password, stored_hash)
    if stored_password is None:
        return False
    try:
        return hmac.compare_digest(
            password.encode("utf-8"), stored_password.encode("utf-8")
        )
    except UnicodeError:
        return False


def login_allowed(
    attempts: Sequence[float],
    now: float | None = None,
    max_attempts: int = 5,
    window_seconds: float = 300,
) -> bool:
    """Allow fewer than ``max_attempts`` failures inside a rolling window.

    Attempts are timestamps in seconds. Keeping these in Streamlit session
    state limits retries within that browser session; it is not a global limit.
    """
    if max_attempts <= 0 or window_seconds <= 0:
        raise ValueError("La limite et la durée doivent être positives.")
    current_time = time.time() if now is None else now
    recent_attempts = sum(
        attempt > current_time - window_seconds for attempt in attempts
    )
    return recent_attempts < max_attempts


def _main() -> int:
    import getpass
    import sys

    password = getpass.getpass("Mot de passe administrateur (12 caractères minimum) : ")
    if len(password) < 12:
        print("Le mot de passe doit contenir au moins 12 caractères.", file=sys.stderr)
        return 1
    confirmation = getpass.getpass("Confirmez le mot de passe : ")
    if not hmac.compare_digest(password.encode("utf-8"), confirmation.encode("utf-8")):
        print("Les mots de passe ne correspondent pas.", file=sys.stderr)
        return 1
    print(hash_password(password))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
