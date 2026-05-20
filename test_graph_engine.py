from graph_engine import build_transaction_graph, degree_centrality, betweenness_centrality


def test_graph_analysis():
    transactions = [
        {"inputs": [{"address": "A"}], "outputs": [{"address": "B", "value": 0.5}]},
        {"inputs": [{"address": "B"}], "outputs": [{"address": "C", "value": 1.0}]},
        {"inputs": [{"address": "A"}], "outputs": [{"address": "C", "value": 0.3}]},
        {"inputs": [{"address": "C"}], "outputs": [{"address": "A", "value": 0.8}]}
    ]

    graph = build_transaction_graph(transactions)
    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 4

    degree_centrality_result = degree_centrality(graph)
    assert set(degree_centrality_result.keys()) == {"A", "B", "C"}
    assert all(v >= 0 for v in degree_centrality_result.values())

    betweenness_centrality_result = betweenness_centrality(graph)
    assert set(betweenness_centrality_result.keys()) == {"A", "B", "C"}
    assert all(v >= 0 for v in betweenness_centrality_result.values())