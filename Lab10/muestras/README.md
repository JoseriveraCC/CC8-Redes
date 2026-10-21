# Muestra WEP pública

`ptw.cap` se descargó el 20 de octubre de 2026 desde
[el servidor oficial de Aircrack-ng](https://dl.aircrack-ng.org/ptw.cap).
El [README del proyecto](https://github.com/aircrack-ng/aircrack-ng/blob/master/README)
la documenta como muestra apta para PTW de WEP de 64 bits, con clave pública
`1F:1F:1F:1F:1F` (40 bits secretos y 24 bits de IV).

En la prueba local se identificó el BSSID `00:12:BF:12:32:29`, ESSID `Appart`.
Estos datos pertenecen a la muestra y **no al router del aula**. El archivo ya
está incluido para practicar sin conexión a Internet y sin transmitir paquetes.

SHA-256:

```text
a1a442ca2e8062901ba3fc0dfd58f9f412e14c22332ee2e4698eeffab6bd787c
```

Desde la raíz del laboratorio:

```bash
sha256sum -c evidencias/muestra.sha256
aircrack-ng -a 1 -b 00:12:BF:12:32:29 muestras/ptw.cap
```

Esta prueba utiliza la captura como entrada. La clave conocida solo sirve para
verificar el resultado; no se pasa como argumento ni como diccionario.
