import sqlite3
import datetime

DB = "favo.db"


def normalize(text: str) -> str:
    """Приводим строку к нормальному виду для поиска."""
    if not text:
        return ""
    return text.lower().strip().replace("ё", "е")


def find_shop(name: str):
    """
    Ищем магазин по нормализованному имени или полному.
    Возвращает tuple (id, name, normalized) или None.
    """
    if not name:
        return None

    name_n = normalize(name)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, normalized
        FROM shops
        WHERE normalized = ? OR name = ?
        """,
        (name_n, name.strip()),
    )

    row = cur.fetchone()
    conn.close()
    return row


def add_shop(name: str):
    """
    Создаём магазин в таблице shops, если его нет.
    Возвращает id нового магазина.
    """
    name = (name or "").strip()
    if not name:
        return None

    exists = find_shop(name)
    if exists:
        return exists[0]

    name_n = normalize(name)
    date_added = datetime.date.today().isoformat()

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO shops (name, normalized, date_added)
        VALUES (?, ?, ?)
        """,
        (name, name_n, date_added),
    )

    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    print(f"📒 [+] Added shop: {name} (id={new_id})")
    return new_id


def get_or_create_shop(name: str):
    """
    Возвращает ID магазина.
    Если не найден — создаёт.
    """
    row = find_shop(name)
    if row:
        return row[0]
    return add_shop(name)


def list_shops():
    """Возвращает список всех магазинов в виде словарей."""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, active, date_added
        FROM shops
        ORDER BY name
        """
    )

    rows = cur.fetchall()
    conn.close()

    return [
        {"id": r[0], "name": r[1], "active": r[2], "date": r[3]}
        for r in rows
    ]
