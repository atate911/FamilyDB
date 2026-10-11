"""The web channel: the page hands a message to the same pipeline as a chat app and comes straight
back.

A turn can take most of a minute, far longer than a browser should be held on a form post, so it
runs on its own thread and the page reads only the message log, which the pipeline writes as it
goes: a reply survives the browser closing and everyone on the chat sees it. One turn at a time
per chat: two at once would build history from each other's half-written conversation and both be
paid for, so a second message is refused, not queued.
"""

from __future__ import annotations

import logging
import threading
from contextlib import closing
from dataclasses import dataclass
from uuid import uuid4

from familydb import whereabouts
from familydb.agent.loop import MessagesAPI
from familydb.app import App
from familydb.base.dates import utc_iso
from familydb.channels.base import IncomingMessage, PhotoNote
from familydb.delivery import deliver
from familydb.pipeline import handle_incoming
from familydb.store import members, messages

log = logging.getLogger(__name__)

CHANNEL = "web"
DEFAULT_CHAT = "web"
MAX_MESSAGE = 4000
NOTHING_SAID = "There was nothing to send."
TOO_LONG = f"That is longer than {MAX_MESSAGE} characters. Send it in a couple of messages."
BUSY = "Still thinking about the last message. Give it a moment."
# What the thread shows for a photo sent with no words, until the log holds it.
PHOTO_SHOWN = "(a photo)"
UNKNOWN_MEMBER = "There is nobody called {name} in the family."
THREAD_NAME = "familydb-web-chat"


def incoming(
    text: str,
    member_name: str,
    chat_id: str = DEFAULT_CHAT,
    photo: tuple[str, bytes] | None = None,
) -> IncomingMessage:
    """Web messages name the sender as console messages do and never repeat an update id.

    The page names the sender (whoever is signed in, or under the shared password whoever they
    said they were), resolved against the family list by display name. A photo comes with it as
    Telegram's does, to be looked at by the pipeline and never kept.
    """
    photos: tuple[PhotoNote, ...] = ()
    if photo is not None:
        mime, data = photo
        photos = (PhotoNote(mime, lambda: data, len(data)),)
    return IncomingMessage(
        channel=CHANNEL,
        channel_update_id=uuid4().hex,
        chat_id=chat_id,
        channel_user_id=member_name,
        text=text,
        photos=photos,
    )


@dataclass(frozen=True)
class Handing:
    update_id: str
    member_name: str
    text: str


class WebChat:
    """What this process is thinking about, and how to start it on something else.

    Built once per served page, kept in the Flask configuration: a turn outlives the request that
    asked for it.
    """

    def __init__(self, app: App, *, api: MessagesAPI | None = None) -> None:
        self.app = app
        self._api = api
        self._running: dict[str, threading.Thread] = {}
        self._handing: dict[str, Handing] = {}
        self._lock = threading.Lock()

    def busy(self, chat_id: str = DEFAULT_CHAT) -> bool:
        with self._lock:
            if self._alive(chat_id):
                return True
        # The retry job resumes an interrupted message on its own thread under a claim: a turn in
        # this chat like any other.
        with closing(self.app.connect()) as conn:
            return messages.claimed_in_chat(conn, chat_id, now=utc_iso(self.app.clock.now()))

    def handing_over(self, chat_id: str = DEFAULT_CHAT) -> Handing | None:
        """The message a turn here is running for, while it runs.

        The turn stores it a moment after starting (naming the phone's place can wait on the map
        service) while the browser is already back, so the page draws it from here until the log
        has it.
        """
        with self._lock:
            return self._handing.get(chat_id) if self._alive(chat_id) else None

    def _alive(self, chat_id: str) -> bool:
        thread = self._running.get(chat_id)
        if thread is None:
            return False
        if thread.is_alive():
            return True
        del self._running[chat_id]
        self._handing.pop(chat_id, None)
        return False

    def ask(
        self,
        text: str,
        member_name: str,
        chat_id: str = DEFAULT_CHAT,
        position: tuple[float, float] | None = None,
        photo: tuple[str, bytes] | None = None,
    ) -> str | None:
        """Start a turn. None when it started, else what to tell whoever sent it. `photo` is a
        picture sent with it (its type and bytes), any words its caption.

        The sender is checked here, not in the thread: the pipeline turns an unknown sender away
        silently, and a message that vanished from the page would be a mystery.
        """
        text = text.strip()
        if not text and photo is None:
            return NOTHING_SAID
        if len(text) > MAX_MESSAGE:
            return TOO_LONG
        with closing(self.app.connect()) as conn:
            if members.find_by_name(conn, member_name) is None:
                return UNKNOWN_MEMBER.format(name=member_name)
            if messages.claimed_in_chat(conn, chat_id, now=utc_iso(self.app.clock.now())):
                return BUSY
        message = incoming(text, member_name, chat_id, photo)
        with self._lock:
            if self._alive(chat_id):
                return BUSY
            # Started under the lock: a thread that exists but has not started is not alive, and a
            # second message in that gap would get through.
            thread = threading.Thread(
                target=self._turn,
                args=(message, member_name, chat_id, position),
                name=f"{THREAD_NAME}-{chat_id}",
                daemon=True,
            )
            self._running[chat_id] = thread
            shown = text or PHOTO_SHOWN
            self._handing[chat_id] = Handing(message.channel_update_id or "", member_name, shown)
            thread.start()
        return None

    def _turn(
        self,
        message: IncomingMessage,
        member_name: str,
        chat_id: str,
        position: tuple[float, float] | None = None,
    ) -> None:
        if position is not None:
            self._note(member_name, position)
        try:
            reply = handle_incoming(self.app, message, api=self._api)
        except Exception:
            # The pipeline stores its own failures for the retry job; what lands here is the
            # database being unreachable.
            log.exception("the web chat turn in %s could not run", chat_id)
            return
        if reply is None:
            return
        if reply.status == "unknown_sender":
            log.warning("web chat: %s is no longer in the family", member_name)
        elif reply.out_message_id is not None:
            # The reply is already on the page; this only marks it sent so the delivery job finds
            # nothing.
            deliver(self.app, reply.out_message_id)

    def _note(self, member_name: str, position: tuple[float, float]) -> None:
        try:
            with closing(self.app.connect()) as conn:
                member = members.find_by_name(conn, member_name)
                if member is not None:
                    whereabouts.note(self.app, conn, member.id, *position)
        except Exception:
            log.exception("could not note where %s is", member_name)

    def wait(self, timeout: float = 30.0) -> bool:
        with self._lock:
            threads = list(self._running.values())
        for thread in threads:
            thread.join(timeout)
        return not any(thread.is_alive() for thread in threads)
