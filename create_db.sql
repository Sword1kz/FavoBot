CREATE TABLE IF NOT EXISTS shops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    normalized TEXT,
    variants TEXT,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_norm TEXT UNIQUE,
    display_name TEXT,
    container_code TEXT,
    volume_l REAL,
    pack_size INTEGER,
    promo_type TEXT,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER,
    order_date TEXT,
    chat_id TEXT,
    message_id TEXT,
    is_additional INTEGER DEFAULT 0,
    raw_text TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    qty_units REAL,
    liters_total REAL,
    promo_info TEXT,
    comment TEXT
);
