"""Passwords as stored: hashed, never in the clear.

The installer's WEB_PASSWORD opens the page the first time; then each person signs in with their
own, kept as a hash in `member_logins` (family.py). A family not yet moved to those may share
one, hashed in the settings table.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

# A password is all that stands between the internet and a signed-in page, with no second factor, so
# it must be long enough not to be guessed.
MIN_LENGTH = 12
MAX_LENGTH = 200
# A starting password is copied off a screen once and replaced at first sign-in: long enough never
# to be guessed meanwhile, short enough to type on a phone.
STARTING_LENGTH = 16
# scrypt from the standard library: memory-hard, nothing to install; about 16 MB and tens of
# milliseconds a check, which a sign-in can afford and a guesser cannot multiply.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
KIND = "scrypt"
READABLE = "abcdefghjkmnpqrstuvwxyzACDEFGHJKLMNPQRTUVWXY34679"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
    )
    return f"{KIND}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def hash_matches(stored: str, given: str) -> bool:
    try:
        kind, n, r, p, salt, digest = stored.split("$")
        if kind != KIND:
            return False
        expected = _unb64(digest)
        candidate = hashlib.scrypt(
            given.encode("utf-8", "replace"),
            salt=_unb64(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected)


def make_up(length: int = 20) -> str:
    return "".join(secrets.choice(READABLE) for _ in range(length))
