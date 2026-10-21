# Guion breve para el video de entrega

«Hola. Este es mi Laboratorio 8 de Link State, ejecutado con Python 3. El programa lee la primera línea del TXT como nodo inicial y las siguientes como enlaces bidireccionales con su costo. Muestra la matriz de enlaces y, después, cada paso de Dijkstra con `D(v)`, `p(v)` y el nodo incorporado a `N'`.

En el paso cero asigno el costo de los vecinos directos; los demás quedan en infinito. En cada iteración elijo el nodo pendiente con menor costo; si varios empatan, elijo el primero alfabéticamente. Para cada vecino actualizo el costo y el predecesor cuando encuentro una ruta menor o igual. Por eso, en `topo2`, `p(h)` pasa de `f` a `g` aunque el costo sigue siendo 6.

Ahora ejecuto `python3 LinkState.py test/topo1.txt` y repito el comando con `topo2.txt` hasta `topo6.txt`. Los tres primeros reproducen los ejemplos de la guía y los otros tres corresponden a los ejercicios incluidos.

Finalmente ejecuto `python3 LinkState.py test/topo7.txt`. Desde `h`, el orden de selección es `h, o, p, i, j, t, m, n, s, r, q, k, l`. Por ejemplo, la ruta final a `l` es `h-o-p-i-t-m-s-r-q-k-l`, de costo 10: cada uno de sus diez enlaces cuesta 1. La última fila muestra `D(l)=10` y `p(l)=k`. Como Dijkstra selecciona siempre el menor costo pendiente y todos los enlaces tienen costos no negativos, ese costo ya no puede disminuir cuando `l` entra en `N'`. Los cambios de predecesor con el mismo costo siguen la regla de empate de la guía.»

> La hoja presencial de topologías mencionada en el PDF no está incluida en este directorio. Si debes entregar sus cuatro ejercicios por separado, muéstralos también en el video.
