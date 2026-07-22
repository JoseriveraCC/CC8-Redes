# Laboratorio #01 - Sockets TCP y UDP

Aplicación cliente/servidor en Java 21 que procesa operaciones matemáticas básicas mediante TCP o UDP.

## Archivos requeridos

- `Client.java`
- `Server.java`

## Valores por defecto

- Protocolo: `TCP`
- Servidor: `127.0.0.1`
- Puerto: `3001`

Los argumentos usan el formato `KEY VALUE` y pueden escribirse en cualquier orden.

## Compilación

```bash
javac Client.java Server.java
```

## Prueba TCP

Terminal 1:

```bash
java Server protocol TCP port 5030
```

Terminal 2:

```bash
java Client port 5030 server 127.0.0.1 protocol TCP
```

## Prueba UDP

Terminal 1:

```bash
java Server port 3001 protocol UDP
```

Terminal 2:

```bash
java Client protocol UDP server 127.0.0.1 port 3001
```

## Operaciones aceptadas

- Suma: `2+3`
- Resta: `5-2`
- Multiplicación: `4*7`
- División: `8/2`
- Módulo: `8%5`
- Números negativos: `-5+2`
- Decimales: `2.5*4`

Para finalizar el cliente y el servidor, escriba:

```text
EXIT
```

## Formato del log

```text
[s] host socketType [yyyy/MM/dd HH:mm:ss] protocol: description
```

Ejemplo:

```text
< 127.0.0.1 client [2026/07/21 13:30:00] TCP: 8%5
> 127.0.0.1 server [2026/07/21 13:30:00] TCP: 3
```
