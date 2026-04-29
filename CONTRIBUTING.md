# Contributing

Thanks for considering a contribution. This is a small project; the bar is
"useful and clean," not "production hardened."

## Bug reports and feature requests

File a GitHub issue:
<https://github.com/doodek/visual-search-image-gen/issues/new/choose>

Two templates exist — please pick the matching one:

- **Bug report** — something is broken or behaves unexpectedly.
- **Feature request** — you'd like the tool to expose a new control,
  parameter, output format, etc.

The templates ask for the minimum I need to act on the issue. Filling them
in beats writing prose.

## Pull requests

PRs are welcome. Before opening one:

- Keep changes focused; one feature or fix per PR.
- Match the existing style — the codebase is small and informal.
- If you change a requirement, update [REQUIREMENTS.md](REQUIREMENTS.md).
- If your change is user-visible, update [README.md](README.md).
- If your change adds a config parameter, plumb it through both the GUI
  (`gui.py`) and the CLI / `render()` signature (`script.py`).

By submitting a PR you agree your contribution is licensed under the
project's BSD-3-Clause license, the same as the rest of the code.

## Local development

```bash
python3 -m venv .venv
.venv/bin/pip install "Pillow>=10.1" numpy
.venv/bin/python gui.py                 # GUI
.venv/bin/python script.py config.json  # CLI
```

A small test suite lives under `tests/`. Run it with:

```bash
.venv/bin/pip install pytest ruff
.venv/bin/ruff check .
.venv/bin/pytest
```

CI runs the same checks on every push and pull request — see
[.github/workflows/ci.yml](.github/workflows/ci.yml).

## If you cite this

You don't have to. BSD doesn't require it. But if
you'd like to, something like:

> Dudek, B. (2026). *imggen: Visual-search image generator* [Computer
> software]. <https://github.com/doodek/visual-search-image-gen>

And don't for get to share the result of your research! I'd love to see it!

For something more reproducible, pin a release tag (e.g. `v0.1.0`) or a
commit hash so reviewers can recover the exact version you used.
