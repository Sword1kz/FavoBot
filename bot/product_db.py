import os
import psycopg2

DB = os.getenv("DATABASE_URL")


def normalize(text: str) -> str:
    if not text:
        return ""
    return text.lower().strip().replace("ё", "е")


def get_or_create_product(display_name: str, volume_l=None, pack_size: int = 1, promo_type: str | None = None):
    """
    Ищет продукт по name_norm. Если не найден — создаёт.
    Возвращает product_id.
    """
    display_name = (display_name or "").strip()
    if not display_name:
        return None

    name_norm = normalize(display_name)
    pack_size = int(pack_size or 1)

    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id FROM products WHERE name_norm = %s", (name_norm,))
    row = cur.fetchone()
    if row:
        pid = row[0]
        cur.close()
        conn.close()
        return pid

    cur.execute(
        """
        INSERT INTO products (name_norm, display_name, volume_l, pack_size, promo_type, active)
        VALUES (%s, %s, %s, %s, %s, 1)
        RETURNING id
        """,
        (name_norm, display_name, volume_l, pack_size, promo_type),
    )

    pid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return pid
