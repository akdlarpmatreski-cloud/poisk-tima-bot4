#!/usr/bin/env python3
"""
Поиск Тима — Telegram-бот
========================
1. Создай бота у @BotFather → получи токен
2. Вставь токен ниже в BOT_TOKEN
3. Запусти:  python3 poisk_tima_bot.py
4. Готово! Бот работает.

Бот хранит анкеты в файле ankety.json (общий для всех).
"""

import json
import os
import time
import random
import urllib.parse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

MSK = ZoneInfo("Europe/Moscow")

# ================== НАСТРОЙКИ ==================
# Сначала берём из переменной окружения (для Railway/Render),
# если нет — используем значение ниже.
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "8824067064:AAGC5jjuIdN6PFbhUd5cfd_rCRzjtZYqpnw"
# ===============================================

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ankety.json")
STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")
CONTEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contest.json")
MARKET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market.json")

# Хранилище состояний пользователей (в памяти)
user_states = {}   # user_id → {"step": ..., "data": {...}}

# =====================================================
#  РАСПИСАНИЕ ИВЕНТОВ SpookyTime
#  Меняй только этот словарь под текущий вайп
#  Формат: "ЧЧ:ММ": "Название ивента"
# =====================================================
events_schedule = {
    "12:00": "Мистический сундук",
    "15:30": "Появление Босса",
    "18:00": "Глобальная Раздача",
    # Добавляй новые строки:
    # "20:00": "Название ивента",
}

# ID администратора (твой Telegram ID) — чтобы только ты мог создавать конкурсы
# Узнать свой ID можно у @userinfobot
ADMIN_IDS = []  # например: [123456789]


def load_ankety():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_ankety(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_stats():
    if not os.path.exists(STATS_FILE):
        return {"users": [], "starts": 0}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": [], "starts": 0}


def save_stats(data):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def track_user(user_id):
    """Записываем уникального пользователя"""
    stats = load_stats()
    uid = str(user_id)
    if uid not in stats["users"]:
        stats["users"].append(uid)
    stats["starts"] = stats.get("starts", 0) + 1
    save_stats(stats)


def api(method, **params):
    """Вызов Telegram Bot API"""
    url = f"{API}/{method}"
    try:
        r = requests.post(url, json=params, timeout=30)
        return r.json()
    except Exception as e:
        print(f"API error: {e}")
        return {}


def send(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api("sendMessage", **payload)


def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = False
    api("answerCallbackQuery", **payload)


def main_keyboard():
    return {
        "keyboard": [
            [{"text": "📝 Оставить анкету"}, {"text": "🏰 Анкета в клан"}],
            [{"text": "📋 Смотреть анкеты"}, {"text": "🛒 Рынок"}],
            [{"text": "🎁 Халявный ресы"}, {"text": "🎉 Конкурсы"}],
            [{"text": "❓ Помощь"}],
        ],
        "resize_keyboard": True,
    }


def inline_interest(anketa_id):
    return {
        "inline_keyboard": [
            [{"text": "✅ Меня заинтересовала", "callback_data": f"interest:{anketa_id}"}]
        ]
    }


# ================== ИВЕНТЫ ==================

def get_now_msk():
    return datetime.now(MSK)


def parse_events():
    now = get_now_msk()
    today = now.date()
    result = []
    for time_str, name in events_schedule.items():
        try:
            hour, minute = map(int, time_str.split(":"))
            event_dt = datetime(today.year, today.month, today.day, hour, minute, tzinfo=MSK)
            result.append((event_dt, name))
        except Exception:
            pass
    result.sort(key=lambda x: x[0])
    return result


def find_next_event():
    now = get_now_msk()
    events = parse_events()
    for event_dt, name in events:
        if event_dt > now:
            return event_dt, name
    if events:
        first_dt, first_name = events[0]
        return first_dt + timedelta(days=1), first_name
    return None


def format_delta(delta):
    total = int(delta.total_seconds())
    if total < 0:
        return "уже начался"
    hours = total // 3600
    minutes = (total % 3600) // 60
    if hours > 0:
        return f"{hours} ч. {minutes} мин."
    return f"{minutes} мин."


def cmd_next_event(chat_id):
    result = find_next_event()
    if not result:
        send(chat_id, "На сегодня ивентов нет.", reply_markup=main_keyboard())
        return
    event_dt, name = result
    now = get_now_msk()
    delta = event_dt - now
    time_str = event_dt.strftime("%H:%M")
    date_str = "сегодня" if event_dt.date() == now.date() else "завтра"
    send(
        chat_id,
        f"⏰ <b>Ближайший ивент</b>\n\n"
        f"📌 <b>{name}</b>\n"
        f"🕒 Время: <b>{time_str}</b> ({date_str})\n"
        f"⏳ Осталось: <b>{format_delta(delta)}</b>",
        reply_markup=main_keyboard(),
    )


def cmd_schedule(chat_id):
    events = parse_events()
    now = get_now_msk()
    if not events:
        send(chat_id, "На сегодня ивентов нет.", reply_markup=main_keyboard())
        return
    lines = ["📅 <b>Расписание ивентов на сегодня</b>\n"]
    for event_dt, name in events:
        time_str = event_dt.strftime("%H:%M")
        status = "✅ прошло" if event_dt < now else "⏳ скоро"
        lines.append(f"<b>{time_str}</b> — {name}  ({status})")
    send(chat_id, "\n".join(lines), reply_markup=main_keyboard())


# ================== КОНКУРСЫ ==================

def load_contest():
    if not os.path.exists(CONTEST_FILE):
        return None
    try:
        with open(CONTEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_contest(data):
    with open(CONTEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cmd_contests(chat_id, user_id):
    contest = load_contest()
    if not contest or not contest.get("active"):
        text = "🎉 Сейчас нет активного конкурса."
        if user_id in ADMIN_IDS or not ADMIN_IDS:
            text += "\n\n<i>Админ: используй /newcontest чтобы создать</i>"
        send(chat_id, text, reply_markup=main_keyboard())
        return

    participants = contest.get("participants", [])
    already = any(p.get("id") == chat_id for p in participants)

    text = (
        f"🎉 <b>Конкурс</b>\n\n"
        f"{contest.get('title', 'Без названия')}\n\n"
        f"🎁 Приз: <b>{contest.get('prize', '—')}</b>\n"
        f"👥 Участников: <b>{len(participants)}</b>\n"
    )
    if already:
        text += "\n✅ Ты уже участвуешь!"
    else:
        text += "\nНажми кнопку ниже, чтобы участвовать."

    markup = None
    if not already:
        markup = {
            "inline_keyboard": [
                [{"text": "✅ Участвовать", "callback_data": "contest_join"}]
            ]
        }
    send(chat_id, text, reply_markup=markup or main_keyboard())


# ================== РЫНОК ==================

def load_market():
    if not os.path.exists(MARKET_FILE):
        return []
    try:
        with open(MARKET_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_market(data):
    with open(MARKET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def start_market_ad(chat_id):
    """Начать создание объявления на рынке"""
    user_states[chat_id] = {"step": "market_item", "data": {}, "type": "market"}
    send(
        chat_id,
        "🛒 <b>Новое объявление на рынке</b>\n\n"
        "1️⃣ Что <b>продаёшь</b>?\n"
        "<i>(например: Незеритовый меч, 64 алмаза, донат VIP)</i>\n\n"
        "Или /cancel чтобы отменить.",
    )


def process_market_step(chat_id, text):
    state = user_states.get(chat_id)
    if not state or state.get("type") != "market":
        return

    step = state["step"]
    data = state["data"]

    if step == "market_item":
        if len(text) < 2 or len(text) > 120:
            send(chat_id, "Слишком коротко или длинно. Напиши, что продаёшь:")
            return
        data["item"] = text
        state["step"] = "market_server"
        send(chat_id, "2️⃣ На каком <b>сервере</b>?\n<i>(например: SpookyTime, FunTime)</i>")

    elif step == "market_server":
        if len(text) < 2 or len(text) > 80:
            send(chat_id, "Напиши название сервера:")
            return
        data["server"] = text
        state["step"] = "market_price"
        send(chat_id, "3️⃣ Какая <b>цена</b>?\n<i>(например: 500 монет, 2 prioritу, договорная)</i>")

    elif step == "market_price":
        if len(text) < 1 or len(text) > 60:
            send(chat_id, "Напиши цену:")
            return
        data["price"] = text
        state["step"] = "market_contact"
        send(
            chat_id,
            "4️⃣ Напиши <b>ЛС</b> для связи:\n"
            "<i>(Telegram @username или Discord)</i>",
        )

    elif step == "market_contact":
        if len(text) < 3 or len(text) > 100:
            send(chat_id, "Контакт слишком короткий или длинный. Попробуй ещё раз:")
            return
        data["contact"] = text

        ad = {
            "id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + os.urandom(2).hex(),
            "item": data["item"],
            "server": data["server"],
            "price": data["price"],
            "contact": data["contact"],
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "from_user": chat_id,
        }
        market = load_market()
        market.insert(0, ad)
        if len(market) > 200:
            market = market[:200]
        save_market(market)

        del user_states[chat_id]
        send(
            chat_id,
            "✅ <b>Объявление добавлено на рынок!</b>\n\n"
            "Другие игроки увидят его в разделе «🛒 Рынок».",
            reply_markup=main_keyboard(),
        )


def show_market(chat_id, page=0):
    market = load_market()
    if not market:
        send(
            chat_id,
            "🛒 Рынок пока пуст.\n\n"
            "Нажми «🛒 Рынок» → создай первое объявление!",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "➕ Создать объявление", "callback_data": "market_new"}]
                ]
            },
        )
        return

    per_page = 5
    total = len(market)
    start = page * per_page
    end = start + per_page
    chunk = market[start:end]

    for ad in chunk:
        text = (
            f"🛒 <b>#{ad['id'][-6:].upper()}</b>\n"
            f"📦 <b>Товар:</b> {ad['item']}\n"
            f"🖥 <b>Сервер:</b> {ad['server']}\n"
            f"💰 <b>Цена:</b> {ad['price']}\n"
            f"📩 <b>ЛС:</b> <code>{ad['contact']}</code>"
        )
        send(chat_id, text)

    # Навигация + кнопка создать
    buttons = []
    nav = []
    if page > 0:
        nav.append({"text": "⬅️", "callback_data": f"market_page:{page-1}"})
    if end < total:
        nav.append({"text": "➡️", "callback_data": f"market_page:{page+1}"})
    if nav:
        buttons.append(nav)
    buttons.append([{"text": "➕ Создать объявление", "callback_data": "market_new"}])

    send(
        chat_id,
        f"Показано {start+1}–{min(end, total)} из {total} объявлений",
        reply_markup={"inline_keyboard": buttons},
    )


def format_anketa_short(a, show_contact=False):
    # Анкета в клан
    if a.get("type") == "clan":
        text = (
            f"🏰 <b>АНКЕТА В КЛАН</b>  #{a['id'][-6:].upper()}\n"
            f"🖥 <b>Сервер:</b> {a['server']}\n"
            f"👥 <b>Соклановцев:</b> {a.get('members', '?')}\n"
        )
    else:
        # Обычная анкета поиска тимы
        cheat_map = {
            "без": "✅ Без чита",
            "с читом": "⚠️ С читом",
            "иногда": "⚡ Иногда с читом",
        }
        cheat = cheat_map.get(a.get("cheat", ""), a.get("cheat", "?"))
        text = (
            f"<b>#{a['id'][-6:].upper()}</b>\n"
            f"🖥 <b>Сервер:</b> {a['server']}\n"
            f"🎂 <b>Возраст:</b> {a.get('age', '?')}\n"
            f"🎮 <b>Читы:</b> {cheat}\n"
        )

    if show_contact:
        text += f"\n📩 <b>Контакт:</b> <code>{a['contact']}</code>"
    else:
        text += "\n🔒 <i>Контакт скрыт. Нажми кнопку ниже, если заинтересовала.</i>"
    return text


# ================== ОБРАБОТЧИКИ ==================

def cmd_start(chat_id, user):
    track_user(chat_id)  # считаем пользователя
    name = user.get("first_name", "друг")
    send(
        chat_id,
        f"Привет, <b>{name}</b>! 👋\n\n"
        f"Это бот <b>Поиск Тима</b>.\n"
        f"Здесь игроки оставляют анкеты, чтобы найти тиммейтов.\n\n"
        f"Контакт виден <b>только</b> тем, кому анкета реально интересна.",
        reply_markup=main_keyboard(),
    )


def cmd_stats(chat_id):
    stats = load_stats()
    ankety = load_ankety()
    unique_users = len(stats.get("users", []))
    total_starts = stats.get("starts", 0)
    total_ankety = len(ankety)

    send(
        chat_id,
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Уникальных пользователей: <b>{unique_users}</b>\n"
        f"▶️ Всего нажатий /start: <b>{total_starts}</b>\n"
        f"📝 Анкет оставлено: <b>{total_ankety}</b>",
        reply_markup=main_keyboard(),
    )


def cmd_help(chat_id):
    send(
        chat_id,
        "<b>Как пользоваться:</b>\n\n"
        "📝 <b>Оставить анкету</b> — поиск тиммейта\n"
        "🏰 <b>Анкета в клан</b> — поиск клана / набор\n"
        "📋 <b>Смотреть анкеты</b> — общая копилка\n"
        "🛒 <b>Рынок</b> — купить / продать вещи\n"
        "🎁 <b>Халявный ресы</b> — каналы с кладами\n"
        "🎉 <b>Конкурсы</b> — участие в конкурсах\n"
        "📊 <b>/stats</b> — статистика бота\n\n"
        "<b>Админ-команды конкурсов:</b>\n"
        "<code>/newcontest Название | Приз</code>\n"
        "<code>/endcontest</code> — выбрать победителя\n\n"
        "Чтобы увидеть контакт человека — нажми кнопку "
        "«Меня заинтересовала» под анкетой.\n\n"
        "─────────────────\n"
        "❓ <b>По всем вопросам пиши:</b>\n"
        "@Feet676",
        reply_markup=main_keyboard(),
    )


def start_anketa(chat_id):
    user_states[chat_id] = {"step": "server", "data": {}}
    send(
        chat_id,
        "📝 <b>Новая анкета</b>\n\n"
        "1️⃣ Напиши <b>сервер</b>, на котором играешь:\n"
        "<i>(например: Hypixel, FunTime, MineBlaze)</i>\n\n"
        "Или нажми /cancel чтобы отменить.",
    )


def process_anketa_step(chat_id, text):
    state = user_states.get(chat_id)
    if not state:
        return

    step = state["step"]
    data = state["data"]

    if step == "server":
        if len(text) < 2 or len(text) > 80:
            send(chat_id, "Сервер слишком короткий или длинный. Попробуй ещё раз:")
            return
        data["server"] = text
        state["step"] = "age"
        send(chat_id, "2️⃣ Сколько тебе <b>лет</b>? (число от 10 до 99)")

    elif step == "age":
        try:
            age = int(text)
            if not 10 <= age <= 99:
                raise ValueError
        except ValueError:
            send(chat_id, "Введи число от 10 до 99:")
            return
        data["age"] = age
        state["step"] = "cheat"
        send(
            chat_id,
            "3️⃣ С читом играешь или без?\n\n"
            "Напиши один из вариантов:\n"
            "• <code>без</code>\n"
            "• <code>с читом</code>\n"
            "• <code>иногда</code>",
        )

    elif step == "cheat":
        text_l = text.lower().strip()
        if text_l not in ("без", "с читом", "иногда"):
            send(chat_id, "Напиши точно: <code>без</code>, <code>с читом</code> или <code>иногда</code>")
            return
        data["cheat"] = text_l
        state["step"] = "contact"
        send(
            chat_id,
            "4️⃣ Напиши <b>контакт</b> (Telegram @username или Discord tag),\n"
            "чтобы с тобой могли связаться:\n\n"
            "<i>Этот контакт будет скрыт, пока человек не нажмёт «заинтересовала».</i>",
        )

    elif step == "contact":
        if len(text) < 3 or len(text) > 100:
            send(chat_id, "Контакт слишком короткий или длинный. Попробуй ещё раз:")
            return
        data["contact"] = text

        # Сохраняем
        anketa = {
            "id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + os.urandom(2).hex(),
            "server": data["server"],
            "age": data["age"],
            "cheat": data["cheat"],
            "contact": data["contact"],
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "from_user": chat_id,
        }
        ankety = load_ankety()
        ankety.insert(0, anketa)
        if len(ankety) > 300:
            ankety = ankety[:300]
        save_ankety(ankety)

        del user_states[chat_id]

        send(
            chat_id,
            "✅ <b>Анкета успешно добавлена!</b>\n\n"
            "Теперь другие игроки могут её увидеть в общей копилке.\n"
            "Твой контакт будет скрыт, пока кто-то не нажмёт «Меня заинтересовала».",
            reply_markup=main_keyboard(),
        )


# ================== АНКЕТА В КЛАН ==================

def start_clan_anketa(chat_id):
    """Начать заполнение анкеты в клан"""
    user_states[chat_id] = {"step": "clan_server", "data": {}, "type": "clan"}
    send(
        chat_id,
        "🏰 <b>Анкета в клан</b>\n\n"
        "1️⃣ На каком <b>сервере</b> ищешь клан?\n"
        "<i>(например: SpookyTime, FunTime, MineBlaze)</i>\n\n"
        "Или нажми /cancel чтобы отменить.",
    )


def process_clan_step(chat_id, text):
    """Обработка шагов анкеты в клан"""
    state = user_states.get(chat_id)
    if not state or state.get("type") != "clan":
        return

    step = state["step"]
    data = state["data"]

    if step == "clan_server":
        if len(text) < 2 or len(text) > 80:
            send(chat_id, "Название сервера слишком короткое или длинное. Попробуй ещё раз:")
            return
        data["server"] = text
        state["step"] = "clan_members"
        send(chat_id, "2️⃣ Сколько примерно <b>соклановцев</b> ты хочешь / у тебя уже есть?\n"
                     "<i>(напиши число, например: 5 или 10-15)</i>")

    elif step == "clan_members":
        if len(text) < 1 or len(text) > 30:
            send(chat_id, "Напиши количество соклановцев (число или диапазон):")
            return
        data["members"] = text
        state["step"] = "clan_contact"
        send(
            chat_id,
            "3️⃣ Напиши <b>ЛС</b>, чтобы с тобой могли связаться:\n"
            "<i>(Telegram @username или Discord tag)</i>\n\n"
            "Этот контакт будет скрыт, пока человек не нажмёт «заинтересовала».",
        )

    elif step == "clan_contact":
        if len(text) < 3 or len(text) > 100:
            send(chat_id, "Контакт слишком короткий или длинный. Попробуй ещё раз:")
            return
        data["contact"] = text

        # Сохраняем анкету клана
        anketa = {
            "id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + os.urandom(2).hex(),
            "type": "clan",
            "server": data["server"],
            "members": data["members"],
            "contact": data["contact"],
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "from_user": chat_id,
        }
        ankety = load_ankety()
        ankety.insert(0, anketa)
        if len(ankety) > 300:
            ankety = ankety[:300]
        save_ankety(ankety)

        del user_states[chat_id]

        send(
            chat_id,
            "✅ <b>Анкета в клан успешно добавлена!</b>\n\n"
            "Теперь другие игроки могут её увидеть.\n"
            "Твой контакт скрыт, пока кто-то не нажмёт «Меня заинтересовала».",
            reply_markup=main_keyboard(),
        )


def show_list(chat_id, page=0):
    ankety = load_ankety()
    if not ankety:
        send(chat_id, "📭 Пока нет ни одной анкеты.\nБудь первым — нажми «Оставить анкету»!", reply_markup=main_keyboard())
        return

    per_page = 5
    total = len(ankety)
    start = page * per_page
    end = start + per_page
    chunk = ankety[start:end]

    for a in chunk:
        send(
            chat_id,
            format_anketa_short(a, show_contact=False),
            reply_markup=inline_interest(a["id"]),
        )

    # Навигация
    buttons = []
    if page > 0:
        buttons.append({"text": "⬅️ Назад", "callback_data": f"page:{page-1}"})
    if end < total:
        buttons.append({"text": "Вперёд ➡️", "callback_data": f"page:{page+1}"})

    nav = {"inline_keyboard": [buttons]} if buttons else None
    send(
        chat_id,
        f"Показано {start+1}–{min(end, total)} из {total} анкет",
        reply_markup=nav,
    )


def handle_callback(callback):
    data = callback.get("data", "")
    chat_id = callback["message"]["chat"]["id"]
    cb_id = callback["id"]

    if data.startswith("interest:"):
        anketa_id = data.split(":", 1)[1]
        ankety = load_ankety()
        anketa = next((a for a in ankety if a["id"] == anketa_id), None)
        if not anketa:
            answer_callback(cb_id, "Анкета уже удалена")
            return

        # Отправляем контакт отдельным сообщением
        send(
            chat_id,
            f"📩 Контакт по анкете <b>#{anketa_id[-6:].upper()}</b>:\n\n"
            f"<code>{anketa['contact']}</code>\n\n"
            f"Можешь писать!",
        )
        answer_callback(cb_id, "Контакт открыт!")

    elif data.startswith("page:"):
        page = int(data.split(":")[1])
        answer_callback(cb_id)
        show_list(chat_id, page)

    elif data == "contest_join":
        contest = load_contest()
        if not contest or not contest.get("active"):
            answer_callback(cb_id, "Конкурс уже закончился")
            return
        participants = contest.get("participants", [])
        if any(p.get("id") == chat_id for p in participants):
            answer_callback(cb_id, "Ты уже участвуешь!")
            return
        user = callback.get("from", {})
        participants.append({
            "id": chat_id,
            "name": user.get("first_name", "Игрок"),
            "username": user.get("username"),
        })
        contest["participants"] = participants
        save_contest(contest)
        answer_callback(cb_id, "Ты в деле! ✅")
        send(chat_id, f"✅ Ты участвуешь в конкурсе!\nСейчас участников: <b>{len(participants)}</b>", reply_markup=main_keyboard())

    elif data == "market_new":
        answer_callback(cb_id)
        start_market_ad(chat_id)

    elif data.startswith("market_page:"):
        page = int(data.split(":")[1])
        answer_callback(cb_id)
        show_market(chat_id, page)


def process_update(update):
    if "callback_query" in update:
        handle_callback(update["callback_query"])
        return

    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    user = message.get("from", {})

    # Команды
    if text in ("/start", "/start@yourbot"):
        cmd_start(chat_id, user)
        return
    if text in ("/help", "❓ Помощь"):
        cmd_help(chat_id)
        return
    if text in ("/stats", "📊 Статистика"):
        cmd_stats(chat_id)
        return
    if text in ("/cancel",):
        if chat_id in user_states:
            del user_states[chat_id]
            send(chat_id, "Отменено.", reply_markup=main_keyboard())
        return
    if text in ("📝 Оставить анкету", "/anketa"):
        start_anketa(chat_id)
        return
    if text in ("🏰 Анкета в клан", "/clan"):
        start_clan_anketa(chat_id)
        return
    if text in ("📋 Смотреть анкеты", "/list"):
        show_list(chat_id)
        return
    if text in ("🎁 Халявный ресы", "/resy", "/халява"):
        send(
            chat_id,
            "🎁 <b>Халявный ресы</b>\n\n"
            "Вот полезные каналы с кладами:\n\n"
            "📦 <b>Клады на 1.16.5</b>\n"
            "→ https://t.me/spok11\n\n"
            "📦 <b>Клады на 1.21.4</b>\n"
            "→ https://t.me/retp3",
            reply_markup=main_keyboard(),
        )
        return
    if text in ("🛒 Рынок", "/market"):
        show_market(chat_id)
        return
    if text in ("🎉 Конкурсы", "/contest"):
        cmd_contests(chat_id, user.get("id"))
        return

    # Админ-команды конкурсов
    if text.startswith("/newcontest"):
        # Формат: /newcontest Название | Приз
        parts = text[len("/newcontest"):].strip().split("|")
        if len(parts) < 2:
            send(chat_id, "Формат:\n<code>/newcontest Название конкурса | Приз</code>")
            return
        title = parts[0].strip()
        prize = parts[1].strip()
        contest = {
            "active": True,
            "title": title,
            "prize": prize,
            "participants": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        save_contest(contest)
        send(chat_id, f"✅ Конкурс создан!\n\n🎉 {title}\n🎁 Приз: {prize}", reply_markup=main_keyboard())
        return

    if text == "/endcontest":
        contest = load_contest()
        if not contest or not contest.get("active"):
            send(chat_id, "Нет активного конкурса.")
            return
        participants = contest.get("participants", [])
        if not participants:
            contest["active"] = False
            save_contest(contest)
            send(chat_id, "Конкурс завершён. Участников не было.")
            return
        winner = random.choice(participants)
        contest["active"] = False
        contest["winner"] = winner
        save_contest(contest)
        send(
            chat_id,
            f"🏆 <b>Конкурс завершён!</b>\n\n"
            f"Победитель: <b>{winner.get('name', 'Неизвестный')}</b>\n"
            f"ID: <code>{winner.get('id')}</code>\n"
            f"🎁 Приз: {contest.get('prize')}",
            reply_markup=main_keyboard(),
        )
        return

    # Если пользователь в процессе заполнения анкеты / объявления
    if chat_id in user_states:
        state = user_states[chat_id]
        if state.get("type") == "clan":
            process_clan_step(chat_id, text)
        elif state.get("type") == "market":
            process_market_step(chat_id, text)
        else:
            process_anketa_step(chat_id, text)
        return

    # Неизвестное
    send(chat_id, "Нажми кнопку ниже или /help", reply_markup=main_keyboard())


def main():
    if BOT_TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER" or not BOT_TOKEN:
        print("=" * 50)
        print("  ОШИБКА: не указан токен бота!")
        print()
        print("  1. Открой Telegram → @BotFather")
        print("  2. Напиши /newbot и создай бота")
        print("  3. Скопируй токен")
        print("  4. Вставь его в файл poisk_tima_bot.py")
        print("     в строку BOT_TOKEN = \"...\"")
        print("  5. Запусти снова: python3 poisk_tima_bot.py")
        print("=" * 50)
        return

    # Проверяем токен
    me = api("getMe")
    if not me.get("ok"):
        print("Неверный токен! Проверь BOT_TOKEN.")
        print(me)
        return

    bot_name = me["result"]["username"]
    print("=" * 50)
    print(f"  Бот @{bot_name} запущен!")
    print("  Нажми Ctrl+C чтобы остановить")
    print("=" * 50)

    # Убираем вебхук на всякий случай
    api("deleteWebhook", drop_pending_updates=True)

    offset = 0
    while True:
        try:
            resp = api("getUpdates", offset=offset, timeout=30)
            if not resp.get("ok"):
                time.sleep(3)
                continue

            for update in resp.get("result", []):
                offset = update["update_id"] + 1
                try:
                    process_update(update)
                except Exception as e:
                    print(f"Update error: {e}")

        except KeyboardInterrupt:
            print("\nБот остановлен.")
            break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
