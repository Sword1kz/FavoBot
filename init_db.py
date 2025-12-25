import sqlite3
import csv
import os

DB_NAME = "favo.db"
SQL_FILE = "create_db.sql"
CSV_FILE = "products.csv"

is_new = not os.path.exists(DB_NAME)

if is_new:
    print("🔧 База не найдена, создаю новую favo.db ...")
else:
    print("ℹ️ База favo.db уже существует, обновляю структуру и справочник товаров...")

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

# 1) Создаём/обновляем структуру таблиц
with open(SQL_FILE, "r", encoding="utf-8") as f:
    sql_script = f.read()
cur.executescript(sql_script)

# 2) Загружаем товары из CSV
with open(CSV_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = []
    for r in reader:
        name_norm = r["name_norm"].strip()
        display_name = r["display_name"].strip()
        container_code = r["container_code"].strip()
        volume_l = float(r["volume_l"]) if r["volume_l"] else 0.0
        pack_size = int(r["pack_size"]) if r["pack_size"] else 0
        promo_type = r["promo_type"].strip()
        active = int(r["active"]) if r["active"] else 1

        rows.append(
            (name_norm, display_name, container_code, volume_l, pack_size, promo_type, active)
        )

# 3) Вставляем/обновляем товары
# Если товар с таким name_norm уже есть — обновим его поля
cur.executemany(
    """
    INSERT INTO products (name_norm, display_name, container_code, volume_l, pack_size, promo_type, active)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(name_norm) DO UPDATE SET
        display_name=excluded.display_name,
        container_code=excluded.container_code,
        volume_l=excluded.volume_l,
        pack_size=excluded.pack_size,
        promo_type=excluded.promo_type,
        active=excluded.active
    """,
    rows,
)

conn.commit()

# Немного статистики
cur.execute("SELECT COUNT(*) FROM products")
count_products = cur.fetchone()[0]

conn.close()

if is_new:
    print(f"✅ База {DB_NAME} создана и заполнена. Товаров в справочнике: {count_products}.")
else:
    print(f"✅ Справочник товаров обновлён. Сейчас в базе {count_products} товаров.")
