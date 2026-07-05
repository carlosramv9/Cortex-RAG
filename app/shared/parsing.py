"""Reusable parsers for environment-driven configuration values.

pydantic-settings JSON-decodes complex fields (list/dict/set) at the *source*
level, before any ``field_validator`` runs. Combined with ``NoDecode`` on the
field, these helpers let a single env var accept both a human-friendly
comma-separated string and a JSON array.
"""

from __future__ import annotations

import json


def parse_str_list(value: object) -> object:
    """Coerce a config value into a list of strings.

    Accepts, in order of preference:

    * an existing list/tuple -> returned as a list (passthrough on defaults);
    * a JSON array string (``'["a", "b"]'``) -> parsed via ``json.loads``;
    * a comma-separated string (``'a, b'``) -> split and trimmed.

    Any other type is returned untouched so pydantic can raise a precise
    validation error. Reuse for future list settings (extensions, languages,
    collections, ...).
    """
    if isinstance(value, (list, tuple)):
        return list(value)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("["):
            return json.loads(raw)
        return [item.strip() for item in raw.split(",") if item.strip()]

    return value
