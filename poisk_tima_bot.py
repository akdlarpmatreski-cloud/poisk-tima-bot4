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
import urllib.parse
from datetime import datetime, timezone

import requests

# ================== НАСТРОЙКИ ==================
# Сначала берём из переменной окружения (для Railway/Render),
# если нет — используем значение ниже.
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "8824067064:AAGC5jjuIdN6PFbhUd5cfd_rCRzjtZYqpnw"
# ===============================================

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ankety.json")
STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")

# Хранилище состояний пользователей (в памяти)
user_states = {}   # user_id → {"step": ..., "data": {...}}


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
            [{"text": "📝 Оставить анкету"}],
            [{"text": "📋 Смотреть анкеты"}, {"text": "🎁 Халявный ресы"}],
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


def format_anketa_short(a, show_contact=False):
    cheat_map = {
        "без": "✅ Без чита",
        "с читом": "⚠️ С читом",
        "иногда": "⚡ Иногда с читом",
    }
    cheat = cheat_map.get(a.get("cheat", ""), a.get("cheat", "?"))
    text = (
        f"<b>#{a['id'][-6:].upper()}</b>\n"
        f"🖥 <b>Сервер:</b> {a['server']}\n"
        f"🎂 <b>Возраст:</b> {a['age']}\n"
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
        "📝 <b>Оставить анкету</b> — заполни 4 поля\n"
        "📋 <b>Смотреть анкеты</b> — общая копилка\n"
        "🎁 <b>Халявный ресы</b> — каналы с кладами\n"
        "📊 <b>/stats</b> — статистика бота\n\n"
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

    # Если пользователь в процессе заполнения анкеты
    if chat_id in user_states:
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
