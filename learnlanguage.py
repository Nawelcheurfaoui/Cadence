
import os
import re
import json
from pathlib import Path
from datetime import date, timedelta

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

from design import apply_design
from languages import LANGUAGE_CONFIG, CEFR_LEVELS


# ============================================================
# SETUP
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PLAN_FILE = BASE_DIR / "confirmed_plan.json"


def save_confirmed_plan(plan):
    with open(PLAN_FILE, "w", encoding="utf-8") as file:
        json.dump(
            plan,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )


st.set_page_config(
    page_title="Cadence",
    page_icon="◌",
    layout="centered",
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
# OFFICIAL WORKLOAD RESEARCH
# ============================================================

def research_workload(
    language,
    current_level,
    target_level,
):
    """
    Researches workload evidence for the requested
    language-level transition.

    Cadence calculates the trajectory.
    Groq researches and interprets external evidence.
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

    if not groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY was not found in the .env file."
        )

    if not tavily_api_key:
        raise RuntimeError(
            "TAVILY_API_KEY was not found in the .env file."
        )

    groq_client = Groq(api_key=groq_api_key)
    tavily_client = TavilyClient(api_key=tavily_api_key)

    language_config = LANGUAGE_CONFIG.get(language, {})

    research_hint = language_config.get(
        "research_hint",
        "Find an appropriate official language education source.",
    )

    query = f"""
You are the research component of an application called Cadence.

Cadence helps a person understand whether their current
learning pace is compatible with a deadline.

The user wants to progress in:

Language: {language}
Current level: {current_level}
Target level: {target_level}

Research guidance:
{research_hint}

Your task is ONLY to find reliable workload evidence
for progressing from the current level to the target level.

IMPORTANT:

1. Search the web for a REAL official or authoritative source.
2. Prefer the official institution responsible for the language,
   an official educational institution, government source,
   or official examination organization.
3. Do NOT invent workload figures.
4. If the source gives cumulative hours for levels,
   calculate the transition mathematically.
5. If you calculate the transition yourself, use:
   EVIDENCE_TYPE = DERIVED.
6. If the source directly gives the workload for the transition,
   use:
   EVIDENCE_TYPE = DIRECT.
7. If the source gives a range, preserve the range.
8. If the source gives only one reliable figure,
   use that figure for LOW_HOURS, HIGH_HOURS and ESTIMATE_HOURS.
9. If the source uses 45-minute teaching units,
   convert them using:
   1 teaching unit = 0.75 hours.
10. Do not present a calculated transition as if the
    official organization published that exact number.
11. Keep the explanation short.
12. Return ONLY valid JSON.

Return exactly this structure:

{{
    "evidence_type": "DIRECT" or "DERIVED",
    "source": "official source name",
    "source_url": "exact official source URL",
    "low_hours": number,
    "high_hours": number or null,
    "estimate_hours": number,
    "reason": "short explanation",
    "evidence": "short statement of the evidence"
}}
"""

    try:
        search_response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
        )

        search_results = search_response.get("results", [])

        if not search_results:
            raise RuntimeError(
                "Tavily found no relevant web sources."
            )

        sources_text = json.dumps(
            search_results,
            ensure_ascii=False,
            indent=2,
        )

        groq_response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Cadence's research component. "
                        "Use only the supplied search results. "
                        "Do not invent sources or workload figures. "
                        "If the evidence is insufficient, say so. "
                        "Return only valid JSON matching the requested schema."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        query
                        + "\n\nWeb search results:\n"
                        + sources_text
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )

    except Exception as error:
        raise RuntimeError(
            "Groq and Tavily could not complete the workload research. "
            f"{error}"
        )

    raw_text = groq_response.choices[0].message.content or ""

    if not raw_text.strip():
        raise RuntimeError(
            "Groq returned an empty research result."
        )

    # --------------------------------------------------------
    # PARSE JSON
    # --------------------------------------------------------

    text = raw_text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    try:
        research = json.loads(text)

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Groq returned invalid JSON.\n\n"
            f"{raw_text}\n\n"
            f"JSON error: {error}"
        )

    # --------------------------------------------------------
    # VALIDATE REQUIRED FIELDS
    # --------------------------------------------------------

    required_fields = [
        "evidence_type",
        "source",
        "source_url",
        "low_hours",
        "high_hours",
        "estimate_hours",
        "reason",
        "evidence",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in research
    ]

    if missing_fields:
        raise RuntimeError(
            "Groq research is missing required fields: "
            + ", ".join(missing_fields)
        )

    # --------------------------------------------------------
    # NORMALIZE VALUES
    # --------------------------------------------------------

    evidence_type = str(
        research["evidence_type"]
    ).strip().upper()

    if evidence_type not in {"DIRECT", "DERIVED"}:
        raise RuntimeError(
            "Groq returned an invalid evidence type."
        )

    source = str(research["source"]).strip()
    source_url = str(research["source_url"]).strip()
    reason = str(research["reason"]).strip()
    evidence = str(research["evidence"]).strip()

    try:
        low_hours = float(research["low_hours"])
        estimate_hours = float(research["estimate_hours"])

    except (TypeError, ValueError):
        raise RuntimeError(
            "Groq returned invalid workload numbers."
        )

    high_value = research["high_hours"]

    if high_value is None:
        high_hours = None
    else:
        try:
            high_hours = float(high_value)

        except (TypeError, ValueError):
            raise RuntimeError(
                "Groq returned an invalid HIGH_HOURS value."
            )

    # --------------------------------------------------------
    # VALIDATE WORKLOAD
    # --------------------------------------------------------

    if low_hours < 0:
        raise RuntimeError(
            "LOW_HOURS cannot be negative."
        )

    if estimate_hours < 0:
        raise RuntimeError(
            "ESTIMATE_HOURS cannot be negative."
        )

    if high_hours is not None:
        if high_hours < low_hours:
            raise RuntimeError(
                "HIGH_HOURS cannot be below LOW_HOURS."
            )

        if not low_hours <= estimate_hours <= high_hours:
            raise RuntimeError(
                "ESTIMATE_HOURS must be within "
                "the researched workload range."
            )

    elif estimate_hours < low_hours:
        raise RuntimeError(
            "ESTIMATE_HOURS cannot be below LOW_HOURS."
        )

    # --------------------------------------------------------
    # RETURN CLEAN RESEARCH RESULT
    # --------------------------------------------------------

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
        st.error(
            "Your start date must be before your deadline."
        )
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

    st.write(
        f"**{language}** · {current_level} → {target_level}"
    )

    st.write(
        f"Start: **{start_date.strftime('%d %B %Y')}**"
    )

    st.write(
        f"Deadline: **{deadline.strftime('%d %B %Y')}**"
    )

    st.write(
        f"Session duration: **{hours_per_session}**"
    )

    st.write(
        f"Sessions per week: **{sessions_per_week}**"
    )

    if selected_days:
        st.write(
            "Study days: **"
            + ", ".join(selected_days)
            + "**"
        )

    st.write(
        f"Weekly capacity: **{weekly_hours:g} hours/week**"
    )

    create_plan = st.button(
        "Create my plan",
        type="primary",
        use_container_width=True,
    )

    if create_plan:

        goal = (
            f"{language} {current_level} → {target_level}"
        )

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

        with st.spinner(
            "Cadence is researching the official workload..."
        ):
            try:
                research = research_workload(
                    language,
                    current_level,
                    target_level,
                )

                st.session_state.research = research
                st.session_state.plan_created = True

            except Exception as error:
                st.error(
                    "Cadence could not complete the live workload research."
                )

                st.warning(
                    "Live research is temporarily unavailable. "
                    "Please try again later."
                )

                st.caption(f"Technical detail: {error}")


# ============================================================
# COMPACT, VISUAL RESULTS
# ============================================================

if (
    st.session_state.plan_created
    and st.session_state.research
    and st.session_state.plan_inputs
):

    inputs = st.session_state.plan_inputs
    research = st.session_state.research

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

    # --------------------------------------------------------
    # RESEARCHED WORKLOAD
    # --------------------------------------------------------

    workload = max(
        float(research["estimate_hours"]),
        0.1,
    )

    low_workload = max(
        float(research["low_hours"]),
        0.0,
    )

    high_value = research["high_hours"]

    if high_value is None:
        high_workload = None
    else:
        high_workload = max(
            float(high_value),
            low_workload,
        )

    # --------------------------------------------------------
    # TIME REMAINING AND REQUIRED PACE
    # --------------------------------------------------------

    today = date.today()

    days_remaining = max(
        (deadline - today).days,
        0,
    )

    weeks_remaining = days_remaining / 7

    if weeks_remaining > 0:
        low_required_pace = low_workload / weeks_remaining
        estimate_required_pace = workload / weeks_remaining

        if high_workload is not None:
            high_required_pace = high_workload / weeks_remaining
        else:
            high_required_pace = None
    else:
        low_required_pace = float("inf")
        estimate_required_pace = float("inf")
        high_required_pace = None

    estimate_gap = max(
        estimate_required_pace - weekly_hours,
        0,
    )

    low_gap = max(
        low_required_pace - weekly_hours,
        0,
    )

    if high_required_pace is not None:
        high_gap = max(
            high_required_pace - weekly_hours,
            0,
        )
    else:
        high_gap = None

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

    if weekly_hours > 0:
        weeks_at_capacity = workload / weekly_hours
    else:
        weeks_at_capacity = float("inf")

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

        full_sessions = int(
            workload // hours_per_session
        )

        remaining_session_hours = (
            workload - full_sessions * hours_per_session
        )

        total_sessions = full_sessions

        if remaining_session_hours > 0:
            total_sessions += 1

        while (
            len(schedule) < total_sessions
            and current_date <= deadline
        ):

            if current_date.weekday() in selected_weekdays:

                session_number = len(schedule) + 1

                if (
                    session_number == total_sessions
                    and remaining_session_hours > 0
                ):
                    duration = remaining_session_hours
                else:
                    duration = hours_per_session

                schedule.append(
                    {
                        "session": session_number,
                        "date": current_date,
                        "duration": duration,
                    }
                )

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

    if weeks_remaining > 0:
        required_hours_per_week = workload / weeks_remaining
    else:
        required_hours_per_week = float("inf")

    st.divider()

    st.caption(
        f"{language.upper()} · {current_level} → {target_level}"
    )

    st.subheader(f"{status_icon} {status_title}")

    st.caption(
        f"Deadline: {deadline.strftime('%d %B %Y')}"
    )

    # --------------------------------------------------------
    # KEY NUMBERS
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Your pace",
            f"{weekly_hours:g} h/wk",
        )

    with col2:
        st.metric(
            "Time available",
            f"{weeks_remaining:.1f} weeks",
        )

    with col3:
        st.metric(
            "Workload estimate",
            f"{workload:g} hours",
        )

    # --------------------------------------------------------
    # VISUAL TIME COMPARISON
    # --------------------------------------------------------

    st.markdown("**Estimated time needed**")

    if weekly_hours > 0:
        st.write(
            f"{weeks_at_capacity:.1f} weeks at your current pace"
        )
    else:
        st.write(
            "Your current pace cannot complete the workload."
        )

    if weeks_at_capacity > 0 and weeks_remaining > 0:

        time_coverage = min(
            weeks_remaining / weeks_at_capacity,
            1.0,
        )

        st.progress(time_coverage)

        if weeks_at_capacity > weeks_remaining:
            st.caption(
                "Your available time is shorter than the "
                "estimated time needed."
            )
        else:
            st.caption(
                "Your available time covers the working estimate."
            )

    elif trajectory == "COMPLETE":
        st.caption(
            "The researched workload is marked complete."
        )
    else:
        st.caption(
            "There is no time remaining before the deadline."
        )

    # --------------------------------------------------------
    # ONE ACTIONABLE RECOMMENDATION
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
            f"study hours per week, instead of "
            f"{weekly_hours:g}."
        )

    st.caption(
        "This is an estimate based on researched workload. "
        "Actual progress varies by learner and study quality."
    )

    # --------------------------------------------------------
    # OPTIONAL RESEARCH DETAILS
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
            st.link_button(
                "View source",
                research["source_url"],
            )

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
    # OPTIONAL STUDY SCHEDULE
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
                f"schedule and date range."
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
