import os
import psycopg2
from decimal import Decimal
from bot.product_db import get_or_create_product
DB = os.getenv("DATABASE_URL")


def create_order(shop_id: int, chat_id: int, message_id: int | None = None, order_date: str | None = None) -> int:
    """
    Создаёт заказ и возвращает order_id
    """
    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    cur.execute(
         """
        INSERT INTO orders (shop_id, chat_id, message_id, order_date)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (shop_id, chat_id, message_id, order_date),
    )

    order_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return order_id


def add_order_item(order_id: int, item: dict):
    """
    Добавляет позицию в order_items.
    item — словарь из parse_message()
    """
    name = (item.get("name") or item.get("title") or item.get("product") or "").strip() 
    raw_text = item.get("raw_text") or name or None

    # qty
    qty = int(item.get("qty") or item.get("qty_units") or 1)

    # pack_size
    pack_size = int(item.get("pack_size") or item.get("pack") or 1)

    # volume_l
    volume_l = item.get("volume_l")

    # считаем итоговые литры
    liter_total = None
    if volume_l is not None:
        liter_total = Decimal(str(volume_l)) * Decimal(pack_size) * Decimal(qty)

    # promo/comment
    promo_info = item.get("promo_info") or item.get("promo") or None
    comment = item.get("comment") or None

    # product_id: если парсер не дал — создадим/найдём по имени
    product_id = item.get("product_id")
    if not product_id and name:
        product_id = get_or_create_product(
        display_name=name,
        volume_l=volume_l,
        pack_size=pack_size,
        promo_type=str(promo_info) if promo_info else None
    )

    # is_additional: если всё равно нет product_id — считаем как доп. позицию
    is_additional = 0 if product_id else 1

   
    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO order_items (
            order_id,
            product_id,
            qty_units,
            volume_l,
            pack_size,
            liter_total,
            is_additional,
            raw_text,
            promo_info,
            comment
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            order_id,
            product_id,
            qty,
            volume_l,
            pack_size,
            liter_total,
            is_additional,
            raw_text,
            promo_info,
            comment,
        ),
    )

    conn.commit()
    cur.close()
    conn.close()



