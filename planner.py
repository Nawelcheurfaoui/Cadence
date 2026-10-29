import os
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

from design import apply_design
from languages import LANGUAGE_CONFIG

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PLAN_FILE = BASE_DIR / "confirmed_plan.json"


def save_confirmed_plan(plan):
    """Save the confirmed learning plan to a JSON file."""
    with PLAN_FILE.open("w", encoding="utf-8") as file:
        json.dump(plan, file, ensure_ascii=False, indent=2)
        
pg = st.navigation(
    [
        st.Page("learnlanguage.py", title="Cadence", default=True),
        st.Page(
            "learning_tracker.py",
            title="Learning Tracker",
            icon="📘",
        ),
    ]
)

apply_design()

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="cadence-title">CADENCE</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="cadence-tagline">'
    "Keep sight of where you're going."
    "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="cadence-subtitle">'
    "Support the person. Stay honest about the trajectory."
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "plan_created" not in st.session_state:
    st.session_state.plan_created = False

if "plan_confirmed" not in st.session_state:
    st.session_state.plan_confirmed = False

if "research" not in st.session_state:
    st.session_state.research = None

if "plan_inputs" not in st.session_state:
    st.session_state.plan_inputs = None


# ============================================================
# WORKLOAD RESEARCH
# ============================================================

# Shared cumulative benchmark for German. These are the Goethe-Institut's
# published approximate instruction-hour ranges from zero, not hours for
# each individual level. Using one shared table prevents independently
# researched goals from contradicting one another (for example, A0→A2
# being estimated as more work than A0→B1).
GERMAN_CUMULATIVE_HOURS = {
    "A0": (0.0, 0.0),
    "A1": (60.0, 150.0),
    "A2": (150.0, 260.0),
    "B1": (260.0, 490.0),
    "B2": (450.0, 600.0),
    "C1": (600.0, 750.0),
    # Goethe publishes C2 as "750+"; without an upper bound, Cadence
    # cannot honestly calculate a midpoint estimate for this target.
    "C2": (750.0, None),
}
GERMAN_GOETHE_SOURCE = "Goethe-Institut Brussels — How long does it take to learn German?"
GERMAN_GOETHE_URL = "https://www.goethe.de/ins/be/en/spr/kur/ogf.html"


def german_workload_from_shared_benchmarks(current_level, target_level):
    """Calculate a German transition from one consistent cumulative source."""
    levels = list(GERMAN_CUMULATIVE_HOURS)
    if current_level not in levels or target_level not in levels:
        return None

    current_index = levels.index(current_level)
    target_index = levels.index(target_level)
    if target_index <= current_index:
        return None

    current_low, current_high = GERMAN_CUMULATIVE_HOURS[current_level]
    target_low, target_high = GERMAN_CUMULATIVE_HOURS[target_level]

    # The C2 benchmark is open-ended, so don't invent an upper bound or
    # midpoint. Report insufficient evidence for a single working estimate.
    if target_high is None or current_high is None:
        return {
            "evidence_type": "INSUFFICIENT",
            "source": GERMAN_GOETHE_SOURCE,
            "source_url": GERMAN_GOETHE_URL,
            "low_hours": None,
            "high_hours": None,
            "estimate_hours": None,
            "reason": (
                "The Goethe-Institut reports C2 as 750+ cumulative hours, "
                "without an upper bound. Cadence cannot calculate a defensible "
                "working estimate for this transition from that open-ended range."
            ),
            "evidence": (
                "The Goethe-Institut publishes cumulative German instruction-hour "
                "ranges for A1–C1 and an open-ended 750+ figure for C2."
            ),
            "sources_found": [{
                "title": GERMAN_GOETHE_SOURCE,
                "url": GERMAN_GOETHE_URL,
                "content": "Published cumulative German instruction-hour ranges by CEFR level.",
            }],
        }

    # The working estimate is the difference between cumulative midpoints.
    # But interval subtraction is only informative when the ranges support a
    # meaningful positive lower bound. Adjacent Goethe ranges can overlap
    # (for example B1 260–490 and B2 450–600), so their subtraction can yield
    # a negative lower bound. Do not turn that into a fake precise range.
    current_midpoint = (current_low + current_high) / 2
    target_midpoint = (target_low + target_high) / 2
    estimate_hours = target_midpoint - current_midpoint
    raw_low = target_low - current_high
    raw_high = target_high - current_low
    range_reliable = raw_low >= 0

    if range_reliable:
        low_hours = raw_low
        high_hours = max(raw_low, raw_high)
        estimate_hours = min(max(estimate_hours, low_hours), high_hours)
        range_note = (
            f"Derived transition range: {low_hours:g}–{high_hours:g} hours, "
            "calculated by subtracting the cumulative bounds."
        )
        reason = (
            f"Cadence derives {current_level}→{target_level} from the "
            "Goethe-Institut's cumulative-from-zero ranges for both levels. "
            "The working estimate is the difference between their midpoints. "
            "The ranges support a non-negative interval subtraction."
        )
    else:
        low_hours = None
        high_hours = None
        range_note = (
            "The cumulative ranges overlap, so they do not establish a reliable "
            "transition-hour range. Cadence shows the midpoint difference only "
            "as a planning estimate, not as a directly verified requirement."
        )
        reason = (
            f"Cadence derives a {current_level}→{target_level} working estimate "
            "from the difference between the Goethe-Institut cumulative midpoints. "
            "Because the cumulative ranges overlap, a reliable transition range "
            "cannot be inferred from their bounds."
        )

    return {
        "evidence_type": "DERIVED",
        "source": GERMAN_GOETHE_SOURCE,
        "source_url": GERMAN_GOETHE_URL,
        "low_hours": low_hours,
        "high_hours": high_hours,
        "estimate_hours": estimate_hours,
        "range_reliable": range_reliable,
        "reason": reason,
        "evidence": (
            f"Cumulative from zero: {current_level} = {current_low:g}–{current_high:g} hours; "
            f"{target_level} = {target_low:g}–{target_high:g} hours. "
            "These are approximate instruction hours and vary by learner and course. "
            f"{range_note}"
        ),
        "raw_text": "",
        "sources_found": [{
            "title": GERMAN_GOETHE_SOURCE,
            "url": GERMAN_GOETHE_URL,
            "content": "Published cumulative German instruction-hour ranges by CEFR level.",
        }],
    }


def research_workload(language, current_level, target_level):
    """
    Find credible workload evidence for a language-level transition.

    Search and interpretation are handled by Tavily and Groq.
    Cadence calculates the user's trajectory separately.
    """

    # German uses one shared cumulative benchmark set from the Goethe-Institut.
    # Do not let a separate model/search call produce incompatible estimates
    # for A0→A2 and A0→B1. Other languages continue through web research below.
    if language.strip().lower() == "german":
        benchmark_result = german_workload_from_shared_benchmarks(
            current_level, target_level
        )
        if benchmark_result is not None:
            return benchmark_result

    groq_api_key = os.getenv("GROQ_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")

    if not groq_api_key:
        try:
            groq_api_key = st.secrets["GROQ_API_KEY"]
        except (KeyError, FileNotFoundError):
            pass

    if not tavily_api_key:
        try:
            tavily_api_key = st.secrets["TAVILY_API_KEY"]
        except (KeyError, FileNotFoundError):
            pass

    if not groq_api_key or not tavily_api_key:
        raise RuntimeError(
            "A required API key is missing. Check your .env file "
            "or your Streamlit Cloud secrets."
        )

    groq_client = Groq(api_key=groq_api_key)
    tavily_client = TavilyClient(api_key=tavily_api_key)

    language_config = LANGUAGE_CONFIG.get(language, {})
    research_hint = language_config.get("research_hint", "")

    queries = [
        (
            f"{language} CEFR {current_level} to {target_level} "
            "learning hours university language school course duration"
        ),
        (
            f"{language} CEFR levels cumulative study hours "
            "official university language centre examination"
        ),
        (
            f"{language} study hours from {current_level} to {target_level} "
            "CEFR transition workload language school university"
        ),
    ]

    search_results = []
    seen_urls = set()

    # Search separately so one failed query doesn't end the research.
    for query in queries:
        try:
            response = tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                include_answer=False,
            )

            for item in response.get("results", []):
                url = str(item.get("url", "")).strip()

                if url and url not in seen_urls:
                    seen_urls.add(url)
                    search_results.append(item)

        except Exception:
            continue

    if not search_results:
        raise RuntimeError(
            "Web search returned no usable results. "
            "Check Tavily and try again."
        )

    sources = []

    for item in search_results:
        sources.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
        })

    prompt = f"""
Research workload evidence for this learning goal.

Language: {language}
Current level: {current_level}
Target level: {target_level}

Language-specific guidance:
{research_hint}

Use only the supplied search results.

Accept relevant evidence from:
- Official language and examination organisations.
- Government and educational institutions.
- Universities and university language centres.
- Established language schools and recognised course providers.

Possible evidence includes:
1. Hours directly associated with the requested transition.
2. Comparable cumulative hours for the current and target levels.
3. Course workload only when the course's entry and exit levels match
   the requested transition.
4. Other credible educational guidance that contextualises workload.

Evidence rules (strict):
- The requested workload is the effort needed to move specifically
  from {current_level} to {target_level}, not merely the duration of
  a course labelled {target_level}.
- DIRECT is allowed only when a supplied source explicitly gives
  workload for this exact transition, or clearly describes a course
  designed for learners entering at {current_level} and finishing at
  {target_level}.
- If a source gives cumulative hours from absolute beginner for both
  levels, and the figures use the same system, subtract the current
  level's cumulative hours from the target level's cumulative hours.
  Label that result DERIVED.
- If {current_level} is absolute beginner (A0/beginner/no prior
  knowledge), a credible cumulative-from-zero figure for {target_level}
  may be used as a DERIVED transition estimate from zero.
- A target-level course duration by itself is NOT proof of total hours
  needed from the user's current level. Do not silently treat it as such.
- Do not subtract figures from incompatible systems or sources.
- Convert 45-minute teaching units to hours by multiplying by 0.75.
- Do not treat a course's duration as a universal requirement for
  attaining a CEFR level.
- Never invent figures, citations, source names, or URLs.
- A credible university or language-school source may be useful
  even if it is not a government publication.
- Preserve a source's workload range when available. If cumulative
  ranges are subtracted, calculate a conservative transition range:
  low = max(0, target low - current high), high = target high - current low.
  Only do this when both ranges are comparable and high is not below low.
- For one supported figure, use the same figure for low, high,
  and estimated hours.
- If no defensible transition estimate can be established, return
  INSUFFICIENT and set all hour fields to null. An honest unknown is
  better than a misleading number.
- Copy the citation URL exactly from the supplied results.

Return only a valid JSON object with exactly these fields:

{{
  "evidence_type": "DIRECT, DERIVED, or INSUFFICIENT",
  "source": "source name or empty string",
  "source_url": "exact result URL or empty string",
  "low_hours": number or null,
  "high_hours": number or null,
  "estimate_hours": number or null,
  "reason": "brief explanation",
  "evidence": "short summary of what the source actually says"
}}

For INSUFFICIENT, all three hour fields must be null.
For a supported range, estimate_hours must be within the range.
Do not claim that a source publishes a calculated figure.
"""

    try:
        groq_response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful research assistant. "
                        "Use only the supplied search results. "
                        "Never invent citations or workload figures. "
                        "Return valid JSON matching the requested schema. "
                        "Use INSUFFICIENT when evidence is inadequate."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        prompt
                        + "\n\nSearch results:\n"
                        + json.dumps(sources, ensure_ascii=False)
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )

    except Exception as error:
        raise RuntimeError(
            "The research service could not complete the request. "
            f"{error}"
        )

    raw_text = groq_response.choices[0].message.content or ""

    try:
        research = json.loads(raw_text)
    except json.JSONDecodeError:
        raise RuntimeError(
            "The research service returned invalid JSON."
        )

    evidence_type = str(
        research.get("evidence_type", "")
    ).strip().upper()

    if evidence_type not in {"DIRECT", "DERIVED", "INSUFFICIENT"}:
        raise RuntimeError(
            "The research response contained an unsupported evidence type."
        )

    # Insufficient evidence is a valid result, not a crash.
    if evidence_type == "INSUFFICIENT":
        return {
            "evidence_type": "INSUFFICIENT",
            "source": str(research.get("source") or "").strip(),
            "source_url": "",
            "low_hours": None,
            "high_hours": None,
            "estimate_hours": None,
            "reason": str(
                research.get("reason")
                or "The available sources did not support a reliable estimate."
            ).strip(),
            "evidence": str(
                research.get("evidence") or ""
            ).strip(),
            "sources_found": sources,
            "raw_text": raw_text,
        }

    source = str(research.get("source") or "").strip()
    source_url = str(research.get("source_url") or "").strip()
    reason = str(research.get("reason") or "").strip()
    evidence = str(research.get("evidence") or "").strip()

    # Accept citations only when the URL was returned by Tavily.
    valid_urls = {item["url"] for item in sources}

    if source_url not in valid_urls:
        raise RuntimeError(
            "The selected citation was not among the retrieved results."
        )

    try:
        low_hours = float(research["low_hours"])
        estimate_hours = float(research["estimate_hours"])

        high_value = research.get("high_hours")
        high_hours = (
            None if high_value is None else float(high_value)
        )

    except (KeyError, TypeError, ValueError):
        raise RuntimeError(
            "The research response did not contain valid workload figures."
        )

    if low_hours < 0 or estimate_hours < 0:
        raise RuntimeError("Workload hours cannot be negative.")

    if high_hours is not None:
        if high_hours < low_hours:
            raise RuntimeError(
                "The upper workload bound is below the lower bound."
            )

        if not low_hours <= estimate_hours <= high_hours:
            raise RuntimeError(
                "The estimate is outside the researched workload range."
            )

    elif estimate_hours < low_hours:
        raise RuntimeError(
            "The estimate is below the reported lower workload bound."
        )

    return {
        "evidence_type": evidence_type,
        "source": source,
        "source_url": source_url,
        "low_hours": low_hours,
        "high_hours": high_hours,
        "estimate_hours": estimate_hours,
        "reason": reason,
        "evidence": evidence,
        "raw_text": raw_text,
        "sources_found": sources,
    }


# ============================================================
# SET YOUR LANGUAGE GOAL
# ============================================================

st.markdown(
    '<div class="section-number">Set your goal</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Choose the language, where you are now, where you want to go, "
    "and the capacity you can realistically give it."
)


# ============================================================
# LANGUAGE
# ============================================================

language_options = ["Choose a language"] + list(
    LANGUAGE_CONFIG.keys()
)

st.markdown(
    '<div style="font-size: 18px; font-weight: 600;">'
    "Which language are you learning?</div>",
    unsafe_allow_html=True,
)

language = st.selectbox(
    "Language",
    language_options,
    index=0,
    label_visibility="collapsed",
    key="cadence_language",
)


# ============================================================
# INITIALIZE GOAL VARIABLES
# ============================================================

current_level = None
target_level = None

current_goal = None
target_goal = None

deadline = None
start_date = None

hours_per_session = None
sessions_per_week = None

selected_days = []


# ============================================================
# CURRENT LEVEL
# ============================================================

if language != "Choose a language":

    available_levels = LANGUAGE_CONFIG[language]["levels"]

    st.markdown(
        '<div style="font-size: 18px; font-weight: 600;">'
        "Where are you starting?</div>",
        unsafe_allow_html=True,
    )

    current_options = [
        "Choose your current level"
    ] + available_levels

    current_level = st.selectbox(
        "Current level",
        current_options,
        index=0,
        label_visibility="collapsed",
        key="cadence_current_level",
    )

    if current_level and current_level != "Choose your current level":
        current_goal = current_level


# ============================================================
# TARGET LEVEL
# ============================================================

if (
    language != "Choose a language"
    and current_level
    and current_level != "Choose your current level"
):

    level_order = LANGUAGE_CONFIG[language]["levels"]

    try:
        current_index = level_order.index(current_level)

        valid_target_levels = [
            level
            for level in level_order
            if level_order.index(level) > current_index
        ]

    except ValueError:
        valid_target_levels = []

    st.markdown(
        '<div style="font-size: 18px; font-weight: 600;">'
        "Where do you want to reach?</div>",
        unsafe_allow_html=True,
    )

    target_options = [
        "Choose your target level"
    ] + valid_target_levels

    target_level = st.selectbox(
        "Target level",
        target_options,
        index=0,
        label_visibility="collapsed",
        key="cadence_target_level",
    )

    if target_level and target_level != "Choose your target level":
        target_goal = target_level


# ============================================================
# DEADLINE
# ============================================================

if target_goal and target_goal != "Choose your target level":

    st.markdown(
        '<div style="font-size: 18px; font-weight: 600;">'
        "When do you want to reach it?</div>",
        unsafe_allow_html=True,
    )

    deadline = st.date_input(
        "Deadline",
        value=None,
        min_value=date.today(),
        format="DD/MM/YYYY",
        label_visibility="collapsed",
        key="cadence_deadline",
    )


# ============================================================
# START DATE
# ============================================================

if deadline:

    st.markdown(
        '<div style="font-size: 18px; font-weight: 600;">'
        "When do you start studying?</div>",
        unsafe_allow_html=True,
    )

    start_date = st.date_input(
        "Start date",
        value=None,
        min_value=date.today(),
        max_value=deadline,
        format="DD/MM/YYYY",
        label_visibility="collapsed",
        key="cadence_start_date",
    )


# ============================================================
# HOURS PER SESSION
# ============================================================

if start_date:

    st.markdown(
        '<div style="font-size: 18px; font-weight: 600;">'
        "How long is one study session?</div>",
        unsafe_allow_html=True,
    )

    hours_per_session = st.selectbox(
        "Hours per session",
        [
            "Choose session duration",
            "0.5 hour",
            "1 hour",
            "1.5 hours",
            "2 hours",
            "2.5 hours",
            "3 hours",
            "3.5 hours",
            "4 hours",
            "5 hours",
            "6 hours",
        ],
        index=0,
        label_visibility="collapsed",
        key="cadence_hours_per_session",
    )


# ============================================================
# SESSIONS PER WEEK
# ============================================================

if (
    hours_per_session
    and hours_per_session != "Choose session duration"
):

    st.markdown(
        '<div style="font-size: 18px; font-weight: 600;">'
        "How many sessions can you study per week?</div>",
        unsafe_allow_html=True,
    )

    sessions_per_week = st.selectbox(
        "Sessions per week",
        [
            "Choose your current pace",
            "0 session / week",
            "1 session / week",
            "2 sessions / week",
            "3 sessions / week",
            "4 sessions / week",
            "5 sessions / week",
            "6 sessions / week",
            "7 sessions / week",
        ],
        index=0,
        label_visibility="collapsed",
        key="cadence_sessions_per_week",
    )


# ============================================================
# STUDY DAYS
# ============================================================

if (
    sessions_per_week
    and sessions_per_week != "Choose your current pace"
):

    sessions_number_preview = int(
        sessions_per_week.split()[0]
    )

    if sessions_number_preview > 0:

        st.markdown(
            '<div style="font-size: 18px; font-weight: 600;">'
            "Which days do you study?</div>",
            unsafe_allow_html=True,
        )

        weekday_options = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6,
        }

        selected_days = st.multiselect(
            "Study days",
            list(weekday_options.keys()),
            max_selections=sessions_number_preview,
            key="cadence_study_days",
            label_visibility="collapsed",
        )

        if len(selected_days) < sessions_number_preview:
            st.caption(
                f"Choose {sessions_number_preview} "
                f"study days to match your "
                f"{sessions_number_preview} "
                f"sessions per week."
            )

    else:
        st.caption(
            "Your current capacity is zero sessions per week."
        )


# ============================================================
# CREATE PLAN
# ============================================================

ready_for_plan = (
    language
    and language != "Choose a language"
    and current_level
    and current_level != "Choose your current level"
    and target_level
    and target_level != "Choose your target level"
    and deadline
    and start_date
    and hours_per_session
    and hours_per_session != "Choose session duration"
    and sessions_per_week
    and sessions_per_week != "Choose your current pace"
)

valid_schedule_inputs = True

if ready_for_plan:

    hours_number = float(hours_per_session.split()[0])
    sessions_number = int(sessions_per_week.split()[0])

    weekly_hours = hours_number * sessions_number

    if start_date > deadline:
        st.error("Your start date must be before your deadline.")
        valid_schedule_inputs = False

    if sessions_number > 0:
        if len(selected_days) != sessions_number:
            st.warning(
                f"Choose exactly {sessions_number} "
                f"study days before creating the plan."
            )
            valid_schedule_inputs = False


if ready_for_plan and valid_schedule_inputs:

    st.markdown("---")

    st.markdown(
        '<div class="section-title">Ready to plan</div>',
        unsafe_allow_html=True,
    )

    st.write(f"**{language}** · {current_level} → {target_level}")
    st.write(f"Start: **{start_date.strftime('%d %B %Y')}**")
    st.write(f"Deadline: **{deadline.strftime('%d %B %Y')}**")
    st.write(f"Session duration: **{hours_per_session}**")
    st.write(f"Sessions per week: **{sessions_per_week}**")

    if selected_days:
        st.write("Study days: **" + ", ".join(selected_days) + "**")

    st.write(f"Weekly capacity: **{weekly_hours:g} hours/week**")

    create_plan = st.button(
        "Create my plan",
        type="primary",
        use_container_width=True,
    )

    if create_plan:

        goal = f"{language} {current_level} → {target_level}"

        st.session_state.plan_inputs = {
            "goal": goal,
            "language": language,
            "current_level": current_level,
            "target_level": target_level,
            "start_date": start_date,
            "deadline": deadline,
            "hours_per_session": hours_number,
            "sessions_per_week": sessions_number,
            "weekly_hours": weekly_hours,
            "selected_days": selected_days,
        }

        st.session_state.plan_created = False
        st.session_state.plan_confirmed = False
        st.session_state.research = None

        with st.spinner("Cadence is researching workload evidence..."):
            try:
                research = research_workload(
                    language,
                    current_level,
                    target_level,
                )

                st.session_state.research = research
                st.session_state.plan_created = True

            except Exception as error:
                st.error("Cadence couldn't complete the workload research.")
                st.warning(
                    "The research service failed. Please try again later."
                )
                st.caption(f"Technical detail: {error}")


# ============================================================
# RESULTS
# ============================================================

if (
    st.session_state.plan_created
    and st.session_state.research
    and st.session_state.plan_inputs
):

    inputs = st.session_state.plan_inputs
    research = st.session_state.research

    # Handle insufficient evidence before doing any workload maths.
    if research["evidence_type"] == "INSUFFICIENT":

        st.divider()
        st.subheader("Evidence not sufficient yet")
        st.write(research["reason"])

        if research["evidence"]:
            st.caption(research["evidence"])

        st.info(
            "Cadence couldn't verify a defensible workload estimate "
            "from the sources found. It won't invent a number or "
            "label your trajectory without one."
        )

        sources_found = research.get("sources_found", [])

        if sources_found:
            with st.expander("Sources found"):
                for item in sources_found:
                    st.markdown(f"**{item.get('title') or 'Source'}**")
                    st.caption(item.get("content", ""))

                    url = item.get("url", "")
                    if url.startswith(("https://", "http://")):
                        st.markdown(f"[Open source]({url})")

        st.stop()

    goal = inputs["goal"]
    language = inputs["language"]
    current_level = inputs["current_level"]
    target_level = inputs["target_level"]

    start_date = inputs["start_date"]
    deadline = inputs["deadline"]

    hours_per_session = inputs["hours_per_session"]
    sessions_per_week = inputs["sessions_per_week"]
    weekly_hours = inputs["weekly_hours"]
    selected_days = inputs["selected_days"]

    workload = max(float(research["estimate_hours"]), 0.1)
    range_reliable = research.get("range_reliable", True)
    low_value = research.get("low_hours")
    high_value = research.get("high_hours")

    # When cumulative bounds overlap, there is no defensible transition range.
    # Use the working estimate as the feasibility threshold, and do not show
    # a fabricated lower/upper range or imply that the range is verified.
    low_workload = (
        max(float(low_value), 0.0)
        if range_reliable and low_value is not None
        else workload
    )
    high_workload = (
        max(float(high_value), low_workload)
        if range_reliable and high_value is not None
        else None
    )

    # --------------------------------------------------------
    # TIME REMAINING, REAL SCHEDULE CAPACITY, AND REQUIRED PACE
    # --------------------------------------------------------

    today = date.today()
    days_remaining = max((deadline - today).days, 0)
    weeks_remaining = days_remaining / 7

    # Count the actual study slots between the chosen start date and
    # deadline. This avoids calling a plan feasible merely because
    # weekly_hours * weeks looks sufficient when the selected study days
    # do not provide enough sessions in the real calendar.
    weekday_options = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    selected_weekdays = {
        weekday_options[day]
        for day in selected_days
        if day in weekday_options
    }

    available_sessions = 0
    if (
        hours_per_session > 0
        and selected_weekdays
        and start_date <= deadline
    ):
        calendar_day = start_date
        while calendar_day <= deadline:
            if calendar_day.weekday() in selected_weekdays:
                available_sessions += 1
            calendar_day += timedelta(days=1)

    scheduled_capacity_hours = available_sessions * hours_per_session
    estimated_sessions_needed = (
        int(workload // hours_per_session)
        + (1 if workload % hours_per_session > 0.001 else 0)
        if hours_per_session > 0
        else 0
    )
    low_sessions_needed = (
        int(low_workload // hours_per_session)
        + (1 if low_workload % hours_per_session > 0.001 else 0)
        if hours_per_session > 0
        else 0
    )

    # Pace figures use the actual planned start date. A one-day plan can
    # still contain a session, so use one-seventh of a week only for the
    # pace display when at least one real study slot exists.
    plan_days = max((deadline - max(start_date, today)).days, 0)
    plan_weeks_for_pace = plan_days / 7
    if plan_weeks_for_pace == 0 and available_sessions > 0:
        plan_weeks_for_pace = 1 / 7

    if plan_weeks_for_pace > 0:
        low_required_pace = low_workload / plan_weeks_for_pace
        estimate_required_pace = workload / plan_weeks_for_pace
        high_required_pace = (
            None
            if high_workload is None
            else high_workload / plan_weeks_for_pace
        )
    else:
        low_required_pace = float("inf") if low_workload > 0 else 0.0
        estimate_required_pace = float("inf")
        high_required_pace = float("inf") if high_workload is not None else None

    # A verdict is based on both the researched range and the actual
    # number of sessions that fit on the selected days—not just an
    # average-hours-per-week comparison.
    if workload <= 0:
        trajectory = "COMPLETE"
    elif scheduled_capacity_hours + 0.001 >= workload:
        trajectory = "ON TRACK"
    elif low_workload > 0 and scheduled_capacity_hours + 0.001 >= low_workload:
        trajectory = "WITHIN RANGE"
    else:
        trajectory = "BELOW RANGE"

    # --------------------------------------------------------
    # TIME AT CURRENT CAPACITY
    # --------------------------------------------------------

    weeks_at_capacity = (
        workload / weekly_hours
        if weekly_hours > 0
        else float("inf")
    )

    # --------------------------------------------------------
    # ACTUAL SESSION SCHEDULE
    # --------------------------------------------------------

    selected_weekdays = sorted(selected_weekdays)

    schedule = []

    if (
        sessions_per_week > 0
        and selected_weekdays
        and hours_per_session > 0
        and workload > 0
    ):

        current_date = start_date

        full_sessions = int(workload // hours_per_session)
        remaining_session_hours = (
            workload - full_sessions * hours_per_session
        )

        total_sessions = full_sessions
        if remaining_session_hours > 0:
            total_sessions += 1

        while len(schedule) < total_sessions and current_date <= deadline:

            if current_date.weekday() in selected_weekdays:

                session_number = len(schedule) + 1

                if (
                    session_number == total_sessions
                    and remaining_session_hours > 0
                ):
                    duration = remaining_session_hours
                else:
                    duration = hours_per_session

                schedule.append({
                    "session": session_number,
                    "date": current_date,
                    "duration": duration,
                })

            current_date += timedelta(days=1)

    # --------------------------------------------------------
    # MAIN VERDICT
    # --------------------------------------------------------

    if trajectory == "COMPLETE":
        status_title = "Workload completed"
        status_icon = "✓"
    elif trajectory == "ON TRACK":
        status_title = "On track"
        status_icon = "✓"
    elif trajectory == "WITHIN RANGE":
        status_title = "At risk"
        status_icon = "!"
    else:
        status_title = "Behind schedule"
        status_icon = "!"

    required_hours_per_week = estimate_required_pace

    st.divider()
    st.caption(f"{language.upper()} · {current_level} → {target_level}")
    st.subheader(f"{status_icon} {status_title}")
    st.caption(f"Deadline: {deadline.strftime('%d %B %Y')}")

    # --------------------------------------------------------
    # KEY NUMBERS
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Your pace", f"{weekly_hours:g} h/wk")

    with col2:
        st.metric("Time available", f"{weeks_remaining:.1f} weeks")

    with col3:
        st.metric("Workload estimate", f"{workload:g} hours")

    # --------------------------------------------------------
    # VISUAL TIME COMPARISON
    # --------------------------------------------------------

    st.markdown("**Estimated time needed**")

    if weekly_hours > 0:
        st.write(f"{weeks_at_capacity:.1f} weeks at your current weekly-hour capacity")
    else:
        st.write("Your current pace cannot complete the workload.")

    st.caption(
        f"Your selected days provide {available_sessions} study slots "
        f"({scheduled_capacity_hours:g} scheduled hours) before the deadline. "
        f"The working estimate needs about {estimated_sessions_needed} sessions."
    )

    if scheduled_capacity_hours + 0.001 >= workload:
        st.progress(1.0)
        st.caption("Your selected calendar has enough session capacity for the working estimate.")
    elif scheduled_capacity_hours + 0.001 >= low_workload:
        coverage = min(scheduled_capacity_hours / workload, 1.0) if workload > 0 else 1.0
        st.progress(coverage)
        st.caption(
            "Your calendar covers the low end of the researched range, "
            "but not the working estimate. Cadence labels this At risk."
        )
    else:
        coverage = min(scheduled_capacity_hours / workload, 1.0) if workload > 0 else 0.0
        st.progress(coverage)
        st.caption(
            "Your selected days do not provide enough session capacity "
            "for the researched workload before the deadline."
        )

    # --------------------------------------------------------
    # NEXT MOVE
    # --------------------------------------------------------

    st.markdown("### Your next move")

    if trajectory == "COMPLETE":
        st.write(
            "Review your progress and confirm whether you have "
            "reached your target level."
        )

    elif weeks_remaining <= 0 and trajectory != "ON TRACK":
        st.write(
            "Your deadline has arrived. Set a new deadline "
            "to calculate a new trajectory."
        )

    elif trajectory == "ON TRACK":
        st.write(
            "Keep your selected study days and current session duration. "
            "Review your progress regularly; the calendar has enough "
            "scheduled capacity for the working estimate."
        )

    elif trajectory == "WITHIN RANGE":
        st.write(
            f"Your calendar fits the low end of the research range, "
            f"but not the {workload:g}-hour working estimate. Add study "
            "sessions, lengthen sessions, or move the deadline if realistic."
        )

    else:
        if available_sessions == 0:
            st.write(
                "No study sessions fit your selected days and date range. "
                "Choose at least one study day, or change the start date "
                "or deadline before treating this as a workable plan."
            )
        elif weekly_hours >= required_hours_per_week:
            st.write(
                "Your average weekly hours look sufficient, but the actual "
                "study days do not provide enough sessions before the deadline. "
                "Add a study day, lengthen sessions, or move the deadline."
            )
        else:
            st.write(
                f"To meet the {workload:g}-hour working estimate, "
                f"aim for about {required_hours_per_week:.1f} "
                f"study hours per week, instead of {weekly_hours:g}, "
                "and check that the selected days fit enough sessions."
            )

    st.caption(
        "This is an estimate based on researched workload. "
        "Actual progress varies by learner and study quality."
    )

    # --------------------------------------------------------
    # RESEARCH DETAILS
    # --------------------------------------------------------

    with st.expander("Research evidence and source"):

        if research["evidence_type"] == "DIRECT":
            st.caption("Direct workload evidence")
        else:
            st.caption("Derived from cumulative level evidence")

        st.write(research["reason"])
        st.write("**Evidence:**", research["evidence"])
        st.write("**Source:**", research["source"])

        if research["source_url"].startswith(("https://", "http://")):
            st.link_button("View source", research["source_url"])

        if range_reliable and high_workload is not None:
            st.caption(
                f"Derived transition range: {low_workload:g}–"
                f"{high_workload:g} hours; working estimate: {workload:g} hours."
            )
        elif research["evidence_type"] == "INSUFFICIENT":
            st.caption("No defensible workload estimate is available for this transition.")
        else:
            st.caption(
                f"Derived working estimate: {workload:g} hours. "
                "No reliable transition range can be inferred from the overlapping "
                "cumulative ranges."
            )

    # --------------------------------------------------------
    # STUDY SCHEDULE
    # --------------------------------------------------------

    with st.expander("View study schedule"):

        if schedule:

            schedule_preview = [
                {
                    "Session": session["session"],
                    "Date": session["date"].strftime("%d %B %Y"),
                    "Hours": round(session["duration"], 2),
                }
                for session in schedule
            ]

            st.dataframe(
                schedule_preview,
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                f"Cadence placed {len(schedule)} of {estimated_sessions_needed} "
                f"required sessions into the selected schedule. "
                f"The calendar contains {available_sessions} possible study slots."
            )

            expected_sessions = int(
                workload // hours_per_session
                + (workload % hours_per_session > 0)
            )

            if len(schedule) < expected_sessions:
                st.warning(
                    "The schedule does not fit the entire working "
                    "estimate before the deadline."
                )

        else:
            st.info(
                "No sessions fit the selected study days and dates. "
                "This plan cannot be feasible unless you add study days "
                "or change the start date/deadline."
            )

      # --------------------------------------------------------
    # CONFIRM PLAN + OPEN TRACKER
    # --------------------------------------------------------

    st.divider()
    st.markdown("### Keep this plan in Cadence")
    st.caption(
        "Confirming saves this researched plan for the Learning Tracker. "
        "Your session history will be tied to this specific plan."
    )

    if st.session_state.plan_confirmed:
        st.success("Plan confirmed and saved.")

        st.button(
    "Open Learning Tracker",
    icon="📘",
    use_container_width=True,
    on_click=lambda: st.switch_page("learning_tracker.py"),
)

    elif st.button(
        "Confirm plan and save",
        type="primary",
        use_container_width=True,
    ):
        plan_to_save = {
            "plan_id": str(uuid4()),
            "goal": goal,
            "language": language,
            "current_level": current_level,
            "target_level": target_level,
            "start_date": start_date.isoformat(),
            "deadline": deadline.isoformat(),
            "hours_per_session": hours_per_session,
            "sessions_per_week": sessions_per_week,
            "weekly_hours": weekly_hours,
            "workload_hours": workload,
            "low_workload_hours": low_workload,
            "high_workload_hours": high_workload,
            "workload_range_reliable": range_reliable,
            "required_pace": (
                required_hours_per_week if required_hours_per_week != float("inf") else 0.0
            ),
            "available_sessions_at_creation": available_sessions,
            "scheduled_capacity_hours_at_creation": scheduled_capacity_hours,
            "estimated_sessions_needed": estimated_sessions_needed,
            "trajectory_at_creation": trajectory,
            "selected_days": selected_days,
            "research_source": research.get("source", "Research"),
            "research_source_url": research.get("source_url", ""),
            "research_reason": research.get("reason", ""),
            "research_evidence": research.get("evidence", ""),
            "evidence_type": research.get("evidence_type", ""),
            "confirmed_at": date.today().isoformat(),
        }

        try:
            save_confirmed_plan(plan_to_save)
            st.session_state.plan_confirmed = True
            st.rerun()

        except OSError as error:
            st.error("Cadence couldn't save this plan.")
            st.caption(f"Technical detail: {error}")
