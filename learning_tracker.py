import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from design import apply_design

# ============================================================
# SETUP
# ============================================================


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
# FILES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR

PLAN_FILE = PROJECT_DIR / "confirmed_plan.json"
SESSION_FILE = PROJECT_DIR / "session_history.json"


# ============================================================
# HELPERS
# ============================================================

def load_json(path, default):

    if not path.exists():
        return default

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return default


def save_json(path, data):

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def parse_date(value):

    if not value:
        return None

    try:
        return date.fromisoformat(value)

    except Exception:
        return None


def format_date(value):

    if not value:
        return "—"

    return value.strftime("%A, %d %b %Y")


# ============================================================
# LOAD PLAN
# ============================================================

plan = load_json(
    PLAN_FILE,
    None,
)


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
# NO PLAN
# ============================================================

if not isinstance(plan, dict):

    st.markdown(
        '<div class="section-number">Learning Tracker</div>',
        unsafe_allow_html=True,
    )

    st.warning(
        "No confirmed learning plan was found yet."
    )

    st.write(
        "Return to the German planner, create and confirm your plan, "
        "then open the tracker again."
    )

    st.stop()


# ============================================================
# PLAN VALUES
# ============================================================

plan_id = str(plan.get("plan_id") or "legacy-plan")

goal = plan.get(
    "goal",
    "Learn German",
)

current_level = plan.get(
    "current_level",
    "A0",
)

target_level = plan.get(
    "target_level",
    "A2",
)

deadline = parse_date(
    plan.get("deadline")
)

start_date = parse_date(
    plan.get("start_date")
)

if start_date is None:
    start_date = date.today()

hours_per_session = float(
    plan.get(
        "hours_per_session",
        1,
    )
)

sessions_per_week = int(
    plan.get(
        "sessions_per_week",
        0,
    )
)

weekly_hours = float(
    plan.get(
        "weekly_hours",
        hours_per_session * sessions_per_week,
    )
)

workload_hours = float(
    plan.get(
        "workload_hours",
        0,
    )
)

low_workload_hours = float(
    plan.get(
        "low_workload_hours",
        workload_hours,
    )
)

high_workload_hours = plan.get(
    "high_workload_hours"
)

if high_workload_hours is not None:
    high_workload_hours = float(
        high_workload_hours
    )

required_pace = float(
    plan.get(
        "required_pace",
        0,
    )
)

selected_days = plan.get(
    "selected_days",
    [],
)

research_source = plan.get(
    "research_source",
    "Research",
)

research_reason = plan.get(
    "research_reason",
    "",
)


# ============================================================
# SESSION HISTORY
# ============================================================

all_session_history = load_json(SESSION_FILE, [])
if not isinstance(all_session_history, list):
    all_session_history = []

# Progress is isolated by plan ID; changing goals won't reuse old progress.
session_history = [
    item for item in all_session_history
    if isinstance(item, dict) and item.get("plan_id") == plan_id
]

def get_session_status(session_date):
    date_string = session_date.isoformat()
    for item in session_history:
        if item.get("date") == date_string:
            return item.get("status")
    return None

def record_session(session_date, status):
    date_string = session_date.isoformat()
    for item in all_session_history:
        if (
            isinstance(item, dict)
            and item.get("plan_id") == plan_id
            and item.get("date") == date_string
        ):
            item["status"] = status
            item["updated_at"] = datetime.now().isoformat()
            break
    else:
        new_item = {
            "plan_id": plan_id,
            "date": date_string,
            "status": status,
            "updated_at": datetime.now().isoformat(),
        }
        all_session_history.append(new_item)
        session_history.append(new_item)

    save_json(SESSION_FILE, all_session_history)


def calculate_completed_sessions():

    return sum(
        1
        for item in session_history
        if item.get("status") == "completed"
    )


def calculate_missed_sessions():

    return sum(
        1
        for item in session_history
        if item.get("status") == "missed"
    )


def get_real_activity():

    return [
        item
        for item in session_history
        if item.get("date")
    ]


# ============================================================
# WORKLOAD → SESSION COUNT
# ============================================================

if hours_per_session > 0:

    total_sessions = int(
        workload_hours // hours_per_session
    )

    remainder = (
        workload_hours
        - (
            total_sessions
            * hours_per_session
        )
    )

    if remainder > 0.001:
        total_sessions += 1

else:

    total_sessions = 0


# ============================================================
# CURRENT TOTALS
# ============================================================

completed_sessions = calculate_completed_sessions()
missed_sessions = calculate_missed_sessions()

remaining_sessions = max(
    total_sessions - completed_sessions,
    0,
)


# ============================================================
# HEADER — TRACKER
# ============================================================

st.divider()

st.markdown(
    '<div class="section-number">Learning Tracker</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Your confirmed plan</div>',
    unsafe_allow_html=True,
)


# ============================================================
# YOUR PLAN
# ============================================================

st.markdown(
    f"""
    <div class="plan-box">

    <strong>{goal}</strong><br>

    {current_level} → {target_level}<br>

    Start: {format_date(start_date)}<br>

    Deadline: {format_date(deadline)}<br>

    {hours_per_session:g} hour(s) per session ·
    {sessions_per_week} session(s) per week<br>

    Weekly capacity: {weekly_hours:g} hours

    </div>
    """,
    unsafe_allow_html=True,
)


if selected_days:

    st.caption(
        "Study days: "
        + ", ".join(selected_days)
    )


# ============================================================
# RESEARCH
# ============================================================

st.divider()

st.markdown(
    '<div class="section-number">01 · Workload</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">What this goal requires</div>',
    unsafe_allow_html=True,
)

if high_workload_hours is not None:

    st.write(
        f"Research estimate: "
        f"{low_workload_hours:g}–{high_workload_hours:g} hours."
    )

else:

    st.write(
        f"Research estimate: at least "
        f"{low_workload_hours:g} hours."
    )

st.caption(
    f"Working estimate: approximately "
    f"{workload_hours:g} hours · "
    f"{total_sessions} Cadence sessions"
)

st.caption(
    f"Source: {research_source}"
)

if plan.get("evidence_type"):
    st.caption(f"Evidence classification: {plan['evidence_type']}")

if plan.get("research_source_url", "").startswith(("https://", "http://")):
    st.markdown(f"[Open research source]({plan['research_source_url']})")

if research_reason:

    st.caption(
        research_reason
    )


# ============================================================
# CURRENT TOTALS
# ============================================================

st.divider()

st.markdown(
    '<div class="section-number">02 · Progress</div>',
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Completed",
        completed_sessions,
    )

with col2:

    st.metric(
        "Missed",
        missed_sessions,
    )

with col3:

    st.metric(
        "Remaining",
        remaining_sessions,
    )


# ============================================================
# PROGRESS BAR
# ============================================================

if total_sessions > 0:

    progress = min(
        completed_sessions / total_sessions,
        1.0,
    )

    st.progress(
        progress
    )

    st.caption(
        f"{completed_sessions} of "
        f"{total_sessions} sessions completed"
    )


# ============================================================
# TRAJECTORY
# ============================================================

st.divider()

st.markdown(
    '<div class="section-number">03 · Trajectory</div>',
    unsafe_allow_html=True,
)

today = date.today()

if deadline:
    days_remaining = max((deadline - today).days, 0)
    weeks_remaining = days_remaining / 7 if days_remaining > 0 else 0
else:
    days_remaining = 0
    weeks_remaining = 0

completed_hours = min(completed_sessions * hours_per_session, workload_hours)
remaining_workload_hours = max(workload_hours - completed_hours, 0.0)
elapsed_days = max((today - start_date).days, 0)
elapsed_weeks = elapsed_days / 7

# On day one, use the intended schedule as the initial pace. Afterwards,
# judge trajectory using completed study time rather than planned capacity alone.
actual_pace = (
    completed_hours / elapsed_weeks
    if elapsed_weeks > 0
    else weekly_hours
)
required_pace = (
    remaining_workload_hours / weeks_remaining
    if weeks_remaining > 0
    else 0.0
)

if remaining_workload_hours <= 0.001 or remaining_sessions == 0:
    trajectory = "COMPLETE"
elif weeks_remaining <= 0:
    trajectory = "DEADLINE REACHED"
elif actual_pace >= required_pace:
    trajectory = "ON TRACK"
else:
    trajectory = "BELOW REQUIRED PACE"


if trajectory == "COMPLETE":

    st.success(
        "COMPLETE"
    )

elif trajectory == "ON TRACK":

    st.success(
        "ON TRACK"
    )

elif trajectory == "BELOW REQUIRED PACE":

    st.warning(
        "BELOW REQUIRED PACE"
    )

else:

    st.warning(
        "DEADLINE REACHED"
    )


if weeks_remaining > 0:

    st.write(
        f"You have {remaining_sessions} sessions remaining "
        f"over approximately {weeks_remaining:.1f} weeks."
    )

    st.caption(f"Recent measured pace: approximately {actual_pace:.1f} hours/week")
    st.caption(f"Required pace from now: approximately {required_pace:.1f} hours/week")


# ============================================================
# SESSIONS DUE
# ============================================================

st.divider()

st.markdown(
    '<div class="section-number">04 · Sessions</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Confirm your sessions</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Tell Cadence what actually happened. "
    "A session can be completed or missed."
)


# ============================================================
# GENERATE SESSION DATES
# ============================================================

weekday_numbers = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


selected_weekdays = sorted(
    weekday_numbers[day]
    for day in selected_days
    if day in weekday_numbers
)


def generate_sessions():

    sessions = []

    if not selected_weekdays:
        return sessions

    current_date = start_date

    session_number = 0

    while (
        current_date <= today
        and (
            deadline is None
            or current_date <= deadline
        )
        and session_number < total_sessions
    ):

        if current_date.weekday() in selected_weekdays:

            session_number += 1

            sessions.append(
                {
                    "number": session_number,
                    "date": current_date,
                }
            )

        current_date += timedelta(days=1)

    return sessions


past_sessions = generate_sessions()


# ============================================================
# DUE / UNCONFIRMED SESSIONS
# ============================================================

unconfirmed_sessions = [
    item
    for item in past_sessions
    if get_session_status(item["date"]) is None
]


if not unconfirmed_sessions:

    st.info(
        "There are no unconfirmed sessions right now."
    )

else:

    for item in unconfirmed_sessions:

        session_date = item["date"]

        with st.container(
            border=True
        ):

            st.subheader(
                f"Session {item['number']} · "
                f"{session_date.strftime('%A, %d %b')}"
            )

            st.write(
                f"{hours_per_session:g} hour(s)"
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "✓ Complete",
                    key=f"complete_{session_date}",
                    use_container_width=True,
                ):

                    record_session(
                        session_date,
                        "completed",
                    )

                    st.rerun()

            with col2:

                if st.button(
                    "× Miss",
                    key=f"miss_{session_date}",
                    use_container_width=True,
                ):

                    record_session(
                        session_date,
                        "missed",
                    )

                    st.rerun()


# ============================================================
# UPCOMING SESSIONS
# ============================================================

future_sessions = []

if selected_weekdays:

    current_date = max(
        today + timedelta(days=1),
        start_date,
    )

    session_number = len(past_sessions)

    while (
        len(future_sessions) < 7
        and session_number < total_sessions
        and (
            deadline is None
            or current_date <= deadline
        )
    ):

        if current_date.weekday() in selected_weekdays:

            session_number += 1

            future_sessions.append(
                {
                    "number": session_number,
                    "date": current_date,
                }
            )

        current_date += timedelta(days=1)


if future_sessions:

    st.markdown(
        '<div class="small-muted">'
        "Upcoming sessions"
        "</div>",
        unsafe_allow_html=True,
    )

    for item in future_sessions[:3]:

        st.caption(
            f"Session {item['number']} · "
            f"{item['date'].strftime('%A, %d %b')}"
        )


# ============================================================
# RECENT ACTIVITY
# ============================================================

real_activity = get_real_activity()

if real_activity:

    st.divider()

    st.markdown(
        '<div class="section-number">05 · Recent activity</div>',
        unsafe_allow_html=True,
    )

    sorted_activity = sorted(
        real_activity,
        key=lambda item: item["date"],
        reverse=True,
    )

    for item in sorted_activity[:7]:

        activity_date = parse_date(
            item["date"]
        )

        if activity_date is None:
            continue

        if item.get("status") == "completed":

            st.success(
                f"{activity_date.strftime('%d %b %Y')} "
                "· ✓ Session completed"
            )

        elif item.get("status") == "missed":

            st.warning(
                f"{activity_date.strftime('%d %b %Y')} "
                "· × Session missed"
            )


# ============================================================
# FOOTER
# ============================================================

st.html(
    """
    <div class="footer-note">
        Soft toward the person. Strict toward the trajectory.
    </div>
    """
)