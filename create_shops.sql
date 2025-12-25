Python 3.10.11 (tags/v3.10.11:7d4cc5a, Apr  5 2023, 00:38:17) [MSC v.1929 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license()" for more information.
>>> CREATE TABLE IF NOT EXISTS shops (
...     id INTEGER PRIMARY KEY AUTOINCREMENT,
...     name TEXT UNIQUE,
...     normalized TEXT,
...     variants TEXT,
...     address TEXT,
...     note TEXT,
...     active INTEGER DEFAULT 1,
...     date_added TEXT
... );
