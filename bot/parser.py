import re
from datetime import date
from typing import Optional

#Проверяем не служебное ли это сообщение
def is_order_header(text: str) -> bool:
    text = text.lower()
    return bool(
        re.search(r"заявк[аи]?\s+на\s+\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}", text)
    )
# Простейшая нормализация даты из текста "заявки на ..."
DATE_PAT = re.compile(r"(?:заявк[аи]\s+на\s+)(\d{1,2}\.\d{1,2}(?:\.\d{2,4})?)", re.I)

def normalize_order_date(text: str) -> Optional[str]:
    m = DATE_PAT.search(text or "")
    if not m:
        return None
    raw = m.group(1)
    parts = raw.split(".")
    if len(parts) == 2:
        d, mth = parts
        y = str(date.today().year)
    else:
        d, mth, y = parts
        if len(y) == 2:
            y = "20" + y
    # zero-pad
    d = str(int(d)).zfill(2)
    mth = str(int(mth)).zfill(2)
    return f"{d}.{mth}.{y}"

# кеги
KEG_30 = {"бархатное", "бархатное янтарное", "немецкое", "прага", "чешское", "пшеничное"}
KEG_50 = {"жигули", "квас", "лимонад", "мохито"}

PET_BAGS = {
    "пэт 1л": 100,
    "пэт 1.5л": 60,
    "пэт 2л": 50,
    "пэт 3л": 40,
}


def _canon_drink(s: str) -> str | None:
    t = s.lower()
    t = t.replace("ё", "е")
    if "жигул" in t:
        return "жигули"
    if "немец" in t:
        return "немецкое"
    if "праг" in t:
        return "прага"
    if "бархат" in t and "янтар" in t:
        return "бархатное янтарное"
    if "бархат" in t:
        return "бархатное"
    if "пшенич" in t:
        return "пшеничное"
    if "чешск" in t:
        return "чешское"
    if "лимонад" in t:
        return "лимонад"
    if "квас" in t:
        return "квас"
    if "мохито" in t:
        return "мохито"
    return None


def _canon_pet(ltr: str) -> str | None:
    ltr = ltr.replace(",", ".")
    if ltr in ("1", "1.0"):
        return "пэт 1л"
    if ltr in ("1.5", "1,5"):
        return "пэт 1.5л"
    if ltr in ("2", "2.0"):
        return "пэт 2л"
    if ltr in ("3", "3.0"):
        return "пэт 3л"
    return None


def _qty_from_liters(line: str):
    """
    'Бархатное 60 л' -> (2, 'бархатное', 'кега 30 л')
    'Жигули 50 л' -> (1, 'жигули', 'кега 50 л')
    """
    t = line.lower()
    m = re.search(r"(\d+)\s*л", t)
    if not m:
        return None
    liters = int(m.group(1))
    base = _canon_drink(t) or "бархатное"
    if base == "жигули" or base in {"квас", "лимонад", "мохито"}:
        size = 50
        uom = "кега 50 л"
    else:
        size = 30
        uom = "кега 30 л"
    qty = max(1, round(liters / size))
    return qty, base, uom


STOP_LINES = {
    "спасибо",
    "заранее спасибо",
    "добрый день",
    "добрый вечер",
    "здравствуйте",
    "ок",
    "окей",
}


def parse_message(text: str, current_shop: str | None = None, order_date: str | None = None):
    """
    Простая, но рабочая логика:
    - первая строка сообщения = название магазина
    - остальные строки = позиции
    """
    if not text:
        return {"type": "unknown"}

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {"type": "unknown"}

    # первая строка — магазин
    shop = lines[0]
    # иногда в первой строке могут написать "заявки на 06.11 ..." — отфильтруем
    if "заявк" in shop.lower() and "на" in shop.lower() and len(lines) > 1:
        shop = lines[1]
        lines = lines[1:]
    else:
        lines = lines[1:]

    if not order_date:
        order_date = normalize_order_date(text)

    items = []

    for raw in lines:
        s = raw.strip()
        s_lower = s.lower()

        # игнор чистых эмодзи и стоп-строк
        if not any(ch.isalpha() or ch.isdigit() for ch in s):
            continue
        if s_lower in STOP_LINES or s_lower == "💰":
            continue

        comment = ""
        promo = ""
        qty = None
        uom = ""

        # вынести 'по 485' в комментарий
        m_price = re.search(r"по\s*(\d+)", s_lower)
        if m_price:
            comment = (comment + f"по {m_price.group(1)}").strip()
            s_lower = s_lower.replace(m_price.group(0), "").strip()

        # if 'замена' — это отметим как комментарий
        if "замена" in s_lower:
            comment = (comment + " замена").strip()
            s_lower = s_lower.replace("замена", "").strip()

        # ПЭТ/бутылки 2л / 1,5л и т.д.
        # варианты: "Пэт 2л-1", "Пэт 1,5 л - 2", "Бутылки 2л - 2"
        m_pet = re.search(r"(пэт|бутылк[аи]?)\s*([\d.,]+)\s*л?\s*[-–—]?\s*(\d+)?", s_lower)
        if m_pet:
            ltr = m_pet.group(2)
            canon = _canon_pet(ltr)
            if canon:
                qty = int(m_pet.group(3)) if m_pet.group(3) else 1
                bag_size = PET_BAGS.get(canon, 0)
                uom = f"меш {bag_size} шт" if bag_size else "меш"
                items.append({
                    "shop": shop,
                    "name": canon,
                    "uom": uom,
                    "qty": qty,
                    "promo": "",
                    "comment": comment,
                })
                continue

        # паллеты Павлодар стекло:
        # "2 паллета павлодар стекло" или "павлодар стекло 2 паллета"
        m_pal1 = re.search(r"(\d+)\s+пал(е|е)т[аоы]?\s+(.+)", s_lower)
        m_pal2 = re.search(r"(.+?)\s+(\d+)\s+пал(е|е)т[аоы]?", s_lower)
        if m_pal1 or m_pal2:
            if m_pal1:
                qty = int(m_pal1.group(1))
                tail = m_pal1.group(3)
            else:
                qty = int(m_pal2.group(2))
                tail = m_pal2.group(1)
            if "павлодар" in tail and "стекло" in tail:
                items.append({
                    "shop": shop,
                    "name": "павлодарское стекло 0.45л",
                    "uom": "палл 20 шт",
                    "qty": qty,
                    "promo": "",
                    "comment": comment,
                })
                continue

        # 'Бархатное 60 л', 'Жигули 50 л'
        mlit = _qty_from_liters(s_lower)
        if mlit:
            qty, base, uom = mlit
            items.append({
                "shop": shop,
                "name": base,
                "uom": uom,
                "qty": qty,
                "promo": "",
                "comment": comment,
            })
            continue

        # Немецкое 1, Бархатное 3, Жигули 2
        m_basic = re.search(r"^(.+?)\s+(\d+)$", s_lower)
        if m_basic:
            name_part = m_basic.group(1).strip()
            qty = int(m_basic.group(2))
            base = _canon_drink(name_part)
            if base:
                name = base
                if base in KEG_50:
                    uom = "кега 50 л"
                elif base in KEG_30:
                    uom = "кега 30 л"
                else:
                    uom = ""
            else:
                name = name_part
                uom = ""

            # если есть слово "акция", определим промо
            if "акци" in s_lower:
                if name == "немецкое":
                    promo = "3+1"
                elif name in {"прага", "пшеничное"}:
                    promo = "5+1"

            items.append({
                "shop": shop,
                "name": name,
                "uom": uom,
                "qty": qty,
                "promo": promo,
                "comment": comment,
            })
            continue

        # 'Немецкое акция' без количества -> 1
        if "акци" in s_lower:
            base = _canon_drink(s_lower) or s_lower
            qty = 1
            if base == "немецкое":
                promo = "3+1"
            elif base in {"прага", "пшеничное"}:
                promo = "5+1"
            if base in KEG_50:
                uom = "кега 50 л"
            elif base in KEG_30:
                uom = "кега 30 л"
            items.append({
                "shop": shop,
                "name": base,
                "uom": uom,
                "qty": qty,
                "promo": promo,
                "comment": comment,
            })
            continue

        # Баллон углекислоты 1
        if "баллон" in s_lower and "углекислот" in s_lower:
            m_q = re.search(r"(\d+)", s_lower)
            qty = int(m_q.group(1)) if m_q else 1
            items.append({
                "shop": shop,
                "name": "Баллон углекислоты",
                "uom": "баллон",
                "qty": qty,
                "promo": "",
                "comment": comment,
            })
            continue

        # если мы сюда дошли — не поняли строку, но сохраним для проверки
        items.append({
            "shop": shop,
            "name": raw,
            "uom": "",
            "qty": "",
            "promo": "",
            "comment": "нужна проверка",
        })

    if not items:
        return {"type": "unknown"}

    return {
        "type": "order",
        "shop": shop,
        "order_date": order_date,
        "items": items,
    }
