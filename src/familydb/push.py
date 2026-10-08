"""Web push, for people who use only the page: a phone or tablet is told "Vera has a message" when
she writes on her own (a reminder, the morning message), so nobody has to keep the page open.

The standards, written out here rather than taken from a library that would bring an async web
stack with it: the message is encrypted to the device (RFC 8291, aes128gcm), and the request to the
browser's push service (Apple's, Google's or Mozilla's) is signed with the install's own key (VAPID,
RFC 8292). The push service sees the device's address, when, and the key's contact; never the
words, which stay on the page: what is sent says only "{name} has a message" and where to look.

Only a message she sent of her own accord (`sent_as`), once it is delivered, and only to the
people who read the conversation it went to: a kid's own conversation, her devices; the family's,
the devices of whoever may decide. What a reply carried, the person is already reading. Sent on one
background thread with a short timeout: a push that fails is logged and forgotten, a device that
is gone (404, 410) is taken off, and one that says slow down (429) is left alone for a while. It
never changes whether the message counts as delivered.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from familydb import roles
from familydb.dates import utc_iso
from familydb.store import members
from familydb.store import push as store
from familydb.store.messages import Message

log = logging.getLogger(__name__)

# How long a push service keeps trying a device that is off (seconds): half a day.
TTL = 12 * 3600
TIMEOUT = 10
RECORD_SIZE = 4096
# Left alone after a push service said too many, before it is tried again (seconds).
BACK_OFF = 10 * 60
# A signed request is good for this long (RFC 8292 allows at most a day).
SIGNED_FOR = 12 * 3600
# Where the notification opens.
OPENS = "/chat#latest"
# The key's contact, which the push service sees: the operator's (GEOCODER_CONTACT) when set,
# else the project's own address, never the family's.
CONTACT = "https://github.com/atate911/familydb"
POINT = ec.SECP256R1()
TOPIC = re.compile(r"[^A-Za-z0-9_-]")


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# -- the install's own key (VAPID)


@dataclass(frozen=True)
class Key:
    private: ec.EllipticCurvePrivateKey

    @property
    def public(self) -> bytes:
        """The public key, as a browser wants it (applicationServerKey): an uncompressed point."""
        return self.private.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )

    @property
    def secret(self) -> bytes:
        return self.private.private_numbers().private_value.to_bytes(32, "big")

    @classmethod
    def generate(cls) -> Key:
        return cls(ec.generate_private_key(POINT))

    @classmethod
    def from_secret(cls, secret: bytes) -> Key:
        return cls(ec.derive_private_key(int.from_bytes(secret, "big"), POINT))


def ensure_key(conn: sqlite3.Connection, now: str) -> Key:
    """The install's key, made once (at start, after migrating; never on a page view). It is kept
    in the database, so a backup and a restore keep every device working."""
    kept = store.key(conn)
    if kept is not None:
        return Key.from_secret(unb64(kept))
    key = Key.generate()
    store.save_key(conn, secret=b64(key.secret), public=b64(key.public), now=now)
    return key


def signed(endpoint: str, key: Key, contact: str, now: float) -> str:
    """The Authorization header for one push service (RFC 8292): a token for its origin, signed
    with the install's key, and the key itself."""
    parts = urlsplit(endpoint)
    claims = {
        "aud": f"{parts.scheme}://{parts.netloc}",
        "exp": int(now) + SIGNED_FOR,
        "sub": contact,
    }
    header = b64(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    body = b64(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{header}.{body}".encode("ascii")
    r, s = decode_dss_signature(key.private.sign(signing_input, ec.ECDSA(hashes.SHA256())))
    token = f"{header}.{body}.{b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
    return f"vapid t={token}, k={b64(key.public)}"


# -- encrypting to one device (RFC 8291)


def _hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    """HKDF-SHA-256, one block (every length here is at most 32)."""
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()[:length]


def encrypt(
    plaintext: bytes,
    device_key: bytes,
    auth_secret: bytes,
    *,
    salt: bytes | None = None,
    sender: ec.EllipticCurvePrivateKey | None = None,
) -> bytes:
    """`plaintext` for one device, as the push message body (aes128gcm, a single record).
    `device_key` is its public key (p256dh), checked to be on the curve; `salt` and `sender` are
    fresh each time unless a test gives them."""
    device = ec.EllipticCurvePublicKey.from_encoded_point(POINT, device_key)
    sender = sender or ec.generate_private_key(POINT)
    sender_public = sender.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    shared = sender.exchange(ec.ECDH(), device)
    ikm = _hkdf(auth_secret, shared, b"WebPush: info\x00" + device_key + sender_public, 32)
    salt = salt if salt is not None else os.urandom(16)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    sealed = AESGCM(cek).encrypt(nonce, plaintext + b"\x02", None)
    header = salt + RECORD_SIZE.to_bytes(4, "big") + bytes([len(sender_public)]) + sender_public
    return header + sealed


def valid_device(p256dh: str, auth: str) -> bool:
    """Whether a subscription's keys are what a browser gives: a point on the curve, and a
    16-byte secret."""
    try:
        ec.EllipticCurvePublicKey.from_encoded_point(POINT, unb64(p256dh))
        return len(unb64(auth)) == 16
    except (ValueError, TypeError):
        return False


# -- telling the devices


def topic(chat_id: str) -> str:
    """One notice per conversation on a device, the newest replacing the last."""
    return TOPIC.sub("-", f"chat-{chat_id}")[:32]


def readers(conn: sqlite3.Connection, chat_id: str) -> list[int]:
    """Who is told of a message in a page conversation: a kid's own, her; the family's, whoever
    may decide (a kid is not buzzed for the grown-ups' messages)."""
    if chat_id.startswith("member:"):
        number = chat_id.removeprefix("member:")
        return [int(number)] if number.isdigit() else []
    if chat_id != "web":
        return []
    return [m.id for m in members.list_all(conn) if roles.may(m.role, "decide")]


class Pusher:
    """What delivery calls once a message of hers is delivered on the page (`App.notifiers`)."""

    def __init__(
        self,
        app: Any,
        *,
        post: Callable[..., int] | None = None,
        later: Callable[[Callable[[], None]], Any] | None = None,
    ) -> None:
        self.app = app
        self._post = post or _post
        self._later = later or self._in_background
        self._pool: ThreadPoolExecutor | None = None
        self._quiet_until: dict[str, float] = {}

    def __call__(self, conn: sqlite3.Connection, message: Message) -> None:
        settings = self.app.settings
        if not settings.web_push or not message.sent_as:
            return
        devices = store.for_members(conn, readers(conn, message.chat_id))
        if not devices:
            return
        kept = store.key(conn)
        if kept is None:
            log.warning("push: no key yet, so devices are not told (it is made at start)")
            return
        from familydb import voice  # here, not at the top: voice reaches back into the store

        words = voice.say(settings, "push_note", seed=message.id)
        payload = json.dumps(
            {"title": words, "url": OPENS, "tag": topic(message.chat_id)},
            separators=(",", ":"),
        ).encode()
        contact = _contact(settings.geocoder_contact)
        key = Key.from_secret(unb64(kept))
        self._later(lambda: self._tell(devices, payload, key, contact, topic(message.chat_id)))

    def _tell(
        self, devices: list[store.Device], payload: bytes, key: Key, contact: str, about: str
    ) -> None:
        for device in devices:
            if self._quiet_until.get(device.endpoint, 0) > time.monotonic():
                continue
            try:
                body = encrypt(payload, unb64(device.p256dh), unb64(device.auth))
                status = self._post(
                    device.endpoint,
                    body,
                    {
                        "TTL": str(TTL),
                        "Content-Encoding": "aes128gcm",
                        "Content-Type": "application/octet-stream",
                        "Urgency": "normal",
                        "Topic": about,
                        "Authorization": signed(device.endpoint, key, contact, time.time()),
                    },
                )
            except Exception:
                log.warning("push: a device could not be told", exc_info=True)
                continue
            self._heard(device, status)

    def _heard(self, device: store.Device, status: int) -> None:
        now = utc_iso(self.app.clock.now())
        if status in (404, 410):  # the browser let it go: take it off
            with closing(self.app.connect()) as conn:
                store.forget(conn, device.endpoint)
            log.info("push: a device has gone, and was taken off")
        elif status == 429:
            self._quiet_until[device.endpoint] = time.monotonic() + BACK_OFF
            log.info("push: a push service asked to slow down")
        elif 200 <= status < 300:
            with closing(self.app.connect()) as conn:
                store.heard(conn, device.endpoint, now)
        else:
            log.warning("push: a push service answered %s", status)

    def _in_background(self, job: Callable[[], None]) -> None:
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="push")
        self._pool.submit(job)


def _contact(operator: str) -> str:
    said = (operator or "").strip()
    if said.startswith(("mailto:", "https://")):
        return said
    if "@" in said and " " not in said:
        return f"mailto:{said}"
    return CONTACT


def _post(endpoint: str, body: bytes, headers: dict[str, str]) -> int:
    import httpx

    response = httpx.post(endpoint, content=body, headers=headers, timeout=TIMEOUT)
    return response.status_code
