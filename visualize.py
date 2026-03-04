"""Graph visualization helpers for transaction graphs.

Provides `draw_transaction_graph` which saves a PNG/SVG of the transaction
graph and highlights the top central nodes.
"""
try:
    import networkx as nx
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except Exception:
    nx = None
    plt = None


def _to_networkx(G):
    if nx is None:
        raise ImportError("networkx is required for visualization")

    if isinstance(G, nx.DiGraph) or isinstance(G, nx.Graph):
        return G

    H = nx.DiGraph()
    for u, v, w in G.edges():
        try:
            H.add_edge(u, v, weight=float(w))
        except Exception:
            H.add_edge(u, v)
    return H


def draw_transaction_graph(G, outpath='graph.png', top_n=5, fmt=None, layout='spring'):
    """Draw and save the transaction graph.

    - `G`: networkx graph or simple graph implementing `.edges()` and `.nodes()`
    - `outpath`: filename to save (png/svg supported)
    - `top_n`: number of top central nodes to highlight
    - `fmt`: output format (e.g., 'png' or 'svg'); inferred from `outpath` if None
    - `layout`: 'spring' or 'shell' or 'kamada_kawai'
    """
    if nx is None or plt is None:
        raise ImportError("Visualization requires networkx and matplotlib")

    H = _to_networkx(G)

    # use degree centrality for sizing
    centrality = nx.degree_centrality(H)
    # normalize sizes
    sizes = []
    for n in H.nodes():
        sizes.append(100 + 2000 * centrality.get(n, 0))

    # pick top nodes
    top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_node_set = {n for n, _ in top_nodes}

    # layout
    if layout == 'spring':
        pos = nx.spring_layout(H, k=0.5, iterations=50)
    elif layout == 'kamada_kawai':
        pos = nx.kamada_kawai_layout(H)
    else:
        pos = nx.shell_layout(H)

    plt.figure(figsize=(14, 10))
    # draw nodes
    node_colors = ['red' if n in top_node_set else 'skyblue' for n in H.nodes()]
    nx.draw_networkx_nodes(H, pos, node_size=sizes, node_color=node_colors, alpha=0.9)
    # draw edges
    nx.draw_networkx_edges(H, pos, arrowstyle='->', arrowsize=8, alpha=0.4)
    # labels for top nodes only
    labels = {n: n for n in top_node_set}
    nx.draw_networkx_labels(H, pos, labels, font_size=8)

    plt.axis('off')
    if fmt is None:
        if outpath.lower().endswith('.svg'):
            fmt = 'svg'
        else:
            fmt = 'png'

    plt.tight_layout()
    plt.savefig(outpath, format=fmt, dpi=150)
    plt.close()
    return outpath
