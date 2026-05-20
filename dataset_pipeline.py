import math
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
import networkx as nx


def build_windows(df: pd.DataFrame,
                  window_minutes: int = 30,
                  horizon_minutes: int = 5,
                  step_minutes: Optional[int] = None,
                  time_col: str = 'timestamp',
                  label_col: str = 'label') -> pd.DataFrame:
    """Construct time-ordered observation windows and align labels to a lead horizon.

    Args:
        df: DataFrame with at least `time_col` (unix secs) and `label_col` (0/1)
        window_minutes: length of observation window in minutes
        horizon_minutes: lead-time horizon in minutes
        step_minutes: sliding step in minutes (None -> non-overlapping windows)
        time_col: name of timestamp column (unix seconds)
        label_col: name of label column (0/1)

    Returns:
        DataFrame of windows with columns: window_id, t_start, t_end, target, n_tx
    """
    if time_col not in df.columns:
        raise ValueError(f"time_col '{time_col}' not in dataframe")

    df = df.copy()
    df = df.sort_values(time_col)
    df['ts'] = pd.to_datetime(df[time_col], unit='s')
    df.set_index('ts', inplace=True)

    step = pd.Timedelta(minutes=step_minutes if step_minutes is not None else window_minutes)
    window = pd.Timedelta(minutes=window_minutes)
    horizon = pd.Timedelta(minutes=horizon_minutes)

    t0 = df.index.min()
    t_end = df.index.max()
    windows: List[Dict[str, Any]] = []
    t = t0
    wid = 0
    while t + window <= t_end:
        w = df[t:t + window]
        future = df[t + window:t + window + horizon]
        target = int(bool(future[label_col].any())) if label_col in df.columns else 0
        windows.append({
            'window_id': wid,
            't_start': t,
            't_end': t + window,
            'target': target,
            'n_tx': int(len(w))
        })
        wid += 1
        t = t + step

    return pd.DataFrame(windows)


def pv_sample(agg_series: pd.Series,
              rolling_n: int = 5,
              z_th: float = 2.0,
              k_max: Optional[int] = None) -> List[pd.Timestamp]:
    """Detect peak and valley time indices from an aggregated time series.

    Args:
        agg_series: time-indexed series (e.g., per-minute volume)
        rolling_n: window size for rolling mean/std
        z_th: z-score threshold for peaks/valleys
        k_max: maximum number of events to return

    Returns:
        Sorted list of timestamps where peaks or valleys occur
    """
    s = agg_series.copy()
    roll_mean = s.rolling(rolling_n, min_periods=1).mean()
    roll_std = s.rolling(rolling_n, min_periods=1).std().replace(0, np.nan).fillna(1.0)
    z = (s - roll_mean) / roll_std
    peaks = z[z > z_th].index
    valleys = z[z < -z_th].index
    events = sorted(set(peaks).union(set(valleys)))
    if k_max is not None:
        events = events[:k_max]
    return list(events)


def build_graph_snapshot(df_window: pd.DataFrame,
                         from_col: str = 'from_addr',
                         to_col: str = 'to_addr',
                         value_col: str = 'value_btc') -> nx.DiGraph:
    """Build a directed NetworkX graph for a single window.

    Aggregates edge values and counts; creates simple node attributes.
    """
    G = nx.DiGraph()
    if df_window.empty:
        return G

    # Aggregate edges
    agg = df_window.groupby([from_col, to_col])[value_col].agg(['sum', 'count']).reset_index()
    for _, row in agg.iterrows():
        u = row[from_col]
        v = row[to_col]
        val = float(row['sum'])
        cnt = int(row['count'])
        if not G.has_node(u):
            G.add_node(u)
        if not G.has_node(v):
            G.add_node(v)
        if G.has_edge(u, v):
            G[u][v]['value_sum'] += val
            G[u][v]['tx_count'] += cnt
        else:
            G.add_edge(u, v, value_sum=val, tx_count=cnt)

    # Node-level aggregates
    in_agg = df_window.groupby(to_col)[value_col].sum().to_dict()
    out_agg = df_window.groupby(from_col)[value_col].sum().to_dict()
    for n in G.nodes():
        G.nodes[n]['in_value'] = float(in_agg.get(n, 0.0))
        G.nodes[n]['out_value'] = float(out_agg.get(n, 0.0))

    return G


__all__ = [
    'build_windows',
    'pv_sample',
    'build_graph_snapshot',
]
