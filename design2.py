

# ============================================================
# DESIGN
# ============================================================

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

        .plan-box {
            background: #eee7de;
            border-left: 4px solid #9a806f;
            padding: 1.2rem 1.3rem;
            border-radius: 0.25rem;
            line-height: 1.7;
        }

        .reality-box {
            background: #eee7de;
            border-left: 4px solid #9a806f;
            padding: 1rem 1.1rem;
            border-radius: 0.25rem;
            line-height: 1.6;
            color: #514139;
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
