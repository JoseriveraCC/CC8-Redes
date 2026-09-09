# Ayuda Laboratorio 5 - Cliente TCP con Raw Sockets

## Que se implemento

Se modifico principalmente el cliente raw TCP para cumplir los dos requerimientos del laboratorio:

- `ClientTCP/tcp_client.c`: ahora permite enviar mensajes personalizados desde consola o desde la opcion `-m/--message`.
- `ClientTCP/tcp_session.c`: ahora imprime un log claro de los segmentos TCP enviados y recibidos.
- `ClientTCP/tcp_client.h`: ahora incluye `local_port` y la opcion `OPT_LOCAL_PORT`.
- `ClientTCP/tcp_session.h`: se agrego el estado `server_closed`, la declaracion de `tcp_session_receive_message()` y el parametro `local_port` en `tcp_session_open()`.

El servidor `ServerTCP.java` no se modifico.

## Que funciones se integraron o cambiaron

### `tcp_client.c`

`print_usage()`:

Ahora muestra que `-m/--message` sirve para enviar un solo mensaje y que, si no se usa, el programa entra en modo interactivo. Tambien muestra `-P/--local-port` para fijar el puerto local.

`parse_cli()`:

Ahora reconoce `-P` y `--local-port`. El valor se guarda en `o->local_port`.

`run_session()`:

Antes abria la sesion, hacia handshake, enviaba un unico mensaje fijo y cerraba. Ahora hace esto:

```text
1. Abre el raw socket y configura la sesion.
2. Hace el three-way handshake.
3. Si existe -m, envia ese unico mensaje.
4. Si no existe -m, entra en un ciclo con fgets().
5. Por cada mensaje normal, envia datos y espera respuesta.
6. Si el mensaje contiene EXIT, espera el FIN del servidor.
7. Envia su propio FIN y cierra el raw socket.
```

`main()`:

Antes el mensaje por defecto era `EXIT OFF`. Ahora `.message = NULL`, lo cual significa modo interactivo por defecto. Tambien se inicializa `.local_port = 0`, lo cual significa puerto aleatorio si el usuario no usa `-P`.

### `tcp_client.h`

`cli_options_t`:

Se agrego:

```c
uint16_t local_port;
```

Esto permite guardar el puerto local fijo recibido por `-P`.

`option_id_t`:

Se agrego:

```c
OPT_LOCAL_PORT
```

Esto permite que el parser de argumentos distinga `-P/--local-port` de las demas opciones.

### `tcp_session.c`

`format_flags()`:

Convierte el byte de flags TCP en texto. Por ejemplo, si el segmento tiene `TCP_SYN | TCP_ACK`, imprime `SYN, ACK`.

`print_data()`:

Imprime los datos del segmento. Si encuentra salto de linea, imprime `\n` en lugar de hacer un salto real. Esto hace que el log sea mas claro.

`log_segment()`:

Es la funcion central del nuevo output. Recibe emisor, receptor, flags, `SEQ`, `ACK`, puertos, ventana, longitud del paquete y datos. Luego imprime una linea con columnas similares a Wireshark:

```text
No.  Time       Source          Destination     Protocol Length Info
4    7.680527   127.0.0.1       127.0.0.1       TCP      75     45000 -> 5001 [PSH, ACK ] Seq=1 Ack=1 Win=5840 Len=21 Checksum=0xabcd DATA="Hola desde Guatemala\n"
```

El programa guarda el `SEQ` inicial del cliente y el `SEQ` inicial del servidor para imprimir numeros relativos, igual que Wireshark cuando tiene habilitado `Relative sequence numbers`. Por eso el primer `SYN` aparece con `Seq=0` y el siguiente segmento del cliente aparece con `Seq=1`.

`print_session_header()` y `print_section()`:

Solo separan visualmente las etapas `HANDSHAKE`, `DATA` y `CLOSE`.

`tcp_session_open()`:

Antes siempre escogia un puerto local aleatorio. Ahora recibe `local_port`. Si el usuario pasa `-P 45000`, se usa ese puerto. Si no, se mantiene el comportamiento anterior y se escoge un puerto aleatorio.

`tcp_session_handshake()`:

Se mantiene la logica original del handshake, pero ahora imprime cada segmento:

```text
Client -> Server SYN
Server -> Client SYN, ACK
Client -> Server ACK
```

Tambien sigue haciendo los incrementos correctos:

```c
s->seq++;
s->ack = server_seq + 1;
```

`tcp_session_send_message()`:

Construye un segmento `PSH, ACK` con el mensaje del usuario. Si el mensaje no trae `\n`, se agrega porque el servidor Java usa `readLine()`. Despues de enviar, incrementa:

```c
s->seq += len;
```

Esto se hace porque cada byte de datos consume un numero de secuencia TCP.

`tcp_session_receive_message()`:

Esta funcion nueva permite esperar una respuesta del servidor despues de cada mensaje normal. Si recibe datos, actualiza `ACK` con la longitud recibida y envia un `ACK` de confirmacion. Si recibe un `FIN`, marca `server_closed = 1`.

`tcp_session_drain_until_close()`:

Se usa cuando el usuario envia un mensaje que contiene `EXIT`. En ese caso el servidor responde el eco y luego cierra la conexion. Esta funcion sigue leyendo hasta observar el `FIN` del servidor.

`tcp_session_close()`:

Envia el `FIN, ACK` del cliente para cerrar su lado de la conexion. Luego espera el `ACK` final del servidor y cierra el raw socket.

### `tcp_session.h`

`server_closed`:

Este campo indica si ya se recibio un `FIN` del servidor. Sirve para que el ciclo interactivo sepa que no debe seguir pidiendo mensajes.

## Interaccion con el usuario

Si se ejecuta el cliente sin `-m`, el programa entra en modo interactivo despues del three-way handshake.

En ese modo se pueden enviar N mensajes dentro de la misma conexion TCP:

```text
Ingrese un mensaje (use EXIT OFF para apagar el servidor): Hello World
Ingrese un mensaje (use EXIT OFF para apagar el servidor): Hola desde Guatemala
Ingrese un mensaje (use EXIT OFF para apagar el servidor): EXIT OFF
```

El mensaje `EXIT` le indica al servidor que cierre la conexion. El mensaje `EXIT OFF` tambien hace que el servidor Java termine completamente.

Tambien se puede enviar un solo mensaje por argumento:

```bash
sudo ./tcp_client -P 45000 -m "Hello World"
sudo ./tcp_client -P 45000 -m "EXIT OFF"
```

## Output TCP

El cliente imprime cada segmento importante con este formato:

```text
No.  Time       Source          Destination     Protocol Length Info
1    0.000000   127.0.0.1       127.0.0.1       TCP      54     45000 -> 5001 [SYN      ] Seq=0 Win=5840 Len=0 Checksum=0x1234
2    0.000374   127.0.0.1       127.0.0.1       TCP      58     5001 -> 45000 [SYN, ACK ] Seq=0 Ack=1 Win=65495 Len=0 Checksum=0x5678
3    0.000453   127.0.0.1       127.0.0.1       TCP      54     45000 -> 5001 [ACK      ] Seq=1 Ack=1 Win=5840 Len=0 Checksum=0x9abc
4    7.680527   127.0.0.1       127.0.0.1       TCP      75     45000 -> 5001 [PSH, ACK ] Seq=1 Ack=1 Win=5840 Len=21 Checksum=0xabcd DATA="Hola desde Guatemala\n"
```

La informacion mostrada es:

- `No.`: numero del segmento dentro del log del cliente.
- `Time`: tiempo relativo desde que se abrio la sesion TCP.
- `Source`: IP origen.
- `Destination`: IP destino.
- `Protocol`: protocolo, en este laboratorio siempre `TCP`.
- `Length`: longitud del frame mostrada al estilo Wireshark.
- `Info`: resumen del segmento TCP.
- Emisor y receptor del segmento.
- Flags TCP: `SYN`, `ACK`, `PSH`, `FIN`, `RST`, `URG`.
- `Seq`: numero de secuencia relativo del segmento.
- `Ack`: siguiente byte relativo que se espera recibir del otro lado, cuando el flag `ACK` esta activo.
- `Win`: ventana TCP anunciada por quien envia el segmento.
- `LEN`: cantidad de bytes de datos TCP.
- `Checksum`: checksum TCP del segmento, mostrado en hexadecimal.
- `DATA`: contenido enviado o recibido, escapando saltos de linea como `\n`.

El checksum TCP es un valor de verificacion calculado sobre el header TCP, los datos y un pseudo-header que incluye IP origen, IP destino, protocolo y longitud TCP. Sirve para detectar errores o corrupcion en el segmento.

## Explicacion low-level

El cliente construye manualmente los headers IPv4 y TCP. No usa `connect()` ni sockets TCP normales. Por eso el programa debe mantener manualmente los numeros `SEQ` y `ACK`.

En un programa normal, el sistema operativo maneja TCP. En este laboratorio, el programa hace manualmente parte de ese trabajo. Por eso el codigo debe decidir cuando subir `SEQ`, cuando subir `ACK`, cuando responder con `ACK` y cuando enviar `FIN`.

Durante el handshake ocurre esto:

- El cliente envia `SYN` con su `SEQ` inicial.
- El servidor responde `SYN, ACK` con su propio `SEQ` y con `ACK = SEQ_cliente + 1`.
- El cliente incrementa su `SEQ` en 1 porque `SYN` consume un numero de secuencia.
- El cliente guarda `ACK = SEQ_servidor + 1` porque espera el siguiente byte del servidor.
- El cliente envia el `ACK` final.

Cuando se envian datos:

- El cliente envia `PSH, ACK` con el mensaje como payload.
- Si el mensaje no termina en salto de linea, el cliente agrega `\n`, porque el servidor usa `readLine()`.
- Despues de enviar datos, el cliente hace `SEQ += LEN`, porque cada byte de datos consume un numero de secuencia.
- Cuando el servidor responde con datos, el cliente hace `ACK += LEN` y envia un `ACK` para confirmar esos bytes.

Cuando se recibe un `FIN`:

- `FIN` indica que el servidor ya no enviara mas datos en esa direccion.
- Aunque no tenga payload, `FIN` consume un numero de secuencia.
- Por eso el cliente hace `ACK++` al recibir `FIN`.
- Luego el cliente responde con `ACK`.
- Finalmente el cliente envia su propio `FIN, ACK` para cerrar su lado de la conexion.
- El servidor responde con el ultimo `ACK` y la conexion queda cerrada.

La secuencia de cierre implementada corresponde a la opcion donde el servidor inicia el cierre despues de recibir un mensaje con `EXIT`:

```text
Servidor -> Cliente  FIN + ACK
Cliente  -> Servidor ACK
Cliente  -> Servidor FIN + ACK
Servidor -> Cliente  ACK
```

## Que es iptables y por que lo usamos

`iptables` es una herramienta de firewall de Linux. Permite crear reglas para aceptar, bloquear o modificar paquetes que entran o salen de la maquina.

No se usa para implementar el protocolo TCP. Se usa para evitar que el kernel de Linux interfiera con el laboratorio.

El problema existe porque este cliente no llama a `connect()`. El kernel no sabe que existe una conexion TCP real entre el puerto local del cliente y el puerto `5001` del servidor. Sin embargo, el kernel tambien ve los paquetes que llegan a la maquina.

Cuando el servidor responde con `SYN, ACK`, el kernel piensa:

```text
Yo no tengo ninguna conexion TCP registrada para este puerto local.
Este paquete SYN, ACK no pertenece a ninguna conexion conocida.
Debo responder con RST para rechazarlo.
```

Ese `RST` automatico puede romper la conexion en el servidor, aunque el programa raw socket si haya recibido el `SYN, ACK` y haya enviado su `ACK` manual.

Por eso puede aparecer este caso:

```text
Client -> Server [SYN]
Server -> Client [SYN, ACK]
Client -> Server [ACK]
Client -> Server [ACK, PSH] DATA="Hello world\n"
[!] Server response timeout
```

El log del cliente muestra el handshake, pero el servidor pudo haber recibido un `RST` automatico del kernel entre esos paquetes. Entonces ya no responde los datos.

Para evitar esto se bloquean solo los `RST` que salgan desde el puerto local usado por el cliente:

```bash
sudo iptables -A OUTPUT -p tcp --sport 45000 --tcp-flags RST RST -j DROP
```

Desglose del comando:

- `sudo`: requiere permisos de administrador.
- `iptables`: modifica reglas del firewall de Linux.
- `-A OUTPUT`: agrega una regla para paquetes salientes.
- `-p tcp`: aplica solo al protocolo TCP.
- `--sport 45000`: aplica solo a paquetes cuyo puerto origen sea `45000`.
- `--tcp-flags RST RST`: aplica a paquetes que tengan el flag `RST` activo.
- `-j DROP`: descarta el paquete.

Se agrego `-P 45000` al cliente para que el puerto local sea predecible. Si el puerto local fuera aleatorio, no sabriamos que puerto bloquear antes de iniciar el handshake.

Al terminar la prueba, se elimina la regla:

```bash
sudo iptables -D OUTPUT -p tcp --sport 45000 --tcp-flags RST RST -j DROP
```

## Como compilar

Compilar el cliente C:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05/ClientTCP
make clean
make
```

Compilar el servidor Java:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05
javac ServerTCP.java
```

## Como correr

Terminal 1, servidor:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05
java ServerTCP
```

Terminal 2, cliente interactivo en loopback:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05/ClientTCP
sudo iptables -A OUTPUT -p tcp --sport 45000 --tcp-flags RST RST -j DROP
sudo ./tcp_client -l 127.0.0.1 -s 127.0.0.1 -p 5001 -P 45000 -i lo
```

Enviar mensajes como:

```text
Hello World
Hola desde Guatemala
EXIT OFF
```

En Linux se usa `sudo` porque los raw sockets requieren privilegios de administrador. En macOS la interfaz de loopback normalmente es `lo0`, por ejemplo:

```bash
sudo ./tcp_client -l 127.0.0.1 -s 127.0.0.1 -p 5001 -i lo0
```

En Linux, despues de probar, quite la regla temporal de `iptables`:

```bash
sudo iptables -D OUTPUT -p tcp --sport 45000 --tcp-flags RST RST -j DROP
```

## Como probar con Wireshark

Si Wireshark esta instalado en Windows, este laboratorio incluye el script:

```bash
./open_wireshark_wsl.sh
```

Ese script crea un tunel por pipe entre WSL y Wireshark de Windows:

```text
tcpdump en WSL -> pipe stdin -> Wireshark.exe en Windows
```

Esto es necesario porque el trafico de `127.0.0.1` dentro de WSL2 ocurre en la red interna de Linux. Wireshark en Windows no siempre puede ver directamente la interfaz `lo` de WSL2. Por eso capturamos con `tcpdump` dentro de WSL y mandamos los paquetes en vivo a Wireshark de Windows.

Si `tcpdump` no esta instalado en WSL, instalarlo con:

```bash
sudo apt update
sudo apt install tcpdump
```

Para abrir Wireshark de Windows capturando el puerto `5001`:

```bash
cd /home/joserivera/CC8/CC8-Redes/Lab05
./open_wireshark_wsl.sh lo "tcp port 5001"
```

Luego, en otra terminal, ejecutar el servidor y el cliente.

Tambien se puede hacer manualmente sin el script:

```bash
sudo tcpdump -i lo -p -n -U -s 0 -w - "tcp port 5001" | "/mnt/c/Program Files/Wireshark/Wireshark.exe" -k -i -
```

### Pasos en Wireshark

1. Abrir Wireshark.
2. Capturar en la interfaz de loopback: `lo` en Linux o `lo0` en macOS.
3. Usar este filtro:

```text
tcp.port == 5001
```

4. Ejecutar el servidor Java.
5. Ejecutar el cliente con `sudo`.
6. Enviar al menos dos mensajes normales y luego `EXIT OFF`.
7. Verificar que se observe el three-way handshake, los segmentos con datos y el cierre TCP.

Una secuencia esperada es:

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

## Errores importantes

Si aparece un error de permisos al crear el raw socket, ejecutar el cliente con `sudo`.

Si se recibe `SYN, ACK` pero despues aparece `Server response timeout`, lo mas probable es que falte bloquear el `RST` automatico con `iptables` o que el cliente se haya ejecutado sin `-P 45000`.

Si no se recibe `SYN, ACK`, revisar que el servidor este corriendo en el puerto `5001`, que la IP destino sea correcta y que la interfaz indicada con `-i` sea la correcta.

Si Wireshark no muestra paquetes, revisar que se este capturando en la interfaz correcta y aplicar el filtro `tcp.port == 5001`.
