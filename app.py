"""Streamlit UI: paste a winning script, get a brief of variations, rate them with 👍/👎."""

from datetime import date

import streamlit as st

import usage
from generator import EXAMPLES_DIR, SECTIONS, generate, get_provider
from memory import (
    MAX_TOKENS,
    add_rule,
    delete_rule,
    estimate_tokens,
    load_rules,
    make_rule,
    should_make_rule,
    template_rule,
)

SECTION_TITLES = {"hooks": "Хуки (0–3 с)", "first_lines": "Перші фрази після хука", "on_screen": "Текст на екрані"}
PROVIDER_LABELS = {"demo": "демо: збережена відповідь", "ollama": "Ollama, локально", "anthropic": "Claude API"}
OWN_SCRIPT = "Свій скрипт"
TEAM_SIZE = 6  # motion designers; rollout goal: ≥4 of 6 use it every week

st.set_page_config(page_title="SockLock: варіації для модифікацій", page_icon="🧦", layout="wide")

# Every click reruns this file from top to bottom. Only four things must survive a rerun:
# the current brief, which cards are rated, the liked variants for the download,
# and a generation counter that gives each new brief fresh widget keys (so old "why" texts don't carry over).
if "brief" not in st.session_state:
    st.session_state.brief = None
    st.session_state.rated = {}  # card key → True (👍) / False (👎)
    st.session_state.liked = []  # (section, variant) pairs
    st.session_state.generation = 0

provider = get_provider()
is_demo = provider == "demo"  # demo clicks are not logged, so they don't spoil the pilot metrics

# One shared instance for the whole team: the name tells whose click it was in usage_log.csv.
with st.sidebar:
    designer = st.text_input("Хто ви", key="designer", placeholder="Ім'я, наприклад Оля").strip()


def rate(section: str, key: str, variant: dict, liked: bool, reason: str) -> None:
    """Log a 👍/👎, turn it into a rule in shared memory when it carries a lesson, and remember the card as rated."""
    if should_make_rule(liked, reason):
        with st.spinner("Записую правило в пам'ять…"):
            try:
                rule = make_rule(variant, section, liked, reason)
            except Exception:  # model unavailable: a template rule is better than losing the feedback
                rule = template_rule(variant, section, liked, reason)
        add_rule(rule)
        st.toast(f"Нове правило: {rule}", icon="🧠")
    else:
        st.toast("👍 записано. Правило з 👍 створюється лише з причиною.", icon="👍")
    if not is_demo:
        usage.log_event(designer, "like" if liked else "dislike", section, variant["angle"])
    st.session_state.rated[key] = liked
    if liked:
        st.session_state.liked.append((section, variant))
    st.rerun()  # redraw so the card shows "rated" and the sidebar shows the new rule


def show_card(section: str, index: int, variant: dict) -> None:
    """One variation: text, angle badge, why, compliance flags, and 👍/👎 with an optional reason."""
    key = f"{st.session_state.generation}-{section}-{index}"
    with st.container(border=True):
        st.badge(variant["angle"], color="violet")
        st.markdown(f"**{variant['text']}**")
        st.caption(variant["why"])
        for flag in variant["flags"]:
            st.warning(flag, icon="⚠️")

        if key in st.session_state.rated:
            st.caption("✓ Оцінено " + ("👍" if st.session_state.rated[key] else "👎"))
            return
        reason = st.text_input(
            "Чому?", key=f"why-{key}", placeholder="Чому? Одне речення (для 👍 потрібне, щоб створити правило)", label_visibility="collapsed"
        )
        like_col, dislike_col = st.columns(2)
        if like_col.button("👍", key=f"like-{key}", width="stretch"):
            rate(section, key, variant, True, reason)
        if dislike_col.button("👎", key=f"dislike-{key}", width="stretch"):
            rate(section, key, variant, False, reason)


def show_removed(removed: dict) -> None:
    """Expander with variations dropped as too similar, and what they were similar to."""
    items = [(section, variant) for section in SECTIONS for variant in removed[section]]
    if not items:
        st.caption("Схожих варіантів не знайдено.")
        return
    with st.expander(f"Прибрано {len(items)} схожих варіантів"):
        for section, variant in items:
            st.markdown(
                f"- **{variant['text']}** · схожість {variant['similarity']:.2f} з «{variant['similar_to']}»"
                f" · _{SECTION_TITLES[section]}_"
            )


def brief_markdown(liked: list[tuple[str, dict]], script: str) -> str:
    """Build the downloadable brief: liked variations grouped by section, plus the original script."""
    lines = [f"# Бриф модифікацій SockLock, {date.today()}", ""]
    for section in SECTIONS:
        variants = [variant for s, variant in liked if s == section]
        if variants:
            lines += [f"## {SECTION_TITLES[section]}", ""]
            lines += [f"- **[{v['angle']}]** {v['text']}  \n  _{v['why']}_" for v in variants]
            lines.append("")
    lines += ["## Оригінал", "", "```", script.strip(), "```", ""]
    return "\n".join(lines)


# ---------- Main: script in, brief out ----------
st.title("🧦 Варіації для модифікацій переможця")
st.caption("Вставте скрипт переможця і отримайте 10 хуків, 5 перших фраз і 5 текстів на екрані з різних кутів.")
if is_demo:
    st.info(
        "Демо-режим: показано збережену відповідь Claude для скрипта з examples/demo_script.md, хоч який скрипт вибрано. "
        "Оцінки потрапляють у пам'ять правил, але не в лог пілоту.",
        icon="ℹ️",
    )

example_files = sorted(EXAMPLES_DIR.glob("winner_*.md"))
choice = st.selectbox("Переможець", [OWN_SCRIPT] + [f.name for f in example_files])
default_script = "" if choice == OWN_SCRIPT else (EXAMPLES_DIR / choice).read_text(encoding="utf-8")
script = st.text_area("Скрипт переможця", value=default_script, height=280)

# The button is always enabled: a disabled one needs a second click after pasting (Streamlit reads text on blur).
if st.button("Згенерувати бриф", type="primary"):
    if not script.strip():
        st.warning("Вставте скрипт переможця або виберіть його зі списку.")
    elif not is_demo and not designer:
        st.warning("Напишіть у сайдбарі, хто ви: так ми рахуємо, скільки дизайнерів користуються інструментом.")
    else:
        with st.spinner("Пишу варіації… (локальна модель може думати до хвилини)"):
            try:
                new_brief = generate(script, load_rules())
            except Exception as error:  # show the error but keep the previous brief and the sidebar
                st.error(f"Не вийшло згенерувати: {error}")
            else:
                st.session_state.brief = new_brief
                st.session_state.rated = {}
                st.session_state.liked = []
                st.session_state.generation += 1
                if not is_demo:
                    usage.log_generate(designer, new_brief, SECTIONS)

brief = st.session_state.brief
if brief:
    show_removed(brief["removed"])
    st.download_button(
        f"⬇️ Завантажити бриф (.md), лайкнуто: {len(st.session_state.liked)}",
        brief_markdown(st.session_state.liked, brief["script"]),
        file_name=f"socklock_brief_{date.today()}.md",
        disabled=not st.session_state.liked,
    )
    for section in SECTIONS:
        st.subheader(SECTION_TITLES[section])
        columns = st.columns(2)
        for index, variant in enumerate(brief[section]):
            with columns[index % 2]:
                show_card(section, index, variant)


# ---------- Sidebar: model, pilot metrics, shared rule memory ----------
# Drawn last, so the metrics and rules already include this run's generate / 👍 / 👎.
with st.sidebar:
    st.badge(f"Модель: {PROVIDER_LABELS.get(provider, provider)}", icon="🤖", color="blue")

    likes, shown = usage.acceptance()
    st.metric(
        "Взято варіантів",
        f"{likes / shown:.0%}" if shown else "—",
        help=f"{likes} 👍 з {shown} показаних. Цифра зупинки пілоту: менше 20%.",
    )
    st.metric(
        "Активних дизайнерів за 7 днів",
        f"{usage.active_designers()} з {TEAM_SIZE}",
        help="Ціль rollout: щонайменше 4 з 6 щотижня.",
    )

    st.subheader("Пам'ять правил команди")
    rules = load_rules()
    st.caption(f"{estimate_tokens(rules)} / {MAX_TOKENS} токенів. Найстаріші правила випадають самі.")
    if not rules:
        st.caption("Поки порожньо. Оцініть варіант 👍 або 👎, і тут з'явиться правило для всієї команди.")
    for i, rule in enumerate(rules):
        text_col, button_col = st.columns([6, 1])
        text_col.markdown(f"{i + 1}. {rule}")
        if button_col.button("✕", key=f"delete-{i}", help="Видалити правило"):
            delete_rule(rule)
            st.rerun()
