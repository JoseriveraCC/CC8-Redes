# Laboratorio 04 - Cliente NTP manual

Ciencias de la Computacion VIII  
Repositorio: `CC8-Redes`  
Lenguaje: **C**

## Objetivo

Este laboratorio implementa un cliente NTP manual basado en el RFC 5905. El programa:

- Construye manualmente paquetes NTP de **48 bytes**.
- Envia solicitudes UDP al puerto `123` de servidores NTP.
- Consulta como minimo **7 servidores NTP**.
- Calcula los cuatro tiempos del algoritmo:
  - `T1`: tiempo interno del cliente al enviar la solicitud.
  - `T2`: tiempo del servidor al recibir la solicitud.
  - `T3`: tiempo del servidor al responder.
  - `T4`: tiempo interno del cliente al recibir la respuesta.
- Calcula:

```text
offset = ((T2 - T1) + (T3 - T4)) / 2
delay  = (T4 - T1) - (T3 - T2)
```

- Elige el servidor con **menor delay**.
- Ajusta un reloj interno simulado.
- Repite el proceso hasta que el offset sea menor al umbral configurado.
- Imprime un log claro de cada iteracion.

> Importante: por seguridad, este laboratorio **no cambia la hora real del sistema operativo**. La sincronizacion se realiza sobre un reloj interno simulado, tal como permite el enunciado.

---

## Archivos

```text
Lab04/
├── ntp_client.c
├── Makefile
└── README.md
```

---

## Compilar

Desde la raiz del repositorio:

```bash
cd ~/CC8/CC8-Redes/Lab04
make
```

Esto genera el binario:

```text
ntp_client
```

---

## Ejecutar con configuracion por defecto

```bash
make run
```

Por defecto usa:

- Hora interna inicial: hora actual del sistema.
- Umbral de offset: `5 ms`.
- Intervalo entre verificaciones: `60 segundos`.
- Timeout por ronda: `2500 ms`.
- Maximo de iteraciones: `10`.
- 7 servidores NTP por defecto:
  - `time.google.com`
  - `time.apple.com`
  - `time.windows.com`
  - `time.cloudflare.com`
  - `time.nist.gov`
  - `time-a.nist.gov`
  - `pool.ntp.org`

---

## Ejecutar para una prueba rapida

Para no esperar un minuto entre iteraciones:

```bash
make test
```

Equivale a:

```bash
./ntp_client --threshold-ms 500 --interval 2 --max-iterations 3 --timeout-ms 3000
```

Uso `500 ms` en `make test` para que la prueba rapida sea tolerante a latencia, jitter de red y diferencias entre servidores publicos. Para la entrega final puedes bajar el umbral, por ejemplo a `10 ms` o `5 ms`, usando `--threshold-ms`.

---

## Ejecutar con fecha local configurable de Guatemala

El enunciado pide que el laboratorio tenga una fecha interna local configurable antes de ejecutarse. El formato esperado es:

```text
YYYY-MM-DD HH:MM:SS.mmm
```

Ejemplo:

```bash
./ntp_client --date '2020-09-01 21:00:17.123' --threshold-ms 10 --interval 2 --max-iterations 4
```

Esa fecha se interpreta como **hora local de Guatemala (UTC-6)**. Internamente el programa la convierte a UTC para poder compararla contra los timestamps NTP.

Tambien puedes ejecutar el objetivo del Makefile:

```bash
make demo-old-date
```

---

## Opciones disponibles

```text
--date 'YYYY-MM-DD HH:MM:SS.mmm'  Fecha inicial local Guatemala UTC-6.
--threshold-ms N                   Offset meta en milisegundos.
--interval N                       Segundos entre iteraciones.
--timeout-ms N                     Timeout por ronda NTP.
--max-iterations N                 Maximo de iteraciones.
--server HOST                      Agrega servidor NTP. Puede repetirse.
--port PORT                        Puerto NTP. Default: 123.
--help                             Mostrar ayuda.
```

Ejemplo con servidores personalizados:

```bash
./ntp_client \
  --server time.google.com \
  --server time.apple.com \
  --server time.windows.com \
  --server time.cloudflare.com \
  --server time.nist.gov \
  --server time-a.nist.gov \
  --server pool.ntp.org \
  --threshold-ms 5 \
  --interval 5
```

El programa exige al menos 7 servidores, porque ese es un requisito del laboratorio.

---

## Como verificar que funciona

1. Compila sin errores:

```bash
make clean
make
```

2. Ejecuta una prueba rapida:

```bash
make test
```

3. En el log revisa que aparezca:

```text
Laboratorio 04 - Cliente NTP manual
Servidores configurados (7)
Formula offset: theta = ((T2 - T1) + (T3 - T4)) / 2
Formula delay : delta = (T4 - T1) - (T3 - T2)
```

4. En cada iteracion debe aparecer una tabla como esta:

```text
Servidor                 IP              Stratum  Offset(ms)     Delay(ms)      Estado
```

5. Debe seleccionar el mejor servidor:

```text
Mejor servidor por menor delay: ...
```

6. Debe mostrar los tiempos:

```text
T1 cliente envia
T2 servidor recibe
T3 servidor responde
T4 cliente recibe
```

7. Debe mostrar el calculo:

```text
Calculo delay
Calculo offset
```

8. Debe ajustar el reloj interno:

```text
Reloj interno DESPUES del ajuste
```

9. Cuando el offset queda bajo el umbral, muestra:

```text
SINCRONIZADO
```

---

## Nota sobre red/firewall

NTP usa UDP puerto `123`. Si todos los servidores aparecen con `timeout sin respuesta`, lo mas probable es que:

- La red bloquee UDP/123.
- El firewall bloquee NTP.
- El entorno WSL/VM no tenga salida UDP hacia ese puerto.
- El servidor NTP consultado no respondio temporalmente.

Prueba desde Linux:

```bash
timedatectl show-timesync --all 2>/dev/null | head
```

O prueba desde otra red. El codigo puede compilar correctamente aunque una red especifica bloquee las respuestas NTP.

---

## Limpiar

```bash
make clean
```

---

## Explicacion breve para el video

Puedes explicar el laboratorio asi:

1. El programa crea un paquete NTP de 48 bytes.
2. En el primer byte coloca `LI = 0`, `Version = 4`, `Mode = 3`, que significa cliente NTP.
3. Antes de enviar, escribe `T1` en el campo `Transmit Timestamp`.
4. El servidor responde copiando ese valor como `Originate Timestamp` y llenando `Receive Timestamp` (`T2`) y `Transmit Timestamp` (`T3`).
5. El cliente captura `T4` apenas recibe el paquete.
6. Con esos cuatro tiempos calcula `delay` y `offset`.
7. Como se consultan varios servidores, se escoge el que tenga menor delay.
8. El offset seleccionado se aplica al reloj interno simulado.
9. El proceso se repite hasta que el offset sea suficientemente cercano a cero.

