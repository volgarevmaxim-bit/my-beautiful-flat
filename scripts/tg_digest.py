#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tg_digest — ежедневная рассылка свежих объявлений ЦИАН в ТГ-группу «My beautiful flat».

Читает data/listings.json (снапшот, кладётся deploy_pages.py из
data/listings_digest.json), шлёт в чат через Bot API (stdlib, без внешних
зависимостей). Свежие группируются по «N-комн <рынок>», комнаты/рынок в строке
объявления не повторяются; итог по снятым — только за снапшот и уже отфильтрован.

Креды:
  TELEGRAM_BOT_TOKEN  — секрет Actions (обязателен)
  TELEGRAM_CHAT_ID    — секрет Actions (необязателен; без него чат ищется
                        по названию из config/telegram.json в getUpdates)

Механика:
  - при первом запуске (нет data/digest_state.json с welcome_sent) шлёт
    закрепляемое welcome-сообщение со ссылкой на дашборд;
  - далее ежедневно: список свежих объявлений (is_new за снапшот, прошедших
    фильтры), снятые с публикации (sold) — или «без изменений»;
  - ПЕРЕПРОВЕРКА перед отправкой (defense-in-depth): fresh повторно фильтруется
    по eligibility, дедуплицируется по id/url и сортируется;
  - дайджест не шлётся повторно: пропуск, если snapshot_date <= last_digest_date;
  - state коммитится обратно в репо.
"""
import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(sys.stdout, "reconfigure") else None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from digest_common import CAP, MARKET_ORDER, is_eligible, sort_fresh
except ImportError as e:  # pragma: no cover — страховка от неполного деплоя
    sys.exit(f"FAIL: digest_common.py не найден ({e}) — deploy_pages.py должен "
             f"копировать scripts/digest_common.py")

LIMIT = 4000
STATE = "data/digest_state.json"
LISTINGS = "data/listings.json"
TG_CFG = "config/telegram.json"
DASH_URL = "https://volgarevmaxim-bit.github.io/my-beautiful-flat/"


def env(name):
    return (os.environ.get(name) or "").strip().strip('"').strip("'")


def api_call(token, method, payload=None, timeout=30):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def send(token, chat_id, text):
    for i, part in enumerate(split_message(text)):
        resp = api_call(token, "sendMessage", {
            "chat_id": chat_id, "text": part,
            "link_preview_options": {"is_disabled": True},
        })
        if not resp.get("ok"):
            sys.exit(f"FAIL send: {resp.get('description')}")
        print(f"OK part {i+1}: message_id={resp['result']['message_id']}")


def split_message(text):
    if len(text) <= LIMIT:
        return [text]
    parts, cur = [], ""
    for block in text.split("\n\n"):
        if len(cur) + len(block) + 2 > LIMIT and cur:
            parts.append(cur.strip())
            cur = block
        else:
            cur = f"{cur}\n\n{block}" if cur else block
    if cur.strip():
        parts.append(cur.strip())
    n = len(parts)
    return [f"{p}\n\n(часть {i + 1}/{n})" for i, p in enumerate(parts)]


def fmt_money(v):
    if v is None:
        return "н/д"
    return f"{v / 1e6:,.1f}".replace(",", " ") + " млн"


def fmt_m2(v):
    return f"{v:,.0f}".replace(",", " ") if v else "н/д"


def fmt_area(v):
    if v is None:
        return ""
    try:
        if float(v).is_integer():
            return f"{int(v)} м²"
    except (TypeError, ValueError):
        pass
    return f"{v} м²"


def fmt_dev(v):
    if v is None:
        return ""
    sign = "+" if v >= 0 else "−"
    return f"IRN {sign}{abs(v):.0f}%"


def fmt_line(o):
    """Строка объявления БЕЗ комнат и рынка (они в заголовке группы)."""
    parts = [x for x in [
        fmt_money(o.get("price")),
        fmt_area(o.get("total_area")),
        (fmt_m2(o.get("price_m2")) + " ₽/м²") if o.get("price_m2") else "",
        o.get("district") or "",
        fmt_dev(o.get("dev_pct")),
    ] if x]
    return "· " + " · ".join(parts)


def group_fresh(fresh):
    """Группы (rooms, market) в порядке rooms+market; внутри — как в fresh."""
    groups = {}
    for o in sort_fresh(fresh):
        key = (o.get("rooms"), o.get("housing_type"))
        groups.setdefault(key, []).append(o)
    ordered = sorted(groups.keys(), key=lambda k: (
        k[0] if isinstance(k[0], int) else 99,
        MARKET_ORDER.get(k[1], 2)))
    return [(k, groups[k]) for k in ordered]


def defense_filter(fresh, snap):
    """Перепроверка fresh перед отправкой: eligibility + дедуп id/url + сорт."""
    out, seen_ids, seen_urls = [], set(), set()
    for o in fresh or []:
        if not is_eligible(o):
            continue
        if o.get("id") in seen_ids or o.get("url") in seen_urls:
            continue
        if (snap and snap != "—" and o.get("first_seen")
                and o.get("first_seen") != snap):
            continue
        seen_ids.add(o.get("id"))
        seen_urls.add(o.get("url"))
        out.append(o)
    return sort_fresh(out)


def resolve_chat(token):
    """chat_id: env → config/telegram.json → getUpdates по названию."""
    cid = env("TELEGRAM_CHAT_ID")
    if cid:
        return int(cid)
    titles = []
    if os.path.exists(TG_CFG):
        cfg = json.load(open(TG_CFG, encoding="utf-8"))
        if cfg.get("chat_id"):
            print("resolved chat from config:", cfg["chat_id"])
            return int(cfg["chat_id"])
        titles = cfg.get("chat_titles") or []
    upd = api_call(token, "getUpdates", {"timeout": 0, "limit": 100,
                                         "allowed_updates": ["message"]})
    for u in upd.get("result", []):
        chat = (u.get("message") or {}).get("chat") or {}
        if chat.get("type") not in ("group", "supergroup"):
            continue
        title = chat.get("title") or ""
        for t in titles:
            if t.lower() in title.lower():
                print(f"resolved chat: {chat['id']} «{title}»")
                return chat["id"]
    sys.exit("FAIL: chat_id не задан и группа не найдена в getUpdates "
             "(нужно сообщение в группе или TELEGRAM_CHAT_ID)")


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {}


def save_state(st):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def is_date(s):
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(s or "")))


def build_message(fresh, sold, snap, total, sold_total):
    """Текст дайджеста (без отправки). fresh уже отфильтрован и отсортирован."""
    if not fresh and not sold:
        return (f"Радар: новых объявлений и снятий за {snap} нет "
                f"(всего в выборке {total if total is not None else '?'}, "
                f"пустых точек «снято» накопилось {sold_total or 0}).")
    lines = [f"Свежие объявления ЦИАН ({len(fresh)}) · снапшот {snap}"]
    groups = group_fresh(fresh)
    # Сохраняем места для всех категорий: многочисленные трёшки не вытеснят
    # редкие четырёх- и пятикомнатные варианты из сообщения.
    shown = 0
    remaining = CAP
    for i, ((rooms, market), items) in enumerate(groups):
        quota = min(len(items), remaining - (len(groups) - i - 1))
        if quota <= 0:
            break
        lines.append("")
        lines.append(f"{rooms}-комн {market}")
        for o in items[:quota]:
            lines.append(fmt_line(o))
            lines.append("  " + (o.get("url") or ""))
        shown += quota
        remaining -= quota
    if len(fresh) > shown:
        lines.append("")
        lines.append(f"… и ещё {len(fresh) - shown}: {DASH_URL} "
                     f"(фильтр «свежая рассылка»)")
    if sold:
        lines.append("")
        lines.append(f"Снято с публикации сегодня (возможно, проданы): {len(sold)}. "
                     f"На графике — пустые точки.")
    return "\n".join(lines)


def main():
    token = env("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("FAIL: TELEGRAM_BOT_TOKEN не задан")
    state = load_state()
    chat_id = int(state["chat_id"]) if state.get("chat_id") else resolve_chat(token)

    if not state.get("welcome_sent"):
        send(token, chat_id,
             f"Моя красивая квартира — радар цен ЦИАН × IRN\n\n"
             f"{DASH_URL}\n\n"
             f"Интерактивный график «стоимость квартиры vs стоимость м²» по 9 районам "
             f"ЮЗАО/ЗАО (3–6 комнат, 35–60 млн ₽). Ежедневно здесь — свежие объявления. "
             f"Закрепите это сообщение.")
        state["welcome_sent"] = True
        state["chat_id"] = chat_id
        save_state(state)
        print("welcome sent")

    if not os.path.exists(LISTINGS):
        sys.exit(f"FAIL: нет {LISTINGS}")
    data = json.load(open(LISTINGS, encoding="utf-8"))
    snap = data.get("snapshot_date") or "—"
    sold = data.get("sold_today") or []
    sold_total = data.get("sold_total")
    total = data.get("total")

    last = state.get("last_digest_date")
    if last and is_date(last) and is_date(snap) and snap <= last:
        print(f"digest {snap} <= last sent {last} — skip (stale/already sent)")
        return

    fresh = defense_filter(data.get("fresh") or [], snap)
    send(token, chat_id, build_message(fresh, sold, snap, total, sold_total))

    state["last_digest_date"] = snap
    save_state(state)
    print("digest done")


if __name__ == "__main__":
    main()
