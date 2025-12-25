import os
from datetime import date
from typing import List, Dict

import pandas as pd

# простое хранилище заявок (на время работы бота)
ORDERS: List[Dict] = []


def record_order(order_date: str, items: List[Dict], shop_id: int | None = None):
    """
    Сохраняем разобранные позиции в память.
    Теперь поддерживаем опциональный shop_id.
    """
    if not order_date:
        order_date = date.today().strftime("%d.%m.%Y")

    for it in items:
        ORDERS.append({
            "order_date": order_date,
            "shop_id": shop_id,                         # id магазина (на будущее)
            "shop": it.get("shop") or "Без названия",
            "product": it.get("name") or "",
            "uom": it.get("uom") or "",
            "qty": it.get("qty") or "",
            "promo": it.get("promo") or "",
            "comment": it.get("comment") or "",
        })


def _liters_per_unit(uom: str, product: str) -> int:
    u = (uom or "").lower()
    p = (product or "").lower()
    if "a30" in u or ("бархат" in p or "пшенич" in p) and "30" in u:
        return 30
    if "p30" in u or ("немец" in p or "праг" in p or "чешск" in p) and "30" in u:
        return 30
    if "kr50" in u or ("жигул" in p and "50" in u):
        return 50
    if "p50" in u or (("лимонад" in p or "квас" in p or "мохито" in p) and "50" in u):
        return 50
    if "кега 30" in u:
        return 30
    if "кега 50" in u:
        return 50
    return 0


def _promo_multiplier(promo: str) -> int:
    """
    Для акций возвращаем во сколько раз кегов больше:
    3+1 -> 4 кеги, 5+1 -> 6 кег.
    Если промо нет — 1.
    """
    if not promo:
        return 1
    promo = promo.strip()
    if promo == "3+1":
        return 4
    if promo == "5+1":
        return 6
    return 1


def export_orders(order_date: str | None = None) -> str | None:
    """
    Строим Excel-отчёт по указанной дате (DD.MM.YYYY).
    """
    if not order_date:
        order_date = date.today().strftime("%d.%m.%Y")

    rows = [r for r in ORDERS if r["order_date"] == order_date]
    if not rows:
        return None

    # группируем: Магазин + Товар + Ед. изм. + Акция + Комментарий
    agg: Dict[tuple, Dict] = {}
    for r in rows:
        key = (r["shop"], r["product"], r["uom"], r["promo"], r["comment"])
        try:
            base_qty = int(r["qty"])
        except (ValueError, TypeError):
            base_qty = 0

        if key not in agg:
            agg[key] = {"qty": 0}

        agg[key]["qty"] += base_qty

    flat = []
    for (shop, product, uom, promo, comment), info in agg.items():
        base_qty = info["qty"]

        # множитель по акции (3+1 -> 4, 5+1 -> 6)
        mult = _promo_multiplier(promo)
        effective_qty = base_qty * mult if base_qty else base_qty

        lit_per = _liters_per_unit(uom, product)
        liters = effective_qty * lit_per if lit_per and effective_qty else ""

        flat.append({
            "Магазин": shop,
            "Товар": product,
            "Ед. изм.": uom,
            "Кол-во": effective_qty if effective_qty else "",
            "Литры": liters,
            "Акция": promo,
            "Комментарий": comment,
        })

    df = pd.DataFrame(
        flat,
        columns=["Магазин", "Товар", "Ед. изм.", "Кол-во", "Литры", "Акция", "Комментарий"]
    )

    # сортировка по магазину и товару
    df = df.sort_values(["Магазин", "Товар"], ignore_index=True)

    # пустим название магазина только на первой строке блока
    last_shop = None
    for i in range(len(df)):
        shop = df.at[i, "Магазин"]
        if shop == last_shop:
            df.at[i, "Магазин"] = ""
        else:
            last_shop = shop

    # ИТОГО по товарам (с учётом акций, 30/50л и т.п.)
    totals = df.groupby(["Товар", "Ед. изм."], dropna=False)[["Кол-во", "Литры"]].sum().reset_index()

    outdir = "exports"
    os.makedirs(outdir, exist_ok=True)
    fname = f"orders_{order_date.replace('.', '-')}.xlsx"
    path = os.path.join(outdir, fname)

    with pd.ExcelWriter(path, engine="openpyxl") as w:
        sheet = "Заявки"

        # шапка
        head = pd.DataFrame([[f"Отчёт по заявкам на {order_date}"]])
        head.to_excel(w, index=False, header=False, sheet_name=sheet, startrow=0)

        # детальная таблица
        start_details = 2
        df.to_excel(w, index=False, sheet_name=sheet, startrow=start_details)

        # блок итогов
        totals_start = start_details + len(df) + 2
        title_totals = pd.DataFrame([["ИТОГО ПО ТОВАРАМ"]])
        title_totals.to_excel(w, index=False, header=False, sheet_name=sheet, startrow=totals_start)

        totals.to_excel(w, index=False, sheet_name=sheet, startrow=totals_start + 1)

    return path
