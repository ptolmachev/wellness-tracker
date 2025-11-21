import streamlit as st


def apply_ios_style(
    font_size: int = 24,
    primary_color: str = "#007aff",
    secondary_color: str = "#5ac8fa",
    app_bg: str = "#f2f2f7",
    expander_bg: str = "rgba(0, 122, 255, 0.12)",
    max_width: int = 1100,
):
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-size: {font_size}px !important;
            font-family: -apple-system, system-ui, BlinkMacSystemFont, "SF Pro Text", sans-serif;
        }}
        [data-testid="stAppViewContainer"] {{
            background-color: {app_bg} !important;
        }}
        .main .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: {max_width}px;
        }}
        h1 {{
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }}

        /* All expanders: iOS-style card */
        div[data-testid="stExpander"] {{
            background-color: {expander_bg} !important;
            border-radius: 18px !important;
            border: 1px solid #c7ddff !important;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
            overflow: hidden;
        }}
        div[data-testid="stExpander"] > div {{
            background-color: transparent !important;
        }}

        /* History cards (optional, use by wrapping in <div class="history-card"> ... ) */
        .history-card {{
            background-color: rgba(255, 204, 0, 0.18) !important;
            border-radius: 16px;
            padding: 14px 16px;
            margin-bottom: 12px;
            border: 1px solid #ffcc00 !important;
        }}

        /* Buttons */
        .stButton > button {{
            background: linear-gradient(135deg, {primary_color}, {secondary_color}) !important;
            color: #ffffff !important;
            border-radius: 999px !important;
            border: none !important;
            padding: 0.5rem 1.6rem !important;
            font-size: {font_size}px !important;
            font-weight: 600 !important;
            box-shadow: 0 8px 16px rgba(10, 132, 255, 0.45) !important;
        }}

        /* Inputs / textareas */
        textarea, input[type="text"], input[type="number"] {{
            font-size: {font_size}px !important;
            border-radius: 12px !important;
            border: 1px solid #d1d1d6 !important;
        }}

        /* Checkboxes / radios */
        div.stCheckbox > label {{
            font-size: {font_size}px !important;
        }}
        div.stCheckbox > label > div:first-child {{
            transform: scale(1.35);
        }}
        div[role="radiogroup"] label {{
            font-size: {font_size}px !important;
        }}
        div[role="radiogroup"] > label > div:first-child {{
            transform: scale(1.25);
        }}

        /* Sliders */
        .stSlider > div > div > div > div {{
            background: {primary_color} !important;
        }}
        .stSlider [role="slider"] {{
            box-shadow: 0 0 0 6px rgba(0, 122, 255, 0.2) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
