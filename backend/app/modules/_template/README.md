# Adding a new report module

1. Copy this folder to `app/modules/<module_id>/` (folder name = `id`).
2. Rename the `*.yaml.example` files to `*.yaml` and edit them.
3. Add fact columns to the conformed tables only if existing ones don't fit (new Alembic migration).
4. Add `loader.py` exposing `load(session, batch) -> int` (see `app/core/modules/loader.py`).
5. Run `pytest` — the registry validates your package and tests load every module.

No core code changes are needed for a typical module.
