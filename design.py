
import streamlit as st


def apply_design():
    st.markdown(
        """
        <style>

        .stApp {
            background: #f7f3ed;
            color: #3f3028;
        }

        .main .block-container {
            max-width: 900px;
            padding-top: 2.5rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3 {
            color: #3f3028;
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
            color: #3f3028;
        }

        .cadence-tagline {
            font-size: 1.05rem;
            color: #806e62;
            margin-top: -0.2rem;
            margin-bottom: 0.3rem;
        }

        .cadence-subtitle {
            font-size: 0.95rem;
            color: #806e62;
            margin-bottom: 2rem;
        }

        .section-number {
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            color: #9a806f;
            text-transform: uppercase;
        }

        .section-title {
            font-size: 1.45rem;
            font-weight: 650;
            color: #3f3028;
            margin-top: 0.15rem;
        }

        .small-muted {
            color: #8a786c;
            font-size: 0.88rem;
        }

        .reality-box {
            background: #eee7de;
            border-left: 4px solid #9a806f;
            padding: 1rem 1.1rem;
            border-radius: 0.25rem;
            line-height: 1.6;
            color: #514139;
        }

        .research-box {
            background: #eee7de;
            padding: 1.25rem;
            border-radius: 0.35rem;
            margin-top: 1rem;
        }

        .research-label {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            color: #9a806f;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }

        .plan-box {
            background: #eee7de;
            padding: 1.25rem;
            border-radius: 0.35rem;
            line-height: 1.6;
        }

        .confirmation-box {
            background: #eee7de;
            border-left: 4px solid #65755d;
            padding: 1.25rem;
            border-radius: 0.25rem;
            line-height: 1.6;
            color: #514139;
            margin-top: 1rem;
            margin-bottom: 1rem;
        }

        .confirmation-title {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            color: #65755d;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        .confirmed-box {
            background: #e6eadf;
            border-left: 4px solid #65755d;
            padding: 1.25rem;
            border-radius: 0.25rem;
            line-height: 1.6;
            color: #4c5a46;
            margin-top: 1rem;
        }

        .confirmed-title {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            color: #65755d;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        .schedule-box {
            background: #eee7de;
            padding: 1rem 1.15rem;
            border-radius: 0.35rem;
            margin-bottom: 0.7rem;
        }

        .schedule-date {
            font-weight: 700;
            color: #3f3028;
        }

        .schedule-duration {
            color: #806e62;
            font-size: 0.9rem;
        }

        .schedule-number {
            color: #9a806f;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.08em;
        }

        .status-behind {
            color: #8b5e4b;
            font-weight: 700;
            letter-spacing: 0.06em;
        }

        .status-on-track {
            color: #65755d;
            font-weight: 700;
            letter-spacing: 0.06em;
        }

        .status-within-range {
            color: #8a725f;
            font-weight: 700;
            letter-spacing: 0.06em;
        }

        .status-complete {
            color: #65755d;
            font-weight: 700;
            letter-spacing: 0.06em;
        }

        .path-line {
            height: 3px;
            background: #cdbdad;
            position: relative;
            margin: 1.5rem 25px 0.5rem 25px;
        }

        .path-dot {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #6f5849;
            position: absolute;
            top: -5px;
            left: 0;
        }

        .path-goal {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            border: 3px solid #6f5849;
            background: #f7f3ed;
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

        div[data-testid="stMetricLabel"] {
            color: #806e62;
        }

        div[data-testid="stMetricValue"] {
            color: #3f3028;
        }

        .stButton > button {
            border-radius: 0.35rem;
            border: 1px solid #bca898;
            background: #f7f3ed;
            color: #4b392f;
        }

        .stButton > button:hover {
            border-color: #806653;
            color: #3f3028;
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div {
            background: #fbf9f6;
            border-color: #cdbdad;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
