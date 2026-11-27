#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Единые правила отбора объявлений в ТГ-дайджест.

Единственный источник истины для «что попадает в рассылку» — используется и
build_dashboard.py (сборка снапшота), и tg_digest.py (защитная перепроверка
перед отправкой). Исключения касаются ТОЛЬКО рассылки, не дашборда/шорт-листа.

Правила:
  - комнаты: целое 3–6 (int, не bool);
  - рынок: вторичка / новостройка;
  - район: канон из CANON_DISTRICTS (допускаются регистр/пробелы/дефисы/ё);
    «Ново-Переделкино» исключён; неизвестный/пустой район не включаем молча;
  - площадь: >= 75 м² (75 ровно — можно); неизвестная площадь не включаем;
  - доля (share_amount): непустая строка (напр. «1/2», «67%») → исключаем.
"""
import re

CAP = 15
MIN_AREA = 75.0
MIN_ROOMS, MAX_ROOMS = 3, 6
MARKETS = ("вторичка", "новостройка")

CANON_DISTRICTS = [
    "Академический",
    "Гагаринский",
    "Ломоносовский",
    "Обручевский",
    "Тёплый Стан",
    "Ново-Переделкино",
    "Проспект Вернадского",
    "Раменки",
    "Тропарёво-Никулино",
]
EXCLUDED_DISTRICTS = {"Ново-Переделкино"}

_WS = re.compile(r"[\s\u00a0\u2009\u200b_-]+")


def normalize_district(name):
    if name is None:
        return ""
    s = str(name).replace("ё", "е").replace("Ё", "Е")
    return _WS.sub("", s).lower()


_CANON_NORM = {normalize_district(d): d for d in CANON_DISTRICTS}


def canon_district(name):
    """Каноническое имя района либо None (неизвестный/пустой)."""
    return _CANON_NORM.get(normalize_district(name))


def has_share(share_amount):
    """Доля (непустая строка, напр. «1/2», «67%») → True; None/'' → False."""
    if share_amount is None:
        return False
    return bool(str(share_amount).strip())


def is_eligible(o):
    """True, если объявление проходит фильтры ТГ-дайджеста."""
    rooms = o.get("rooms")
    if not (isinstance(rooms, int) and not isinstance(rooms, bool)
            and MIN_ROOMS <= rooms <= MAX_ROOMS):
        return False
    if o.get("housing_type") not in MARKETS:
        return False
    d = canon_district(o.get("district"))
    if d is None or d in EXCLUDED_DISTRICTS:
        return False
    area = o.get("total_area")
    if isinstance(area, bool) or not isinstance(area, (int, float)):
        return False
    if not MIN_AREA <= area < float("inf"):
        return False
    if has_share(o.get("share_amount")):
        return False
    return True


MARKET_ORDER = {"вторичка": 0, "новостройка": 1}


def sort_key(o):
    """Сортировка свежих по rooms+market (вторичка перед новостройкой)."""
    rooms = o.get("rooms")
    return (rooms if isinstance(rooms, int) and not isinstance(rooms, bool) else 99,
            MARKET_ORDER.get(o.get("housing_type"), 2))


def sort_fresh(fresh):
    return sorted(fresh, key=sort_key)
