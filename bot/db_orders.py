import os
import psycopg2
from decimal import Decimal

DB = os.getenv("DATABASE_URL")


def create_order(shop_id: int, chat_id: int, message_id: int | None = None) -> int:
    """
    Создаёт заказ и возвращает order_id
    """
    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO orders (shop_id, chat_id, message_id)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (shop_id, chat_id, message_id),
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
    product_id = item.get("product_id")  # может быть None
    qty = int(item.get("qty", 1))

    volume_l = item.get("volume_l")
    pack_size = int(item.get("pack_size", 1))

    # считаем итоговые литры
    liter_total = None
    if volume_l is not None:
        liter_total = Decimal(str(volume_l)) * Decimal(pack_size) * Decimal(qty)

    is_additional = 1 if product_id is None else 0
    raw_text = item.get("raw_text")

    promo_info = item.get("promo")
    comment = item.get("comment")

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
