# README Lab 05 - Cliente TCP con Raw Sockets

## Objetivo del laboratorio

Este laboratorio implementa y modifica un cliente TCP que no usa la API normal de sockets TCP (`connect()`, `send()`, `recv()`), sino que construye manualmente paquetes IPv4 y segmentos TCP usando raw sockets.

El objetivo principal fue tomar el cliente base y agregar:

- Mensajes personalizados ingresados por el usuario.
- Envio de varios mensajes dentro de la misma sesion TCP.
- Output de consola suficientemente claro para reconstruir la sesion TCP.
- Documentacion para compilar, ejecutar, probar y explicar el comportamiento low-level.

## Archivos modificados

Los archivos modificados fueron:

- `ClientTCP/tcp_client.c`
- `ClientTCP/tcp_client.h`
- `ClientTCP/tcp_session.c`
- `ClientTCP/tcp_session.h`
- `ClientTCP/README.md`
- `Ayuda.md`

Tambien se agrego este archivo:

- `README_Lab.md`

No se modifico `ServerTCP.java`, porque el servidor de prueba ya permite recibir lineas, responderlas como eco y cerrar cuando recibe `EXIT` o `EXIT OFF`.

## Modificaciones realizadas

### 1. Mensajes personalizados

Antes, el cliente usaba un mensaje fijo por defecto: `EXIT OFF`.

Ahora hay dos formas de enviar mensajes.

Modo interactivo:

```bash
sudo ./tcp_client -l 127.0.0.1 -s 127.0.0.1 -p 5001 -P 45000 -i lo
```

El programa pregunta:

```text
Ingrese un mensaje (use EXIT OFF para apagar el servidor):
```

El usuario puede escribir varios mensajes dentro de la misma conexion TCP:

```text
Hello World
Hola desde Guatemala
EXIT OFF
```

Modo de un solo mensaje:

```bash
sudo ./tcp_client -l 127.0.0.1 -s 127.0.0.1 -p 5001 -P 45000 -i lo -m "Hello World"
```

Si el mensaje contiene `EXIT`, el servidor cierra la conexion. Si contiene `EXIT OFF`, el servidor tambien se apaga.

### 2. Puerto local fijo

Se agrego la opcion:

```bash
-P, --local-port
```

Ejemplo:

```bash
sudo ./tcp_client -P 45000
```

Esto permite que el cliente use siempre el puerto local `45000` en lugar de elegir uno aleatorio.

Esta opcion es importante porque en Linux hay que bloquear los paquetes `RST` automaticos del kernel antes de iniciar el handshake TCP manual. Para poder bloquearlos, necesitamos saber de antemano que puerto local usara el cliente.

### 3. Output mejorado de consola

Se agrego un log estructurado de segmentos TCP.

Ejemplo:

```text
==================== TCP SESSION ====================
No.  Time       Source          Destination     Protocol Length Info
-------------------- HANDSHAKE
1    0.000000   127.0.0.1       127.0.0.1       TCP      54     45000 -> 5001 [SYN      ] Seq=0 Win=5840 Len=0 Checksum=0x1234
2    0.000374   127.0.0.1       127.0.0.1       TCP      58     5001 -> 45000 [SYN, ACK ] Seq=0 Ack=1 Win=65495 Len=0 Checksum=0x5678
3    0.000453   127.0.0.1       127.0.0.1       TCP      54     45000 -> 5001 [ACK      ] Seq=1 Ack=1 Win=5840 Len=0 Checksum=0x9abc

Ingrese un mensaje (use EXIT OFF para apagar el servidor): Hello World
-------------------- DATA
4    7.680527   127.0.0.1       127.0.0.1       TCP      66     45000 -> 5001 [PSH, ACK ] Seq=1 Ack=1 Win=5840 Len=12 Checksum=0xabcd DATA="Hello World\n"
5    7.680568   127.0.0.1       127.0.0.1       TCP      54     5001 -> 45000 [ACK      ] Seq=1 Ack=13 Win=65474 Len=0 Checksum=0x1111
6    7.681637   127.0.0.1       127.0.0.1       TCP      66     5001 -> 45000 [PSH, ACK ] Seq=1 Ack=13 Win=65474 Len=12 Checksum=0x2222 DATA="Hello World\n"
7    7.681710   127.0.0.1       127.0.0.1       TCP      54     45000 -> 5001 [ACK      ] Seq=13 Ack=13 Win=5840 Len=0 Checksum=0x3333
```

El output permite ver:

- Quien envia el segmento.
- Quien recibe el segmento.
- Numero del segmento en la sesion.
- Tiempo relativo.
- IP origen.
- IP destino.
- Protocolo.
- Longitud estilo Wireshark.
- Puertos origen y destino.
- Flags TCP.
- Numero de secuencia `SEQ`.
- Numero de reconocimiento `ACK`.
- Ventana TCP `Win`.
- Longitud de datos `LEN`.
- Checksum TCP.
- Datos enviados o recibidos `DATA`.

## Como funciona la interaccion con el usuario

La interaccion esta implementada en `run_session()` dentro de `ClientTCP/tcp_client.c`.

El flujo es:

1. Se abre la sesion raw TCP con `tcp_session_open()`.
2. Se realiza el three-way handshake con `tcp_session_handshake()`.
3. Si el usuario paso `-m`, se envia solo ese mensaje.
4. Si el usuario no paso `-m`, se entra en un ciclo interactivo con `fgets()`.
5. Cada texto ingresado se envia con `tcp_session_send_message()`.
6. Despues de cada mensaje normal, se espera la respuesta del servidor con `tcp_session_receive_message()`.
7. Si el mensaje contiene `EXIT`, se llama a `tcp_session_drain_until_close()` para esperar el cierre iniciado por el servidor.
8. Finalmente el cliente envia su propio `FIN, ACK` con `tcp_session_close()`.

El servidor Java usa `BufferedReader.readLine()`, por eso el cliente agrega automaticamente `\n` al final de cada mensaje si el usuario no lo escribio. Sin ese salto de linea, el servidor seguiria esperando y no responderia.

## Como se genera el output

El output se genera principalmente en `ClientTCP/tcp_session.c`.

Se agregaron funciones auxiliares:

- `format_flags()`: convierte el byte de flags TCP en texto legible, por ejemplo `SYN, ACK`.
- `print_data()`: imprime el payload de forma segura, mostrando `\n`, `\r` o bytes no imprimibles como hexadecimal.
- `log_segment()`: imprime una linea del log con columnas tipo Wireshark: `No.`, `Time`, `Source`, `Destination`, `Protocol`, `Length` e `Info`.
- `print_session_header()`: imprime el encabezado visual de la sesion.
- `print_section()`: separa visualmente las fases `HANDSHAKE`, `DATA` y `CLOSE`.

Cada vez que el cliente envia un segmento, despues de `send_packet()` se llama a `log_segment()`.

Cada vez que el cliente recibe un segmento valido del servidor, despues de `wait_for_packet()` se llama a `log_segment()`.

## Informacion TCP mostrada

El programa muestra los campos principales que permiten seguir la sesion:

`Client -> Server` o `Server -> Client`:

Indica la direccion del segmento.

`[SYN]`, `[SYN, ACK]`, `[ACK]`, `[ACK, PSH]`, `[ACK, FIN]`:

Indica los flags TCP activos.

`SEQ`:

Numero de secuencia TCP relativo, como lo muestra Wireshark por defecto. Representa la posicion del primer byte enviado por ese segmento dentro del flujo TCP. El `SYN` inicial aparece como `Seq=0`.

`ACK`:

Numero de reconocimiento relativo. Indica el siguiente byte que se espera recibir del otro extremo.

`Win`:

Ventana TCP anunciada por quien envia el segmento.

`Checksum`:

Checksum TCP del segmento, mostrado en hexadecimal. En paquetes enviados por el cliente es el checksum que el programa calcula antes de enviar. En paquetes recibidos es el checksum que venia en el segmento del servidor.

`LEN`:

Cantidad de bytes de datos TCP. Los segmentos de control como `SYN`, `ACK` puro o `FIN` normalmente tienen `LEN=0`.

`DATA`:

Muestra el contenido del payload cuando el segmento lleva datos.

## Por que se usa iptables

`iptables` no forma parte de la implementacion de TCP del laboratorio, pero es necesario para ejecutar correctamente un cliente TCP hecho con raw sockets en Linux.

Cuando se usa un socket TCP normal, el kernel sabe que existe una conexion porque la aplicacion llama a `connect()`. En este laboratorio no hacemos eso. El programa construye el `SYN`, el `ACK`, los datos y el `FIN` manualmente.

El problema es que el kernel de Linux tambien ve los paquetes que llegan del servidor. Cuando recibe un `SYN, ACK` dirigido a un puerto local que el kernel no tiene registrado como conexion real, interpreta ese paquete como inesperado y responde automaticamente con `RST`.

`RST` significa reset. Le dice al servidor que aborte la conexion.

Entonces puede pasar esto:

```text
Cliente raw -> Servidor SYN
Servidor -> Cliente SYN, ACK
Kernel Linux -> Servidor RST automatico
Cliente raw -> Servidor ACK manual
Cliente raw -> Servidor PSH, ACK, DATA
Servidor ya considera la conexion rota o inconsistente
Cliente espera respuesta
Timeout
```

Por eso en la prueba aparecio:

```text
[!] Server response timeout
```

El handshake parecia correcto en el log del programa porque el programa si alcanzo a ver el `SYN, ACK`. Pero al mismo tiempo el kernel pudo haber enviado un `RST` automatico fuera del control del programa.

Para evitarlo se usa:

```bash
sudo iptables -A OUTPUT -p tcp --sport 45000 --tcp-flags RST RST -j DROP
```

Ese comando significa:

- `iptables`: herramienta de firewall de Linux.
- `-A OUTPUT`: agrega una regla a los paquetes que salen de la computadora.
- `-p tcp`: aplica solo a TCP.
- `--sport 45000`: aplica solo si el puerto origen es `45000`.
- `--tcp-flags RST RST`: aplica solo a paquetes TCP con flag `RST` activo.
- `-j DROP`: descarta esos paquetes, es decir, no los deja salir.

No estamos usando `iptables` para implementar TCP. Lo usamos para evitar que el kernel interfiera con la conexion TCP manual que el laboratorio esta construyendo con raw sockets.

## Como verificar con Wireshark

Como el entorno usado es WSL2 y Wireshark esta instalado en Windows, se agrego el script:

```bash
open_wireshark_wsl.sh
```

Este script abre Wireshark de Windows y le envia una captura en vivo desde WSL usando `tcpdump`.

Flujo interno:

```text
tcpdump captura en WSL -> salida pcap por stdout -> Wireshark.exe lee desde stdin
```

Esto funciona como un tunel de captura. No es un tunel TCP de red; es un pipe de paquetes capturados. Se usa porque el trafico de loopback `127.0.0.1` dentro de WSL2 pertenece al stack de red de Linux y Wireshark en Windows no siempre lo ve directamente.

Comando recomendado:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05
./open_wireshark_wsl.sh lo "tcp port 5001"
```

Si falta `tcpdump` en WSL:

```bash
sudo apt update
sudo apt install tcpdump
```

El comando manual equivalente es:

```bash
sudo tcpdump -i lo -p -n -U -s 0 -w - "tcp port 5001" | "/mnt/c/Program Files/Wireshark/Wireshark.exe" -k -i -
```

Pasos recomendados:

1. Abrir Wireshark.
2. Capturar en la interfaz `lo` si se esta probando en Linux con `127.0.0.1`.
3. Usar el filtro:

```text
tcp.port == 5001
```

4. Levantar el servidor:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05
java ServerTCP
```

5. Bloquear `RST` automaticos para el puerto local elegido:

```bash
sudo iptables -A OUTPUT -p tcp --sport 45000 --tcp-flags RST RST -j DROP
```

6. Ejecutar el cliente:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05/ClientTCP
sudo ./tcp_client -l 127.0.0.1 -s 127.0.0.1 -p 5001 -P 45000 -i lo
```

7. Enviar mensajes:

```text
Hello World
Hola desde Guatemala
EXIT OFF
```

8. Confirmar en Wireshark que se ve la secuencia completa:

```text
Client -> Server SYN
Server -> Client SYN, ACK
Client -> Server ACK
Client -> Server PSH, ACK, DATA
Server -> Client ACK
Server -> Client PSH, ACK, DATA
Client -> Server ACK
Server -> Client FIN, ACK
Client -> Server ACK
Client -> Server FIN, ACK
Server -> Client ACK
```

9. Eliminar la regla temporal:

```bash
sudo iptables -D OUTPUT -p tcp --sport 45000 --tcp-flags RST RST -j DROP
```

## Comandos completos de ejecucion

Terminal 1:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05
javac ServerTCP.java
java ServerTCP
```

Terminal 2:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05/ClientTCP
make clean
make
sudo iptables -A OUTPUT -p tcp --sport 45000 --tcp-flags RST RST -j DROP
sudo ./tcp_client -l 127.0.0.1 -s 127.0.0.1 -p 5001 -P 45000 -i lo
sudo iptables -D OUTPUT -p tcp --sport 45000 --tcp-flags RST RST -j DROP
```

## Resultado esperado

El programa debe permitir enviar varios mensajes, mostrar cada segmento TCP importante y cerrar correctamente cuando se envie `EXIT OFF`.

El cierre esperado es iniciado por el servidor:

```text
Server -> Client FIN, ACK
Client -> Server ACK
Client -> Server FIN, ACK
Server -> Client ACK
```
