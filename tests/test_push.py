"""Web push (familydb/push.py): the encryption against RFC 8291's own example, the signature a
push service checks, and who is told of what."""

from __future__ import annotations

import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from familydb import push
from familydb.push import b64, unb64

# RFC 8291, Appendix A: "When I grow up, I want to be a watermelon".
PLAINTEXT = b"When I grow up, I want to be a watermelon"
AS_PRIVATE = "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"
UA_PUBLIC = (
    "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4"
)
AUTH_SECRET = "BTBZMqHH6r4Tts7J_aSIgg"
SALT = "DGv6ra1nlYgDCS1FRnbzlw"
BODY = (
    "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27ml"
    "mlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPT"
    "pK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN"
)


def test_a_message_is_encrypted_exactly_as_rfc_8291_shows():
    sender = ec.derive_private_key(int.from_bytes(unb64(AS_PRIVATE), "big"), ec.SECP256R1())
    body = push.encrypt(
        PLAINTEXT, unb64(UA_PUBLIC), unb64(AUTH_SECRET), salt=unb64(SALT), sender=sender
    )
    assert b64(body) == BODY


def test_a_push_service_can_check_who_signed_the_request():
    key = push.Key.generate()
    said = push.signed("https://web.push.apple.com/QGuQyavXutnMm", key, "mailto:a@b.c", 1000.0)
    token, public = said.removeprefix("vapid t=").split(", k=")
    header, claims, signature = token.split(".")
    assert json.loads(unb64(header)) == {"typ": "JWT", "alg": "ES256"}
    assert json.loads(unb64(claims)) == {
        "aud": "https://web.push.apple.com",
        "exp": 1000 + push.SIGNED_FOR,
        "sub": "mailto:a@b.c",
    }
    raw = unb64(signature)
    verifier = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), unb64(public))
    verifier.verify(
        encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
        f"{header}.{claims}".encode(),
        ec.ECDSA(hashes.SHA256()),
    )
    assert push.Key.from_secret(key.secret).public == key.public


def test_a_device_key_off_the_curve_is_refused():
    assert push.valid_device(UA_PUBLIC, AUTH_SECRET)
    assert not push.valid_device(b64(b"\x04" + b"\x01" * 64), AUTH_SECRET)
    assert not push.valid_device(UA_PUBLIC, b64(b"short"))


UA_PRIVATE = "q1dXpw3UpT5VOmu_cf_v6ih07Aems3njxI-JWgLcM94"


def _opened(body: bytes) -> dict:
    """What the test device reads: the message decrypted with its own key (RFC 8291, receiving)."""
    import hashlib
    import hmac

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt, size, sender = body[:16], body[20], body[21 : 21 + body[20]]
    sealed = body[21 + size :]
    own = ec.derive_private_key(int.from_bytes(unb64(UA_PRIVATE), "big"), ec.SECP256R1())
    mine = own.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    shared = own.exchange(
        ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), sender)
    )

    def hkdf(salt, ikm, info, n):
        prk = hmac.new(salt, ikm, hashlib.sha256).digest()
        return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()[:n]

    ikm = hkdf(unb64(AUTH_SECRET), shared, b"WebPush: info\x00" + mine + sender, 32)
    cek = hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    plain = AESGCM(cek).decrypt(nonce, sealed, None)
    assert plain.endswith(b"\x02")
    return json.loads(plain[:-1])


def _sent_on_her_own(conn, chat_id: str, event: str | None = "reminder") -> int:
    from familydb.store import db, messages

    with db.transaction(conn):
        out = messages.insert_out(
            conn,
            channel="web",
            chat_id=chat_id,
            text="Reminder: bins out.",
            now="2026-09-20T21:03:00Z",
        )
        if event:
            messages.mark_sent_as(conn, out.id, event)
    return out.id


def test_she_is_said_to_have_written_to_whoever_reads_it_and_never_what(
    settings, clock, conn, family
):
    from familydb import family as rules
    from familydb.app import App
    from familydb.delivery import deliver
    from familydb.store import push as store

    app = App(settings, clock)
    push.ensure_key(conn, "2026-09-20T21:03:00Z")
    for member, endpoint in (
        (family["sam"], "https://push.example/sam"),
        (family["girls"], "https://push.example/girls"),
    ):
        rules.subscribe_push(
            conn, member, endpoint=endpoint, p256dh=UA_PUBLIC, auth=AUTH_SECRET, now=clock.now()
        )
    posted: list[tuple[str, bytes, dict]] = []
    answer = {"status": 201}
    app.notifiers["web"] = push.Pusher(
        app,
        post=lambda endpoint, body, headers: (
            posted.append((endpoint, body, headers)) or answer["status"]
        ),
        later=lambda job: job(),
    )
    assert deliver(app, _sent_on_her_own(conn, "web"))
    ((endpoint, body, headers),) = posted  # the family's conversation: the grown-ups' devices
    assert endpoint == "https://push.example/sam"
    assert _opened(body) == {
        "title": "Vera has a message",
        "url": "/chat#latest",
        "tag": "chat-web",
    }
    assert headers["Content-Encoding"] == "aes128gcm" and headers["Topic"] == "chat-web"
    assert headers["Authorization"].startswith("vapid t=") and headers["TTL"] == str(push.TTL)
    deliver(app, _sent_on_her_own(conn, "web", event=None))  # a reply: they are reading it already
    assert len(posted) == 1
    girls = f"member:{family['girls'].id}"
    answer["status"] = 410  # her device has gone
    deliver(app, _sent_on_her_own(conn, girls))
    assert posted[-1][0] == "https://push.example/girls"
    assert store.for_members(conn, [family["girls"].id]) == []
    app.settings = settings.model_copy(update={"web_push": False})
    deliver(app, _sent_on_her_own(conn, "web"))
    assert len(posted) == 2


def test_a_device_is_turned_on_and_off_from_your_own_page(settings, clock, conn, family):
    import re

    from familydb.app import App
    from familydb.store import push as store
    from tests.test_web_logins import SAMS, SHARED, _as, _as_family, _browser, _tokens

    app = App(settings.model_copy(update={"web_password": SHARED}), clock)
    browser = _as_family(app)
    assert "Notifications on this device" not in browser.get("/you").text  # nobody in particular
    form = {**_tokens(browser, "/you"), "member": str(family["sam"].id), "new": SAMS, "again": SAMS}
    browser.post("/you", data=form)
    push.ensure_key(conn, "2026-09-20T21:03:00Z")
    sam = _as(app, "Sam", SAMS)
    page = sam.get("/you").text
    assert "Notifications on this device" in page and 'src="/static/push.js' in page
    key = re.search(r'data-key="([^"]+)"', page).group(1)
    assert len(unb64(key)) == 65
    csrf = re.search(r'data-csrf="([^"]+)"', page).group(1)
    device = {
        "csrf": csrf,
        "endpoint": "https://push.example/1",
        "p256dh": UA_PUBLIC,
        "auth": AUTH_SECRET,
    }
    assert sam.post("/you/push", data=device).status_code == 204
    assert [d.endpoint for d in store.for_members(conn, [family["sam"].id])] == [
        "https://push.example/1"
    ]
    bad = {**device, "endpoint": "http://not-a-push-service"}
    assert sam.post("/you/push", data=bad).status_code == 400
    assert sam.post("/you/push", data={**device, "csrf": "wrong"}).status_code == 403
    off = {"csrf": csrf, "endpoint": "https://push.example/1"}
    assert sam.post("/you/push/off", data=off).status_code == 204
    assert store.for_members(conn, [family["sam"].id]) == []
    worker = _browser(app).get("/sw.js")  # open before sign-in, like the manifest
    assert worker.status_code == 200 and worker.mimetype == "text/javascript"
