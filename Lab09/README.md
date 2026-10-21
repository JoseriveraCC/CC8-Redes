# Laboratorio 9 — SpeedTest con TCP RAW

Se implementó la opción **Upload Speed** del PDF: el cliente crea manualmente
los encabezados IPv4 y TCP, abre una conexión, sube diez copias de un archivo
de 1 KB, mide sus confirmaciones y cierra con FIN/ACK. El receptor usa TCP del
sistema operativo. Todo el código utiliza Python y su biblioteca estándar.

## Requisitos

- Linux, Python **3.9 o posterior** y `make`. No se instalan paquetes Python.
- Para ejecutar el cliente: `sudo` o `CAP_NET_RAW`.
- `iptables` para impedir los RST que genera automáticamente el TCP de Linux
  al ver una conexión que fue creada fuera de su pila TCP.
- Para la prueba aislada: además `unshare` (util-linux) e `ip` (iproute2).

Se eligió Linux como plataforma de entrega permitida por el PDF. El cliente
RAW y los comandos de firewall no están preparados para macOS.

## Archivos

| Archivo | Responsabilidad |
| --- | --- |
| `speedtest.py` | Cliente RAW: encabezados, checksums, SEQ/ACK, tiempos y CSV. |
| `server.py` | Receptor TCP: una conexión, 10 000 bytes y verificación de las diez copias. |
| `archivo_1kb.bin` | Archivo binario aleatorio de exactamente **1000 bytes**. |
| `tests/test_speedtest.py` | Pruebas de paquetes, estados y flujo sin privilegios. |
| `tests/integration.py` | Subida RAW real dentro de una red temporal aislada. |
| `Makefile` | Comprobación de sintaxis, ejecución, pruebas y ZIP. |

Se usa KB decimal, igual que el ejemplo `(1000 × 8)` del PDF; no 1024 bytes.
El archivo de entrada no se modifica y se reutiliza en los diez envíos.

## Comprobar y ejecutar

Desde `Lab09/`:

```bash
make
make test
```

Python no necesita enlazado ni compilador externo. `make` verifica la sintaxis
y compila a bytecode los cuatro archivos Python. `make test` ejecuta doce
pruebas con `unittest`.

### Prueba completa en una red aislada

Si Linux permite espacios de usuario sin privilegios:

```bash
make integration-user
```

En caso contrario, use:

```bash
sudo make integration
```

Crea una red temporal con `unshare --net`, activa su loopback e instala una
regla RST dentro de ella. Inicia el receptor y el cliente RAW, comprueba una
sola conexión, diez tiempos positivos, apertura/cierre y los **10 000 bytes
exactos** contra el archivo original repetido diez veces. Retira la regla al
terminar. No modifica las reglas del espacio de red principal y sus archivos
de resultados son temporales.

Un contenedor puede impedir esta prueba aunque se invoque `sudo`: hacen falta
permisos para crear espacios de red, administrar su firewall y abrir RAW.
En ese caso ejecútela en una máquina Linux o VM con esos permisos.

### Ejecución manual en dos terminales

Terminal 1, receptor sin privilegios:

```bash
make server
```

Terminal 2, regla específica para esta prueba y cliente:

```bash
sudo iptables -I OUTPUT -p tcp -s 127.0.0.1 --sport 40000 -d 127.0.0.1 --dport 3001 --tcp-flags RST RST -j DROP
sudo make client CLIENT_ARGS="--verbose --csv resultados.csv"
```

**Retire la regla al terminar**, también si el cliente falla:

```bash
sudo iptables -D OUTPUT -p tcp -s 127.0.0.1 --sport 40000 -d 127.0.0.1 --dport 3001 --tcp-flags RST RST -j DROP
```

El receptor finaliza después de la conexión y guarda `recibido.bin`. Para
otra medición, vuelva a iniciar el receptor. La reserva de puerto del cliente
solo hace `bind`; nunca establece una conexión TCP del sistema operativo.
El tráfico de subida, apertura y cierre sale exclusivamente por `SOCK_RAW`.

Para dos máquinas, inicie el receptor con
`make server SERVER_ARGS="--bind 0.0.0.0 --port 3001"`. En el cliente use
`--server IP_DEL_RECEPTOR`, cambie `-s` por su IPv4 local y `-d` por la IPv4 del
receptor en ambos comandos `iptables`. Permita TCP/3001 en el firewall del
receptor. Si cambia puertos, actualice la regla RST para que coincida con
`--source-port` y `--port`. Use una red directa de laboratorio sin NAT que
interfiera con el seguimiento de la conexión RAW.

## Secuencia implementada

```text
Cliente RAW                             Receptor TCP del SO
    SYN, SEQ=x ------------------------>
               <------------------------ SYN|ACK, SEQ=y, ACK=x+1
    ACK, SEQ=x+1, ACK=y+1 ------------->
    PSH|ACK, archivo 1 ---------------->
               <------------------------ ACK de todos sus bytes
                  ... repetir hasta archivo 10 ...
    FIN|ACK --------------------------->
               <------------------------ ACK y FIN (juntos o separados)
    ACK ------------------------------->
```

El cliente serializa los campos en orden de red, calcula el checksum IPv4
y el TCP con su pseudoencabezado, anuncia MSS y filtra respuestas por ambas
IP y ambos puertos. SYN y FIN consumen un número de secuencia; los datos
consumen uno por byte. Los SEQ/ACK se calculan módulo 2³².

Solo se mantiene un segmento pendiente. Si el MSS o la ventana anunciada son
menores que un archivo, este se divide en segmentos; sigue contando como un
archivo y una muestra hasta que se confirman todos sus bytes. Los ACK viejos
se ignoran; al vencer el tiempo se retransmiten los mismos bytes y SEQ, hasta
dos reintentos por defecto. Un RST, un cierre anticipado, una ventana cero o
un timeout definitivo se informan como error con código de salida distinto
de cero. No se imprime un resultado exitoso si falta completar el cierre.

El receptor acumula el flujo hasta EOF, verifica tamaño y diez copias iguales,
y guarda el resultado. No supone que una llamada a `recv()` corresponde a un
archivo. No responde con datos de aplicación que alteren la medición de subida.

## Mediciones y fórmula

Se usa `time.perf_counter()`, reloj monotónico de alta resolución:

1. **Latencia TCP / RTT de apertura**: desde SYN hasta el SYN+ACK válido.
2. **RTT + transmisión por archivo**: desde su primer segmento de datos hasta
   el ACK que confirma su último byte. Se guardan diez muestras en
   `resultados.csv` (`archivo,bytes,rtt_transmision_ms`).
3. **Promedio**: media aritmética de las diez muestras.
4. **Velocidad estimada según el PDF**:

```text
tiempo_estimado_s = latencia_apertura_s + promedio_rtt_transmision_s
velocidad_Kbps   = (1000 * 8) / tiempo_estimado_s / 1000
```

El PDF suma un RTT de apertura y `(RTT + tiempo de transmisión)`. Aquí el
segundo término ya está incluido en la muestra de cada archivo: no se vuelve
a duplicar. La apertura ocurre una sola vez; se usa su latencia como término
de la estimación didáctica. Para reproducir el ejemplo del PDF, si ambos
términos son 0.032 s, resulta **125 Kbps**. El cierre y la espera final quedan
fuera de la medición. La salida incluye los diez tiempos, latencia, promedio,
velocidad estimada, total confirmado y número de retransmisiones.

Esta es una estimación del ejercicio, no una medición de capacidad máxima
del enlace. Incluye procesamiento, planificación y posibles ACK retardados
del receptor. En loopback mide comportamiento local. Si hay retransmisiones,
sus esperas también forman parte de los tiempos informados.

## Wireshark

Inicie la captura antes del cliente, elija `lo` para la prueba local o la
interfaz de su red para dos máquinas y aplique:

```text
tcp.port == 3001 && tcp.port == 40000
```

Observe SYN → SYN/ACK → ACK, los incrementos de SEQ por los datos, ACK
acumulativos y FIN/ACK. La prueba aislada usa otro espacio de red, por lo que
para capturar fácilmente con Wireshark use la ejecución manual. Los tiempos
reales dependen de su equipo; no se incluyen resultados de ejemplo como si
fueran mediciones realizadas.

## Alcance y referencias

Es una implementación didáctica de subida IPv4, no una pila TCP completa:
no incluye control de congestión, persistencia de ventana cero ni recepción
de datos de aplicación. La espera final para repetir el ACK ante FIN duplicado
dura un segundo, en lugar del TIME-WAIT general de 2×MSL.
Se calculan los dos checksums de salida y se verifica el IPv4 recibido.
El checksum TCP entrante no se valida: el offload puede dejarlo pendiente
en capturas locales; una validación general requeriría también sus metadatos.

Se revisaron `../Lab01/Server.java`, `../Lab03/` y `../Lab04/ntp_client.c`.
Lab01 es una calculadora con mensajes de texto por línea; se eligió un receptor
binario específico, permitido por el PDF, para evitar mezclar su protocolo
con los archivos. Lab03/04 sirvieron como referencia de envío, recepción,
longitud efectiva y timeout de datagramas; UDP no realiza esta subida TCP.

- Enunciado: `Laboratorio_-_SpeedTest.pdf`, páginas 1–3.
- [RFC 9293 — TCP](https://www.rfc-editor.org/rfc/rfc9293.html): encabezado,
  pseudoencabezado, números de secuencia, apertura y cierre.
- [Linux raw(7)](https://man7.org/linux/man-pages/man7/raw.7.html): `SOCK_RAW`,
  `IP_HDRINCL`, recepción y permisos `CAP_NET_RAW`.

## Entrega

```bash
make zip
```

Produce `Lab09_SpeedTest.zip` con código, archivo de prueba, Makefile, README,
pruebas y PDF dentro de `Lab09/`. Extráigalo y ejecute `make test` desde ese
directorio para comprobar la entrega. `make clean` retira solo cachés de
bytecode; conserva resultados y archivos recibidos.

La subida del ZIP al GES se realiza por separado.
