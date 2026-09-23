"""Authenticated browser forms. All writes pass the blueprint's CSRF/origin gate."""

from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from contextlib import closing
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from itsdangerous import BadSignature, URLSafeSerializer
from pydantic import ValidationError

from familydb.dates import utc_iso
from familydb.errors import ToolError, ToolUnavailable
from familydb.pipeline import retry_message
from familydb.store import ideas, members, messages, plans
from familydb.store.db import transaction
from familydb.tools.gcal import (
    CreateEventInput,
    DeleteEventInput,
    UpdateEventInput,
    create_event,
    delete_event,
    update_event,
)
from familydb.tools.ideas import AddIdeaInput
from familydb.tools.registry import ToolContext
from familydb.tools.urls import clean_url
from familydb.web import auth

bp = Blueprint("actions", __name__)
log = logging.getLogger(__name__)
MAX_ID = 2**63 - 1


def _app():
    return current_app.config["FAMILYDB_APP"]


@bp.before_request
def protect():
    if request.method == "POST":
        if not auth.origin_ok():
            return auth.BAD_ORIGIN, 403
        if not auth.csrf_ok(request.form.get("csrf")):
            return auth.STALE_FORM, 403
    return None


def _signer():
    return URLSafeSerializer(current_app.secret_key, salt="familydb-web-form-v1")


def token(purpose: str) -> str:
    return _signer().dumps([auth.csrf_token(), purpose, uuid.uuid4().hex])


def operation(purpose: str) -> str:
    try:
        csrf, scope, nonce = _signer().loads(request.form.get("operation", ""))
        if csrf != auth.csrf_token() or scope != purpose:
            abort(400)
        return nonce
    except (BadSignature, ValueError, TypeError):
        abort(400)


def revision(record) -> str:
    return hashlib.sha256(record.model_dump_json().encode()).hexdigest()


def _idea_values(form):
    values = {
        key: form.get(key, "").strip()
        for key in ("title", "kind", "description", "location_name", "url", "setting", "weather")
    }
    if not values["title"] or len(values["title"]) > 200:
        raise ValueError("Give this idea a title of 1 to 200 characters.")
    if not values["kind"] or len(values["kind"]) > 40:
        raise ValueError("Choose a kind of idea.")
    if values["url"] and not clean_url(values["url"]):
        raise ValueError("The website must be a full http:// or https:// address.")
    for key in ("participants", "tags", "seasons"):
        values[key] = [part.strip() for part in form.get(key, "").split(",") if part.strip()]
    for key in ("duration_min", "duration_max", "cost_level", "lead_time_days"):
        raw = form.get(key, "").strip()
        values[key] = int(raw) if raw else None
        if values[key] is not None and not 0 <= values[key] <= 100000:
            raise ValueError("Durations and advance booking days must be positive numbers.")
    if (
        values["duration_min"] is not None
        and values["duration_max"] is not None
        and values["duration_min"] > values["duration_max"]
    ):
        raise ValueError("Maximum duration must be at least the minimum duration.")
    values["needs_booking"] = form.get("needs_booking") == "on"
    values = AddIdeaInput.model_validate(values).model_dump(exclude={"suggested_by"})
    status = form.get("status", "idea")
    if status not in ("idea", "planned", "done", "dropped"):
        raise ValueError("Choose a valid status.")
    return {**values, "status": status}


@bp.route("/ideas/new", methods=["GET", "POST"])
@bp.route(f"/idea/<int(max={MAX_ID}):idea_id>/edit", methods=["GET", "POST"])
def edit_idea(idea_id=None):
    app = _app()
    error = None
    status = 200
    purpose = f"idea:{idea_id}"
    with closing(app.connect()) as conn:
        record = ideas.get(conn, idea_id) if idea_id else None
        if idea_id and record is None:
            abort(404)
        form = (
            record.model_dump()
            if record
            else {
                "kind": "restaurant" if request.args.get("kind") == "restaurant" else "activity",
                "setting": "either",
                "weather": "any",
                "status": "idea",
            }
        )
        if record:
            for key in ("tags", "participants", "seasons"):
                form[key] = ", ".join(form[key])
        nonce = token(purpose)
        if request.method == "POST":
            op = operation(purpose)
            nonce = request.form["operation"]
            form = request.form.to_dict()
            try:
                values = _idea_values(form)
                with transaction(conn):
                    prior = conn.execute(
                        "SELECT result_id FROM web_submissions WHERE token = ?", (op,)
                    ).fetchone()
                    if prior:
                        return redirect(url_for("web.idea", idea_id=prior["result_id"]), 303)
                    latest = ideas.get(conn, idea_id) if idea_id else None
                    if idea_id and (
                        latest is None or request.form.get("revision") != revision(latest)
                    ):
                        raise ValueError(
                            "Someone changed this idea. Open it again before saving your changes."
                        )
                    saved = (
                        ideas.update(conn, idea_id, values, now=utc_iso(app.clock.now()))
                        if idea_id
                        else ideas.insert(conn, **values, now=utc_iso(app.clock.now()))
                    )
                    conn.execute(
                        "INSERT INTO web_submissions(token, result_id) VALUES (?, ?)",
                        (op, saved.id),
                    )
                flash("Idea saved.")
                return redirect(url_for("web.idea", idea_id=saved.id), 303)
            except (ValueError, ValidationError) as exc:
                error = (
                    "Check the selected values and numbers."
                    if isinstance(exc, ValidationError)
                    else str(exc)
                )
                status = 422
        return render_template(
            "idea_form.html",
            form=form,
            record=record,
            error=error,
            operation=nonce,
            revision=request.form.get("revision", revision(record) if record else ""),
            kinds=ideas.KIND_SUGGESTIONS,
        ), status


def _context(conn, scope):
    app = _app()
    return ToolContext(
        conn=conn,
        settings=app.settings,
        clock=app.clock,
        calendar=app.calendar,
        scratch={"calendar_scope": "web:" + scope},
    )


@bp.route("/family", methods=["GET", "POST"])
def family():
    app = _app()
    error = None
    status = 200
    with closing(app.connect()) as conn:
        if request.method == "POST":
            operation("family:add")
            name = " ".join(request.form.get("display_name", "").split())
            role = request.form.get("role", "member")
            if not name or len(name) > 80 or role not in members.ROLES:
                error, status = "Enter a name of 1 to 80 characters and choose a role.", 422
            else:
                with transaction(conn):
                    existing = next(
                        (
                            person
                            for person in members.list_all(conn, active_only=False)
                            if person.display_name.casefold() == name.casefold()
                        ),
                        None,
                    )
                    if existing:
                        error = (
                            "That name is already in the family."
                            if existing.active
                            else "That name is inactive. Restore their profile below."
                        )
                        status = 409
                    else:
                        members.add(conn, name, role, now=utc_iso(app.clock.now()))
                if not error:
                    flash(f"{name} added to the family.")
                    return redirect(url_for("actions.family"), 303)
        people = members.list_all(conn, active_only=False)
        return render_template(
            "family.html",
            people=people,
            form=request.form,
            error=error,
            operation=token("family:add"),
        ), status


@bp.route(f"/family/<int(max={MAX_ID}):member_id>/edit", methods=["GET", "POST"])
def edit_member(member_id):
    app = _app()
    error, status = None, 200
    with closing(app.connect()) as conn:
        person = members.get(conn, member_id)
        if person is None:
            abort(404)
        form = request.form if request.method == "POST" else person.model_dump()
        if request.method == "POST":
            operation(f"member:{member_id}")
            name = " ".join(form.get("display_name", "").split())
            role = form.get("role", "member")
            active = form.get("active") == "yes"
            try:
                if not name or len(name) > 80 or role not in members.ROLES:
                    raise ValueError("Enter a name of 1 to 80 characters and choose a role.")
                if form.get("active") not in {"yes", "no"}:
                    raise ValueError("Choose whether this member is active.")
                with transaction(conn):
                    latest = members.get(conn, member_id)
                    if latest is None or form.get("revision") != revision(latest):
                        raise ValueError(
                            "This profile changed. Reopen it before saving your edits."
                        )
                    everyone = members.list_all(conn, active_only=False)
                    if any(
                        p.id != member_id and p.display_name.casefold() == name.casefold()
                        for p in everyone
                    ):
                        raise ValueError("Another family member already uses that name.")
                    if (
                        latest.active
                        and latest.role == "admin"
                        and (not active or role != "admin")
                        and not any(
                            p.id != member_id and p.active and p.role == "admin" for p in everyone
                        )
                    ):
                        raise ValueError(
                            "Keep an active administrator. Add another administrator first."
                        )
                    now = utc_iso(app.clock.now())
                    busy = conn.execute(
                        "SELECT 1 FROM messages WHERE member_id = ? AND direction = 'in' "
                        "AND claim_until > ? LIMIT 1",
                        (member_id, now),
                    ).fetchone()
                    if busy:
                        raise ValueError(
                            "This member has a request running. "
                            "Wait for it to finish before editing their profile."
                        )
                    members.update_profile(
                        conn, member_id, display_name=name, role=role, active=active
                    )
                    if not active:
                        pending = conn.execute(
                            "SELECT id FROM messages WHERE member_id = ? AND direction = 'in' "
                            "AND status IN ('received', 'failed') AND give_up = 0",
                            (member_id,),
                        ).fetchall()
                        for row in pending:
                            messages.mark_failed(conn, row["id"], "member_inactive", now=now)
                            messages.give_up(conn, row["id"])
                flash("Family profile saved.")
                return redirect(url_for("actions.family"), 303)
            except ValueError as exc:
                error, status = str(exc), 422
        return render_template(
            "member_form.html",
            person=person,
            form=form,
            error=error,
            operation=token(f"member:{member_id}"),
            revision=form.get("revision", revision(person)),
        ), status


@bp.route("/plans/new", methods=["GET", "POST"])
@bp.route(f"/plan/<int(max={MAX_ID}):plan_id>/edit", methods=["GET", "POST"])
def edit_plan(plan_id=None):
    app = _app()
    error = None
    status = 200
    purpose = f"plan:{plan_id}"
    with closing(app.connect()) as conn:
        record = plans.get(conn, plan_id) if plan_id else None
        if plan_id and record is None:
            abort(404)
        form = record.model_dump() if record else {}
        if record:
            for key in ("start", "end"):
                if form[key] and not record.all_day:
                    form[key] = (
                        datetime.fromisoformat(form[key])
                        .astimezone(app.settings.tzinfo)
                        .strftime("%Y-%m-%dT%H:%M")
                    )
        idea_id = request.args.get("idea_id", type=int)
        idea = ideas.get(conn, idea_id) if idea_id and 0 < idea_id <= MAX_ID else None
        if idea and not record:
            form.update(title=idea.title, location=idea.location_name, idea_id=idea.id)
        nonce = token(purpose)
        if request.method == "POST":
            scope = operation(purpose)
            nonce = request.form["operation"]
            form = request.form.to_dict()
            try:
                if not form.get("title", "").strip():
                    raise ValueError("Give your plan a title.")
                values = {
                    key: form.get(key, "").strip()
                    for key in ("title", "start", "location", "notes")
                }
                values["end"] = form.get("end", "").strip() or None
                values["all_day"] = form.get("all_day") == "on"
                if "start_date" in form:
                    for field in ("start", "end"):
                        day = form.get(f"{field}_date", "")
                        hour = form.get(f"{field}_time", "")
                        if field == "end" and not day and not hour:
                            values[field] = None
                            continue
                        if not day or (not values["all_day"] and not hour):
                            raise ValueError("Choose a date and time, or select All day.")
                        values[field] = day if values["all_day"] else f"{day}T{hour}"
                ctx = _context(conn, scope)
                if plan_id:
                    update_event(ctx, UpdateEventInput(plan_id=plan_id, **values))
                else:
                    selected = int(form["idea_id"]) if form.get("idea_id") else None
                    if selected is not None and not 0 < selected <= MAX_ID:
                        raise ValueError("Choose a valid idea.")
                    created = create_event(ctx, CreateEventInput(idea_id=selected, **values))
                    with transaction(conn):
                        plans.update(
                            conn,
                            created["plan"]["id"],
                            {"channel": "web", "chat_id": "web:family"},
                            now=utc_iso(app.clock.now()),
                        )
                flash("Plan saved to the family calendar.")
                return redirect(url_for("web.plans"), 303)
            except (ToolError, ToolUnavailable, ValueError, ValidationError) as exc:
                error = (
                    str(exc)
                    if not isinstance(exc, ValidationError)
                    else "Check the dates and selected values."
                )
                status = 422
            except Exception:
                log.exception("Browser calendar save failed")
                error = (
                    "Calendar did not confirm the save. Retry this form; "
                    "a new plan will not be duplicated."
                )
                status = 503
        return render_template(
            "plan_form.html",
            form=form,
            record=record,
            error=error,
            operation=nonce,
            cancel_operation=token(f"cancel:{plan_id}"),
            connected=app.calendar is not None,
            timezone=str(app.settings.tzinfo),
            ideas=ideas.list_all(conn),
        ), status


@bp.post(f"/plan/<int(max={MAX_ID}):plan_id>/cancel")
def cancel_plan(plan_id):
    scope = operation(f"cancel:{plan_id}")
    if request.form.get("confirm") != "yes":
        abort(400)
    with closing(_app().connect()) as conn:
        if plans.get(conn, plan_id) is None:
            abort(404)
        try:
            delete_event(_context(conn, scope), DeleteEventInput(plan_id=plan_id))
            flash("Plan cancelled.")
        except (ToolError, ToolUnavailable):
            flash("Could not cancel this plan. Check the calendar connection and try again.")
        except Exception:
            log.exception("Browser calendar cancellation failed")
            flash("Calendar did not confirm cancellation. Check Plans before trying again.")
    return redirect(url_for("web.plans"), 303)


def _process(app, message_id, gate):
    try:
        retry_message(app, message_id)
    except Exception:
        log.exception("Browser assistant request failed; saved for retry")
    finally:
        gate.release()


def _start_process(app, message_id, gate):
    threading.Thread(target=_process, args=(app, message_id, gate), daemon=True).start()


@bp.post(f"/assistant/<int(max={MAX_ID}):message_id>/retry")
def retry_assistant(message_id):
    operation(f"retry:{message_id}")
    app = _app()
    with closing(app.connect()) as conn:
        row = messages.get(conn, message_id)
        if row is None or row.channel != "web" or row.direction != "in":
            abort(404)
        if row.give_up or row.retries >= app.settings.retry_max_attempts:
            flash("Retry limit reached. Check Status before sending a new request.")
            return redirect(url_for("actions.assistant"), 303)
    gate = current_app.config["FAMILYDB_WEB_CHAT_GATE"]
    if gate.acquire(blocking=False):
        try:
            _start_process(app, message_id, gate)
        except Exception:
            gate.release()
            raise
    return redirect(url_for("actions.assistant"), 303)


@bp.route("/assistant", methods=["GET", "POST"])
def assistant():
    app = _app()
    error = None
    status = 200
    form = request.form.to_dict() if request.method == "POST" else {}
    with closing(app.connect()) as conn:
        people = members.list_all(conn)
        if request.method == "POST":
            nonce = operation("assistant")
            text = form.get("message", "").strip()
            member = next((m for m in people if str(m.id) == form.get("member_id")), None)
            if not text or len(text) > 8000 or member is None:
                error, status = (
                    "Choose a family member and write a message of 1 to 8,000 characters.",
                    422,
                )
            else:
                gate = current_app.config["FAMILYDB_WEB_CHAT_GATE"]
                if not gate.acquire(blocking=False):
                    error, status = (
                        "The assistant is answering another request. "
                        "Your draft is below; try again shortly.",
                        409,
                    )
                else:
                    try:
                        with transaction(conn):
                            current_member = members.get(conn, member.id)
                            if current_member is None or not current_member.active:
                                raise ValueError(
                                    "This family member is no longer active. Choose another name."
                                )
                            prior = conn.execute(
                                "SELECT id FROM messages WHERE channel = 'web' "
                                "AND channel_update_id = ?",
                                (nonce,),
                            ).fetchone()
                            if prior:
                                message_id = prior["id"]
                            else:
                                pending = conn.execute(
                                    "SELECT id FROM messages WHERE channel = 'web' "
                                    "AND direction = 'in' AND status = 'received' "
                                    "AND give_up = 0 AND retries < ? LIMIT 1",
                                    (app.settings.retry_max_attempts,),
                                ).fetchone()
                                if pending:
                                    raise ValueError(
                                        "An earlier request is still waiting. "
                                        "Refresh the conversation before sending another."
                                    )
                                saved = messages.insert_in(
                                    conn,
                                    channel="web",
                                    channel_update_id=nonce,
                                    chat_id="web:family",
                                    member_id=member.id,
                                    text=text,
                                    now=utc_iso(app.clock.now()),
                                )
                                message_id = saved.id
                        _start_process(app, message_id, gate)
                    except ValueError as exc:
                        gate.release()
                        error, status = str(exc), 409
                    except Exception:
                        gate.release()
                        raise
                    else:
                        return redirect(url_for("actions.assistant"), 303)
        rows = conn.execute(
            "SELECT m.*, p.display_name FROM messages m "
            "LEFT JOIN members p ON p.id=m.member_id "
            "WHERE m.channel='web' AND m.chat_id='web:family' ORDER BY m.id DESC LIMIT 50"
        ).fetchall()
        pending = any(
            row["direction"] == "in"
            and row["status"] == "received"
            and not row["give_up"]
            and row["retries"] < app.settings.retry_max_attempts
            for row in rows
        )
        return render_template(
            "assistant.html",
            rows=list(reversed(rows)),
            people=people,
            form=form,
            operation=request.form.get("operation") or token("assistant"),
            error=error,
            pending=pending,
            retry_limit=app.settings.retry_max_attempts,
            retry_tokens={
                row["id"]: token(f"retry:{row['id']}")
                for row in rows
                if row["direction"] == "in" and row["status"] != "processed"
            },
        ), status
