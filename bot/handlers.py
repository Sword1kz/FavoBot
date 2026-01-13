from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton

from bot.parser import parse_message, normalize_order_date, is_order_header
from bot.exporter import record_order, export_orders
from bot.shop_db import get_or_create_shop, list_shops

import os
from dotenv import load_dotenv

load_dotenv()

raw_admins = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {
    int(x) for x in raw_admins.replace(" ", "").split(",")
    if x.strip().isdigit()
}


router = Router()

# 👉 сюда впиши свой Telegram user_id и id других админов

CURRENT_ORDER_DATE: dict[int, str] = {}

# Простое состояние диалога "Заявка": user_id -> dict
FORM_STATE: dict[int, dict] = {}


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧾 Заявка")],
            [KeyboardButton(text="💸 Цены")],
        ],
        resize_keyboard=True,
    )


# === Служебная команда: кто я? ===

@router.message(Command("whoami"))
async def handle_whoami(msg: types.Message):
    await msg.answer(f"Твой user_id: <code>{msg.from_user.id}</code>", parse_mode="HTML")


# === START / HELP ===

@router.message(Command("start", "help"))
async def handle_start(msg: types.Message):
    is_admin = msg.from_user.id in ADMIN_IDS

    if is_admin:
        text = (
            "Привет! Я FavoBot.\n\n"
            "📌 Клиентская часть:\n"
            "• Нажми «🧾 Заявка» — оформим заявку по шагам.\n"
            "• Можно просто прислать текстом заявку — я разберу.\n"
            "• «💸 Цены» — позже привяжем к прайсу.\n\n"
            "📊 Админ-команды:\n"
            "• /export_compact 06.11.2025 — Excel за дату\n"
            "• /export_compact — за сегодня\n"
            "• /shops — список всех магазинов\n"
            "• /whoami — твой user_id\n"
        )
    else:
        text = (
            "Привет! Я FavoBot.\n\n"
            "Ты можешь:\n"
            "• жать «🧾 Заявка» и оформлять заказ по шагам;\n"
            "• отправлять заявки просто текстом.\n\n"
            "Остальные команды доступны только администратору."
            "Узнать свой ID  можно командой /whoami."
        )

    await msg.answer(text, reply_markup=main_keyboard())


# === EXPORT (только для админа) ===

@router.message(Command("export_compact"))
async def handle_export(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Эта команда доступна только администратору.")
        return

    text = (msg.text or "").strip()

    parts = text.split(maxsplit=1)
    if len(parts) == 2:
        order_date = parts[1].strip()
    else:
        order_date = normalize_order_date("")

    path = export_orders(order_date)
    if not path:
        await msg.answer(f"На {order_date} пока нет заявок.")
        return

    doc = FSInputFile(path)
    await msg.answer_document(doc, caption=f"Отчёт по заявкам на {order_date}")


# === SHOPS (только для админа) ===

@router.message(Command("shops"))
async def handle_shops(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Эта команда доступна только администратору.")
        return

    shops = list_shops()
    if not shops:
        await msg.answer("Справочник магазинов пуст.")
        return

    text_lines = ["📒 Список магазинов:"]
    for s in shops:
        status = "🟢" if s["active"] else "🔴"
        text_lines.append(f"{status} {s['id']}. {s['name']}  ({s['date']})")

    result = "\n".join(text_lines)
    if len(result) < 4000:
        await msg.answer(result)
    else:
        chunk = []
        for line in text_lines:
            chunk.append(line)
            if len("\n".join(chunk)) > 3000:
                await msg.answer("\n".join(chunk))
                chunk = []
        if chunk:
            await msg.answer("\n".join(chunk))


# === FORM HANDLING (🧾 Заявка) ===

async def handle_form_step(msg: types.Message, state: dict):
    user_id = msg.from_user.id
    text = (msg.text or "").strip()

    # возможность отмены
    if text.lower() in {"отмена", "cancel"}:
        FORM_STATE.pop(user_id, None)
        await msg.answer("Ок, отменил 💛", reply_markup=main_keyboard())
        return

    step = state.get("step")

    # 1 — выбираем магазин
    if step == "shop":
        shop_name = text
        state["shop_name"] = shop_name

        # сохраняем в БД
        shop_id = get_or_create_shop(shop_name)
        state["shop_id"] = shop_id

        state["step"] = "date"
        await msg.answer(
            "На какую дату заявка? (например: 06.11.2025)\n"
            "Можно написать: сегодня",
        )
        return

    # 2 — выбираем дату
    if step == "date":
        if text.lower() == "сегодня" or not text:
            order_date = normalize_order_date("")
        else:
            order_date = text

        state["order_date"] = order_date
        state["step"] = "items"

        await msg.answer(
            "Теперь пришли список позиций одним сообщением.\n"
            "Например:\n"
            "Жигули 3\n"
            "Немецкое акция\n"
            "Пэт 2л-1\n\n"
            "Когда закончишь — просто отправь.",
        )
        return

    # 3 — принимаем позиции
    if step == "items":
        shop_name = state["shop_name"]
        shop_id = state["shop_id"]
        order_date = state["order_date"]

        synthetic_msg = shop_name + "\n" + text

        result = parse_message(synthetic_msg)
        if result.get("type") != "order":
            await msg.answer("⚠ Не смог разобрать позиции. Попробуй ещё раз.")
            FORM_STATE.pop(user_id, None)
            return

        items = result.get("items") or []

        record_order(order_date, items, shop_id=shop_id)

        FORM_STATE.pop(user_id, None)

        await msg.answer(
            f"Заявка оформлена ✅\n"
            f"🏪 Магазин: {shop_name}\n"
            f"📅 Дата: {order_date}\n"
            f"📦 Позиции: {len(items)}",
            reply_markup=main_keyboard(),
        )
        return


# === ОБРАБОТКА ТЕКСТА (кнопки + свободный формат) ===

@router.message(F.text)
async def handle_text(msg: types.Message):
    user_id = msg.from_user.id
    text = (msg.text or "").strip()
    # === СЛУЖЕБНОЕ СООБЩЕНИЕ: ПРИЁМ ЗАЯВОК ===
    if is_order_header(text):
        date = normalize_order_date(text)
        if date:
            CURRENT_ORDER_DATE[msg.chat.id] = date
            await msg.answer(f"📅 Принял. Дата заявок: {date}")
        else:
            await msg.answer("📅 Принял сообщение о приёме заявок.")
        return

    if not text:
        return

    # продолжаем форму
    if user_id in FORM_STATE:
        await handle_form_step(msg, FORM_STATE[user_id])
        return

    # кнопка заявки
    if text in {"🧾 Заявка", "Заявка"}:
        FORM_STATE[user_id] = {"step": "shop"}
        await msg.answer(
            "🧾 Новая заявка\n\n"
            "Шаг 1 — Как называется магазин?",
        )
        return

    # цены
    if text in {"💸 Цены", "Цены"}:
        await msg.answer("Прайс пока не подключён 💛")
        return

    # сторонние команды игнорируем
    if text.startswith("/"):
        return

    # ==== СВОБОДНЫЙ ФОРМАТ ЗАЯВКИ ====
    result = parse_message(text)
    if result.get("type") != "order":
        await msg.answer("⚠ Я не смог понять сообщение как заявку.")
        return

    order_date = result.get("order_date")
    shop_name = result.get("shop") or "неизвестный магазин"
    items = result.get("items") or []

    shop_id = get_or_create_shop(shop_name)

    record_order(order_date, items, shop_id=shop_id)

    await msg.answer(f"{shop_name} ✓ {len(items)} позиций")


