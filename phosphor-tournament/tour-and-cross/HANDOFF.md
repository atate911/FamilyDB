# Handoff: the cheaper Phosphor tournament

A copy of `../harness-round14-changes/` (the harness files in `harness/`, the reasons in `README.md`), saved here with this note so the work can continue in a new session.

## Where to pick up

State as of 2026-10-03: the cheaper harness (below) is built, committed and dry-run tested with
stand-in agents (split, prepare, screen, cut, final, tally, assemble, choose). No real agent has
run on it yet, and round 14 has not been launched. To continue in a fresh session:

1. Restore the harness ("Restoring it", including the round-14 copy step), start the demo
   server (`"$S/harness/serve.sh"`), and re-render round 14's carried designs so their cards exist.
2. Run round 14 by "Resuming" step 2: design, `prepare`, the screen, `cut`, the final, `tally`,
   finish, `assemble`.
3. After the round, run `python3 stages.py usage <each workflow's transcript folder>` to measure
   the saving, and check the final's order looks sensible against the screen's scores.
4. Read the rewritten `lessons-digest.md` before round 15 to make sure the learn agent kept the
   owner's words verbatim.

Restore and run steps: `../README.md`, "Restoring it" and "Resuming"; with this folder, copy `tour-and-cross/harness/.` over the harness instead.
