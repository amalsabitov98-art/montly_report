"""Rebuild the July and August report screens from the current workbook extract."""
import json
import re
from collections import defaultdict
from html import escape
from pathlib import Path


ROOT = Path(__file__).parent
REPORT = ROOT / "Turon_Tour_August_2026_FINAL.html"
JUNE = {"bookings": 27, "tourists": 85, "sales": 93_949, "profit": 5_417}


def load_month(filename):
    data = json.loads((ROOT / filename).read_text(encoding="utf-8"))
    rows = [dict(zip(data["columns"], row)) for row in data["rows"]]
    for row in rows:
        row["manager"] = normalize_manager(row["manager"])
        row["partner"] = normalize_partner(row["partner"])
        row["direction"] = normalize_direction(row["direction"])
    return data, rows


def normalize_manager(value):
    names = {
        "AZIZA": "Азиза", "SARVINOZ": "Сарвиноз", "MUSLIMJON": "Муслимжон",
        "SHAHNOZA": "Шахноза", "ABDULKARIM": "Абдулкарим", "MADINA": "Мадина",
    }
    raw = str(value).strip()
    return names.get(raw.upper(), raw.title())


def normalize_partner(value):
    raw = " ".join(str(value).strip().split())
    known = {
        "individual": "Individual", "turon": "Turon", "kazunion": "Kazunion",
        "asialuxe": "Asialuxe", "kompas": "Kompas", "pegas": "Pegas",
        "prestige": "Prestige", "easybooking": "Easybooking", "fun&sun": "Fun&Sun",
        "ratehawk": "Ratehawk", "rezlive": "Rezlive",
    }
    return known.get(raw.casefold(), raw.title())


def normalize_direction(value):
    raw = " ".join(str(value).strip().split())
    upper = raw.upper()
    if ("ГРУЗИЯ" in upper and "ТУРЦИЯ" in upper) or ("GEORGIA" in upper and "TURKEY" in upper):
        return "Грузия + Турция"
    if any(token in upper for token in ("TURKIYA", "TURKEY", "BODRUM", "FETHIYE", "ANTALYA")) or upper == "ТУРЦИЯ":
        return "Турция"
    if "SHARM" in upper or "ШАРМ" in upper:
        return "Шарм-эль-Шейх"
    if "VIETNAM" in upper or "ВЬЕТНАМ" in upper:
        return "Вьетнам"
    compact = upper.replace(" ", "")
    if "BATUMI+RIZE" in compact:
        return "Батуми + Ризе"
    translations = {
        "MALAYSIA": "Малайзия", "BALI": "Бали", "BALI + SINGAPORE": "Бали + Сингапур",
        "DUBAI": "Дубай", "GEORGIA": "Грузия", "CHINA": "Китай",
    }
    return translations.get(upper, raw.title())


def stats(rows):
    result = {"bookings": len(rows)}
    for key in ("tourists", "sales", "net", "profit", "received", "debt", "paid"):
        result[key] = sum((row[key] or 0) for row in rows)
    result["average"] = result["sales"] / result["bookings"]
    result["margin"] = result["profit"] / result["sales"] * 100
    result["partner_debt"] = result["net"] - result["paid"]
    return result


def grouped(rows, key, exclude=()):
    excluded = {item.casefold() for item in exclude}
    result = defaultdict(lambda: {"bookings": 0, "tourists": 0, "sales": 0, "profit": 0})
    for row in rows:
        if str(row[key]).casefold() in excluded:
            continue
        group = result[row[key]]
        group["bookings"] += 1
        for metric in ("tourists", "sales", "profit"):
            group[metric] += row[metric] or 0
    return sorted(result.items(), key=lambda item: (-item[1]["sales"], item[0]))


def money(value):
    value = round(value, 2)
    if value == int(value):
        body = f"{int(value):,}".replace(",", " ")
    else:
        body = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return "$" + body


def percent(value, signed=False):
    prefix = "+" if signed and value > 0 else ""
    return prefix + f"{value:.1f}".replace(".", ",") + "%"


def count_word(number, one, few, many):
    if 11 <= number % 100 <= 14:
        return many
    if number % 10 == 1:
        return one
    if 2 <= number % 10 <= 4:
        return few
    return many


def pair(label, value):
    return f"<div><span>{label}</span><b>{value}</b></div>"


def panel(title, content):
    return f'<article class="augPanel"><h3>{title}</h3>{content}</article>'


def header(month, period, variant):
    subtitle = "Финансовый дашборд" if variant == "finance" else "Структура продаж"
    return f'''<header class="appbar"><div class="brand"><img src="{{logo}}" alt="Turon Tour"><div><b>TURON TOUR</b><span>ПРОДАЖИ И ВАЛОВАЯ ПРИБЫЛЬ</span></div></div><div class="titleBlock"><small>УПРАВЛЕНЧЕСКИЙ ОТЧЁТ</small><h2>{month.upper()} 2026</h2><p>{subtitle}</p></div><div class="spacer"></div><div class="viewTabs"><button class="{'selected' if variant == 'finance' else ''}">ФИНАНСЫ</button><button class="{'selected' if variant != 'finance' else ''}">СТРУКТУРА</button></div><div class="period">{period}</div></header>'''


def tabs(rows, variant):
    specs = (
        ("directions", "НАПРАВЛЕНИЯ", "direction", ()),
        ("managers", "МЕНЕДЖЕРЫ", "manager", ()),
        ("partners", "ПАРТНЁРЫ", "partner", ("Turon", "Individual")),
    )
    buttons = "".join(
        f'<button class="{"selected" if variant == name else ""}"><span>{label}</span><b>{len(grouped(rows, key, excluded))}</b></button>'
        for name, label, key, excluded in specs
    )
    return f'<div class="cutTabs">{buttons}</div>'


def data_table(rows, key, heading, exclude=()):
    body = "".join(
        f'<tr><td>{escape(name)}</td><td>{values["bookings"]}</td><td>{int(values["tourists"])}</td><td class="money">{money(values["sales"])}</td><td>{money(values["profit"])}</td></tr>'
        for name, values in grouped(rows, key, exclude)
    )
    return f'<div class="augTableScroll tableWrap"><table class="dataTable"><thead><tr><th>{heading}</th><th>Брони</th><th>Туристы</th><th>Продажи</th><th>Валовая прибыль</th></tr></thead><tbody>{body}</tbody></table></div>'


def kpi(label, value, note, css=""):
    return f'<article class="augKpi {css}"><span>{label}</span><strong>{value}</strong><p>{note}</p></article>'


def dashboard(rows, number, month, period, comparison, marketing=None):
    current = stats(rows)
    sales_change = (current["sales"] / comparison["sales"] - 1) * 100
    avg_change = (current["average"] / (comparison["sales"] / comparison["bookings"]) - 1) * 100
    tourist_change = (current["tourists"] / comparison["tourists"] - 1) * 100
    profit_change = (current["profit"] / comparison["profit"] - 1) * 100
    finance_pairs = "".join(pair(label, value) for label, value in (
        ("Продажи", money(current["sales"])), ("Нетто-стоимость", money(current["net"])),
        ("Валовая прибыль", money(current["profit"])), ("Маржа", percent(current["margin"])),
        ("Средний чек", money(round(current["average"]))),
    ))
    comparison_pairs = "".join(pair(label, percent(value, True)) for label, value in (
        ("Продажи", sales_change), ("Валовая прибыль", profit_change),
        ("Туристы", tourist_change), ("Средний чек", avg_change),
    ))
    if marketing is not None:
        commission = current["profit"] / 2
        manager_marketing = 4 * 159.6
        comparison_title = "Распределение прибыли"
        comparison_pairs = "".join(pair(label, value) for label, value in (
            ("Валовая прибыль", money(current["profit"])), ("Комиссия менеджеров, 50%", money(commission)),
            ("Маркетинг, всего", money(marketing)), ("Доля маркетинга офиса", money(marketing - manager_marketing)),
            ("Выплаты менеджерам после маркетинга", money(commission - manager_marketing)),
        ))
    else:
        comparison_title = "Изменение к июню"
    settlement_pairs = "".join(pair(label, value) for label, value in (
        ("Получено от клиентов", money(current["received"])), ("Оплачено партнёрам", money(current["paid"])),
        ("Долг клиентов", money(current["debt"])), ("Долг партнёрам", money(current["partner_debt"])),
    ))
    finance = header(month, period, "finance") + '<div class="augBody"><div class="augKpis">'
    finance += kpi("ПРОДАЖИ", money(current["sales"]), percent(sales_change, True) + " к прошлому месяцу")
    finance += kpi("ВАЛОВАЯ ПРИБЫЛЬ", money(current["profit"]), "Маржа " + percent(current["margin"]), "gold")
    finance += kpi("БРОНИ / ТУРИСТЫ", f'{current["bookings"]} / {int(current["tourists"])}', "Средний чек " + money(round(current["average"])))
    finance += '</div><div class="augFinanceGrid">' + panel("Финансы месяца", '<div class="augPairs">' + finance_pairs + '</div>')
    finance += panel(comparison_title, '<div class="augPairs">' + comparison_pairs + '</div>')
    finance += panel("Взаиморасчёты", '<div class="augPairs">' + settlement_pairs + '</div>') + '</div></div>'
    variants = [("finance", finance)]
    for variant, key, heading, excluded in (
        ("directions", "direction", "Направление", ()),
        ("managers", "manager", "Менеджер", ()),
        ("partners", "partner", "Партнёр", ("Turon", "Individual")),
    ):
        own = sum(row["sales"] for row in rows if row["partner"] == "Turon")
        direct = sum(row["sales"] for row in rows if row["partner"] == "Individual")
        strips = ""
        if variant == "partners":
            strips = f'<div class="augStrips"><span>Собственный продукт Turon <b>{money(own)}</b></span><span>Прямые продажи Individual <b>{money(direct)}</b></span></div>'
        content = header(month, period, variant) + '<div class="augBody">' + tabs(rows, variant) + strips
        content += panel("Продажи по структуре", data_table(rows, key, heading, excluded)) + '</div>'
        variants.append((variant, content))
    blocks = "".join(f'<div class="dashboardVariant {"active" if name == "finance" else ""}" data-variant="{name}">{content}</div>' for name, content in variants)
    return f'<section class="screen dashboard august" data-screen="{number}" id="{month.casefold()}">{blocks}</section>'


def ranking(rows, key, exclude=()):
    return '<ol>' + ''.join(
        f'<li><span>{escape(name)}</span><b>{money(values["sales"])}</b></li>'
        for name, values in grouped(rows, key, exclude)[:3]
    ) + '</ol>'


def summary(rows, number, month, month_number, comparison, marketing=None):
    current = stats(rows)
    sales_change = (current["sales"] / comparison["sales"] - 1) * 100
    avg_change = (current["average"] / (comparison["sales"] / comparison["bookings"]) - 1) * 100
    top_directions = grouped(rows, "direction")[:3]
    top_value = sum(values["sales"] for _, values in top_directions)
    own = sum(row["sales"] for row in rows if row["partner"] == "Turon")
    direct = sum(row["sales"] for row in rows if row["partner"] == "Individual")
    foot = f'Собственный продукт {money(own)} · прямые продажи {money(direct)}'
    if marketing is not None:
        foot += f' · маркетинг {money(marketing)}'
    month_genitive = {"Июль": "ИЮЛЯ", "Август": "АВГУСТА"}[month]
    return f'''<section class="screen augustSummary {'julySummary' if month_number == 7 else ''}" data-screen="{number}" id="{month.casefold()}-summary"><div class="augSummaryInner">
<header class="augSummaryBrand"><img src="{{logo}}" alt="Turon Tour"><span>TURON TOUR <em>/ ИТОГИ {month_genitive}</em></span><span class="augSummaryIndex">{month_number:02d} / 2026</span></header>
<div class="augSummaryTitle"><h1>{month.upper()} 2026</h1><p>{current["bookings"]} {count_word(current["bookings"], "бронирование", "бронирования", "бронирований")} · {int(current["tourists"])} {count_word(int(current["tourists"]), "турист", "туриста", "туристов")}</p></div>
<div class="augSummaryMain"><article class="augHeroMetric"><span>ПРОДАЖИ МЕСЯЦА</span><strong>{money(current["sales"])}</strong><p>{percent(sales_change, True)} к прошлому месяцу</p><div>Средний чек <b>{money(round(current["average"]))}</b><small>{percent(avg_change, True)} к прошлому месяцу</small></div></article>
<div class="augSummaryRight"><article class="augGold"><span>ВАЛОВАЯ ПРИБЫЛЬ</span><strong>{money(current["profit"])}</strong><p>Маржа {percent(current["margin"])}</p></article></div></div>
<div class="augSummaryBottom"><article><h3>Топ-3 направления</h3><div class="augTopValue">{money(top_value)} <small>{percent(top_value/current["sales"]*100)} продаж</small></div><p>{' · '.join(name for name, _ in top_directions)}</p></article><article><h3>Топ-3 менеджера по продажам</h3>{ranking(rows, "manager")}</article><article><h3>Топ-3 внешних партнёра</h3>{ranking(rows, "partner", ("Turon", "Individual"))}</article></div>
<footer class="augSummaryFoot"><span>{foot}</span></footer></div></section>'''


def replace_screen(html, number, content):
    pattern = rf'<section class="[^"]+" data-screen="{number}"[^>]*>.*?</section>'
    updated, count = re.subn(pattern, content, html, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"screen {number} was not found")
    return updated


def main():
    html = REPORT.read_text(encoding="utf-8")
    logo = re.search(r'<div class="brand"><img src="([^"]+)"', html)[1]
    july_data, july_rows = load_month("july-data.json")
    august_data, august_rows = load_month("august-data.json")
    july_stats = stats(july_rows)
    replacements = {
        5: dashboard(july_rows, 5, "Июль", "01.07.2026 — 31.07.2026", JUNE),
        6: summary(july_rows, 6, "Июль", 7, JUNE),
        7: dashboard(august_rows, 7, "Август", "01.08.2026 — 31.08.2026", july_stats, august_data["marketing"]),
        8: summary(august_rows, 8, "Август", 8, july_stats, august_data["marketing"]),
    }
    for number, content in replacements.items():
        html = replace_screen(html, number, content.replace("{logo}", logo))
    html = html.replace("ЧИСТАЯ ПРИБЫЛЬ", "ВАЛОВАЯ ПРИБЫЛЬ")
    html = html.replace("Чистая прибыль", "Валовая прибыль")
    cover_art = "cover-gross-profit-per-tourist-may-august-2026-v3.png"
    cover = f'''<section class="screen cover active" data-screen="0" id="cover"><div class="visualFrame"><img class="visualBackdrop" src="{cover_art}" alt="" aria-hidden="true"><div class="visualShade" aria-hidden="true"></div><img class="visualArtwork" src="{cover_art}" alt="Отчёт Turon Tour по продажам и валовой прибыли за май — август 2026: 461 турист, $40 220 валовой прибыли, $87,25 валовой прибыли с туриста"></div></section>'''
    html = replace_screen(html, 0, cover)
    html = re.sub(r'<title>.*?</title>', '<title>Turon Tour — Отчёт по продажам и валовой прибыли, май–август 2026</title>', html, count=1)
    REPORT.write_text(html, encoding="utf-8")
    print(json.dumps({
        "source": july_data["source"], "july": stats(july_rows), "august": stats(august_rows),
        "overall": {"bookings": 139, "tourists": 461, "sales": 581220, "profit": 40220},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
