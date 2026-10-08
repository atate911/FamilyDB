"""`maintain.sh check`: the machine's side of the report (scripts/lib/doctor.sh), read from a real
install on a temporary folder with one thing broken at a time. The program's own side is
tests/test_doctor.py.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time

import pytest

from tests.install_fixture import (
    age_file,
    corrupt,
    drop_last_migration,
    healthy_install,
    maintain,
    rows,
    stub,
    unit_file,
)

pytestmark = pytest.mark.skipif(not shutil.which("bash") or os.name == "nt", reason="needs bash")
IS_ROOT = os.geteuid() == 0 if hasattr(os, "geteuid") else False


def check(target, env, *args, **more):
    return maintain(target, env, "check", "--all", *args, **more)


def mark_of(done, name: str) -> str:
    found = rows(done.stdout)
    assert name in found, f"no row {name!r} in {sorted(found)}\n{done.stdout}"
    return found[name][0]


def detail_of(done, name: str) -> str:
    return rows(done.stdout)[name][1]


def test_an_install_that_is_well_is_all_fine_and_exits_0(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = check(target, env)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "[ OK ] All " in done.stdout
    assert "✗" not in done.stdout and " ! " not in done.stdout, done.stdout
    for section in (
        "Files",
        "Git",
        "Config",
        "Python",
        "Database",
        "Web server",
        "Host",
        "Backups",
    ):
        assert f"▸ {section}" in done.stdout, done.stdout
    assert "stopped unexpectedly" not in done.stderr


# -- the files


def test_a_program_file_that_is_gone_is_named_with_the_command_that_puts_it_back(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / "src/familydb/web/templates/base.html").unlink()
    done = check(target, env)
    assert done.returncode == 1
    assert mark_of(done, "program files") == "✗"
    assert "base.html" in detail_of(done, "program files")
    assert "checkout -- ." in done.stdout
    assert mark_of(done, "missing files") == "✗"  # and git says the same, from the other side
    assert "rescue wont-start" in done.stdout
    assert "Start here" in done.stdout


def test_an_env_file_other_users_can_read_is_a_warning_and_a_missing_one_a_failure(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").chmod(0o644)
    done = check(target, env)
    assert mark_of(done, ".env") == "!"
    assert "mode 644" in detail_of(done, ".env")
    assert done.returncode == 0  # worth a look, not a stop

    (target / ".env").unlink()
    gone = check(target, env)
    assert mark_of(gone, ".env") == "✗"
    assert gone.returncode == 1


def test_a_missing_data_folder_and_code_anyone_can_write_are_found(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / "src/familydb/cli.py").chmod(0o666)
    done = check(target, env)
    assert mark_of(done, "install folder") == "!"
    assert "src/familydb/cli.py" in detail_of(done, "install folder")

    shutil.rmtree(target / "data")
    gone = check(target, env)
    assert mark_of(gone, "data folder") == "✗"
    assert "does not exist" in detail_of(gone, "data folder")
    assert mark_of(gone, "database file") == "✗"


@pytest.mark.skipif(not IS_ROOT, reason="needs to give files to another user")
def test_files_in_the_data_folder_that_belong_to_someone_else_are_the_classic_readonly_database(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    subprocess.run(["chown", "nobody", str(target / "data/familydb.sqlite3")], check=True)
    done = maintain(target, env, "check", "--all", "--user", "root")
    assert mark_of(done, "database file") == "✗"
    assert "owned by nobody" in detail_of(done, "database file")
    assert mark_of(done, "data folder") == "✗"
    assert "readonly database" in detail_of(done, "data folder")


# -- git


def test_a_changed_tracked_file_is_a_warning_the_next_upgrade_will_meet(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    with open(target / "scripts/maintain.sh", "a") as handle:
        handle.write("\n# edited on the server\n")
    done = check(target, env)
    assert mark_of(done, "working tree") == "!"
    assert "scripts/maintain.sh" in detail_of(done, "working tree")
    assert mark_of(done, "missing files") == "✓"


def test_a_tracked_file_deleted_from_the_checkout_is_a_failure(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / "src/familydb/web/static/themes.css").unlink()
    done = check(target, env)
    assert mark_of(done, "missing files") == "✗"
    assert "themes.css" in detail_of(done, "missing files")
    assert done.returncode == 1


def test_a_folder_that_is_not_a_checkout_cannot_be_upgraded(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    shutil.rmtree(target / ".git")
    done = check(target, env)
    assert mark_of(done, "checkout") == "!"
    assert "upgrade" in detail_of(done, "checkout")


def test_a_credential_written_into_the_remote_is_said(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    subprocess.run(
        [
            "git",
            "-C",
            str(target),
            "remote",
            "set-url",
            "origin",
            "https://x-access-token:SECRET@github.com/o/r.git",
        ],
        check=True,
    )
    done = check(target, env)
    assert mark_of(done, "remote") == "!"
    assert "credential" in detail_of(done, "remote")
    assert "SECRET" not in done.stdout  # the row says it is there; it never repeats it


def test_a_missing_deploy_key_is_found_before_the_upgrade_needs_it(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    subprocess.run(
        [
            "git",
            "-C",
            str(target),
            "config",
            "core.sshCommand",
            f"ssh -i {tmp_path}/no-such-key -o IdentitiesOnly=yes",
        ],
        check=True,
    )
    done = check(target, env)
    assert mark_of(done, "deploy key") == "!"
    key = tmp_path / "key"
    key.write_text("x")
    key.chmod(0o644)
    subprocess.run(
        ["git", "-C", str(target), "config", "core.sshCommand", f"ssh -i {key}"], check=True
    )
    loose = check(target, env)
    assert "readable by others" in detail_of(loose, "deploy key")


def test_an_upgrade_that_stopped_part_way_is_said_and_one_that_finished_is_dated(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    (ledger / "upgrade-pending").write_text("target=main\nbefore=abc\nbackup=/x\n")
    done = check(target, env)
    assert mark_of(done, "upgrade") == "!"
    assert "stopped part-way" in detail_of(done, "upgrade")
    assert "rescue rollback" in done.stdout
    (ledger / "upgrade-pending").unlink()
    (ledger / "last-upgrade").write_text(
        f"at={int(time.time()) - 7200}\nfrom=abc\nfrom_label=v0.2.0+10\n"
        "to=def\nto_label=v0.2.0+12\nbackup=/x\n"
    )
    finished = check(target, env)
    assert mark_of(finished, "last upgrade") == "✓"
    assert "v0.2.0+10" in detail_of(finished, "last upgrade") and "v0.2.0+12" in detail_of(
        finished, "last upgrade"
    )


# -- .env


def test_an_env_file_that_cannot_be_read_properly_says_which_lines(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").write_text(
        "WEB_ENABLED=true\r\nWEB_PORT=8080\r\nthis line is nonsense\n"
        'ANTHROPIC_API_KEY="never closed\nTZ = UTC\n'
    )
    done = check(target, env)
    assert mark_of(done, ".env syntax") == "!"
    text = detail_of(done, ".env syntax")
    assert "line 3 is not NAME=value" in text
    assert "unclosed quote on line 4" in text
    assert "spaces before the =" in text
    assert "Windows way" in text

    (target / ".env").write_bytes(b"\xef\xbb\xbfWEB_ENABLED=true\n")
    bom = check(target, env)
    assert mark_of(bom, ".env syntax") == "✗"
    assert "byte-order mark" in detail_of(bom, ".env syntax")


def test_an_option_set_twice_says_the_last_one_wins(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").write_text("WEB_ENABLED=true\nWEB_PORT=8080\nWEB_PORT=9090\n")
    done = check(target, env)
    assert mark_of(done, "repeated options") == "!"
    assert "WEB_PORT" in detail_of(done, "repeated options")


@pytest.mark.parametrize("port", ["eighty", "80", "70000"])
def test_a_web_port_the_service_cannot_bind_is_a_failure(tmp_path, port) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").write_text(f"WEB_ENABLED=true\nWEB_PORT={port}\n")
    done = check(target, env)
    assert mark_of(done, "web port") == "✗"
    assert done.returncode == 1


def test_a_page_switched_off_is_said_and_nothing_is_asked_of_it(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").write_text("WEB_ENABLED=false\n")
    done = check(target, env)
    assert mark_of(done, "web page") == "!"
    assert "switched off" in detail_of(done, "web page")
    assert "rescue locked-out" in done.stdout
    assert "sign-in page" not in rows(done.stdout)


# -- python


def test_a_python_that_is_gone_is_a_failure_that_names_the_rebuild(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".venv/bin/python").unlink()
    done = check(target, env)
    assert mark_of(done, "interpreter") == "✗"
    assert "rescue wont-start" in done.stdout
    assert done.returncode == 1


def test_a_package_the_program_needs_that_is_not_installed_is_named(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    toml = target / "pyproject.toml"
    toml.write_text(
        toml.read_text().replace(
            '"waitress>=3.0,<4",', '"waitress>=3.0,<4",\n    "no-such-package-xyz>=1",'
        )
    )
    done = check(target, env)
    assert mark_of(done, "packages") == "✗"
    assert "no-such-package-xyz" in detail_of(done, "packages")
    assert "uv sync --frozen --no-dev" in done.stdout


def test_a_program_that_fails_to_load_shows_the_last_line_of_why(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = check(target, env, FAKE_HELP_FAIL="ModuleNotFoundError: No module named 'waitress'")
    assert mark_of(done, "program") == "✗"
    assert "No module named 'waitress'" in detail_of(done, "program")


# -- the database file


def test_a_database_that_is_not_there_is_a_failure(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / "data/familydb.sqlite3").unlink()
    done = check(target, env)
    assert mark_of(done, "database file") == "✗"
    assert "none at" in detail_of(done, "database file")


def test_a_database_sqlite_cannot_read_points_at_the_rescue(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    corrupt(target / "data/familydb.sqlite3")
    done = check(target, env)
    assert mark_of(done, "integrity") == "✗"
    assert "rescue database" in done.stdout
    assert "Break glass" in done.stdout and "rescue database" in done.stdout.split("Break glass")[1]


def test_a_database_behind_or_ahead_of_the_code_is_said_either_way(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    drop_last_migration(target / "data/familydb.sqlite3")
    behind = check(target, env)
    assert mark_of(behind, "schema") == "✗"
    assert "db migrate" in behind.stdout

    (tmp_path / "second").mkdir()
    target2, env2 = healthy_install(tmp_path / "second")
    import sqlite3

    with sqlite3.connect(target2 / "data/familydb.sqlite3") as conn:
        conn.execute("insert into schema_version (version, applied_at) values (9999, 'x')")
    ahead = check(target2, env2)
    assert mark_of(ahead, "schema") == "!"
    assert "older checkout" in detail_of(ahead, "schema")


def test_a_database_other_users_can_read_is_a_warning(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / "data/familydb.sqlite3").chmod(0o644)
    done = check(target, env)
    assert mark_of(done, "database file") == "!"
    assert "every message" in detail_of(done, "database file")


# -- the service


def test_a_unit_pointing_at_a_program_that_is_gone_is_found_without_starting_anything(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    unit_file(tmp_path, env, target, ExecStart=f"{target}/.venv/bin/no-such-program run")
    done = check(target, env)
    assert mark_of(done, "unit file") == "✗"
    assert "no-such-program" in detail_of(done, "unit file")


def test_a_sandbox_that_leaves_the_database_read_only_is_found(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    unit_file(tmp_path, env, target, ReadWritePaths=f"{target}/elsewhere")
    done = check(target, env)
    assert mark_of(done, "unit file") == "✗"
    assert "read-only" in detail_of(done, "unit file")


def test_a_well_unit_is_running_and_boots_with_the_machine(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    unit_file(tmp_path, env, target)
    done = check(target, env)
    assert mark_of(done, "unit file") == "✓"
    assert mark_of(done, "service") == "✓"
    assert "starts at boot" in detail_of(done, "service")
    assert mark_of(done, "restarts") == "✓"
    assert done.returncode == 0, done.stdout


@pytest.mark.parametrize(
    ("state", "name", "mark", "words"),
    [
        ({"active": "failed", "SubState": "failed"}, "service", "✗", "nothing is serving"),
        ({"enabled": "disabled"}, "service", "!", "will not come back"),
        ({"NRestarts": "7"}, "restarts", "✗", "crashes on start"),
        ({"NRestarts": "2"}, "restarts", "!", "2 automatic"),
        ({"Result": "oom-kill"}, "last exit", "✗", "for want of memory"),
        ({"Result": "start-limit-hit"}, "last exit", "✗", "stopped trying"),
        ({"NeedDaemonReload": "yes"}, "unit loaded", "!", "daemon-reload"),
    ],
)
def test_what_systemd_says_about_the_service_is_read(tmp_path, state, name, mark, words) -> None:
    target, env = healthy_install(tmp_path)
    unit_file(tmp_path, env, target)
    done = check(target, env, FAKE_SYSTEMD=json.dumps(state))
    assert mark_of(done, name) == mark, done.stdout
    assert words in detail_of(done, name) + done.stdout


def test_docker_that_is_down_or_a_container_that_has_stopped_is_found(tmp_path) -> None:
    target, env = healthy_install(tmp_path, docker=True)
    stub(env, "docker", "#!/bin/sh\nexit 1\n")
    down = check(target, env)
    assert mark_of(down, "docker") == "✗"
    assert "does not answer" in detail_of(down, "docker")

    stub(
        env,
        "docker",
        "#!/bin/sh\n"
        'case "$*" in\n'
        '  *"ps -a --format"*) echo "bot|exited|Exited (1) 3 minutes ago" ;;\n'
        '  *"ps -aq"*) echo abc123 ;;\n'
        "  *inspect*) echo 0 ;;\n"
        "esac\n",
    )
    stopped = check(target, env)
    assert mark_of(stopped, "service") == "✗"
    assert "exited" in detail_of(stopped, "service")


# -- the page


def test_a_page_that_does_not_answer_is_a_failure_and_the_rest_of_the_web_checks_are_left(
    tmp_path,
) -> None:
    target, env = healthy_install(tmp_path)
    done = check(target, env, FAKE_PAGES=json.dumps({"/healthz": None}), FAKE_LISTEN="none")
    assert mark_of(done, "listening") == "✗"
    assert mark_of(done, "page") == "✗"
    assert "sign-in page" not in rows(done.stdout)
    assert done.returncode == 1


def test_a_page_that_crashes_when_it_is_drawn_looks_well_at_healthz_and_is_not(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = check(
        target, env, FAKE_PAGES=json.dumps({"/": [500, {"Content-Type": "text/html"}, "oops"]})
    )
    assert mark_of(done, "page") == "✓"
    assert mark_of(done, "sign-in page") == "✗"
    assert "crashes when it is drawn" in detail_of(done, "sign-in page")


def test_another_program_on_the_port_is_not_the_page(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = check(target, env, FAKE_LISTEN="nginx")
    assert mark_of(done, "listening") == "✗"
    assert "held by nginx" in detail_of(done, "listening")


def test_missing_protections_and_missing_styles_are_found_from_outside(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    pages = {
        "/": [200, {"Content-Type": "text/html"}, "<html>"],
        "/static/style.css": [404, {}, "not found"],
    }
    done = check(target, env, FAKE_PAGES=json.dumps(pages))
    assert mark_of(done, "page headers") == "!"
    assert "content-security-policy" in detail_of(done, "page headers")
    assert mark_of(done, "styles") == "✗"
    assert "without any layout" in detail_of(done, "styles")


# -- HTTPS


def _https(tmp_path, **env_changes):
    target, env = healthy_install(tmp_path)
    (target / ".env").write_text("WEB_ENABLED=true\nWEB_PORT=8080\nWEB_DOMAIN=family.example.com\n")
    stub(env, "getent", "#!/bin/sh\necho '203.0.113.9 STREAM family.example.com'\n")
    stub(env, "caddy", "#!/bin/sh\nexit 0\n")
    stub(env, "openssl", __import__("tests.install_fixture", fromlist=["OPENSSL"]).OPENSSL)
    unit_file(tmp_path, env, target)
    caddyfile = tmp_path / "Caddyfile"
    caddyfile.write_text("family.example.com {\n  reverse_proxy 127.0.0.1:8080\n}\n")
    return target, env, caddyfile


def test_a_domain_that_does_not_resolve_is_a_failure_with_the_record_to_add(tmp_path) -> None:
    target, env, _ = _https(tmp_path)
    stub(env, "getent", "#!/bin/sh\nexit 2\n")
    done = check(target, env)
    assert mark_of(done, "dns") == "✗"
    assert "A record" in done.stdout


def test_a_domain_pointing_somewhere_else_is_a_warning_that_names_both_addresses(tmp_path) -> None:
    target, env, _ = _https(tmp_path)
    stub(env, "getent", "#!/bin/sh\necho '198.51.100.7 STREAM family.example.com'\n")
    done = check(target, env)
    assert mark_of(done, "dns") == "!"
    assert "198.51.100.7" in detail_of(done, "dns") and "203.0.113.9" in detail_of(done, "dns")


def test_caddy_that_is_down_or_pointed_at_the_wrong_port_is_found(tmp_path) -> None:
    target, env, _ = _https(tmp_path)
    done = check(target, env, FAKE_SYSTEMD=json.dumps({"caddy": "inactive"}))
    assert mark_of(done, "caddy") == "✗"
    assert "nobody can open the page from outside" in detail_of(done, "caddy")


def test_a_certificate_that_is_missing_or_about_to_expire_is_found(tmp_path) -> None:
    target, env, _ = _https(tmp_path)
    none = check(target, env, FAKE_CERT="no")
    assert mark_of(none, "certificate") == "✗"
    assert "could not get one" in detail_of(none, "certificate")
    soon = check(target, env, FAKE_CERT_END="Jan  1 00:00:00 2000 GMT")
    assert mark_of(soon, "certificate") == "✗"
    assert "expired" in detail_of(soon, "certificate")


def test_a_firewall_that_shuts_the_ports_is_a_warning(tmp_path) -> None:
    target, env, _ = _https(tmp_path)
    stub(
        env,
        "ufw",
        "#!/bin/sh\nprintf 'Status: active\\n\\nTo Action From\\n22/tcp ALLOW Anywhere\\n'\n",
    )
    done = check(target, env)
    assert mark_of(done, "firewall") == "!"
    assert "does not allow port 80" in detail_of(done, "firewall")


# -- the host


@pytest.mark.parametrize(
    ("free", "mark", "words"),
    [(50, "✗", "writes are failing"), (300, "!", "300 MB free"), (30000, "✓", "free of")],
)
def test_the_disk_is_read_in_bytes_and_in_files(tmp_path, free, mark, words) -> None:
    target, env = healthy_install(tmp_path)
    done = check(target, env, FAKE_DF_FREE_MB=str(free))
    assert mark_of(done, "disk space") == mark
    assert words in detail_of(done, "disk space")


def test_a_disk_out_of_file_slots_is_a_failure_though_it_has_room(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = check(target, env, FAKE_DF_INODE_PERCENT="99")
    assert mark_of(done, "inodes") == "✗"


def test_little_memory_or_no_swap_on_a_small_machine_is_a_warning(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 512000 kB\nMemAvailable: 300000 kB\nSwapTotal: 0 kB\n")
    done = check(target, env)
    assert mark_of(done, "memory") == "!"
    assert "Killed" in detail_of(done, "memory")
    meminfo.write_text("MemTotal: 4096000 kB\nMemAvailable: 40000 kB\nSwapTotal: 0 kB\n")
    squeezed = check(target, env)
    assert "will kill something" in detail_of(squeezed, "memory")


def test_a_clock_that_is_wrong_and_a_disk_gone_read_only_are_found(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    stub(env, "timedatectl", "#!/bin/sh\necho no\n")
    stub(env, "findmnt", "#!/bin/sh\necho ro,relatime\n")
    done = check(target, env)
    assert mark_of(done, "clock") == "!"
    assert mark_of(done, "file system") == "✗"
    assert "read-only" in detail_of(done, "file system")


def test_errors_in_the_service_log_in_the_last_day_are_counted(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    unit_file(tmp_path, env, target)
    stub(
        env,
        "journalctl",
        "#!/bin/sh\necho 'Sep 14 familydb: ERROR digest failed'\n"
        "echo 'Sep 14 familydb: ERROR again'\n",
    )
    done = check(target, env)
    assert mark_of(done, "log") == "!"
    assert "2 error line(s)" in detail_of(done, "log")
    assert "again" in detail_of(done, "log")


# -- backups


def test_backups_that_are_stale_missing_or_unscheduled_are_each_said(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    age_file(target / "backups/familydb-20260914030000.sqlite3", 50)
    stale = check(target, env)
    assert mark_of(stale, "backup files") == "!"
    assert "36 hours" in detail_of(stale, "backup files")

    (target / "backups/familydb-20260914030000.sqlite3").unlink()
    none = check(target, env)
    assert mark_of(none, "backup files") == "!"
    assert "none in" in detail_of(none, "backup files")

    stub(env, "crontab", "#!/bin/sh\nexit 1\n")
    unscheduled = check(target, env)
    assert mark_of(unscheduled, "backup schedule") == "!"


# -- the program's side joins the machine's


def test_the_programs_rows_join_the_machines_under_their_own_headings(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    report = (
        "▸ Model\n! spending today: $2.10 of $2.00: used up\n    → Raise the limit\n"
        "✓ model key: configured\n\nIt will run."
    )
    done = check(target, env, FAKE_DOCTOR=report)
    assert "▸ Model" in done.stdout
    assert mark_of(done, "spending today") == "!"
    assert "Raise the limit" in done.stdout
    assert done.returncode == 0
    assert "[WARN] Nothing is broken; 1 thing worth a look" in done.stdout
    assert (
        "It will run." in done.stdout
    )  # its own verdict, with nothing of the machine's to contradict it


def test_a_program_that_prints_no_report_is_a_row_with_why_and_not_a_silent_pass(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    done = check(target, env, FAKE_DOCTOR="")
    assert mark_of(done, "its own check") == "✗"
    assert "printed no report" in detail_of(done, "its own check")
    assert done.returncode == 1


def test_a_name_is_reported_once_and_the_machines_word_wins(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    unit_file(tmp_path, env, target)
    done = check(
        target,
        env,
        FAKE_DOCTOR="▸ Running\n· service: no systemd unit\n✓ scheduled jobs: ticking\n\nok",
    )
    assert mark_of(done, "service") == "✓"
    assert done.stdout.count("service ") >= 1
    assert "no systemd unit" not in done.stdout


# -- the view


def test_the_default_view_folds_what_is_well_and_opens_what_is_not(tmp_path) -> None:
    target, env = healthy_install(tmp_path)
    (target / ".env").chmod(0o644)
    done = maintain(target, env, "check")
    out = done.stdout
    assert "▸ Files" in out and "!" in out
    assert "✓ Git" in out  # a section with nothing wrong is one line
    assert "▸ Git" not in out
    assert "other users on this machine can read your keys" in out
    assert "fine:" in out  # and the section that is open says how many of its rows were fine
    full = check(target, env)
    assert "▸ Git" in full.stdout
