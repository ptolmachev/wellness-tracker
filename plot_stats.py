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
) -> go.Figure:
    """
    Plot a time series for a single metric over a specified period.
    
    Args:
        df: DataFrame with 'date' column (YYYY-MM-DD format) and data columns
        column: Column name to plot
        period: "week", "month", or "year"
        title: Optional custom title
    
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
    
    # Create figure
    fig = go.Figure()
    
    # Add scatter points
    fig.add_trace(
        go.Scatter(
            x=df_filtered["date"],
            y=df_filtered[column],
            mode="lines+markers",
            name=column,
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>" + column + ": %{y:.2f}<extra></extra>",
        )
    )
    
    # Update layout
    fig.update_layout(
        title=title or f"{column} – Last {period.capitalize()}",
        xaxis_title="Date",
        yaxis_title=column,
        template="plotly_white",
        height=400,
        hovermode="x unified",
    )
    
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
