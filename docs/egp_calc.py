"""Перерахунок усіх цифр ДЗ3 SockLock: EGP, сценарії, 6 проблем, перевірки. Запуск: python docs/egp_calc.py"""

# ROMI у дата-румі = виручка (LTV 12 міс.) / spend. EGP = Spend * (ROMI - 1).


def egp(spend: float, romi: float) -> float:
    """EGP = Spend x (ROMI - 100%)."""
    return spend * (romi - 1)


def line(title: str) -> None:
    """Друкує заголовок розділу."""
    print("\n" + "=" * 70 + "\n" + title + "\n" + "=" * 70)


# ---------------------------------------------------------------- 1. Джерела
line("1. EGP за джерелами")
sources = {"US originals": (120_000, 1.30), "US mods": (230_000, 1.40), "UK/CA/AU": (50_000, 1.24)}
total_spend = sum(s for s, _ in sources.values())
total_rev = sum(s * r for s, r in sources.values())
for name, (s, r) in sources.items():
    print(f"{name:14s} spend ${s/1e3:.0f}k  ROMI {r:.0%}  EGP = {s/1e3:.0f}k x {r-1:.2f} = ${egp(s, r)/1e3:.1f}k")
total_romi = total_rev / total_spend
total_egp = egp(total_spend, total_romi)
print(f"Разом spend ${total_spend/1e3:.0f}k, виручка ${total_rev/1e3:.0f}k, ROMI {total_romi:.1%}, EGP ${total_egp/1e3:.0f}k")
print(f"Частка модифікацій в EGP: {egp(*sources['US mods'])/total_egp:.1%}")
us_romi = (120_000 * 1.30 + 230_000 * 1.40) / 350_000
print(f"ROMI США (змішаний): {us_romi:.1%}")

# ---------------------------------------------------------------- 5. Воронка
line("5. Воронка США: узгодженість")
cpm, ctr, cr, ltv = 12.0, 0.012, 0.02, 68.0
cpc = cpm / (1000 * ctr)
cpa = cpc / cr
print(f"CPC = CPM / (1000 x CTR) = 12 / 12 = ${cpc:.2f}")
print(f"CPA = CPC / CR = {cpc:.2f} / {cr} = ${cpa:.0f}")
print(f"ROMI воронки = LTV / CPA = 68 / {cpa:.0f} = {ltv/cpa:.0%}  (vs змішаний ROMI США {us_romi:.1%})")
quiz = {"open": .88, "s3": .61, "s4": .58, "s5": .36, "offer": .31, "pay": .02}
print(f"Відвал на кроці 4 = 1 - 36/58 = {1 - quiz['s5']/quiz['s4']:.1%}")
print(f"Оплата від тих, хто дійшов до кроку 5 = 2,0/36 = {quiz['pay']/quiz['s5']:.2%}")

# ---------------------------------------------------------------- 2. Проблема 1
line("2. Проблема 1: текстові варіації модифікацій")
mods_now, hours_per_mod, orig_n, orig_h, designers = 240, 3.0, 40, 12.0, 6
mod_hours = mods_now * hours_per_mod
spend_per_mod = 230_000 / mods_now
romi_new = 1.30  # Припущення
egp_per_mod = egp(spend_per_mod, romi_new)
print(f"Spend на модифікацію = 230k / 240 = ${spend_per_mod:.0f}")
print(f"EGP на нову модифікацію = {spend_per_mod:.0f} x (1.30 - 1) = ${egp_per_mod:.1f}")
total_h = mod_hours + orig_n * orig_h
print(f"Завантаження: 240x3 + 40x12 = {mod_hours:.0f} + {orig_n*orig_h:.0f} = {total_h:.0f} год/міс; "
      f"на дизайнера {total_h/designers:.0f} год/міс = {total_h/designers/160:.0%} від 160 год")
scen = {"Песимістичний": 2.5, "Базовий": 2.0, "Оптимістичний": 1.5}
p1 = {}
for name, h in scen.items():
    n = mod_hours / h
    extra = n - mods_now
    p1[name] = extra * egp_per_mod
    print(f"{name:14s} 3->{h} год: {mod_hours:.0f}/{h} = {n:.0f} мод., +{extra:.0f}, "
          f"+EGP = {extra:.0f} x {egp_per_mod:.1f} = ${p1[name]/1e3:.1f}k, додатковий spend ${extra*spend_per_mod/1e3:.0f}k")
for text_h in (1.0, 1.5):
    for name, h in scen.items():
        print(f"  текстова частина {text_h} год: сценарій {name} знімає {(3-h)/text_h:.0%} текстової роботи")
print(f"Щоб зробити 500 мод. за ті самі 720 год, треба {mod_hours/500:.2f} год/мод.")
for h in (3.0, 2.0):
    need = 500 * h + orig_n * orig_h
    print(f"500 мод. по {h} год + оригінали = {need:.0f} год = {need/200:.1f} дизайн. по 200 год / {need/160:.1f} по 160 год")
for r in (1.40, 1.30, 1.20, 1.15, 1.10):
    print(f"  чутливість: ROMI нових мод. {r:.0%} -> базовий +EGP ${120*egp(spend_per_mod, r)/1e3:.1f}k")

# Альтернатива: найм
line("2b. Альтернатива: найняти дизайнерів на +120 модифікацій")
need_h = 120 * hours_per_mod
salary = 4_000  # Припущення: повна вартість дизайнера $/міс.
for label, cap in (("200 год (як зараз)", 200), ("160 год (норма)", 160), ("128 год (80% від норми)", 128)):
    d = need_h / cap
    print(f"{need_h:.0f} год / {label} = {d:.2f} дизайнера -> ${d*salary/1e3:.1f}k/міс")

# ---------------------------------------------------------------- 3. Шість проблем
line("3. Шість проблем: EGP (pess/base/opt), ефорт, коефіцієнт")
base_rev_all = total_rev  # $540k
us_egp = egp(120_000, 1.30) + egp(230_000, 1.40)  # $128k


def quiz_fix(drop_new: float, buy_ratio: float, spend: float, romi: float) -> tuple[float, float, float, float]:
    """Повертає (новий CR, новий ROMI, +EGP, відносний ріст CR) після зменшення відвалу на кроці 4."""
    s5_new = quiz["s4"] * (1 - drop_new)
    saved = s5_new - quiz["s5"]
    pay_rate = quiz["pay"] / quiz["s5"]
    cr_new = quiz["pay"] + saved * pay_rate * buy_ratio
    lift = cr_new / quiz["pay"] - 1
    return cr_new, romi * (1 + lift), spend * romi * lift, lift


print("P3 (квіз), база: відвал 38% -> 30%, врятовані купують у 2 рази гірше")
for label, spend, romi in (("весь spend $400k", 400_000, total_romi), ("лише США $350k", 350_000, us_romi),
                           ("на $800k", 800_000, 1.30)):
    c, r, g, lift = quiz_fix(0.30, 0.5, spend, romi)
    print(f"  {label}: CR {quiz['pay']:.2%} -> {c:.3%} (+{lift:.1%}), CPA ${cpc/c:.1f}, "
          f"ROMI {romi:.1%} -> {r:.1%}, +EGP ${g/1e3:.1f}k")
c, r, g, lift = quiz_fix(0.30, 0.5, 350_000, us_romi)
print(f"  ROMI воронки США: 68 / {cpc/c:.2f} = {ltv/(cpc/c):.1%}")

P = {}
P["1 Текстові варіації модифікацій"] = dict(egp=(p1["Песимістичний"], p1["Базовий"], p1["Оптимістичний"]),
                                            mvp_days=1, weeks=3.5, p=0.7)
# P2: більше переможців -> EGP США росте з еластичністю 0.3 (модифікації впираються в дизайнерів)
elast = 0.3  # Припущення
P["2 Мало оригіналів / win rate 2%"] = dict(
    egp=tuple(us_egp * elast * (wr / 0.02 - 1) for wr in (0.022, 0.025, 0.03)), mvp_days=3, weeks=6, p=0.3)
P["3 Відвал на кроці 4 квізу"] = dict(
    egp=(quiz_fix(0.34, 0.5, 400_000, total_romi)[2], quiz_fix(0.30, 0.5, 400_000, total_romi)[2],
         quiz_fix(0.26, 0.75, 400_000, total_romi)[2]), mvp_days=1, weeks=2, p=0.4)
# P4: CAPI / атрибуція -> відносний ріст виручки на тому ж spend
P["4 Meta не бачить 12% покупок"] = dict(
    egp=tuple(base_rev_all * x for x in (0.01, 0.025, 0.05)), mvp_days=2, weeks=2, p=0.6)
# P5: втрата = програші x зекономлені дні x денний бюджет тесту x (1 - ROMI програшу)
losers = 200  # Припущення: ~200 з 280 нових креативів/міс. вимикаються
P["5 UA: звіти і затримка kill/scale"] = dict(
    egp=tuple(losers * d * b * (1 - rl) for d, b, rl in ((0.25, 100, 0.7), (0.5, 150, 0.7), (0.75, 200, 0.6))),
    mvp_days=2, weeks=3, p=0.6)
# P6: DE/FR spend x (ROMI-1) + економія на локалізації 20 креативів x $80
P["6 Локалізація, DE/FR стоять"] = dict(
    egp=tuple(s * (r - 1) + 20 * 80 for s, r in ((20_000, 1.05), (30_000, 1.15), (60_000, 1.22))),
    mvp_days=2, weeks=4, p=0.4)

rows = []
for name, d in P.items():
    lo, base, hi = d["egp"]
    rows.append((name, lo, base, hi, d["mvp_days"], d["weeks"], base / d["weeks"], d["p"], base * d["p"] / d["weeks"]))
rows.sort(key=lambda x: -x[6])
print(f"{'Проблема':36s} {'песим':>7s} {'база':>7s} {'оптим':>7s} MVP,дн тижні  коеф,$k/тиж  P(успіх) з ризиком")
for i, (n, lo, b, hi, md, w, k, p, kr) in enumerate(rows, 1):
    print(f"{i}. {n:33s} {lo/1e3:6.1f}k {b/1e3:6.1f}k {hi/1e3:6.1f}k {md:5d} {w:6.1f} {k/1e3:10.1f} {p:8.1f} {kr/1e3:8.1f}")
print("Ранжир з поправкою на ризик:", [r[0][:1] for r in sorted(rows, key=lambda x: -x[8])])

# ---------------------------------------------------------------- 4. Приховані знахідки
line("4. Приховані знахідки")
print(f"Запас ROMI: {total_romi:.0%} - 125% = {(total_romi-1.25)*100:.0f} п.п.; UK/CA/AU 124% вже нижче порогу")
seen = 6160 / 7000
print(f"Meta бачить 6160/7000 = {seen:.0%}")
for name, (s, r) in sources.items():
    print(f"  {name:14s} реальний ROMI {r:.0%} -> у кабінеті {r*seen:.1%}")
print(f"  Весь акаунт: {total_romi:.0%} -> {total_romi*seen:.1%}")
print(f"  Поріг 125% реальний = {1.25*seen:.0%} у кабінеті; окупність 100% = {seen:.0%} у кабінеті")

# ---------------------------------------------------------------- 4b. $800k
line("4b. Загальний ROMI на $800k")
need_marg = (1.25 * 800_000 - total_rev) / 400_000
print(f"Умова: (540k + 400k x m) / 800k >= 125%  ->  m >= {need_marg:.0%} (ROMI додаткових $400k)")
for drop in (0, 0.03, 0.05, 0.10):
    old_rev = total_rev - 400_000 * drop
    m = (1.25 * 800_000 - old_rev) / 400_000
    print(f"  якщо ROMI старих $400k впаде на {drop*100:.0f} п.п. -> нові $400k мають дати >= {m:.0%}")


def scenario(parts: dict) -> float:
    """Друкує сценарій і повертає загальний ROMI."""
    s = sum(v[0] for v in parts.values())
    rev = sum(v[0] * v[1] for v in parts.values())
    for k, (sp, r) in parts.items():
        print(f"    {k:28s} ${sp/1e3:.0f}k @ {r:.0%}")
    print(f"    Разом ${s/1e3:.0f}k, ROMI {rev/s:.1%}, EGP ${egp(s, rev/s)/1e3:.0f}k, у кабінеті Meta {rev/s*seen:.1%}")
    return rev / s


print("  A) 500 модифікацій (базовий скейл):")
scenario({"US оригінали": (200_000, 1.25), "US мод. старі": (230_000, 1.40),
          "US мод. нові (+260)": (250_000, 1.30), "UK/CA/AU": (120_000, 1.20)})
print("  B) лише 360 модифікацій (інструмент, без найму), решту доливаємо в оригінали:")
scenario({"US оригінали": (335_000, 1.20), "US мод. старі": (230_000, 1.40),
          "US мод. нові (+120)": (115_000, 1.30), "UK/CA/AU": (120_000, 1.20)})
print("  C) стрес: нові мод. 115%, оригінали 115%, UK/CA/AU 115%, старі мод. 135%:")
scenario({"US оригінали": (200_000, 1.15), "US мод. старі": (230_000, 1.35),
          "US мод. нові": (250_000, 1.15), "UK/CA/AU": (120_000, 1.15)})
