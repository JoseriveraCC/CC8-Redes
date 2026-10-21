''' #####################
Función para leer el archivo y crea estructura {Nodo1, Nodo2, Costo}
Retorna el nodo inicial y la estructura.
'''
def routingFile(file_path):
    with open(file_path, encoding='utf-8') as file:
        lines = file.readlines()

    if not lines or not lines[0].strip():
        raise ValueError('Falta el nodo inicial en la primera línea.')

    initNode = lines[0].strip()
    routeDict = {initNode: {}}
    for number, line in enumerate(lines[1:], start=2):
        line = line.strip()
        if not line:
            continue
        edge, colon, value = line.partition(':')
        node1, dash, node2 = edge.partition('-')
        node1, node2 = node1.strip(), node2.strip()
        if not colon or not dash or not node1 or not node2 or node1 == node2:
            raise ValueError(f'Línea {number}: se esperaba Nodo1-Nodo2:Costo.')
        try:
            cost = int(value)
        except ValueError as error:
            raise ValueError(f'Línea {number}: el costo debe ser un entero.') from error
        if cost < 0:
            raise ValueError(f'Línea {number}: Dijkstra requiere costos no negativos.')
        routeDict.setdefault(node1, {})[node2] = cost
        routeDict.setdefault(node2, {})[node1] = cost

    return initNode, routeDict











