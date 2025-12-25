import sqlite3

DB = "favo.db"

shop_id = int(input("Введите id магазина для удаления: "))  # ← ЗАМЕНИ НА НУЖНЫЙ ID

conn = sqlite3.connect(DB)
cur = conn.cursor()

# удаляем заявки магазина
cur.execute("DELETE FROM orders WHERE shop_id = ?", (shop_id,))

# удаляем сам магазин
cur.execute("DELETE FROM shops WHERE id = ?", (shop_id,))

conn.commit()
conn.close()

print(f"❌ Магазин с id={shop_id} удалён полностью")
