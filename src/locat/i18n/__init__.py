"""Tiny translation helper: t(lang, key, **values)."""
from locat.i18n import en, sw

_TABLES = {"en": en.STRINGS, "sw": sw.STRINGS}


def t(lang: str, key: str, **values) -> str:
    table = _TABLES.get(lang, en.STRINGS)
    text = table.get(key) or en.STRINGS[key]  # fall back to English
    return text.format(**values) if values else text