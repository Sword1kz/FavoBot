import asyncpg

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS shops (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    normalized TEXT NOT NULL UNIQUE,
    variants TEXT,
    active INTEGER DEFAULT 1,
    data_added TIMESTAMP DEFAULT now(),
    adress TEXT,
    note TEXT
   
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name_norm TEXT NOT NULL,
    display_name TEXT NOT NULL,
    container_code TEXT,
    volume_l NUMERIC(10,2),
    active INTEGER DEFAULT 1,
    promo_type TEXT,
    pack_size INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER REFERENCES shops(id) ON DELETE CASCADE,
    chat_id BIGINT NOT NULL,
    message_id INTEGER,
    is_additional INTEGER DEFAULT 0,
    raw_text TEXT    
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    qty_units INTEGER NOT NULL DEFAULT 1,
    liters_total NUMERIC(10,2),
    promo_info TEXT,
    comment TEXT
);
"""

async def init_db(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLES_SQL)
    print("✅ init_db: таблицы проверены/созданы")


