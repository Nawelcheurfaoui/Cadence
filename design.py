import streamlit as st

def apply_design():
    st.markdown(
        """
        <style>
        :root {
            --sage: #788b70;
            --sage-dark: #65755d;
            --sage-light: #e6eadf;
            --cream: #f7f3ed;
            --brown: #3f3028;
            --muted: #806e62;
            --border: #cdbdad;
        }

        .stApp {
            background: var(--cream);
            color: var(--brown);
            --primary-color: var(--sage-dark);
        }

        .main .block-container {
            max-width: 900px;
            padding-top: 2.5rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3 {
            color: var(--brown);
            letter-spacing: -0.02em;
        }

        p, label, .stMarkdown {
            color: #5c4b41;
        }

        .cadence-title {
            font-size: 3rem;
            font-weight: 700;
            letter-spacing: -0.05em;
            margin-bottom: 0;
            color: var(--brown);
        }

        .cadence-tagline {
            font-size: 1.05rem;
            color: var(--muted);
            margin-top: -0.2rem;
            margin-bottom: 0.3rem;
        }

        .cadence-subtitle {
            font-size: 0.95rem;
            color: var(--muted);
            margin-bottom: 2rem;
        }

        .section-number, .schedule-number {
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            color: #9a806f;
            text-transform: uppercase;
        }

        .section-title {
            font-size: 1.45rem;
            font-weight: 650;
            color: var(--brown);
            margin-top: 0.15rem;
        }

        .small-muted {
            color: #8a786c;
            font-size: 0.88rem;
        }

        .reality-box, .research-box, .plan-box, .schedule-box,
        .confirmation-box {
            background: #eee7de;
            padding: 1.15rem;
            border-radius: 0.35rem;
            line-height: 1.6;
            margin-top: 1rem;
        }

        .reality-box, .confirmation-box {
            border-left: 4px solid var(--sage);
            color: #514139;
        }

        .confirmed-box {
            background: var(--sage-light);
            border-left: 4px solid var(--sage-dark);
            padding: 1.25rem;
            border-radius: 0.25rem;
            line-height: 1.6;
            color: #4c5a46;
            margin-top: 1rem;
        }

        .research-label, .confirmation-title, .confirmed-title {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            color: var(--sage-dark);
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        .schedule-box {
            margin-bottom: 0.7rem;
        }

        .schedule-date {
            font-weight: 700;
            color: var(--brown);
        }

        .schedule-duration {
            color: var(--muted);
            font-size: 0.9rem;
        }

        .status-behind, .status-on-track, .status-within-range,
        .status-complete {
            font-weight: 700;
            letter-spacing: 0.06em;
        }

        .status-behind { color: #8b5e4b; }
        .status-on-track, .status-complete { color: var(--sage-dark); }
        .status-within-range { color: #8a725f; }

        .path-line {
            height: 3px;
            background: #cdbdad;
            position: relative;
            margin: 1.5rem 25px 0.5rem;
        }

        .path-dot {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: var(--sage);
            position: absolute;
            top: -5px;
            left: 0;
        }

        .path-goal {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            border: 3px solid var(--sage-dark);
            background: var(--cream);
            position: absolute;
            top: -7px;
            right: 0;
        }

        .path-labels {
            display: flex;
            justify-content: space-between;
            margin: 0 18px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            color: #927d6e;
        }

        .footer-note {
            text-align: center;
            color: #9a897d;
            font-size: 0.82rem;
            margin-top: 3rem;
        }

        div[data-testid="stMetric"] {
            background: #eee7de;
            border-radius: 0.4rem;
            padding: 1rem;
        }

        div[data-testid="stMetricLabel"] { color: var(--muted); }
        div[data-testid="stMetricValue"] { color: var(--brown); }

        /* Main buttons: no red hover */
        .stButton > button,
        .stFormSubmitButton > button {
            border-radius: 0.4rem;
            border: 1px solid var(--sage);
            background: var(--sage);
            color: #ffffff;
            transition: background 0.15s ease, border-color 0.15s ease;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            background: var(--sage-dark) !important;
            border-color: var(--sage-dark) !important;
            color: #ffffff !important;
        }

        .stButton > button:focus,
        .stFormSubmitButton > button:focus {
            border-color: var(--sage-dark) !important;
            box-shadow: 0 0 0 0.15rem #788b7040 !important;
            color: #ffffff !important;
        }

        /* Inputs and dropdowns */
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div {
            background: #fbf9f6;
            border-color: var(--border);
        }

        /* Study-day multiselect chips */
        span[data-baseweb="tag"] {
            background: var(--sage-light) !important;
            border-color: var(--sage) !important;
            color: var(--brown) !important;
        }

        span[data-baseweb="tag"] * {
            color: var(--brown) !important;
        }

        /* Sliders and progress indicators */
        div[data-testid="stSlider"] [role="slider"] {
            background: var(--sage-dark) !important;
            border-color: var(--sage-dark) !important;
        }

        div[data-testid="stSlider"] [data-baseweb="slider"] > div > div {
            background: var(--sage) !important;
        }

        div[data-testid="stProgress"] > div > div {
            background: var(--sage) !important;
        }

        /* Focused controls */
        div[data-baseweb="input"] > div:focus-within,
        div[data-baseweb="select"] > div:focus-within {
            border-color: var(--sage-dark) !important;
            box-shadow: 0 0 0 1px var(--sage-dark) !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
