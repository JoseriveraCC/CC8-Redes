''' #####################
Función Muestra la estructura {Nodo1, Nodo2, Costo}
Valores no definidos coloca el simbolo ∞
'''
def routeStruct(initNode, routeDict):
    nodes = sorted(routeDict.keys())
    fixWidth = 2

    # Función Separador Entrelineado de la Tabla
    def create_separator(length):
        return "+" + "+".join(["-" * (fixWidth + 2)] * length) + "+"
    
    print("\n\tTabla: Costos - Nodo a Nodo\n\tNodo Inicial: " + initNode)
    # Inicio de la tabla
    print(create_separator(len(nodes) + 1))
    # Encabezado de la tabla
    print("|" + f" ".rjust(fixWidth + 2) + "|" + "".join(f" {node} ".rjust(fixWidth + 2) + "|" for node in nodes) )
    # Separador del encabezado
    print(create_separator(len(nodes) + 1))

    # Filas de la Tabla
    for node1 in nodes:
        print( f"| {node1.rjust(fixWidth)} |" + "".join(f" {str(routeDict[node1].get(node2, '∞')).rjust(fixWidth)} |" for node2 in nodes) )
        # Separador entre lineas
        print(create_separator(len(nodes) + 1))



''' #####################
Función Muestra todos pasos del Algoritmo Dijkstra
Valores no definidos coloca el simbolo ∞
'''
def stepsCalculatingRoute(initNode, routeDict, stepsCalcs):
    nodes = sorted(routeDict)
    headers = ["Paso"] + [f"D({node}),p({node})" for node in nodes if node != initNode] + ["N'"]
    rows = [[str(value) for value in step] for step in stepsCalcs]
    widths = [max(len(header), *(len(row[i]) for row in rows))
              for i, header in enumerate(headers)]
    separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def print_row(values):
        print("| " + " | ".join(value.rjust(width) for value, width in zip(values, widths)) + " |")

    print("\n\tTabla: Pasos de Algoritmo Dijkstra\n\tNodo Inicial: " + initNode)
    print("\tN = " + ", ".join(nodes))
    print(separator)
    print_row(headers)
    print(separator)
    for row in rows:
        print_row(row)
        print(separator)

    


