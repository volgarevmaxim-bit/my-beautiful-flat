#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tg_digest — ежедневная рассылка свежих объявлений ЦИАН в ТГ-группу «My beautiful flat».

Читает data/listings.json (снапшот, кладётся deploy_pages.py),
шлёт в чат через Bot API (stdlib, без внешних зависимостей).

Креды:
  TELEGRAM_BOT_TOKEN  — секрет Actions (обязателен)
  TELEGRAM_CHAT_ID    — секрет Actions (необязателен; без него чат ищется
                        по названию из config/telegram.json в getUpdates)

Механика:
  - при первом запуске (нет data/digest_state.json с welcome_sent) шлёт
    закрепляемое welcome-сообщение со ссылкой на дашборд;
  - далее ежедневно: список свежих объявлений (is_new), снятые с
    публикации (sold) — или «без изменений»;
  - state коммитится обратно в репо.
"""
import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


def fmt_dev(v):
    if v is None:
        return ""
    sign = "+" if v >= 0 else "−"
    return f" · IRN {sign}{abs(v):.0f}%"


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
        save_state(st)
        print("welcome sent")

    if not os.path.exists(LISTINGS):
        sys.exit(f"FAIL: нет {LISTINGS}")
    data = json.load(open(LISTINGS, encoding="utf-8"))
    fresh = data.get("fresh") or []
    sold = data.get("sold_ids") or []
    snap = data.get("snapshot_date") or "—"

    if state.get("last_digest_date") == snap:
        print(f"digest for {snap} already sent — skip")
        return

    if not fresh and not sold:
        send(token, chat_id,
             f"Радар: новых объявлений и снятий за {snap} нет "
             f"(всего в выборке {data.get('total')}).")
    else:
        lines = [f"Свежие объявления ЦИАН ({len(fresh)}) · снапшот {snap}"]
        for o in fresh[:15]:
            rooms = f"{o['rooms']}-комн." if o.get("rooms") else ""
            area = f"{o['total_area']} м²" if o.get("total_area") else ""
            parts = [x for x in [
                rooms, fmt_money(o.get("price")), area,
                (fmt_m2(o.get("price_m2")) + " ₽/м²") if o.get("price_m2") else "",
                o.get("district") or "", o.get("housing_type") or "",
                fmt_dev(o.get("dev_pct")),
            ] if x]
            lines.append("· " + " · ".join(parts))
            lines.append("  " + o.get("url", ""))
        if len(fresh) > 15:
            lines.append(f"… и ещё {len(fresh) - 15}: {DASH_URL} (фильтр «сегодня»)")
        if sold:
            lines.append(f"\nСнято с публикации (возможно, проданы): {len(sold)}. "
                         f"На графике — пустые точки.")
        send(token, chat_id, "\n".join(lines))

    state["last_digest_date"] = snap
    save_state(st)
    print("digest done")


if __name__ == "__main__":
    main()
