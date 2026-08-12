# Explicacion del Laboratorio 04 - Cliente NTP

Ciencias de la Computacion VIII  
Laboratorio: **Lab04 - NTP Client**  
Lenguaje usado: **C**  
Archivo principal: `ntp_client.c`

---

## 1. Que se hizo en este laboratorio

En este laboratorio se implemento un **cliente NTP manual**. El objetivo fue simular como una computadora puede sincronizar su reloj con servidores de tiempo confiables en internet.

El programa realiza lo siguiente:

1. Crea un paquete NTP de 48 bytes.
2. Llena manualmente los campos principales del paquete.
3. Envia solicitudes UDP al puerto `123`, que es el puerto usado por NTP.
4. Consulta al menos 7 servidores NTP.
5. Recibe respuestas de los servidores.
6. Extrae los timestamps enviados por el servidor.
7. Calcula:
   - `offset`, que indica cuanto debe corregirse el reloj del cliente.
   - `delay`, que indica cuanto tardo aproximadamente la comunicacion de ida y vuelta.
8. Escoge el servidor con menor delay.
9. Ajusta un reloj interno simulado.
10. Repite el proceso hasta que el offset sea suficientemente cercano a cero.

El reloj real del sistema operativo **no se modifica**. Se usa un reloj interno simulado para evitar problemas de permisos y para que el laboratorio sea seguro de ejecutar.

---

## 2. Que es NTP - Explicacion profesional

**NTP**, o **Network Time Protocol**, es un protocolo de red utilizado para sincronizar los relojes de computadoras, servidores, routers y otros dispositivos a traves de una red IP.

NTP opera normalmente sobre **UDP puerto 123** y permite que un cliente consulte uno o varios servidores de tiempo para estimar la diferencia entre su reloj local y una fuente de tiempo confiable.

El protocolo usa timestamps para calcular dos valores importantes:

```text
offset = diferencia estimada entre el reloj del cliente y el reloj del servidor

delay = tiempo estimado de ida y vuelta entre cliente y servidor
```

En una comunicacion NTP basica intervienen cuatro tiempos:

```text
T1 = momento en que el cliente envia la solicitud
T2 = momento en que el servidor recibe la solicitud
T3 = momento en que el servidor envia la respuesta
T4 = momento en que el cliente recibe la respuesta
```

Con esos cuatro tiempos se calculan:

```text
offset = ((T2 - T1) + (T3 - T4)) / 2

delay = (T4 - T1) - (T3 - T2)
```

El **offset** sirve para saber cuanto debe corregirse el reloj local. El **delay** sirve para estimar que tan confiable o rapida fue la respuesta del servidor. Si se consulta a varios servidores, normalmente se prefiere el que tenga menor delay porque su respuesta probablemente tiene menor error de red.

NTP es importante porque muchos sistemas dependen de una hora correcta:

- Logs de servidores.
- Certificados SSL/TLS.
- Bases de datos distribuidas.
- Autenticacion.
- Sistemas bancarios.
- Sistemas de monitoreo.
- Protocolos de seguridad.
- Orden correcto de eventos en redes.

---

## 3. Que es NTP - Explicacion como para un nino de 5 anios

Imagina que tienes un reloj de juguete, pero no sabes si tiene la hora correcta.

Entonces le preguntas a varios relojes grandes que si saben la hora correcta:

> "Hola reloj grande, que hora es?"

El reloj grande te responde:

> "Son las 3:00."

Pero como el mensaje tarda un poquito en ir y regresar, tu programa calcula cuanto se tardo el mensaje. Asi puede adivinar mejor la hora verdadera.

Si le preguntas a muchos relojes grandes, escoges el que respondio mas rapido, porque probablemente te dio la mejor respuesta.

Entonces arreglas tu reloj de juguete para que marque la misma hora que el reloj grande.

Eso es NTP: una forma de que las computadoras pregunten la hora correcta y arreglen su reloj.

---

## 4. Como funciona el flujo del laboratorio

El flujo del laboratorio es este:

```text
Inicio
  |
  v
Leer configuracion
  |
  v
Crear reloj interno simulado
  |
  v
Preparar lista de 7 servidores NTP
  |
  v
Por cada iteracion:
  |
  +--> Crear paquete NTP de 48 bytes
  |
  +--> Guardar T1 antes de enviar
  |
  +--> Enviar paquete UDP a cada servidor
  |
  +--> Esperar respuestas con select()
  |
  +--> Al recibir respuesta, guardar T4
  |
  +--> Extraer T2 y T3 del paquete recibido
  |
  +--> Calcular delay y offset
  |
  +--> Elegir servidor con menor delay
  |
  +--> Ajustar reloj interno usando offset
  |
  +--> Revisar si offset <= umbral
  |
  v
Si esta sincronizado, terminar
Si no, esperar intervalo y repetir
```

---

## 5. Archivos creados

### `ntp_client.c`

Es el archivo principal. Contiene toda la implementacion del cliente NTP.

Se encarga de:

- Parsear argumentos de consola.
- Convertir fecha Guatemala a UTC.
- Crear paquetes NTP.
- Enviar paquetes UDP.
- Recibir respuestas.
- Convertir timestamps NTP a tiempo Unix.
- Calcular offset y delay.
- Escoger el mejor servidor.
- Ajustar el reloj interno simulado.
- Mostrar logs claros.

### `Makefile`

Sirve para compilar y ejecutar facilmente.

Comandos principales:

```bash
make
make run
make test
make demo-old-date
make clean
```

### `README.md`

Explica como compilar, ejecutar, probar y presentar el laboratorio.

### `EXPLICACION_LAB04_NTP.md`

Este documento. Sirve para entender que se hizo, como se hizo y prepararte para preguntas del catedratico.

---

## 6. Partes importantes del codigo

### 6.1 Constantes principales

```c
#define NTP_PACKET_SIZE 48
#define NTP_PORT "123"
#define NTP_UNIX_EPOCH_DELTA 2208988800ULL
```

Estas constantes significan:

- `NTP_PACKET_SIZE 48`: un paquete NTP basico mide 48 bytes.
- `NTP_PORT "123"`: NTP usa UDP puerto 123.
- `NTP_UNIX_EPOCH_DELTA`: diferencia en segundos entre 1900 y 1970.

NTP cuenta el tiempo desde 1900. Unix cuenta el tiempo desde 1970. Por eso se necesita sumar o restar `2208988800` segundos.

---

### 6.2 Servidores NTP por defecto

```c
static const char *DEFAULT_SERVERS[] = {
    "time.google.com",
    "time.apple.com",
    "time.windows.com",
    "time.cloudflare.com",
    "time.nist.gov",
    "time-a.nist.gov",
    "pool.ntp.org"
};
```

El laboratorio pide conectarse como minimo a 7 servidores. Por eso el programa trae 7 servidores configurados por defecto.

---

### 6.3 Conversion entre Unix Time y NTP Time

Unix Time cuenta segundos desde:

```text
1970-01-01 00:00:00 UTC
```

NTP Time cuenta segundos desde:

```text
1900-01-01 00:00:00 UTC
```

Por eso existe una diferencia:

```text
2208988800 segundos
```

Cuando se quiere convertir de Unix a NTP:

```text
ntp_time = unix_time + 2208988800
```

Cuando se quiere convertir de NTP a Unix:

```text
unix_time = ntp_time - 2208988800
```

Ademas, NTP usa 64 bits para un timestamp:

```text
32 bits para segundos
32 bits para fraccion de segundo
```

La fraccion permite representar milisegundos o incluso mas precision.

---

### 6.4 Construccion del paquete NTP

El paquete NTP tiene 48 bytes. En el codigo se crea asi:

```c
unsigned char packet[NTP_PACKET_SIZE];
memset(packet, 0, NTP_PACKET_SIZE);
```

Luego se llena el primer byte:

```c
packet[0] = 0x23;
```

Ese `0x23` significa:

```text
LI = 0
VN = 4
Mode = 3
```

Donde:

- `LI`: Leap Indicator. Indica ajustes especiales de segundos. Aqui va 0.
- `VN`: Version Number. Se uso version 4.
- `Mode`: modo de operacion. 3 significa cliente.

En binario:

```text
0x23 = 00100011

LI   = 00
VN   = 100
Mode = 011
```

---

### 6.5 Campo Transmit Timestamp

Antes de enviar el paquete, el cliente escribe su tiempo `T1` en el campo **Transmit Timestamp**:

```c
unix_to_ntp_bytes(t1_unix, packet + 40);
```

El offset `packet + 40` se usa porque en un paquete NTP el campo Transmit Timestamp empieza en el byte 40.

Cuando el servidor responde, copia ese tiempo del cliente como **Originate Timestamp** y agrega sus propios tiempos:

```text
T2 = Receive Timestamp del servidor
T3 = Transmit Timestamp del servidor
```

---

### 6.6 Envio UDP a multiples servidores

El programa usa sockets UDP:

```c
socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol)
```

Y envia el paquete con:

```c
send(q->sockfd, packet, sizeof(packet), 0)
```

Cada servidor tiene su propio socket. Asi el programa puede enviar solicitudes a varios servidores y esperar respuestas de todos.

---

### 6.7 Uso de `select()`

Para no quedarse esperando servidor por servidor, se usa:

```c
select(maxfd + 1, &readfds, NULL, NULL, &tv)
```

`select()` permite esperar respuestas de varios sockets al mismo tiempo.

Esto cumple mejor el requisito de consultar varios servidores, porque el programa no pregunta uno por uno de forma lenta, sino que manda solicitudes y espera respuestas dentro de un timeout.

---

### 6.8 Calculo de T1, T2, T3 y T4

El programa maneja los tiempos asi:

```text
T1 = reloj interno del cliente al enviar
T2 = timestamp del servidor cuando recibe
T3 = timestamp del servidor cuando responde
T4 = reloj interno del cliente al recibir
```

T2 y T3 vienen dentro del paquete de respuesta NTP.

En el codigo:

```c
q->t2 = ntp_to_unix_from_bytes(packet + 32);
q->t3 = ntp_to_unix_from_bytes(packet + 40);
```

- `packet + 32`: Receive Timestamp, o sea T2.
- `packet + 40`: Transmit Timestamp, o sea T3.

---

### 6.9 Calculo de delay y offset

El codigo calcula:

```c
q->delay = (q->t4 - q->t1) - (q->t3 - q->t2);
q->offset = ((q->t2 - q->t1) + (q->t3 - q->t4)) / 2.0;
```

En forma conceptual:

```text
delay = cuanto tardo el viaje de ida y vuelta, descontando el tiempo que el servidor tardo procesando.

offset = cuanto debe moverse el reloj del cliente para parecerse al reloj del servidor.
```

Si el offset es positivo, significa que el reloj interno del cliente esta atrasado y debe adelantarse.

Si el offset es negativo, significa que el reloj interno del cliente esta adelantado y debe atrasarse.

---

### 6.10 Seleccion del mejor servidor

El programa compara los delays de los servidores que respondieron:

```c
if (best < 0 || fabs(q->delay) < fabs(best_delay)) {
    best = i;
    best_delay = q->delay;
}
```

Se escoge el servidor con menor delay absoluto porque la respuesta con menor delay usualmente tiene menor error por latencia de red.

---

### 6.11 Ajuste del reloj interno

El ajuste se hace sobre una variable interna:

```c
internal_clock = b->t4 + b->offset;
```

Esto significa:

```text
nueva hora interna = hora local al recibir respuesta + correccion calculada
```

No se cambia la hora real de Linux/Windows. Esto es intencional porque cambiar la hora del sistema requiere permisos de administrador y podria afectar otros programas.

---

## 7. Como correr el laboratorio

Entrar al directorio:

```bash
cd ~/CC8/CC8-Redes/Lab04
```

Compilar:

```bash
make clean
make
```

Ejecutar prueba rapida:

```bash
make test
```

Ejecutar con fecha configurable:

```bash
./ntp_client --date '2020-09-01 21:00:17.123' --threshold-ms 500 --interval 1 --max-iterations 3
```

Ejecutar con umbral mas estricto:

```bash
./ntp_client --threshold-ms 50 --interval 2 --max-iterations 10
```

---

## 8. Que deberias explicar en tu video

Puedes explicar el flujo asi:

> Mi laboratorio implementa un cliente NTP en C. Primero crea un reloj interno configurable. Luego construye manualmente un paquete NTP de 48 bytes. En el primer byte coloca version 4 y modo cliente. Antes de enviar el paquete guarda T1 en el campo Transmit Timestamp. Despues envia solicitudes UDP al puerto 123 de 7 servidores NTP. Cuando recibe respuestas, extrae T2 y T3 del paquete, captura T4 localmente y calcula delay y offset. Luego selecciona el servidor con menor delay y usa su offset para ajustar el reloj interno simulado. El proceso se repite hasta que el offset queda bajo el umbral configurado.

---

## 9. Preguntas posibles del catedratico - de facil a dificil

A continuacion tienes **20 preguntas** posibles, ordenadas de facil a dificil. Incluyo una respuesta sugerida para que puedas practicar.

### Facil

1. **Que es NTP?**  
   Es el Network Time Protocol, un protocolo que permite sincronizar la hora de una computadora con servidores de tiempo en la red.

2. **Que puerto usa NTP?**  
   Usa UDP puerto `123`.

3. **Por que NTP usa UDP y no TCP?**  
   Porque necesita mensajes pequenos y rapidos. UDP evita el overhead de establecer conexion como en TCP.

4. **Cuanto mide un paquete NTP basico?**  
   Mide 48 bytes.

5. **Que significa que el laboratorio use un reloj interno simulado?**  
   Significa que el programa corrige una variable interna de tiempo, no la hora real del sistema operativo.

6. **Por que no cambiamos la hora real del sistema operativo?**  
   Porque requiere permisos de administrador y podria afectar otros programas. Para el laboratorio basta con simular la sincronizacion.

7. **Que servidores NTP usa el laboratorio?**  
   Usa servidores como `time.google.com`, `time.apple.com`, `time.windows.com`, `time.cloudflare.com`, `time.nist.gov`, `time-a.nist.gov` y `pool.ntp.org`.

### Intermedio

8. **Que significan T1, T2, T3 y T4?**  
   `T1` es cuando el cliente envia, `T2` cuando el servidor recibe, `T3` cuando el servidor responde y `T4` cuando el cliente recibe.

9. **Cual es la formula del offset?**

```text
offset = ((T2 - T1) + (T3 - T4)) / 2
```

10. **Cual es la formula del delay?**

```text
delay = (T4 - T1) - (T3 - T2)
```

11. **Que representa el offset?**  
    Representa cuanto debe corregirse el reloj del cliente para acercarse al reloj del servidor.

12. **Que representa el delay?**  
    Representa el tiempo estimado de ida y vuelta entre el cliente y el servidor, descontando el tiempo de procesamiento del servidor.

13. **Por que se consulta a varios servidores NTP?**  
    Para comparar respuestas y elegir la que probablemente tiene menor error. El laboratorio escoge el servidor con menor delay.

14. **Que es el stratum en NTP?**  
    Es el nivel de distancia de un servidor respecto a una fuente de tiempo primaria. Un stratum 1 esta muy cerca de una fuente confiable; stratum 2 obtiene tiempo de un stratum 1, y asi sucesivamente.

15. **Que contiene el primer byte del paquete NTP?**  
    Contiene `LI`, `VN` y `Mode`: Leap Indicator, Version Number y modo de operacion. En el laboratorio se usa `0x23`, que significa version 4 y modo cliente.

### Dificil

16. **Por que se necesita convertir entre Unix Epoch y NTP Epoch?**  
    Porque Unix cuenta segundos desde 1970 y NTP desde 1900. Hay una diferencia de `2208988800` segundos.

17. **Como representa NTP sus timestamps?**  
    Usa 64 bits: 32 bits para segundos y 32 bits para la fraccion del segundo.

18. **Por que se usa `select()` en el laboratorio?**  
    Para esperar respuestas de varios sockets UDP al mismo tiempo sin bloquearse con un solo servidor.

19. **Que pasa si un servidor NTP no responde?**  
    El programa marca timeout para ese servidor y continua usando las respuestas de los otros servidores.

20. **Describa el flujo completo de su laboratorio.**  
    El programa inicia leyendo configuracion, crea un reloj interno, construye paquetes NTP, envia solicitudes UDP a 7 servidores, captura T1 y T4 localmente, extrae T2 y T3 de las respuestas, calcula offset y delay, selecciona el menor delay, ajusta el reloj interno y repite hasta cumplir el umbral de sincronizacion.

---

## 10. Respuestas cortas tipo examen

### Que contiene el paquete NTP?

Contiene campos de control como LI, Version, Mode, Stratum, Poll, Precision y varios timestamps: Reference, Originate, Receive y Transmit Timestamp.

### Por que es importante T1?

Porque permite saber en que momento salio la solicitud desde el cliente. Sin T1 no se puede calcular correctamente el delay ni el offset.

### Por que es importante T4?

Porque permite saber en que momento regreso la respuesta al cliente. Es necesario para calcular el tiempo total de ida y vuelta.

### Que se implemento para escoger mejor servidor?

Se implemento consulta a multiples servidores y seleccion por menor delay.

### Que ocasiona escoger el menor delay?

Reduce la incertidumbre causada por la red y mejora la calidad de la sincronizacion estimada.

### Describa el flujo de su laboratorio

El laboratorio crea un reloj interno, arma un paquete NTP de 48 bytes, envia solicitudes UDP a 7 servidores, captura T1 y T4, extrae T2 y T3, calcula offset y delay, escoge el servidor con menor delay, ajusta el reloj interno y repite hasta estar sincronizado.

---

## 11. Comandos finales recomendados

Compilar:

```bash
cd ~/CC8/CC8-Redes/Lab04
make clean
make
```

Prueba rapida:

```bash
make test
```

Prueba con fecha configurable:

```bash
./ntp_client --date '2020-09-01 21:00:17.123' --threshold-ms 500 --interval 1 --max-iterations 3
```

Prueba mas estricta:

```bash
./ntp_client --threshold-ms 50 --interval 2 --max-iterations 10
```

---

## 12. Idea clave para recordar

La idea central del laboratorio es esta:

> NTP no solo pregunta que hora es. NTP calcula cuanto tardo la pregunta y la respuesta para estimar cuanto debe corregirse el reloj del cliente.

Esa es la diferencia entre simplemente pedir la hora y realmente sincronizar un reloj por red.
