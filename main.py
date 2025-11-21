import os
from datetime import datetime
import pandas as pd
import streamlit as st
import yaml

from style import apply_ios_style


# ================= DATA HANDLER ================= #

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
        now = datetime.now()

        mask = df["date"] == day_str

        if not mask.any():
            row = {"date": day_str, "timestamp": now}
            row.update(updates)
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            idx = df[mask].index[0]
            for k, v in updates.items():
                df.loc[idx, k] = v
            df.loc[idx, "timestamp"] = now

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


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def cast_initial_value(field: dict, stored):
    t = field["type"]
    default = field.get("default")

    v = stored if stored is not None else default

    if t == "number":
        subtype = field.get("subtype", "float")
        return int(v) if subtype == "int" else float(v)

    if t == "checkbox":
        return bool(v)

    if t == "select":
        opts = field.get("options", [])
        if v in opts:
            return v
        return opts[0] if opts else ""

    if t == "slider":
        return int(v)

    if t in ("text", "textarea"):
        return "" if v is None else str(v)

    if t == "time":
        if isinstance(v, str) and v != "now":
            try:
                return datetime.strptime(v, "%H:%M:%S").time()
            except Exception:
                pass
        return datetime.now().time()

    return v


def render_field(field: dict, col, today_data: dict, block_id: str):
    name = field["name"]
    label = field["label"]
    ftype = field["type"]
    key = f"{block_id}__{name}"

    stored = today_data.get(name, None)
    init = cast_initial_value(field, stored)

    if ftype == "number":
        subtype = field.get("subtype", "float")
        kwargs = {}
        if "min" in field:
            kwargs["min_value"] = field["min"]
        if "max" in field:
            kwargs["max_value"] = field["max"]
        if "step" in field:
            kwargs["step"] = field["step"]
        if subtype == "int":
            return col.number_input(label, value=int(init), key=key, **kwargs)
        return col.number_input(label, value=float(init), key=key, **kwargs)

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
        return col.text_area(label, value=str(init), key=key, max_chars=max_chars)

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

        today_str = datetime.now().strftime("%Y-%m-%d")
        today_data = self.handler.get_for_date(today_str)

        tabs = st.tabs(["Entry", "Stats"])
        with tabs[0]:
            self.render_entry_tab(today_str, today_data)
        with tabs[1]:
            self.render_stats_tab()

    def render_entry_tab(self, today_str: str, today_data: dict):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.header(f"New Entry – {today_str}")
            self.render_blocks(today_str, today_data)

        with col2:
            self.render_history()

    def render_blocks(self, today_str: str, today_data: dict):
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
                    values[field["name"]] = render_field(
                        field, col, today_data, block_id
                    )

                if st.button(save_label, key=f"save__{block_id}"):
                    self.handler.upsert_for_date(today_str, values)
                    st.success(f"{title} saved.")

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
            ts_str = ts.strftime("%Y-%m-%d %H:%M")
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
        st.header("Stats (coming soon)")
        st.info("This tab is ready for future plots / summaries from the same CSV.")


# ================= ENTRY POINT ================= #


def main():
    app = WellnessApp(config_path="configs/example_config.yaml")
    app.run()


if __name__ == "__main__":
    main()
