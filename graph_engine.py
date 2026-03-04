try:
    import networkx as nx
except Exception:
    nx = None


class _SimpleDiGraph:
    def __init__(self):
        self._adj = {}
        self._nodes = set()
        self._edge_count = 0

    def add_edge(self, u, v, weight=1.0):
        self._nodes.add(u)
        self._nodes.add(v)
        self._adj.setdefault(u, []).append((v, weight))
        self._edge_count += 1

    def number_of_nodes(self):
        return len(self._nodes)

    def number_of_edges(self):
        return self._edge_count

    def nodes(self):
        return list(self._nodes)

    def edges(self):
        for u, outs in self._adj.items():
            for v, w in outs:
                yield (u, v, w)


def build_transaction_graph(transactions):
    if nx is not None:
        G = nx.DiGraph()
    else:
        G = _SimpleDiGraph()

    for tx in transactions:
        inputs = tx.get("inputs", [])
        outputs = tx.get("outputs", [])

        for i in inputs:
            if not i or "address" not in i:
                continue
            for o in outputs:
                if not o or "address" not in o:
                    continue
                try:
                    weight = float(o.get("value", 0))
                except Exception:
                    weight = 0.0
                G.add_edge(i["address"], o["address"], weight=weight)

    return G


def degree_centrality(G):
    if nx is not None:
        return nx.degree_centrality(G)

    nodes = G.nodes()
    n = len(nodes)
    if n <= 1:
        return {}

    counts = {node: 0 for node in nodes}
    # outgoing
    for u, outs in getattr(G, "_adj", {}).items():
        counts[u] += len(outs)
        for v, _ in outs:
            counts.setdefault(v, 0)
            counts[v] += 1

    return {node: counts.get(node, 0) / (n - 1) for node in nodes}