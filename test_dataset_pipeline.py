import pandas as pd
from dataset_pipeline import build_windows, pv_sample, build_graph_snapshot


def test_pv_sample():
    data = {
        'timestamp': pd.date_range(start='2026-03-10', periods=10, freq='min'),
        'value': [1, 3, 7, 1, 2, 8, 6, 4, 2, 1]
    }
    series = pd.Series(data['value'], index=data['timestamp'])

    result = pv_sample(series, rolling_n=3, z_th=1.0)
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(ts in series.index for ts in result)


def test_build_graph_snapshot():
    data = {
        'from_addr': ['A', 'B', 'A', 'C'],
        'to_addr': ['B', 'C', 'C', 'A'],
        'value_btc': [0.5, 1.0, 0.3, 0.8]
    }
    df_window = pd.DataFrame(data)

    graph = build_graph_snapshot(df_window)
    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 4
    assert graph.has_edge('A', 'B')
    assert graph['A']['B']['value_sum'] == 0.5
    assert graph.nodes['A']['out_value'] > 0


def test_build_windows():
    data = {
        'timestamp': [1610000000, 1610000600, 1610001200, 1610001800, 1610002400],
        'label': [0, 1, 0, 1, 0]
    }
    df = pd.DataFrame(data)

    result = build_windows(df, window_minutes=30, horizon_minutes=5)
    assert not result.empty
    assert set(['window_id', 't_start', 't_end', 'target', 'n_tx']).issubset(result.columns)
    assert result['window_id'].is_monotonic_increasing

