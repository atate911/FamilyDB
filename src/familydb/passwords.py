"""The family password as it is stored: hashed, never written down in the clear.

The installer makes one up and puts it in WEB_PASSWORD, because something has to open the page the
first time. The family then chooses their own on the page, and that one is kept only as a hash in
the settings table, where the page and `familydb password` are the only things that set it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

# One password guards everything and there is no second factor, so it has to be long enough not to
# be guessed from the open internet. A short sentence is easy to remember and fits.
MIN_LENGTH = 12
# scrypt from the standard library: memory-hard, nothing to install. About 16 MB and a few tens of
# milliseconds a check, which a sign-in can afford and somebody guessing cannot multiply.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
KIND = "scrypt"
# Letters and digits that cannot be mistaken for each other when read off a screen.
READABLE = "abcdefghjkmnpqrstuvwxyzACDEFGHJKLMNPQRTUVWXY34679"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    """The password as it is stored: the kind, the cost, a fresh salt and the digest."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
    )
    return f"{KIND}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def hash_matches(stored: str, given: str) -> bool:
    """Whether `given` is the password `stored` was made from. A malformed hash matches nothing."""
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
    """A password for somebody to copy off a screen once and then replace with their own."""
    return "".join(secrets.choice(READABLE) for _ in range(length))
