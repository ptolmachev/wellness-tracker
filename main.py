import os
import datetime as dt
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import yaml
import plotly.graph_objects as go

from style import apply_ios_style
from plot_stats import plot_time_series, plot_activity_calendar, plot_exercise_calendar, get_activity_score


# ================= DATA HANDLER ================= #

import os
from datetime import datetime, timedelta
import pandas as pd


class WellnessDataHandler:
    def __init__(self, filename: str):
        self.filename = filename

    def load_data(self) -> pd.DataFrame:
        if not os.path.exists(self.filename):
            return pd.DataFrame()
        df = pd.read_csv(self.filename)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def save_data(self, df: pd.DataFrame):
        folder = os.path.dirname(self.filename) or "."
        os.makedirs(folder, exist_ok=True)
        df.to_csv(self.filename, index=False)

    def _ensure_date_column(self, df: pd.DataFrame) -> pd.DataFrame:
        if "date" not in df.columns:
            if "timestamp" in df.columns:
                df["date"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d")
            else:
                df["date"] = pd.NaT
        return df

    def upsert_for_date(self, day_str: str, updates: dict):
        df = self.load_data()
        df = self._ensure_date_column(df)
        entry_date = dt.datetime.strptime(day_str, "%Y-%m-%d")

        mask = df["date"] == day_str

        if not mask.any():
            row = {"date": day_str, "timestamp": entry_date}
            row.update(updates)
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            idx = df[mask].index[0]
            for k, v in updates.items():
                df.loc[idx, k] = v
            df.loc[idx, "timestamp"] = entry_date

        self.save_data(df)


    def get_for_date(self, day_str: str) -> dict:
        df = self.load_data()
        if df.empty:
            return {}
        df = self._ensure_date_column(df)
        row = df[df["date"] == day_str]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()


# ================= HELPERS ================= #


def get_subjective_average(entry) -> float:
    try:
        score = (
            float(entry["motivation"])
            + float(entry["mental_clarity"])
            + float(entry["mood_content"])
            + float(entry["productivity"])
            + (10.0 - float(entry["fatigue"]))
            + (10.0 - float(entry["stress"]))
            + (10.0 - float(entry["overstimulation"]))
        ) / 7.0
        return round(score, 1)
    except Exception:
        return float("nan")


def get_or_default(d: dict, key: str, default):
    v = d.get(key, default)
    try:
        if pd.isna(v):
            return default
    except Exception:
        pass
    return v


def get_entry_day() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")

def shift_day(day_str: str, delta: int) -> str:
    d = dt.datetime.strptime(day_str, "%Y-%m-%d")
    return (d + dt.timedelta(days=delta)).strftime("%Y-%m-%d")


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def cast_initial_value(field: dict, stored):
    t = field["type"]
    default = field.get("default")

    # Prefer stored value; fall back to default from config
    v = stored if stored is not None else default

    if t == "number":
        subtype = field.get("subtype", "float")
        # treat special "empty" values as None
        if v is None or (isinstance(v, str) and v.strip().lower() in {"", "none", "nan"}):
            return None
        try:
            return int(v) if subtype == "int" else float(v)
        except (TypeError, ValueError):
            return None

    if t == "checkbox":
        if v is None:
            return bool(default)
        try:
            if pd.isna(v):
                return bool(default)
        except Exception:
            pass
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "t", "yes", "y"}
        return bool(v)

    if t == "select":
        opts = field.get("options", [])
        if v in opts:
            return v
        return opts[0] if opts else ""

    if t == "slider":
        # slider always needs a numeric value for UI
        if v is None or (isinstance(v, str) and v.strip().lower() in {"", "none", "nan"}):
            # fall back to default, then min, then 0
            v = field.get("default", field.get("min", 0))
        try:
            return int(v)
        except (TypeError, ValueError):
            # final fallback so Streamlit never sees a non-numeric slider value
            return int(field.get("default", field.get("min", 0)))

    if t in ("text", "textarea"):
        return "" if v is None else str(v)

    if t == "time":
        if isinstance(v, str) and v != "now":
            try:
                return dt.datetime.strptime(v, "%H:%M:%S").time()
            except Exception:
                pass
        return datetime.now().time()

    return v


def render_field(field: dict, col, today_data: dict, block_id: str, day_str: str):
    name = field["name"]
    label = field["label"]
    ftype = field["type"]
    key = f"{day_str}__{block_id}__{name}"  # <- include day

    stored = today_data.get(name, None)
    init = cast_initial_value(field, stored)


    if ftype == "number":
        subtype = field.get("subtype", "float")
        allow_none = field.get("allow_none", False)

        if allow_none:
            # Use free-text input so it can be left blank (None)
            raw = col.text_input(
                label,
                value="" if init is None else str(init),
                key=key,
                placeholder=field.get("placeholder", "Leave blank if not measured"),
            ).strip()
            if raw == "":
                return None
            try:
                return int(raw) if subtype == "int" else float(raw)
            except ValueError:
                # Invalid entry → treat as None
                return None

        # Normalize numeric kwargs so Streamlit doesn't complain about mixed types
        kwargs = {}
        if subtype == "int":
            caster = int
        else:
            caster = float

        if "min" in field:
            kwargs["min_value"] = caster(field["min"])
        if "max" in field:
            kwargs["max_value"] = caster(field["max"])
        if "step" in field:
            kwargs["step"] = caster(field["step"])

        if init is None:
            init_val = field.get("min", 0 if subtype == "int" else 0.0)
        else:
            init_val = int(init) if subtype == "int" else float(init)
        init_val = caster(init_val)

        return col.number_input(label, value=init_val, key=key, **kwargs)

    if ftype == "checkbox":
        return col.checkbox(label, value=bool(init), key=key)

    if ftype == "select":
        options = field.get("options", [])
        index = 0
        if init in options:
            index = options.index(init)
        return col.selectbox(label, options, index=index, key=key)

    if ftype == "slider":
        return col.slider(
            label,
            int(field.get("min", 0)),
            int(field.get("max", 10)),
            int(init),
            key=key,
        )

    if ftype == "text":
        return col.text_input(label, value=str(init), key=key)

    if ftype == "textarea":
        max_chars = field.get("max_chars", None)
        return col.text_area(label, value=str(init), key=key, max_chars=max_chars, height=300)

    if ftype == "time":
        return col.time_input(label, value=init, key=key)

    return col.text_input(label, value=str(init), key=key)


# ================= UI CONSTRUCTOR CLASS ================= #


class WellnessApp:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.app_conf = self.config["app"]
        self.blocks_conf = self.config["blocks"]

        data_file = self.app_conf.get("data_file", "./wellness_data.csv")
        self.handler = WellnessDataHandler(data_file)

    def setup_page(self):
        st.set_page_config(
            page_title=self.app_conf.get("title", "Daily Wellness Tracker"),
            page_icon="📈",
            layout="wide",
        )
        apply_ios_style(font_size=self.app_conf.get("font_size", 24))
        st.title(self.app_conf.get("title", "Daily Health & Performance Log"))

    def run(self):
        self.setup_page()

        tabs = st.tabs(["Entry", "Stats"])
        with tabs[0]:
            self.render_entry_tab()
        with tabs[1]:
            self.render_stats_tab()

    def render_entry_tab(self):
        entry_day_str = self.render_day_selector()
        entry_data = self.handler.get_for_date(entry_day_str)
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.header(f"New Entry – {entry_day_str}")
            self.render_blocks(entry_day_str, entry_data)

        with col2:
            self.render_history()

    def render_blocks(self, entry_day_str: str, entry_data: dict):
        for block in self.blocks_conf:
            block_id = block["id"]
            title = block["title"]
            expanded = block.get("expanded", True)
            save_label = block.get("save_label", "Save")
            n_cols = block.get("n_cols", 1)

            with st.expander(title, expanded=expanded):
                cols = st.columns(n_cols)
                values = {}

                for field in block["fields"]:
                    col_idx = field.get("col", 0)
                    col_idx = max(0, min(col_idx, n_cols - 1))
                    col = cols[col_idx]
                    values[field["name"]] = render_field(field, col, entry_data, block_id, entry_day_str)

                if st.button(save_label, key=f"save__{entry_day_str}__{block_id}"):
                    self.handler.upsert_for_date(entry_day_str, values)
                    st.success(f"{title} saved.")

    def render_day_selector(self) -> str:
        if "entry_day" not in st.session_state:
            st.session_state.entry_day = get_entry_day()

        day = st.session_state.entry_day
        today = get_entry_day()

        st.markdown("""
        <style>
        .day-plaque{
            border:1px solid rgba(0,120,255,.35);
            border-radius:16px;
            padding:12px 14px;
            background:linear-gradient(180deg, rgba(0,120,255,.14), rgba(0,120,255,.06));
            box-shadow:0 2px 8px rgba(0,80,200,.12);
            text-align:center;
            line-height:1.15;
        }
        .day-plaque .kicker{font-size:12px; opacity:.75; margin-bottom:6px; color:rgba(0,70,170,.9);}
        .day-plaque .big{font-size:24px; font-weight:800; color:rgba(0,60,150,.98);}
        .day-plaque .sub{font-size:16px; font-weight:700; margin-top:8px; color:rgba(0,80,200,.95);}
        .day-plaque .sub span{font-weight:900;}
        </style>
        """, unsafe_allow_html=True)

        c0, c1, c2 = st.columns([1, 3, 1])

        prev_clicked = c0.button("◀︎", key="day_prev", use_container_width=True)
        next_clicked = c2.button("▶︎", key="day_next", use_container_width=True)

        if prev_clicked:
            day = shift_day(day, -1)
        if next_clicked:
            day = shift_day(day, 1)

        st.session_state.entry_day = day

        c1.markdown(
            f"""
            <div class="day-plaque">
            <div class="kicker">Editing date</div>
            <div class="big">{day}</div>
            <div class="sub">Today: <span>{today}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return day


    def render_history(self):
        st.header("History")
        df = self.handler.load_data()
        if df.empty:
            st.info("No data yet.")
            return

        df = self.handler._ensure_date_column(df)
        df_display = df.sort_values(by="timestamp", ascending=False)

        for _, row in df_display.iterrows():
            ts = row.get("timestamp", None)
            if pd.isna(ts):
                continue
            ts_str = ts.strftime("%Y-%m-%d")
            avg_score = get_subjective_average(row)

            with st.container():
                st.subheader(f"📅 {ts_str}")
                if avg_score == avg_score:
                    st.metric("Overall Vibe", f"{avg_score}/10")
                st.markdown(
                    f"""
                    **Sleep:** {row.get('sleep_hours', '–')}h (Q: {row.get('sleep_quality', '–')})  
                    **Glucose:** {row.get('fasting_glucose', '–')} | **HRV:** {row.get('hrv', '–')}  
                    **Exercise:** gym={row.get('gym', 0)}, run={row.get('run_km', 0)} km  
                    **Steps:** {row.get('walking_steps', '–')}  
                    """
                )

    def render_stats_tab(self):
        st.header("Stats")
        
        # Add custom CSS for better styling
        st.markdown("""
        <style>
        .stSelectbox > label {
            font-weight: 600;
        }
        .stSelectbox [data-baseweb="select"] {
            border: 2px solid #3498db !important;
            border-radius: 6px !important;
            background-color: white !important;
        }
        .stSelectbox [data-baseweb="select"] > div {
            background-color: white !important;
            border: 2px solid #3498db !important;
        }
        .stButton > button {
            height: 2.5rem;
            width: 100%;
        }
        [data-testid="column"] {
            display: flex;
            align-items: flex-start;
        }
        </style>
        """, unsafe_allow_html=True)
        
        df = self.handler.load_data()
        if df.empty:
            st.info("No data available yet.")
            return
        
        # Ensure date column is properly formatted
        df = self.handler._ensure_date_column(df)
        
        # Get stats configuration
        stats_conf = self.config.get("stats", [])
        
        first_plot = True
        for stat in stats_conf:
            stat_id = stat.get("id")
            stat_label = stat.get("label", stat_id)
            column = stat.get("column")
            plot_type = stat.get("plot_type", "time_series")
            description = stat.get("description", stat_label)
            
            # Skip if column doesn't exist in data
            if column not in df.columns:
                continue
            
            # Add divider between plots (except before the first one)
            if not first_plot:
                st.divider()
            first_plot = False
            
            st.subheader(stat_label)
            
            if plot_type == "time_series":
                # Time series plot with period selector (no zoom buttons)
                period = st.selectbox(
                    "",
                    options=["week", "month", "year"],
                    index=1,  # Default to month
                    format_func=lambda x: f"Time Period: {x.capitalize()}",
                    key=f"{stat_id}_period"
                )
                
                fig = plot_time_series(
                    df,
                    column,
                    period=period,
                    title=description
                )
                st.plotly_chart(fig, use_container_width=True, key=f"{stat_id}_plot")
            
            elif plot_type == "calendar":
                # Calendar plot with period selector and navigation buttons
                today = datetime.now().date()
                
                # Initialize calendar state
                state_year_key = f"{stat_id}_calendar_year"
                state_month_key = f"{stat_id}_calendar_month"
                state_week_key = f"{stat_id}_calendar_week_start"
                
                if state_year_key not in st.session_state:
                    st.session_state[state_year_key] = today.year
                if state_month_key not in st.session_state:
                    st.session_state[state_month_key] = today.month
                if state_week_key not in st.session_state:
                    st.session_state[state_week_key] = today - timedelta(days=today.weekday())
                
                # Period selector with radio buttons
                col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.2, 3])
                
                with col1:
                    if st.button("Week", key=f"{stat_id}_week", use_container_width=True):
                        period = "week"
                        st.session_state[f"{stat_id}_selected_period"] = "week"
                
                with col2:
                    if st.button("Month", key=f"{stat_id}_month", use_container_width=True):
                        period = "month"
                        st.session_state[f"{stat_id}_selected_period"] = "month"
                
                with col3:
                    if st.button("Year", key=f"{stat_id}_year", use_container_width=True):
                        period = "year"
                        st.session_state[f"{stat_id}_selected_period"] = "year"
                
                # Get current period from session state (default to month)
                period = st.session_state.get(f"{stat_id}_selected_period", "month")
                
                with col4:
                    nav_cols = st.columns(3, gap="small")
                    
                    with nav_cols[0]:
                        if st.button("← Prev", key=f"{stat_id}_prev", use_container_width=True):
                            if period == "month":
                                if st.session_state[state_month_key] == 1:
                                    st.session_state[state_month_key] = 12
                                    st.session_state[state_year_key] -= 1
                                else:
                                    st.session_state[state_month_key] -= 1
                            elif period == "week":
                                st.session_state[state_week_key] -= timedelta(days=7)
                            elif period == "year":
                                st.session_state[state_year_key] -= 1
                            st.rerun()
                    
                    with nav_cols[1]:
                        if st.button("◆ Cur", key=f"{stat_id}_current", use_container_width=True):
                            st.session_state[state_year_key] = today.year
                            st.session_state[state_month_key] = today.month
                            st.session_state[state_week_key] = today - timedelta(days=today.weekday())
                            st.rerun()
                    
                    with nav_cols[2]:
                        if st.button("Next →", key=f"{stat_id}_next", use_container_width=True):
                            if period == "month":
                                if st.session_state[state_month_key] == 12:
                                    st.session_state[state_month_key] = 1
                                    st.session_state[state_year_key] += 1
                                else:
                                    st.session_state[state_month_key] += 1
                            elif period == "week":
                                st.session_state[state_week_key] += timedelta(days=7)
                            elif period == "year":
                                st.session_state[state_year_key] += 1
                            st.rerun()
                
                # Determine period title
                if period == "month":
                    import calendar as cal
                    month_name = cal.month_name[st.session_state[state_month_key]]
                    period_title = f"{month_name} {st.session_state[state_year_key]}"
                    fig = plot_exercise_calendar(
                        df,
                        column,
                        period="month",
                        year=st.session_state[state_year_key],
                        month=st.session_state[state_month_key],
                        title=description
                    )
                elif period == "week":
                    week_number = st.session_state[state_week_key].isocalendar()[1]
                    week_year = st.session_state[state_week_key].isocalendar()[0]
                    period_title = f"Week {week_number} {week_year}"
                    fig = plot_exercise_calendar(
                        df,
                        column,
                        period="week",
                        week_start_date=st.session_state[state_week_key],
                        title=description
                    )
                else:  # year
                    period_title = f"{st.session_state[state_year_key]}"
                    fig = plot_exercise_calendar(
                        df,
                        column,
                        period="year",
                        year=st.session_state[state_year_key],
                        title=description
                    )
                
                st.markdown(f"##### {period_title}")
                st.plotly_chart(fig, use_container_width=True, key=f"{stat_id}_calendar")


# ================= ENTRY POINT ================= #


def main():
    app = WellnessApp(config_path="configs/myconfig.yaml")
    app.run()


if __name__ == "__main__":
    main()
