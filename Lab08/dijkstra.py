"""Cálculo de rutas mínimas desde el nodo inicial."""

from math import inf


def init(initNode, routeDict):
    """Devuelve una fila por cada paso: (paso, D(v),p(v)..., nodo añadido)."""
    nodes = sorted(routeDict)
    distances = {node: inf for node in nodes}
    previous = {node: None for node in nodes}
    distances[initNode] = 0
    visited = {initNode}
    steps = []

    def record(node):
        values = []
        for destination in nodes:
            if destination != initNode:
                cost = distances[destination]
                values.append(f"{'∞' if cost == inf else cost}, {previous[destination] or '-'}")
        steps.append((len(steps), *values, node))

    for neighbor, cost in routeDict[initNode].items():
        distances[neighbor] = cost
        previous[neighbor] = initNode
    record(initNode)

    while len(visited) < len(nodes):
        node = min((n for n in nodes if n not in visited),
                   key=lambda n: (distances[n], n))
        visited.add(node)
        if distances[node] != inf:
            for neighbor, cost in routeDict[node].items():
                if neighbor not in visited:
                    candidate = distances[node] + cost
                    # La guía prefiere el nuevo predecesor cuando hay empate.
                    if candidate <= distances[neighbor]:
                        distances[neighbor] = candidate
                        previous[neighbor] = node
        record(node)

    return steps
