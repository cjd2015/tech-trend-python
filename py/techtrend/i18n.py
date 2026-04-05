"""Crucix Internationalization (i18n) Module"""
import os
import json
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent
LOCALES_DIR = BASE_DIR / "locales"

SUPPORTED_LOCALES = ["en", "fr"]
DEFAULT_LOCALE = "en"

locale_cache: dict = {}


def get_language() -> str:
    lang = (os.getenv("CRUCIX_LANG") or os.getenv("LANGUAGE") or os.getenv("LANG") or DEFAULT_LOCALE).lower()[:2]
    return lang if lang in SUPPORTED_LOCALES else DEFAULT_LOCALE


def load_locale(lang: str) -> dict:
    if lang in locale_cache:
        return locale_cache[lang]
    
    locale_path = LOCALES_DIR / f"{lang}.json"
    if not locale_path.exists():
        print(f"[i18n] Locale file not found: {locale_path}, falling back to {DEFAULT_LOCALE}")
        return load_locale(DEFAULT_LOCALE)
    
    try:
        with open(locale_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        locale_cache[lang] = data
        return data
    except Exception as e:
        print(f"[i18n] Failed to load locale {lang}: {e}")
        if lang != DEFAULT_LOCALE:
            return load_locale(DEFAULT_LOCALE)
        return {}


def get_locale() -> dict:
    return load_locale(get_language())


def t(key_path: str, params: Optional[dict] = None) -> str:
    locale = get_locale()
    keys = key_path.split(".")
    
    value = locale
    for key in keys:
        if value and isinstance(value, dict) and key in value:
            value = value[key]
        else:
            print(f"[i18n] Missing translation: {key_path}")
            return key_path
    
    if not isinstance(value, str):
        return key_path
    
    if params:
        for k, v in params.items():
            value = value.replace(f"{{{k}}}", str(v))
    return value


def get_supported_locales() -> list[dict]:
    return [
        {
            "code": code,
            "name": load_locale(code).get("meta", {}).get("name", code),
            "nativeName": load_locale(code).get("meta", {}).get("nativeName", code),
        }
        for code in SUPPORTED_LOCALES
    ]


current_language = get_language()
print(f"[i18n] Language: {current_language}")