"""
Plot statistics for wellness data.

Provides two main plotting functions:
1. plot_time_series() - Line/scatter plots for measured metrics over time
2. plot_activity_calendar() - Calendar heatmap showing activity intensity
"""

from datetime import datetime, timedelta
from typing import List, Literal
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st


def plot_time_series(
    df: pd.DataFrame,
    column: str,
    period: Literal["week", "month", "year"] = "month",
    title: str = None,
    enable_zoom: bool = False,
    zoom_level: float = 1.0,
) -> go.Figure:
    """
    Plot a time series for a single metric over a specified period.
    
    Args:
        df: DataFrame with 'date' column (YYYY-MM-DD format) and data columns
        column: Column name to plot
        period: "week", "month", or "year"
        title: Optional custom title
        enable_zoom: If True, adds zoom in/out buttons for y-axis (deprecated, use zoom_level instead)
        zoom_level: Zoom factor for y-axis (1.0 = default, 0.5 = 2x zoom in, 2.0 = 2x zoom out)
    
    Returns:
        Plotly Figure object
    """
    if df.empty or column not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available")
        return fig
    
    # Ensure date column is datetime
    if "date" not in df.columns:
        return go.Figure().add_annotation(text="Missing 'date' column")
    
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    
    # Filter by period
    today = datetime.now().date()
    if period == "week":
        start_date = today - timedelta(days=7)
    elif period == "month":
        start_date = today - timedelta(days=30)
    elif period == "year":
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)
    
    df_filtered = df[df["date"].dt.date >= start_date].sort_values("date")
    
    if df_filtered.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"No data for the last {period}")
        return fig
    
    # Extract values and handle NaN
    df_filtered = df_filtered.copy()
    df_filtered[column] = pd.to_numeric(df_filtered[column], errors="coerce")
    
    # Create complete date range and interpolate missing values
    date_range = pd.date_range(start=df_filtered["date"].min(), end=df_filtered["date"].max(), freq="D")
    df_complete = pd.DataFrame({"date": date_range})
    df_complete = df_complete.merge(df_filtered[["date", column]], on="date", how="left")
    
    # Interpolate missing values linearly
    df_complete[column] = df_complete[column].interpolate(method="linear")
    
    # Create figure
    fig = go.Figure()
    
    # Add scatter points for actual measured values
    fig.add_trace(
        go.Scatter(
            x=df_filtered["date"],
            y=df_filtered[column],
            mode="markers",
            name="Measured",
            marker=dict(size=8, color="rgba(0, 102, 204, 1)"),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>" + column + ": %{y:.2f}<extra></extra>",
        )
    )
    
    # Add interpolated line
    fig.add_trace(
        go.Scatter(
            x=df_complete["date"],
            y=df_complete[column],
            mode="lines",
            name="Interpolated",
            line=dict(color="rgba(0, 102, 204, 0.6)", width=2),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>" + column + ": %{y:.2f}<extra></extra>",
        )
    )
    
    # Calculate y-axis range based on zoom level
    y_values = df_filtered[column].dropna()
    if len(y_values) > 0:
        y_min = y_values.min()
        y_max = y_values.max()
        y_range = y_max - y_min if y_max > y_min else 1
        y_center = (y_min + y_max) / 2
        
        # Apply zoom level to the range
        # zoom_level = 1.0: default range with padding
        # zoom_level = 0.5: 2x narrower (zoomed in)
        # zoom_level = 2.0: 2x wider (zoomed out)
        padding = y_range * 0.1
        current_range = y_range + 2 * padding
        adjusted_range = current_range * zoom_level
        
        y_range_adjusted = adjusted_range / 2
        y_low = y_center - y_range_adjusted
        y_high = y_center + y_range_adjusted
    
    # Create weekend shading
    shapes = []
    date_range_all = pd.date_range(start=df_complete["date"].min(), end=df_complete["date"].max(), freq="D")
    for date in date_range_all:
        if date.weekday() >= 5:  # Saturday (5) and Sunday (6)
            shapes.append(
                dict(
                    type="rect",
                    xref="x",
                    yref="paper",
                    x0=date,
                    x1=date + pd.Timedelta(days=1),
                    y0=0,
                    y1=1,
                    fillcolor="rgba(200, 200, 200, 0.1)",
                    line=dict(width=0),
                )
            )
    
    # Update layout
    layout_dict = {
        "title": title or f"{column} – Last {period.capitalize()}",
        "xaxis_title": "Date",
        "yaxis_title": column,
        "template": "plotly_white",
        "height": 400,
        "hovermode": "x unified",
        "shapes": shapes,
    }
    
    # Set y-axis range based on zoom level
    if len(y_values) > 0:
        layout_dict["yaxis_range"] = [y_low, y_high]
    
    fig.update_layout(**layout_dict)
    
    return fig


def plot_activity_calendar(
    df: pd.DataFrame,
    column: str,
    period: Literal["week", "month", "year"] = "month",
    title: str = None,
    value_threshold: float = None,
) -> go.Figure:
    """
    Plot a calendar heatmap showing activity intensity.
    
    Args:
        df: DataFrame with 'date' column (YYYY-MM-DD format)
        column: Column name to use for coloring
        period: "week", "month", or "year"
        title: Optional custom title
        value_threshold: Optional threshold for binary coloring (positive/negative activity)
    
    Returns:
        Plotly Figure object
    """
    if df.empty or column not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available")
        return fig
    
    # Ensure date column is datetime
    if "date" not in df.columns:
        return go.Figure().add_annotation(text="Missing 'date' column")
    
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    
    # Filter by period
    today = datetime.now().date()
    if period == "week":
        start_date = today - timedelta(days=7)
    elif period == "month":
        start_date = today - timedelta(days=30)
    elif period == "year":
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)
    
    df_filtered = df[df["date"].dt.date >= start_date].copy()
    
    if df_filtered.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"No data for the last {period}")
        return fig
    
    # Convert to numeric
    df_filtered[column] = pd.to_numeric(df_filtered[column], errors="coerce")
    
    # Create week and day columns for calendar layout
    df_filtered["week"] = df_filtered["date"].dt.isocalendar().week
    df_filtered["day"] = df_filtered["date"].dt.day_name()
    df_filtered["date_str"] = df_filtered["date"].dt.strftime("%Y-%m-%d")
    
    # Determine colors based on values
    if value_threshold is not None:
        # Binary coloring: negative (red) vs positive (green)
        df_filtered["color"] = df_filtered[column].apply(
            lambda x: "Negative" if pd.isna(x) or x < value_threshold else "Positive"
        )
        color_discrete_map = {"Negative": "#FF6B6B", "Positive": "#51CF66", "No Data": "#E0E0E0"}
    else:
        # Continuous coloring based on value
        df_filtered["color"] = df_filtered[column]
        color_discrete_map = None
    
    # Create figure
    fig = px.scatter(
        df_filtered,
        x="date",
        y="day",
        size=abs(df_filtered[column].fillna(0)) + 1,
        color="color" if value_threshold is not None else df_filtered[column],
        hover_data={"date_str": True, column: True},
        title=title or f"{column} Activity – Last {period.capitalize()}",
        color_continuous_scale="RdYlGn" if value_threshold is None else None,
        color_discrete_map=color_discrete_map if value_threshold is not None else None,
    )
    
    fig.update_layout(
        height=400,
        xaxis_title="Date",
        yaxis_title="Day of Week",
        template="plotly_white",
        hovermode="closest",
    )
    
    fig.update_xaxes(type="date")
    
    return fig


def get_activity_score(entry: dict) -> float:
    """
    Calculate a composite activity score for calendar highlighting.
    
    Combines exercise, steps, and other activity metrics into a single score.
    Returns a value where negative indicates low activity, positive indicates high activity.
    """
    try:
        score = 0
        
        # Exercise activities (positive)
        if entry.get("gym"):
            score += 3
        
        run_km = float(entry.get("run_km", 0) or 0)
        score += run_km * 2
        
        steps = float(entry.get("walking_steps", 0) or 0)
        if steps > 5000:
            score += 2
        elif steps > 2000:
            score += 1
        
        morning_exercise = entry.get("morning_exercise")
        if morning_exercise:
            score += 2
        
        # Meditation (positive)
        if entry.get("meditation"):
            score += 1
        
        # Negative factors
        compulsive = entry.get("compulsive_behavior")
        if compulsive:
            score -= 2
        
        cannabis = float(entry.get("cannabis", 0) or 0)
        if cannabis > 0:
            score -= 1
        
        return score
    except Exception:
        return 0.0

def plot_exercise_calendar(
    df: pd.DataFrame,
    column: str,
    period: str = "month",
    year: int = None,
    month: int = None,
    week_start_date: datetime = None,
    title: str = "Exercise Calendar"
) -> go.Figure:
    """
    Create a calendar view for exercise tracking.
    
    Parameters:
    - df: DataFrame with exercise data (must have 'date' column and boolean/numeric column)
    - column: Column name containing exercise data
    - period: "week", "month", or "year"
    - year, month: For month/year views
    - week_start_date: For week view
    - title: Plot title
    
    Returns: Plotly Figure with calendar visualization
    """
    import calendar as cal
    
    # Prepare data
    df_copy = df.copy()
    df_copy["date"] = pd.to_datetime(df_copy["date"], errors="coerce")
    df_copy = df_copy.dropna(subset=["date"])
    
    # Convert column to boolean
    if df_copy[column].dtype == 'object':
        df_copy["exercise"] = df_copy[column].apply(
            lambda x: str(x).lower() in ['true', '1', 'yes'] if pd.notna(x) else False
        )
    else:
        df_copy["exercise"] = pd.to_numeric(df_copy[column], errors="coerce").fillna(False).astype(bool)
    
    # Create dict for quick lookup: date -> bool
    exercise_dict = dict(zip(df_copy["date"].dt.date, df_copy["exercise"]))
    
    if period == "month":
        return _create_month_calendar(exercise_dict, year, month, title)
    elif period == "week":
        return _create_week_calendar(exercise_dict, week_start_date, title)
    elif period == "year":
        return _create_year_calendar(exercise_dict, year, title)


def _create_month_calendar(exercise_dict: dict, year: int, month: int, title: str) -> go.Figure:
    """Create a monthly calendar view."""
    import calendar as cal
    
    today = datetime.now().date()
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    
    # Get calendar for this month
    month_cal = cal.monthcalendar(year, month)
    month_name = cal.month_name[month]
    
    # Create grid data
    x_positions = []
    y_positions = []
    dates = []
    hover_texts = []
    colors = []
    
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    for week_num, week in enumerate(month_cal):
        for day_num, day in enumerate(week):
            if day == 0:
                continue
            
            x_positions.append(day_num)
            y_positions.append(-week_num)
            
            date_obj = datetime(year, month, day).date()
            dates.append(date_obj)
            
            has_exercise = exercise_dict.get(date_obj, False)
            hover_texts.append(f"{date_obj}<br>Exercise: {'Yes' if has_exercise else 'No'}")
            
            # Green for exercise, light gray for no exercise
            if has_exercise:
                colors.append("rgba(76, 175, 80, 0.8)")  # Green
            else:
                colors.append("rgba(200, 200, 200, 0.2)")  # Light gray
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=x_positions,
            y=y_positions,
            mode="markers+text",
            marker=dict(
                size=35,
                color=colors,
                opacity=0.7,
                line=dict(width=1, color="rgba(100, 100, 100, 0.3)")
            ),
            text=[d.strftime("%d") for d in dates],
            textposition="middle center",
            textfont=dict(size=14, color="black"),
            hovertext=hover_texts,
            hoverinfo="text",
            showlegend=False
        )
    )
    
    fig.update_layout(
        xaxis=dict(
            tickvals=list(range(7)),
            ticktext=day_names,
            showgrid=False,
            zeroline=False,
            side="top",
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
        ),
        template="plotly_white",
        height=400,
        showlegend=False,
        hovermode="closest",
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


def _create_week_calendar(exercise_dict: dict, week_start_date: datetime, title: str) -> go.Figure:
    """Create a weekly calendar view."""
    if week_start_date is None:
        today = datetime.now().date()
        # Find Monday of current week
        week_start_date = today - timedelta(days=today.weekday())
    elif isinstance(week_start_date, datetime):
        week_start_date = week_start_date.date()
    
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    x_positions = []
    y_positions = []
    dates = []
    hover_texts = []
    colors = []
    
    for i in range(7):
        date_obj = week_start_date + timedelta(days=i)
        x_positions.append(i)
        y_positions.append(0)
        dates.append(date_obj)
        
        has_exercise = exercise_dict.get(date_obj, False)
        hover_texts.append(f"{date_obj}<br>Exercise: {'Yes' if has_exercise else 'No'}")
        
        if has_exercise:
            colors.append("rgba(76, 175, 80, 0.8)")  # Green
        else:
            colors.append("rgba(200, 200, 200, 0.2)")  # Light gray
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=x_positions,
            y=[0] * 7,
            mode="markers+text",
            marker=dict(
                size=50,
                color=colors,
                opacity=0.7,
                line=dict(width=1, color="rgba(100, 100, 100, 0.3)")
            ),
            text=[d.strftime("%d") for d in dates],
            textposition="middle center",
            textfont=dict(size=16, color="black"),
            hovertext=hover_texts,
            hoverinfo="text",
            showlegend=False
        )
    )
    
    week_end = week_start_date + timedelta(days=6)
    week_number = week_start_date.isocalendar()[1]
    year = week_start_date.isocalendar()[0]
    
    fig.update_layout(
        xaxis=dict(
            tickvals=list(range(7)),
            ticktext=day_names,
            showgrid=False,
            zeroline=False,
            side="top",
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
        ),
        template="plotly_white",
        height=250,
        showlegend=False,
        hovermode="closest",
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


def _create_year_calendar(exercise_dict: dict, year: int, title: str) -> go.Figure:
    """Create a yearly calendar heatmap view."""
    import calendar as cal
    
    if year is None:
        year = datetime.now().year
    
    # Create data for heatmap
    weeks_data = []
    day_of_week_data = []
    dates_list = []
    hover_texts = []
    colors = []
    
    # Iterate through all days of the year
    start_date = datetime(year, 1, 1).date()
    end_date = datetime(year, 12, 31).date()
    
    current = start_date
    week_num = 0
    
    while current <= end_date:
        has_exercise = exercise_dict.get(current, False)
        
        weeks_data.append(current.isocalendar()[1])  # Week number
        day_of_week_data.append(current.weekday())  # Day of week (0=Mon, 6=Sun)
        dates_list.append(current)
        
        hover_texts.append(f"{current}<br>Exercise: {'Yes' if has_exercise else 'No'}")
        
        if has_exercise:
            colors.append(1)  # Exercise
        else:
            colors.append(0)  # No exercise
        
        current += timedelta(days=1)
    
    # Create scatter plot for year view
    fig = go.Figure()
    
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    fig.add_trace(
        go.Scatter(
            x=weeks_data,
            y=day_of_week_data,
            mode="markers",
            marker=dict(
                size=12,
                color=colors,
                colorscale=[[0, "rgba(200, 200, 200, 0.3)"], [1, "rgba(76, 175, 80, 0.8)"]],
                showscale=False,
                line=dict(width=0.5, color="rgba(150, 150, 150, 0.3)")
            ),
            hovertext=hover_texts,
            hoverinfo="text",
            showlegend=False
        )
    )
    
    fig.update_layout(
        xaxis=dict(
            title="Week Number",
            showgrid=False,
            side="top",
            zeroline=False,
            tickvals=[1, 13, 26, 39, 52],
            ticktext=["1", "13", "26", "39", "52"],
        ),
        yaxis=dict(
            tickvals=list(range(7)),
            ticktext=day_names,
            showgrid=False,
            scaleanchor="x",
            scaleratio=1,
            zeroline=False,
            range=[6.5, -0.5],  # Explicitly reverse range to show Monday at top, Sunday at bottom
        ),
        template="plotly_white",
        height=500,
        showlegend=False,
        hovermode="closest",
        margin=dict(l=80, r=50, t=80, b=50)
    )
    
    return fig