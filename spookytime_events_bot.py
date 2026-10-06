#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Бот расписания ивентов для сервера SpookyTime (Minecraft)
=======================================================
Команды и кнопки:
  /start                  — главное меню
  ⏰ Ближайший ивент      — показывает следующий ивент и сколько до него осталось
  📅 Расписание на сегодня — полный список ивентов
  🔔 Включить уведомления — (заготовка, сохраняет chat_id)

Токен и расписание легко меняются в начале файла.
"""

import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

# ================== НАСТРОЙКИ ==================

# Вставь сюда токен своего бота (от @BotFather)
TOKEN = "МЕСТО_ДЛЯ_ТОКЕНА"

# Часовой пояс сервера (Москва)
MSK = ZoneInfo("Europe/Moscow")

# =====================================================
#  РАСПИСАНИЕ ИВЕНТОВ
#  Меняй только этот словарь под текущий вайп SpookyTime
#  Формат: "ЧЧ:ММ": "Название ивента"
# =====================================================
events_schedule = {
    "12:00": "Мистический сундук",
    "15:30": "Появление Босса",
    "18:00": "Глобальная Раздача",
    # Добавляй новые строки по этому же шаблону:
    # "20:00": "Название ивента",
}

# Файл для хранения тех, кто включил уведомления
NOTIFY_FILE = "notify_users.json"

# =====================================================

API = f"https://api.telegram.org/bot{TOKEN}"


def api(method, **params):
    """Отправка запроса к Telegram Bot API"""
    try:
        r = requests.post(f"{API}/{method}", json=params, timeout=30)
        return r.json()
    except Exception as e:
        print(f"Ошибка API: {e}")
        return {}


def send(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """Отправить сообщение"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api("sendMessage", **payload)


def main_keyboard():
    """Главная клавиатура"""
    return {
        "keyboard": [
            [{"text": "⏰ Ближайший ивент"}],
            [{"text": "📅 Расписание на сегодня"}],
            [{"text": "🔔 Включить уведомления"}],
        ],
        "resize_keyboard": True,
    }


def load_notify():
    """Загрузить список пользователей с уведомлениями"""
    if not os.path.exists(NOTIFY_FILE):
        return []
    try:
        with open(NOTIFY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_notify(users):
    """Сохранить список пользователей"""
    with open(NOTIFY_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_now_msk():
    """Текущее время по Москве"""
    return datetime.now(MSK)


def parse_events():
    """
    Превращает словарь events_schedule в список кортежей (datetime, название)
    Время берётся на сегодня по Москве.
    """
    now = get_now_msk()
    today = now.date()
    result = []

    for time_str, name in events_schedule.items():
        try:
            hour, minute = map(int, time_str.split(":"))
            # Создаём время с московским часовым поясом
            event_dt = datetime(today.year, today.month, today.day, hour, minute, tzinfo=MSK)
            result.append((event_dt, name))
        except Exception as e:
            print(f"Ошибка в расписании ({time_str}): {e}")

    # Сортируем по времени
    result.sort(key=lambda x: x[0])
    return result


def find_next_event():
    """
    Находит ближайший будущий ивент.
    Возвращает (datetime_ивента, название) или None.
    """
    now = get_now_msk()
    events = parse_events()

    for event_dt, name in events:
        if event_dt > now:
            return event_dt, name

    # Если все ивенты сегодня уже прошли — берём первый на завтра
    if events:
        first_dt, first_name = events[0]
        tomorrow = first_dt + timedelta(days=1)
        return tomorrow, first_name

    return None


def format_delta(delta: timedelta) -> str:
    """Красиво форматирует оставшееся время"""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "уже начался / прошёл"

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"{hours} ч. {minutes} мин."
    else:
        return f"{minutes} мин."


# ================== ОБРАБОТЧИКИ ==================

def cmd_start(chat_id, user):
    name = user.get("first_name", "игрок")
    send(
        chat_id,
        f"Привет, <b>{name}</b>!\n\n"
        f"Это бот расписания ивентов сервера <b>SpookyTime</b>.\n"
        f"Выбери, что тебе нужно:",
        reply_markup=main_keyboard(),
    )


def cmd_next_event(chat_id):
    """Кнопка «⏰ Ближайший ивент»"""
    result = find_next_event()

    if not result:
        send(chat_id, "На сегодня ивентов нет.", reply_markup=main_keyboard())
        return

    event_dt, name = result
    now = get_now_msk()
    delta = event_dt - now

    time_str = event_dt.strftime("%H:%M")
    date_str = "сегодня" if event_dt.date() == now.date() else "завтра"

    text = (
        f"⏰ <b>Ближайший ивент</b>\n\n"
        f"📌 <b>{name}</b>\n"
        f"🕒 Время: <b>{time_str}</b> ({date_str})\n"
        f"⏳ Осталось: <b>{format_delta(delta)}</b>"
    )
    send(chat_id, text, reply_markup=main_keyboard())


def cmd_schedule_today(chat_id):
    """Кнопка «📅 Расписание на сегодня»"""
    events = parse_events()
    now = get_now_msk()

    if not events:
        send(chat_id, "На сегодня ивентов нет.", reply_markup=main_keyboard())
        return

    lines = ["📅 <b>Расписание на сегодня</b>\n"]

    for event_dt, name in events:
        time_str = event_dt.strftime("%H:%M")
        if event_dt < now:
            status = "✅ прошло"
        else:
            status = "⏳ скоро"
        lines.append(f"<b>{time_str}</b> — {name}  ({status})")

    send(chat_id, "\n".join(lines), reply_markup=main_keyboard())


def cmd_enable_notify(chat_id):
    """Кнопка «🔔 Включить уведомления»"""
    users = load_notify()
    if chat_id not in users:
        users.append(chat_id)
        save_notify(users)
        send(
            chat_id,
            "🔔 Уведомления <b>включены</b>!\n\n"
            "Пока это базовая версия — бот запомнил тебя.\n"
            "Полноценные напоминания за 5–10 минут до ивента можно добавить позже.",
            reply_markup=main_keyboard(),
        )
    else:
        send(chat_id, "Уведомления у тебя уже включены.", reply_markup=main_keyboard())


def process_update(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    user = message.get("from", {})

    if text in ("/start", "/start@yourbot"):
        cmd_start(chat_id, user)
    elif text == "⏰ Ближайший ивент":
        cmd_next_event(chat_id)
    elif text == "📅 Расписание на сегодня":
        cmd_schedule_today(chat_id)
    elif text == "🔔 Включить уведомления":
        cmd_enable_notify(chat_id)
    else:
        send(chat_id, "Выбери кнопку в меню 👇", reply_markup=main_keyboard())


def main():
    if TOKEN == "МЕСТО_ДЛЯ_ТОКЕНА" or not TOKEN:
        print("=" * 50)
        print("  ОШИБКА: не указан токен!")
        print("  Открой файл и вставь токен в строку TOKEN = \"...\"")
        print("=" * 50)
        return

    # Проверяем токен
    me = api("getMe")
    if not me.get("ok"):
        print("Неверный токен или нет интернета")
        print(me)
        return

    bot_username = me["result"]["username"]
    print("=" * 50)
    print(f"  Бот @{bot_username} запущен!")
    print("  Расписание ивентов SpookyTime")
    print("  Остановить: Ctrl+C")
    print("=" * 50)

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
                    print(f"Ошибка обработки: {e}")

        except KeyboardInterrupt:
            print("\nБот остановлен.")
            break
        except Exception as e:
            print(f"Ошибка цикла: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
