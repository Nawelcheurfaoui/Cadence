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

def research_workload(language, current_level, target_level):
    """
    Find credible workload evidence for a language-level transition.

    Search and interpretation are handled by Tavily and Groq.
    Cadence calculates the user's trajectory separately.
    """

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
            f"{language} {target_level} CEFR course hours "
            "language institute study workload"
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
3. Course workload and duration for the target level.
4. Other credible educational guidance that contextualises workload.

Evidence rules:
- Prefer evidence relevant to the requested transition.
- If cumulative figures for both levels are comparable, subtract
  the lower-level figure from the target-level figure.
- Label calculated transitions DERIVED, not DIRECT.
- Do not subtract figures from incompatible systems or sources.
- Convert 45-minute teaching units to hours by multiplying by 0.75.
- Do not treat a course's duration as a universal requirement for
  attaining a CEFR level.
- Never invent figures, citations, source names, or URLs.
- A credible university or language-school source may be useful
  even if it is not a government publication.
- Preserve a source's workload range when available.
- For one supported figure, use the same figure for low, high,
  and estimated hours.
- If no defensible numerical estimate can be established, return
  INSUFFICIENT and set all hour fields to null.
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
    low_workload = max(float(research["low_hours"]), 0.0)

    high_value = research["high_hours"]
    high_workload = (
        None
        if high_value is None
        else max(float(high_value), low_workload)
    )

    # --------------------------------------------------------
    # TIME REMAINING AND REQUIRED PACE
    # --------------------------------------------------------

    today = date.today()
    days_remaining = max((deadline - today).days, 0)
    weeks_remaining = days_remaining / 7

    if weeks_remaining > 0:
        low_required_pace = low_workload / weeks_remaining
        estimate_required_pace = workload / weeks_remaining

        high_required_pace = (
            None
            if high_workload is None
            else high_workload / weeks_remaining
        )
    else:
        low_required_pace = float("inf")
        estimate_required_pace = float("inf")
        high_required_pace = None

    # --------------------------------------------------------
    # TRAJECTORY STATUS
    # --------------------------------------------------------

    if workload <= 0:
        trajectory = "COMPLETE"
    elif weeks_remaining <= 0:
        trajectory = "BELOW RANGE"
    elif weekly_hours >= estimate_required_pace:
        trajectory = "ON TRACK"
    elif weekly_hours >= low_required_pace:
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

    weekday_options = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    selected_weekdays = sorted(
        weekday_options[day]
        for day in selected_days
        if day in weekday_options
    )

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

    required_hours_per_week = (
        workload / weeks_remaining
        if weeks_remaining > 0
        else float("inf")
    )

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
        st.write(f"{weeks_at_capacity:.1f} weeks at your current pace")
    else:
        st.write("Your current pace cannot complete the workload.")

    if weeks_at_capacity > 0 and weeks_remaining > 0:

        time_coverage = min(weeks_remaining / weeks_at_capacity, 1.0)
        st.progress(time_coverage)

        if weeks_at_capacity > weeks_remaining:
            st.caption(
                "Your available time is shorter than the estimated time needed."
            )
        else:
            st.caption(
                "Your available time covers the working estimate."
            )

    elif trajectory == "COMPLETE":
        st.caption("The researched workload is marked complete.")
    else:
        st.caption("There is no time remaining before the deadline.")

    # --------------------------------------------------------
    # NEXT MOVE
    # --------------------------------------------------------

    st.markdown("### Your next move")

    if trajectory == "COMPLETE":
        st.write(
            "Review your progress and confirm whether you have "
            "reached your target level."
        )

    elif weeks_remaining <= 0:
        st.write(
            "Your deadline has arrived. Set a new deadline "
            "to calculate a new trajectory."
        )

    elif weekly_hours >= required_hours_per_week:
        st.write(
            "Keep your current study pace and review your "
            "progress regularly."
        )

    else:
        st.write(
            f"To meet the {workload:g}-hour working estimate, "
            f"aim for about {required_hours_per_week:.1f} "
            f"study hours per week, instead of {weekly_hours:g}."
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

        if high_workload is not None:
            st.caption(
                f"Researched range: {low_workload:g}–"
                f"{high_workload:g} hours."
            )
        else:
            st.caption(
                f"Available workload figure: {low_workload:g} hours."
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
                f"{len(schedule)} sessions fit into the selected "
                "schedule and date range."
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
                "No sessions fit the selected study days and dates."
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
            "required_pace": (
                workload / weeks_remaining if weeks_remaining > 0 else 0.0
            ),
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