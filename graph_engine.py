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


def betweenness_centrality(G):
    """Compute betweenness centrality for nodes in G.

    Uses networkx if available; otherwise falls back to an unweighted
    Brandes algorithm implementation for our simple graph.
    """
    if nx is not None:
        try:
            return nx.betweenness_centrality(G)
        except Exception:
            pass

    # Fallback Brandes algorithm (unweighted, directed)
    nodes = G.nodes()
    centrality = {v: 0.0 for v in nodes}
    adj = getattr(G, "_adj", {})

    for s in nodes:
        # single-source shortest-paths (BFS)
        stack = []
        predecessors = {w: [] for w in nodes}
        sigma = dict.fromkeys(nodes, 0.0)  # number of shortest paths
        dist = dict.fromkeys(nodes, -1)

        sigma[s] = 1.0
        dist[s] = 0
        from collections import deque

        Q = deque()
        Q.append(s)

        while Q:
            v = Q.popleft()
            stack.append(v)
            for w, _ in adj.get(v, []):
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    Q.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    predecessors[w].append(v)

        # accumulation
        delta = dict.fromkeys(nodes, 0.0)
        while stack:
            w = stack.pop()
            for v in predecessors.get(w, []):
                if sigma[w] != 0:
                    delta_v = (sigma[v] / sigma[w]) * (1.0 + delta[w])
                    delta[v] += delta_v
            if w != s:
                centrality[w] += delta[w]

    # normalization for directed graphs similar to networkx default
    n = len(nodes)
    if n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        for v in centrality:
            centrality[v] *= scale

    return centrality


def node_connectivity(G):
    """Estimate node connectivity for G.

    Uses networkx if available; otherwise returns a simple approximation
    (the minimum undirected degree) which is an upper bound on node
    connectivity but is cheap to compute.
    """
    if nx is not None:
        try:
            return nx.node_connectivity(G)
        except Exception:
            pass

    nodes = G.nodes()
    if not nodes:
        return 0

    # build undirected neighbor sets from adjacency
    neighbors = {n: set() for n in nodes}
    adj = getattr(G, "_adj", {})
    for u, outs in adj.items():
        for v, _ in outs:
            neighbors.setdefault(u, set()).add(v)
            neighbors.setdefault(v, set()).add(u)

    # nodes that are isolated or missing in adjacency
    for n in nodes:
        neighbors.setdefault(n, set())

    degrees = [len(neighbors[n]) for n in nodes]
    if not degrees:
        return 0

    # minimum degree is an upper bound on node connectivity
    return min(degrees)