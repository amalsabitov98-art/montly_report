"""Build the May-August report with reconciled July and August figures."""
import json
import re
from collections import defaultdict
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
source = (ROOT / 'Turon_Tour_Report_May-July_2026 (4).html').read_text(encoding='utf-8')
data = json.loads((ROOT / 'august-data.json').read_text(encoding='utf-8'))
excluded_booking_ids = set(data.get('excludedBookingIds', []))
rows = [dict(zip(data['columns'], r)) for r in data['rows'] if r[0] not in excluded_booking_ids]
logo = re.search(r'<div class="brand"><img src="([^"]+)"', source)[1]
money = lambda n: '$' + f'{n:,.2f}'.replace(',', ' ').replace('.', ',') if n % 1 else '$' + f'{n:,.0f}'.replace(',', ' ')
percent = lambda n: f'{n:.1f}'.replace('.', ',') + '%'
july_sales = 208_751
july_bookings = 52
july_tourists = 167
july_profit = 13_144
june_sales = 93_949
june_bookings = 27
june_tourists = 85

def update_screen(html, screen_number, replacements):
    pattern = rf'(<section class="[^"]+" data-screen="{screen_number}"[^>]*>)(.*?)(</section>)'
    match = re.search(pattern, html, re.S)
    if not match:
        raise ValueError(f'Screen {screen_number} not found')
    body = match[2]
    for old, new in replacements:
        body = body.replace(old, new)
    return html[:match.start()] + match[1] + body + match[3] + html[match.end():]

july_replacements = [
    ('$206 271', '$208 751'), ('$206&nbsp;271', '$208&nbsp;751'),
    ('>163<', '>167<'), ('6,4%', '6,3%'),
    ('$3 967', '$4 014'), ('$3&nbsp;967', '$4&nbsp;014'),
    ('+119,6%', '+122,2%'), ('+91,8%', '+96,5%'), ('+14,0%', '+15,4%'),
    ('<td class="">Турция</td><td class="">16</td><td class="">55</td><td class="money">$77&nbsp;085</td>',
     '<td class="">Турция</td><td class="">16</td><td class="">59</td><td class="money">$79&nbsp;635</td>'),
    ('$16&nbsp;314', '$16&nbsp;244'),
    ('<td class="sub">Нафталан</td><td class="">1</td><td class="">2</td><td class="money">$2&nbsp;970</td>',
     '<td class="sub">Нафталан</td><td class="">1</td><td class="">2</td><td class="money">$2&nbsp;900</td>'),
    ('<td class="">Сарвиноз</td><td class="">18</td><td class="">48</td><td class="money">$59&nbsp;295</td>',
     '<td class="">Сарвиноз</td><td class="">18</td><td class="">52</td><td class="money">$61&nbsp;775</td>'),
    ('ПРЯМЫЕ ПРОДАЖИ БЕЗ АГЕНТА</span><b>$26&nbsp;635</b>',
     'ПРЯМЫЕ ПРОДАЖИ БЕЗ АГЕНТА</span><b>$29&nbsp;615</b>'),
    ('<td class="">Asialuxe</td><td class="">4</td><td class="">13</td><td class="money">$23&nbsp;090</td>',
     '<td class="">Asialuxe</td><td class="">4</td><td class="">15</td><td class="money">$22&nbsp;590</td>'),
    ('По трём броням на $9 670 нетто-стоимость и прибыль не подтверждены и в расчёт финансового результата не включены.',
     'Прибыль $903 по трём июльским броням получена и учтена в августе, поэтому не включена в прибыль июля.'),
    ('По трём броням на $9 670 нетто-стоимость и прибыль не подтверждены и в расчёт финансового результата не включены.',
     'Прибыль $903 по трём июльским броням получена и учтена в августе, поэтому не включена в прибыль июля.'),
]
source = update_screen(source, 5, july_replacements)
sales = sum(r['sales'] for r in rows)
profit = sum(r['profit'] or 0 for r in rows)
net = sum(r['net'] for r in rows)
received = sum(r['received'] for r in rows)
debt = sum(r['debt'] for r in rows)
tourists = sum(r['tourists'] for r in rows)
booking_count = len(rows)
sales_change = (sales / july_sales - 1) * 100
average_check = sales / booking_count
july_average_check = july_sales / july_bookings
average_check_change = (average_check / july_average_check - 1) * 100
summary_profit = sum(data['managerSummary'].values())
commission = summary_profit / 2
manager_marketing = data['managerMarketingDeduction'] * 4
manager_payout = commission - manager_marketing
office_marketing = data['marketing'] - manager_marketing
office = summary_profit - manager_payout - data['marketing']
prior_profit = sum(data['priorMonthProfit'].values())
assert round(profit + prior_profit, 2) == summary_profit

def groups(key, exclude=()):
    result = defaultdict(lambda: dict(bookings=0, tourists=0, sales=0, profit=0, pending=0))
    for r in rows:
        if r[key] in exclude:
            continue
        g = result[r[key]]
        g['bookings'] += 1
        for metric in ['tourists', 'sales', 'profit']:
            g[metric] += r[metric] or 0
        g['pending'] += r['profit'] is None
    return sorted(result.items(), key=lambda v: -v[1]['sales'])

def table(key, title, exclude=()):
    body = ''
    for name, g in groups(key, exclude):
        mark = '<sup>*</sup>' if g['pending'] else ''
        body += f'<tr><td>{escape(name)}{mark}</td><td>{g["bookings"]}</td><td>{g["tourists"]}</td><td class="money">{money(g["sales"])}</td><td>{money(g["profit"])}</td></tr>'
    return f'<div class="augTableScroll tableWrap"><table class="dataTable"><thead><tr><th>{title}</th><th>Брони</th><th>Туристы</th><th>Продажи</th><th>Прибыль по строкам</th></tr></thead><tbody>{body}</tbody></table></div>'

def pair(label, value, cls=''):
    return f'<div class="{cls}"><span>{label}</span><b>{value}</b></div>'

def panel(title, content, cls=''):
    return f'<article class="augPanel {cls}"><h3>{title}</h3>{content}</article>'

def header(variant):
    finance = variant == 'finance'
    return f'''<header class="appbar"><div class="brand"><img src="{logo}" alt="Turon Tour"><div><b>TURON TOUR</b><span>ОТЧЁТ ПО ПРОДАЖАМ</span></div></div><div class="titleBlock"><small>УПРАВЛЕНЧЕСКИЙ ОТЧЁТ</small><h2>АВГУСТ 2026</h2><p>{'Финансовый дашборд' if finance else 'Структура продаж'}</p></div><div class="spacer"></div><div class="viewTabs"><button class="{'selected' if finance else ''}">ФИНАНСЫ</button><button class="{'' if finance else 'selected'}">СТРУКТУРА</button></div><div class="period">01.08.2026 — 31.08.2026</div></header>'''

def tabs(variant):
    return '<div class="cutTabs">' + ''.join(f'<button class="{"selected" if variant==v else ""}"><span>{label}</span><b>{len(groups(key, exclude))}</b></button>' for v,label,key,exclude in [('directions','НАПРАВЛЕНИЯ','direction',()),('managers','МЕНЕДЖЕРЫ','manager',()),('partners','ПАРТНЁРЫ','partner',('Turon','Individual'))]) + '</div>'

def kpi(label, value, note, cls=''):
    return f'<article class="augKpi {cls}"><span>{label}</span><strong>{value}</strong><p>{note}</p></article>'

notice = f'<aside class="augNotice"><b>Прибыль августа</b><span>{money(summary_profit)} учтено в августе: {money(profit)} по августовским броням и {money(prior_profit)}, полученные в августе по июльским броням (Сарвиноз $760, Шахноза $143).</span></aside>'
finances = ''.join(pair(a,b) for a,b in [
    ('Стоимость пакетов',money(sales)),('Нетто-стоимость',money(net)),('Прибыль августовских броней',money(profit)),
    ('Прибыль по июльским броням',money(prior_profit)),('Всего к распределению',money(summary_profit)),
    ('Маржа августовских броней',percent(profit/sales*100))])
settle = ''.join(pair(a,b) for a,b in [('Получено по августовским броням',money(received)),('Оплачено партнёрам',money(net)),('Долг партнёрам по строкам','$0'),('Долг клиентов',money(debt))])
settle += '<p class="augNote">Июльские поступления учитываются отдельно в распределении августовской прибыли и не увеличивают августовские продажи.</p>'
payout = ''.join(pair(a,b) for a,b in [('Всего к распределению',money(summary_profit)),('Комиссия менеджеров, 50%',money(commission)),('Маркетинг, всего',money(data['marketing'])),('Доля маркетинга офиса',money(office_marketing)),('Выплаты менеджерам после маркетинга',money(manager_payout))])
finance = header('finance') + '<div class="augBody">'
finance += '<div class="augKpis">'+kpi('ПРОДАЖИ',money(sales),percent(sales_change)+' к июлю')+kpi('ПРИБЫЛЬ АВГУСТА',money(summary_profit),'Включая $903 по июльским броням','gold')+kpi('БРОНИ / ТУРИСТЫ',f'{booking_count} / {tourists}','Средний чек '+money(round(average_check)))+'</div>'
finance += notice + '<div class="augFinanceGrid">'+panel('Финансы месяца','<div class="augPairs">'+finances+'</div>')+panel('Распределение прибыли','<div class="augPairs">'+payout+'</div>')+panel('Взаиморасчёты','<div class="augPairs">'+settle+'</div>')+'</div>'
finance += '<footer class="augFoot">Данные сгруппированы по месяцу бронирования. Июльские доплаты $903 отражены только в августовской прибыли.</footer></div>'

directions = header('directions')+'<div class="augBody">'+tabs('directions')+panel('Продажи по направлениям',table('direction','Направление'))+'<footer class="augFoot">Прибыль — сумма заполненных значений по бронированиям, до комиссий и маркетинга. Грузия + Турция сохранена как отдельное направление источника.</footer></div>'
manager_rows=''
for name,g in groups('manager'):
    summary=data['managerSummary'][name]
    allocation=data['managerMarketingDeduction'] if name!='Абдулкарим' else 0
    diff=data['priorMonthProfit'].get(name,0)
    assert round(g['profit']+diff,2)==summary
    manager_rows+=f'<tr><td>{name}</td><td>{g["bookings"]}</td><td>{g["tourists"]}</td><td class="money">{money(g["sales"])}</td><td>{money(g["profit"])}</td><td>{money(summary)}</td><td class="money">{money(diff)}</td><td>{money(summary/2)}</td><td>{money(round(allocation,2))}</td><td>{money(round(summary/2-allocation,2))}</td></tr>'
managers = header('managers')+'<div class="augBody">'+tabs('managers')+notice+panel('Менеджеры: продажи и распределение',f'<div class="augTableScroll tableWrap"><table class="dataTable"><thead><tr><th>Менеджер</th><th>Брони</th><th>Туристы</th><th>Продажи</th><th>По августовским<br>броням</th><th>Всего к<br>распределению</th><th>Получено<br>по июльским</th><th>Комиссия</th><th>Маркетинг</th><th>К выплате</th></tr></thead><tbody>{manager_rows}</tbody></table></div>')+'<footer class="augFoot">Удержание маркетинга по Excel: по $159,60 у четырёх менеджеров, всего $638,40. Абдулкарим — без удержания. К выплате менеджерам $6 236,60; офису остаётся $6 236,40. Доплаты из июля не увеличивают августовские продажи.</footer></div>'
own=sum(r['sales'] for r in rows if r['partner']=='Turon')
direct=sum(r['sales'] for r in rows if r['partner']=='Individual')
partners=header('partners')+'<div class="augBody">'+tabs('partners')+f'<div class="augStrips"><span>Собственный продукт Turon <b>{money(own)}</b></span><span>Individual — отдельно от внешних партнёров <b>{money(direct)}</b></span></div>'+panel('Внешние партнёры',table('partner','Партнёр',('Turon','Individual')))+'<footer class="augFoot">Прибыль — по строкам бронирований. Составные названия партнёров сохранены.</footer></div>'
dashboard='<section class="screen dashboard august" data-screen="7" id="august">'+''.join(f'<div class="dashboardVariant {"active" if v=="finance" else ""}" data-variant="{v}">{content}</div>' for v,content in [('finance',finance),('directions',directions),('managers',managers),('partners',partners)])+'</section>'

topdirs=groups('direction')[:3]
topvalue=sum(g['sales'] for _,g in topdirs)
def ranking(key,exclude=()):
    return '<ol>'+''.join(f'<li><span>{name}</span><b>{money(g["sales"])}</b></li>' for name,g in groups(key,exclude)[:3])+'</ol>'
summary=f'''<section class="screen augustSummary" data-screen="8" id="august-summary"><div class="augSummaryInner">
<header class="augSummaryBrand"><img src="{logo}" alt="Turon Tour"><span>TURON TOUR <em>/ ИТОГИ АВГУСТА</em></span><span class="augSummaryIndex">08 / 2026</span></header>
<div class="augSummaryTitle"><h1>АВГУСТ 2026</h1><p>{booking_count} бронирований · {tourists} туристов</p></div>
<div class="augSummaryMain"><article class="augHeroMetric"><span>ПРОДАЖИ МЕСЯЦА</span><strong>{money(sales)}</strong><p>{percent(sales_change)} к июлю</p><div>Средний чек <b>{money(round(average_check))}</b><small>{percent(average_check_change)} к июлю</small></div></article>
<div class="augSummaryRight"><article class="augGold"><span>ПРИБЫЛЬ АВГУСТА</span><strong>{money(summary_profit)}</strong><p>{money(profit)} по августовским броням + {money(prior_profit)}, полученные в августе по июльским</p></article></div></div>
<div class="augSummaryBottom"><article><h3>Топ-3 направления</h3><div class="augTopValue">{money(topvalue)} <small>{percent(topvalue/sales*100)} продаж</small></div><p>{' · '.join(n for n,_ in topdirs)}</p></article><article><h3>Топ-3 менеджера по продажам</h3>{ranking('manager')}</article><article><h3>Топ-3 внешних партнёра</h3>{ranking('partner',('Turon','Individual'))}</article></div>
<footer class="augSummaryFoot"><span>Собственный продукт {money(own)} · Individual {money(direct)} · маркетинг {money(data['marketing'])}, 50/50</span><span>Июльская прибыль {money(prior_profit)} получена и учтена в августе.</span></footer>
</div></section>'''

july_sales_change = (july_sales / june_sales - 1) * 100
july_average = july_sales / july_bookings
july_average_change = (july_average / (june_sales / june_bookings) - 1) * 100
july_top_directions = 79_635 + 38_330 + 27_030
july_summary = f'''<section class="screen augustSummary julySummary" data-screen="6" id="july-summary"><div class="augSummaryInner">
<header class="augSummaryBrand"><img src="{logo}" alt="Turon Tour"><span>TURON TOUR <em>/ ИТОГИ ИЮЛЯ</em></span><span class="augSummaryIndex">07 / 2026</span></header>
<div class="augSummaryTitle"><h1>ИЮЛЬ 2026</h1><p>{july_bookings} бронирования · {july_tourists} туристов</p></div>
<div class="augSummaryMain"><article class="augHeroMetric"><span>ПРОДАЖИ МЕСЯЦА</span><strong>{money(july_sales)}</strong><p>+{percent(july_sales_change)} к июню</p><div>Средний чек <b>{money(round(july_average))}</b><small>+{percent(july_average_change)} к июню</small></div></article>
<div class="augSummaryRight"><article class="augGold"><span>ПРИБЫЛЬ ИЮЛЯ</span><strong>{money(july_profit)}</strong><p>Маржа {percent(july_profit / july_sales * 100)}. Доплата по трём июльским броням отражена в августе.</p></article><article class="augGold"><span>ТУРИСТЫ</span><strong>{july_tourists}</strong><p>+{percent((july_tourists / june_tourists - 1) * 100)} к июню</p></article></div></div>
<div class="augSummaryBottom"><article><h3>Топ-3 направления</h3><div class="augTopValue">{money(july_top_directions)} <small>{percent(july_top_directions / july_sales * 100)} продаж</small></div><p>Турция · Шарм-эль-Шейх · Вьетнам</p></article><article><h3>Топ-3 менеджера по продажам</h3><ol><li><span>Сарвиноз</span><b>$61 775</b></li><li><span>Муслимжон</span><b>$59 437</b></li><li><span>Азиза</span><b>$47 975</b></li></ol></article><article><h3>Топ-3 внешних партнёра</h3><ol><li><span>Kazunion</span><b>$27 050</b></li><li><span>Asialuxe</span><b>$22 590</b></li><li><span>Kompas</span><b>$18 880</b></li></ol></article></div>
<footer class="augSummaryFoot"><span>Собственный продукт $22 985 · прямые продажи без агента $29 615</span><span>Прибыль $903 по июльским броням получена и учтена в августе.</span></footer>
</div></section>'''

source = re.sub(
    r'<section class="screen [^"]*" data-screen="6"[^>]*>.*?</section>',
    july_summary,
    source,
    count=1,
    flags=re.S,
)
cover = '<section class="screen cover active" data-screen="0" id="cover"><div class="visualFrame"><img class="visualBackdrop" src="cover-gross-profit-per-tourist-may-august-2026.png" alt="" aria-hidden="true"><div class="visualShade" aria-hidden="true"></div><img class="visualArtwork" src="cover-gross-profit-per-tourist-may-august-2026.png" alt="Отчёт Turon Tour по продажам и валовой прибыли за май — август 2026: 467 туристов, $40 463 валовой прибыли, $86,64 валовой прибыли с туриста"></div></section>'
source = re.sub(
    r'<section class="screen cover[^>]*>.*?</section>',
    cover,
    source,
    count=1,
    flags=re.S,
)

# Resolved reconciliation commentary is omitted from the presentation.
dashboard = re.sub(r'<aside class="augNotice">.*?</aside>', '', dashboard, flags=re.S)
dashboard = re.sub(r'<p class="augNote">.*?</p>', '', dashboard, flags=re.S)
dashboard = re.sub(r'<footer class="augFoot">.*?</footer>', '', dashboard, flags=re.S)
dashboard = dashboard.replace('<sup>*</sup>', '')

css='''
/* August screens are scoped; historical screens are left intact. */
.august .augBody{height:calc(100vh - 82px);padding:18px 36px 12px 28px;display:flex;flex-direction:column;gap:13px;overflow:auto;scrollbar-width:thin}
.august .augKpis{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.augKpi{background:#0a1921;border:1px solid #284a55;border-top:2px solid #22dfd0;border-radius:7px;padding:17px 18px}.augKpi>span{font-size:12px;letter-spacing:.08em;color:#adc3c8;font-weight:700}.augKpi strong{display:block;font-size:clamp(28px,2.7vw,46px);color:#75fff4;margin:13px 0 7px;white-space:nowrap}.augKpi p{font-size:12px;color:#9fb4ba;margin:0}.augKpi.gold{border-top-color:#dfad50}.augKpi.gold strong{color:#e9b75e}
.augNotice{border:1px solid #285762;background:#092028;border-radius:6px;padding:10px 14px;display:flex;align-items:baseline;gap:14px;font-size:12px;line-height:1.5;color:#a9c3cb}.augNotice b{color:#75fff4;white-space:nowrap}
.augFinanceGrid{display:grid;grid-template-columns:.92fr 1.14fr 1fr;gap:12px;flex:1;min-height:340px}.augPanel{background:#091820;border:1px solid #244751;border-radius:7px;overflow:hidden;min-height:0}.augPanel h3{font-size:16px;font-weight:650;margin:0;padding:14px 17px;border-bottom:1px solid #244751}.augPairs{padding:4px 17px 12px}.augPairs>div{display:flex;justify-content:space-between;gap:14px;padding:12px 0;border-bottom:1px solid #17343e;font-size:13px;line-height:1.35}.augPairs>div span{color:#a9bec5}.augPairs>div b{white-space:nowrap;text-align:right}.augPairs>div:last-of-type{border:0}.augNote{font-size:12px;line-height:1.55;color:#a4b9c0;margin:9px 0 0}.augFoot{font-size:12px;line-height:1.5;color:#9eb4bb;flex-shrink:0}.august .cutTabs{flex-shrink:0;margin:0}.august .cutTabs button span{font-size:12px}.august .augBody>.augPanel{flex:1;min-height:180px;display:flex;flex-direction:column}.augTableScroll{overflow:auto;min-height:0;flex:1;scrollbar-width:thin}.august .dataTable{width:100%}.august .dataTable th{font-size:12px;padding:12px;position:sticky;top:0;background:#08141b;z-index:1}.august .dataTable td{font-size:14px;padding:11px 12px}.august .dataTable sup{color:#e9b75e;margin-left:3px}.augWarn{color:#e9b75e}.augStrips{display:flex;gap:12px;flex-wrap:wrap;font-size:14px}.augStrips span{border:1px solid #244751;padding:12px 17px;border-radius:6px;color:#9eb4bb}.augStrips b{color:#75fff4;margin-left:12px}
.augustSummary{background:radial-gradient(ellipse at 18% 43%,#09272e 0,transparent 48%),#020b12;overflow:auto!important}.augSummaryInner{min-height:100vh;max-width:1800px;margin:auto;padding:22px 42px 16px;display:flex;flex-direction:column;gap:14px}.augSummaryBrand{display:flex;gap:14px;align-items:center;border-bottom:1px solid #19313a;padding-bottom:12px}.augSummaryBrand img{width:56px;height:56px;object-fit:contain}.augSummaryBrand span{font-size:20px;letter-spacing:.07em}.augSummaryBrand em{font-style:normal;color:#22dfd0}.augSummaryBrand .augSummaryIndex{margin-left:auto;font-size:13px;color:#8ba7b1}.augSummaryTitle{display:flex;align-items:baseline;justify-content:space-between;gap:20px}.augSummaryTitle h1{font:400 clamp(46px,5.4vw,88px)/1.05 Georgia,'Times New Roman',serif;letter-spacing:-.035em;margin:5px 0;color:#ebe9e3}.augSummaryTitle p{font-size:17px;color:#aec1c7;margin:0}.augSummaryMain{display:grid;grid-template-columns:1.65fr 1fr;gap:16px;flex:1}.augHeroMetric,.augSummaryRight article,.augSummaryBottom article{border:1px solid #24636c;border-radius:13px;background:rgba(3,14,21,.66);padding:24px}.augHeroMetric>span,.augSummaryRight article>span{font-size:17px;letter-spacing:.07em;color:#22dfd0}.augHeroMetric>strong{display:block;font-size:clamp(62px,7.5vw,124px);letter-spacing:-.045em;color:#35ded8;line-height:1.2;margin:16px 0 8px}.augHeroMetric>p{font-size:26px;color:#75fff4;margin:0 0 22px}.augHeroMetric>div{display:flex;align-items:baseline;gap:10px;font-size:19px;color:#c0cdd0}.augHeroMetric small{font-size:13px;color:#89a8b3;margin-left:auto}.augSummaryRight{display:grid;grid-template-rows:1fr;gap:14px}.augSummaryRight .augGold{border-color:#806231;padding:20px 24px;display:flex;flex-direction:column;justify-content:center}.augGold>strong{display:block;font-size:clamp(33px,3.5vw,57px);letter-spacing:-.025em;line-height:1.2;color:#efbd69;margin:9px 0}.augGold>p{font-size:13px;color:#bdb9a9;margin:0;line-height:1.45}.augSummaryRight .augGold>span{color:#eabb6e;font-size:15px}.augSummaryBottom{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}.augSummaryBottom article{padding:18px 21px}.augSummaryBottom h3{font-size:14px;letter-spacing:.025em;color:#43d9d5;margin:0 0 14px;font-weight:500}.augSummaryBottom p{font-size:14px;color:#c5d0d2;margin:10px 0 0}.augTopValue{font-size:30px;color:#75fff4;white-space:nowrap}.augTopValue small{font-size:12px;color:#adc3ca;margin-left:8px}.augSummaryBottom ol{list-style:none;counter-reset:rank;margin:0;padding:0}.augSummaryBottom li{counter-increment:rank;display:flex;gap:9px;align-items:baseline;font-size:15px;padding:6px 0}.augSummaryBottom li:before{content:counter(rank);color:#22dfd0}.augSummaryBottom li b{font-weight:500;margin-left:auto;white-space:nowrap}.augSummaryFoot{color:#9bb2bc;font-size:12px;line-height:1.6;display:flex;flex-direction:column}
@media(min-height:850px){.augSummaryInner{gap:20px;padding-top:30px;padding-bottom:24px}.augSummaryMain{min-height:365px}.augSummaryBottom article{padding-top:23px;padding-bottom:23px}}
@media(max-height:800px){.august .augBody{height:calc(100vh - 74px);gap:10px;padding-top:12px}.augKpi{padding:12px 15px}.augKpi strong{margin:9px 0 5px}.augPairs>div{padding:9px 0}.augFinanceGrid{min-height:310px}.augSummaryInner{gap:10px;padding-top:15px}.augSummaryBrand{padding-bottom:8px}.augSummaryBrand img{height:44px;width:44px}.augSummaryTitle h1{font-size:62px}.augHeroMetric,.augSummaryRight article{padding:18px}.augHeroMetric>strong{font-size:88px}.augHeroMetric>p{margin-bottom:16px}.augSummaryBottom article{padding:13px 18px}.augSummaryBottom h3{margin-bottom:9px}}
@media(max-width:800px){.siteShell:has(.august.active),.siteShell:has(.augustSummary.active){min-width:0}.august .appbar{height:auto;min-height:112px;padding:12px 20px;flex-wrap:wrap;gap:10px}.august .brand{min-width:0}.august .brand img{width:36px;height:36px}.august .brand div{display:none}.august .titleBlock h2{font-size:24px}.august .titleBlock{padding-left:12px}.august .viewTabs{margin-left:auto}.august .viewTabs button{padding:9px;font-size:12px}.august .spacer{display:none}.august .augBody{height:calc(100dvh - 112px);padding:14px 26px 20px 14px}.august .augKpis{grid-template-columns:1fr 1fr}.augKpi strong{font-size:27px}.augKpi>span{font-size:12px}.augFinanceGrid{display:flex;flex-direction:column;min-height:0;flex:none}.augFinanceGrid .augPanel{flex:none}.augNotice{display:block}.augNotice b{display:block}.august .cutTabs{height:auto;min-height:48px}.august .cutTabs button{padding:8px;gap:4px;flex-wrap:wrap}.august .cutTabs button span{font-size:12px}.august .dataTable td{font-size:13px}.august .dataTable th{font-size:12px}.augSummaryInner{padding:18px 26px 24px 18px;min-height:100dvh;gap:17px}.augSummaryBrand span{font-size:13px}.augSummaryBrand img{height:38px;width:38px}.augSummaryBrand .augSummaryIndex{display:none}.augSummaryTitle{display:block}.augSummaryTitle h1{font-size:43px;margin-bottom:10px}.augSummaryTitle p{font-size:15px}.augSummaryMain{grid-template-columns:1fr}.augHeroMetric>strong{font-size:70px}.augHeroMetric>div{font-size:16px;flex-wrap:wrap}.augSummaryRight{grid-template-columns:1fr;grid-template-rows:auto}.augGold>strong{font-size:40px}.augSummaryBottom{grid-template-columns:1fr}.augSummaryBottom h3{font-size:15px}.augSummaryBottom li{font-size:16px}.augSummaryFoot{font-size:12px}}
'''

result=source.replace('</style>',css+'</style>',1)
result=result.replace('<nav class="rail"',dashboard+summary+'<nav class="rail"',1)
result=result.replace('</nav></main>','<button data-go="7" aria-label="Август — дашборд"><span>Август — дашборд</span></button><button data-go="8" aria-label="Итоги августа"><span>Итоги августа</span></button></nav></main>',1)
result=result.replace('<title>Turon Tour — Отчёт по продажам</title>','<title>Turon Tour — Отчёт по продажам и валовой прибыли, май–август 2026</title>')
result=result.replace('<span>ОТЧЁТ ПО ПРОДАЖАМ</span>','<span>ПРОДАЖИ И ВАЛОВАЯ ПРИБЫЛЬ</span>')
result=result.replace('  go(0);','  const startScreen={"#august":7,"#august-summary":8}[location.hash]??0;go(startScreen);')
# Internal August scrolling should not advance screens unexpectedly.
result=result.replace("const w=e.target.closest('.tableWrap');if(w&&w.scrollHeight>w.clientHeight+2)e.stopPropagation();", "for(let w=e.target.closest('.tableWrap, .augBody, .augustSummary');w;w=w.parentElement?.closest('.tableWrap, .augBody, .augustSummary')){const max=w.scrollHeight-w.clientHeight;if(max>2&&((e.deltaY>0&&w.scrollTop<max-2)||(e.deltaY<0&&w.scrollTop>2))){e.stopPropagation();return;}}")
result=result.replace("if(touchStart===null)return;const d=", "if(touchStart===null)return;const area=e.target.closest('.augBody, .augustSummary');if(area&&area.scrollHeight>area.clientHeight+2){touchStart=null;return;}const d=")
path=ROOT/'Turon_Tour_August_2026_FINAL.html'
path.write_text(result, encoding='utf-8')
(ROOT/'index.html').write_text('''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Turon Tour — Отчёт</title><script>location.replace('Turon_Tour_August_2026_FINAL.html'+(location.hash||'#cover'))</script><a href="Turon_Tour_August_2026_FINAL.html#cover">Открыть отчёт</a></html>''', encoding='utf-8')
print(json.dumps(dict(sales=sales,tourists=tourists,profit_rows=profit,profit_summary=summary_profit,net=net,received=received,debt_stated=debt,office_from_summary=office,own_product=own,individual=direct,top_directions=topdirs,output=str(path)),ensure_ascii=False,indent=2))
