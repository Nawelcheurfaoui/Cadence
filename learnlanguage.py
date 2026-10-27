import streamlit as st

from design import apply_design

st.set_page_config(
    page_title="Cadence",
    page_icon="🎯",
    layout="wide",
)

apply_design()

pg = st.navigation(
    [
        st.Page("planner.py", title="Cadence", default=True),
        st.Page(
            "learning_tracker.py",
            title="Learning Tracker",
            icon="📘",
        ),
    ]
)

pg.run()