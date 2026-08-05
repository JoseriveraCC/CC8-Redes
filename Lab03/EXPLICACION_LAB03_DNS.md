# Explicacion Lab03 - Servidor DNS en Java sobre UDP

## Objetivo Del Laboratorio

El objetivo del Lab03 es implementar un servidor DNS usando UDP. El servidor debe escuchar consultas DNS, interpretar el paquete recibido, construir respuestas validas y usar multithreading para poder atender varias solicitudes.

En esta implementacion se hizo en Java usando:

- `DatagramSocket` para comunicacion UDP.
- `ExecutorService` con `FixedThreadPool` para multithreading.
- Parser manual del formato DNS.
- Respuestas locales para registros `A`, `AAAA`, `PTR` y `SOA`.
- Reenvio recursivo a DNS publicos para dominios externos.

## Archivos Usados

- `DnsServer.java`: implementacion principal del servidor DNS.
- `Makefile`: comandos para compilar y ejecutar el servidor.
- `README.md`: documentacion de uso y pruebas.

El archivo principal agregado fue:

```text
Lab03/DnsServer.java
```

## Como Ejecutar

Para probar sin permisos de administrador se usa el puerto `5353`:

```bash
cd Lab03
make rundns ARGS="-port 5353 -threads 4"
```

Para ejecutar en el puerto oficial DNS `53`:

```bash
cd Lab03
make rundns53
```

El puerto `53` normalmente requiere permisos de administrador. En WSL puede estar ocupado por `systemd-resolved`, por eso para pruebas locales usamos `5353`.

## Estructura General Del Servidor

El servidor inicia leyendo argumentos como `-port` y `-threads`:

```java
Map<String, String> options = parseArgs(args);
int port = parseInt(options.get("-port"), DEFAULT_PORT);
int threads = parseInt(options.get("-threads"), DEFAULT_THREADS);
```

Los valores por defecto son:

```java
private static final int DEFAULT_PORT = 53;
private static final int DEFAULT_THREADS = 4;
```

Esto significa que si no se pasan argumentos, intenta escuchar en `UDP:53` con 4 hilos.

## Uso De DatagramSocket

DNS usa UDP normalmente. Por eso se crea un socket UDP con `DatagramSocket`:

```java
try (DatagramSocket socket = new DatagramSocket(port)) {
    System.out.printf("DNS server listening on UDP:%d with %d threads%n", port, threads);
    while (true) {
        byte[] buffer = new byte[MAX_DNS_PACKET];
        DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
        socket.receive(packet);
```

Esta parte hace que el servidor quede esperando paquetes UDP. Cuando llega una consulta DNS, `socket.receive(packet)` recibe el paquete.

Luego se copia el contenido real del paquete:

```java
byte[] request = Arrays.copyOfRange(packet.getData(), packet.getOffset(),
        packet.getOffset() + packet.getLength());
```

Esto es importante porque el buffer puede ser mas grande que el mensaje DNS real.

## Uso De Multithreading Con ThreadPool

Para atender varias consultas, se usa un pool de hilos:

```java
ExecutorService pool = Executors.newFixedThreadPool(threads);
```

Cada paquete recibido se manda a un hilo del pool:

```java
pool.execute(() -> handleRequest(socket, request, client));
```

Esto cumple el requisito de usar multithreading con ThreadPool. La idea es parecida al Lab02, pero adaptada a UDP en lugar de TCP/HTTP.

## Flujo Principal De Una Consulta

Cuando llega una consulta, el metodo principal que la procesa es:

```java
private static void handleRequest(DatagramSocket serverSocket, byte[] request, InetSocketAddress client)
```

El flujo es:

1. Leer el ID DNS del paquete.
2. Parsear la consulta DNS.
3. Registrar el request en logs.
4. Intentar responder localmente.
5. Si no es dominio local, reenviar a DNS publico.
6. Enviar la respuesta al cliente.
7. Registrar el response en logs.

Snippet principal:

```java
DnsMessage message = parseRequest(request);
log(">", client.getAddress().getHostAddress(), client.getPort(), id, summarize(message.questions));

byte[] response = buildLocalResponse(message, request);
if (response == null) {
    response = forwardToUpstream(request);
}

if (response == null) {
    response = buildErrorResponse(request, RCODE_SERVER_FAILURE);
}

sendResponse(serverSocket, response, client);
log("<", client.getAddress().getHostAddress(), client.getPort(), id,
        response.length + " bytes");
```

## Como Se Lee Un Paquete DNS

Un paquete DNS inicia con un header de 12 bytes. En ese header vienen datos como:

- ID de la consulta.
- Flags.
- Cantidad de preguntas.
- Cantidad de respuestas.
- Cantidad de registros de autoridad.
- Cantidad de registros adicionales.

En el codigo se leen estos campos asi:

```java
message.id = readUnsignedShort(packet, 0);
message.flags = readUnsignedShort(packet, 2);
int questionCount = readUnsignedShort(packet, 4);
int offset = 12;
```

Despues del header vienen las preguntas DNS. Cada pregunta contiene:

- Nombre del dominio.
- Tipo de registro, por ejemplo `A`, `AAAA`, `PTR`, `SOA`.
- Clase, normalmente `IN` para internet.

Snippet:

```java
NameResult name = readName(packet, offset);
offset = name.nextOffset;

DnsQuestion question = new DnsQuestion();
question.name = normalizeName(name.name);
question.type = readUnsignedShort(packet, offset);
question.qclass = readUnsignedShort(packet, offset + 2);
```

## Como Se Lee El Nombre Del Dominio

En DNS, un dominio como `lab.local` no viene como texto normal. Viene por etiquetas:

```text
3 lab 5 local 0
```

El metodo que interpreta eso es:

```java
private static NameResult readName(byte[] packet, int startOffset) throws DnsFormatException
```

Parte importante:

```java
int length = packet[offset] & 0xff;

if (length == 0) {
    offset++;
    break;
} else {
    offset++;
    if (name.length() > 0) {
        name.append('.');
    }
    name.append(new String(packet, offset, length, StandardCharsets.US_ASCII));
    offset += length;
}
```

Tambien soporta compresion DNS usando punteros, que aparecen cuando los dos bits superiores del byte estan activos:

```java
if ((length & 0xc0) == 0xc0) {
    offset = ((length & 0x3f) << 8) | (packet[offset + 1] & 0xff);
}
```

Esto es importante porque muchas respuestas DNS reales usan compresion de nombres.

## Registros Locales Implementados

El servidor tiene registros locales definidos en mapas:

```java
private static final Map<String, String> A_RECORDS = new HashMap<>();
private static final Map<String, String> AAAA_RECORDS = new HashMap<>();
private static final Map<String, String> PTR_RECORDS = new HashMap<>();
```

Registros `A`, IPv4:

```java
A_RECORDS.put("lab.local", "127.0.0.1");
A_RECORDS.put("www.lab.local", "127.0.0.1");
A_RECORDS.put("ns.lab.local", "127.0.0.1");
A_RECORDS.put("server.lab.local", "192.168.1.53");
```

Registros `AAAA`, IPv6:

```java
AAAA_RECORDS.put("lab.local", "::1");
AAAA_RECORDS.put("www.lab.local", "::1");
AAAA_RECORDS.put("ns.lab.local", "::1");
AAAA_RECORDS.put("server.lab.local", "fd00::53");
```

Registros `PTR`, resolucion inversa:

```java
PTR_RECORDS.put("1.0.0.127.in-addr.arpa", "localhost");
PTR_RECORDS.put("53.1.168.192.in-addr.arpa", "server.lab.local");
```

Tambien se implementa `SOA` para la zona `lab.local`.

## Como Se Decide Si Responder Localmente

El metodo `localRecordsFor` busca si la consulta coincide con algun registro local:

```java
if (question.type == TYPE_A && A_RECORDS.containsKey(question.name)) {
    records.add(new ResourceRecord(question.name, TYPE_A,
            InetAddress.getByName(A_RECORDS.get(question.name)).getAddress()));
} else if (question.type == TYPE_AAAA && AAAA_RECORDS.containsKey(question.name)) {
    records.add(new ResourceRecord(question.name, TYPE_AAAA,
            InetAddress.getByName(AAAA_RECORDS.get(question.name)).getAddress()));
} else if (question.type == TYPE_PTR && PTR_RECORDS.containsKey(question.name)) {
    records.add(new ResourceRecord(question.name, TYPE_PTR, encodeName(PTR_RECORDS.get(question.name))));
} else if (question.type == TYPE_SOA && isLocalDomain(question.name)) {
    records.add(new ResourceRecord(question.name, TYPE_SOA, encodeSoaRecord()));
}
```

Si el dominio es local pero no existe, el servidor responde `NXDOMAIN`:

```java
int rcode = answers.isEmpty() ? RCODE_NAME_ERROR : 0;
```

`RCODE_NAME_ERROR` equivale a `3`, que en DNS significa que el dominio no existe.

## Como Se Construye Una Respuesta DNS

La respuesta DNS mantiene el mismo ID de la consulta. Esto es importante porque el cliente usa ese ID para saber que respuesta corresponde a su pregunta.

```java
writeShort(out, message.id);
writeShort(out, responseFlags(message.flags, rcode));
writeShort(out, message.questions.size());
writeShort(out, answers.size());
writeShort(out, 0);
writeShort(out, 0);
```

Luego se copia la pregunta original:

```java
out.write(request, 12, message.questionEndOffset - 12);
```

Despues se agregan las respuestas:

```java
for (ResourceRecord answer : answers) {
    writeName(out, answer.name);
    writeShort(out, answer.type);
    writeShort(out, CLASS_IN);
    writeInt(out, TTL_SECONDS);
    writeShort(out, answer.data.length);
    out.write(answer.data);
}
```

Cada respuesta contiene:

- Nombre del dominio.
- Tipo de registro.
- Clase `IN`.
- TTL.
- Longitud de datos.
- Datos del registro.

## Recursividad Con DNS Publicos

Si el dominio no es local, el servidor reenvia la consulta original a DNS publicos:

```java
private static final String[] UPSTREAM_DNS = {"1.1.1.1", "8.8.8.8"};
```

El metodo encargado es:

```java
private static byte[] forwardToUpstream(byte[] request)
```

Snippet:

```java
DatagramPacket query = new DatagramPacket(request, request.length, address, 53);
socket.send(query);

byte[] buffer = new byte[MAX_DNS_PACKET];
DatagramPacket response = new DatagramPacket(buffer, buffer.length);
socket.receive(response);
```

Esto permite que una consulta como `example.com A` sea respondida aunque no exista en los registros locales.

## Logs Del Servidor

El servidor imprime logs en consola. Ejemplo:

```text
DNS server listening on UDP:5353 with 4 threads
> 127.0.0.1:48692 [2026/07/28 12:48:50] DNS id=852 lab.local A
< 127.0.0.1:48692 [2026/07/28 12:48:50] DNS id=852 52 bytes
```

Significado:

- `>`: request recibido.
- `<`: response enviado.
- `127.0.0.1:48692`: IP y puerto del cliente.
- `DNS id=852`: identificador DNS de la consulta.
- `lab.local A`: dominio y tipo de registro consultado.
- `52 bytes`: tamano de la respuesta enviada.

## Pruebas Con dig

Primero ejecutar el servidor:

```bash
make rundns ARGS="-port 5353 -threads 4"
```

En otra terminal probar:

```bash
dig @127.0.0.1 -p 5353 lab.local A
dig @127.0.0.1 -p 5353 lab.local AAAA
dig @127.0.0.1 -p 5353 lab.local SOA
dig @127.0.0.1 -p 5353 53.1.168.192.in-addr.arpa PTR
dig @127.0.0.1 -p 5353 example.com A
dig @127.0.0.1 -p 5353 no-existe.lab.local A
```

Resultados esperados:

```text
lab.local A                 -> NOERROR, 1 answer, 127.0.0.1
lab.local AAAA              -> NOERROR, 1 answer, ::1
lab.local SOA               -> NOERROR, 1 answer, ns.lab.local
53.1.168.192.in-addr.arpa   -> NOERROR, 1 answer, server.lab.local
example.com A               -> NOERROR, answers desde DNS publico
no-existe.lab.local A       -> NXDOMAIN, 0 answers
```

## Ejemplo De Salida Real Con dig

Consulta `A`:

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR
;; flags: qr rd ra; QUERY: 1, ANSWER: 1

;; ANSWER SECTION:
lab.local.        300    IN    A    127.0.0.1
```

Consulta `AAAA`:

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR
;; flags: qr rd ra; QUERY: 1, ANSWER: 1

;; ANSWER SECTION:
lab.local.        300    IN    AAAA    ::1
```

Consulta `PTR`:

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR
;; flags: qr rd ra; QUERY: 1, ANSWER: 1

;; ANSWER SECTION:
53.1.168.192.in-addr.arpa. 300 IN PTR server.lab.local.
```

Consulta recursiva:

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR
;; flags: qr rd ra; QUERY: 1, ANSWER: 2

;; ANSWER SECTION:
example.com.    112    IN    A    104.20.23.154
example.com.    112    IN    A    172.66.147.243
```

Dominio inexistente:

```text
;; ->>HEADER<<- opcode: QUERY, status: NXDOMAIN
;; flags: qr rd ra; QUERY: 1, ANSWER: 0
```

## Nota Sobre .local

Al usar `lab.local`, `dig` puede mostrar esta advertencia:

```text
WARNING: .local is reserved for Multicast DNS
```

No significa que el servidor este mal. `.local` normalmente se usa para mDNS, pero en este laboratorio se consulta directamente al servidor con:

```bash
dig @127.0.0.1 -p 5353 lab.local A
```

Como se especifica el servidor y el puerto, la consulta llega correctamente a nuestro DNS.

## Que Se Puede Explicar En La Presentacion

Puntos clave para presentar:

- El servidor DNS esta implementado en Java.
- Usa UDP porque DNS normalmente trabaja sobre UDP.
- Usa `DatagramSocket`, igual que la parte UDP del Lab01.
- Usa `ExecutorService` y `FixedThreadPool`, siguiendo la idea de ThreadPool del Lab02.
- Lee manualmente el header DNS y las preguntas.
- Construye respuestas DNS binarias validas.
- Implementa cuatro tipos de registros: `A`, `AAAA`, `PTR` y `SOA`.
- Si la consulta no es local, reenvia a DNS publicos para hacer recursividad.
- Fue probado con `dig` en puerto `5353` por restricciones de permisos/WSL.
- El puerto real del protocolo DNS es `53`, y el servidor lo usa por defecto.

## Limitaciones Actuales

- No guarda logs en archivo, solo en consola.
- No implementa cache de respuestas recursivas.
- No implementa todos los tipos DNS posibles, solo los necesarios para cumplir mas de 3 tipos.
- Las respuestas locales estan hardcodeadas en mapas dentro de `DnsServer.java`.

Estas limitaciones son aceptables para una implementacion de laboratorio porque el objetivo principal es entender UDP, DNS, parsing de paquetes y multithreading.
