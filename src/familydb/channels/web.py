"""The web channel: talk to the bot from the page, through the same pipeline as a chat app.

A turn is a model call, and a model call that runs tools can take the better part of a minute.
That is far longer than a browser should be held on a form post, so the page hands the message
over and comes straight back. The thinking happens on its own thread; the only thing the page
ever reads is the message log, which the pipeline writes as it goes. A reply therefore survives
the browser being closed or refreshed, and everyone looking at the same chat sees it.

One turn at a time per chat. Two at once would each build their history from a conversation the
other was halfway through writing, and both would be paid for, so a second message sent while
the first is still being thought about is refused rather than queued.
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
from familydb.channels.base import IncomingMessage
from familydb.dates import utc_iso
from familydb.delivery import deliver
from familydb.pipeline import handle_incoming
from familydb.store import members, messages

log = logging.getLogger(__name__)

CHANNEL = "web"
DEFAULT_CHAT = "web"
# Longer than anyone types into a chat box, and well inside the body the page will accept.
MAX_MESSAGE = 4000
NOTHING_SAID = "There was nothing to send."
TOO_LONG = f"That is longer than {MAX_MESSAGE} characters. Send it in a couple of messages."
BUSY = "Still thinking about the last message. Give it a moment."
UNKNOWN_MEMBER = "There is nobody called {name} in the family."
THREAD_NAME = "familydb-web-chat"


def incoming(text: str, member_name: str, chat_id: str = DEFAULT_CHAT) -> IncomingMessage:
    """Web messages name the sender the way console messages do, and never repeat an update id.

    The page names the sender: whoever is signed in, or, while the family still shares one
    password, whoever the person said they were. Either way it is resolved against the family
    list by display name.
    """
    return IncomingMessage(
        channel=CHANNEL,
        channel_update_id=uuid4().hex,
        chat_id=chat_id,
        channel_user_id=member_name,
        text=text,
    )


@dataclass(frozen=True)
class Handing:
    """A message a turn was started for: who sent it, what it says, and its update id."""

    update_id: str
    member_name: str
    text: str


class WebChat:
    """What this process is thinking about, and how to start it thinking about something else.

    Built once per served page and kept in the Flask configuration, because a turn outlives the
    request that asked for it: the page that comes back next is a different request looking at
    the same message log.
    """

    def __init__(self, app: App, *, api: MessagesAPI | None = None) -> None:
        self.app = app
        self._api = api  # a test's fake model; the real one is chosen per turn from the settings
        self._running: dict[str, threading.Thread] = {}
        self._handing: dict[str, Handing] = {}
        self._lock = threading.Lock()

    def busy(self, chat_id: str = DEFAULT_CHAT) -> bool:
        """Whether a turn for this chat is being thought about, here or by the retry job."""
        with self._lock:
            if self._alive(chat_id):
                return True
        # The retry job picks up a message a restart interrupted, on its own thread and under
        # a claim; that is a turn in this chat as much as one started from the page.
        with closing(self.app.connect()) as conn:
            return messages.claimed_in_chat(conn, chat_id, now=utc_iso(self.app.clock.now()))

    def handing_over(self, chat_id: str = DEFAULT_CHAT) -> Handing | None:
        """The message a turn here is running for, while it runs.

        The turn stores it a moment after it starts (after naming where the phone is, which can
        wait on the map service), and the browser comes straight back to the page, often sooner.
        The page draws it from here until the log has it, so a message never seems to vanish.
        """
        with self._lock:
            return self._handing.get(chat_id) if self._alive(chat_id) else None

    def _alive(self, chat_id: str) -> bool:
        """Caller holds the lock. Forgets a thread that has finished, so the table stays small."""
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
    ) -> str | None:
        """Start a turn. None when it started, else what to tell whoever sent it.

        The sender is checked here rather than in the thread: the pipeline turns an unknown one
        away without storing anything, and a message that simply vanished from the page would be
        a mystery. The window between this check and the turn is a member being deactivated mid
        message, which the pipeline still refuses safely.
        """
        text = text.strip()
        if not text:
            return NOTHING_SAID
        if len(text) > MAX_MESSAGE:
            return TOO_LONG
        with closing(self.app.connect()) as conn:
            if members.find_by_name(conn, member_name) is None:
                return UNKNOWN_MEMBER.format(name=member_name)
            if messages.claimed_in_chat(conn, chat_id, now=utc_iso(self.app.clock.now())):
                return BUSY
        message = incoming(text, member_name, chat_id)
        with self._lock:
            if self._alive(chat_id):
                return BUSY
            # Started under the lock: a thread that exists but has not started yet is not alive,
            # and a second message arriving in that gap would be let through.
            thread = threading.Thread(
                target=self._turn,
                args=(message, member_name, chat_id, position),
                name=f"{THREAD_NAME}-{chat_id}",
                daemon=True,  # a stuck model call must not hold the process open on shutdown
            )
            self._running[chat_id] = thread
            self._handing[chat_id] = Handing(message.channel_update_id or "", member_name, text)
            thread.start()
        return None

    def _turn(
        self,
        message: IncomingMessage,
        member_name: str,
        chat_id: str,
        position: tuple[float, float] | None = None,
    ) -> None:
        """One turn, on its own thread. Everything it produces is in the message log."""
        if position is not None:
            # Here rather than in the form post: naming the place may wait on the map service.
            self._note(member_name, position)
        try:
            reply = handle_incoming(self.app, message, api=self._api)
        except Exception:
            # The pipeline stores its own failures and the retry job picks them up. What lands
            # here is the database being unreachable, which is worth a log and nothing else.
            log.exception("the web chat turn in %s could not run", chat_id)
            return
        if reply is None:
            return
        if reply.status == "unknown_sender":
            log.warning("web chat: %s is no longer in the family", member_name)
        elif reply.out_message_id is not None:
            # The reply is already on the page; this only marks it sent, so the delivery job
            # has nothing to find.
            deliver(self.app, reply.out_message_id)

    def _note(self, member_name: str, position: tuple[float, float]) -> None:
        try:
            with closing(self.app.connect()) as conn:
                member = members.find_by_name(conn, member_name)
                if member is not None:
                    whereabouts.note(self.app, conn, member.id, *position)
        except Exception:  # where they are is a help, never a reason to drop the message
            log.exception("could not note where %s is", member_name)

    def wait(self, timeout: float = 30.0) -> bool:
        """Block until nothing is being thought about. True when it went quiet in time."""
        with self._lock:
            threads = list(self._running.values())
        for thread in threads:
            thread.join(timeout)
        return not any(thread.is_alive() for thread in threads)
