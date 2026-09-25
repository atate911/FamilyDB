"""Behaviour checks against a real model: does the bot do the right thing with the family's words?

Not part of `pytest`: each run is a paid call per message, a few cents for the whole set on the
default model. Run by hand when a prompt, a tool description or the model changes, and compare:

    uv run python -m evals                     # every case once, on the configured model
    uv run python -m evals --repeat 3          # how often each passes, not just whether
    uv run python -m evals --provider anthropic --model claude-haiku-4-5
    uv run python -m evals --level better      # the configured company's stronger model
    uv run python -m evals --case sushi_open_now --show

Grading is code, never another model: which tools ran with which arguments, what was saved, and
what the reply says. A check names what it wants, so a failure says what went wrong.
"""
