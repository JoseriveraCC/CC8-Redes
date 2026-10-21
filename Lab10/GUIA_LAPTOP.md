# Lab10: guía para preparar la laptop, ejecutar y entender la práctica

Esta guía acompaña a `lab10.py` y al informe de Ciencias de la Computación VIII.
Los comandos de captura se refieren exclusivamente al router WEP que indique el
docente. Puedes practicar la recuperación de la muestra incluida sin router,
sin otras personas y sin transmitir paquetes.

## Ruta actual: Arch Linux nativo

La ejecución en clase se hará en la laptop del compañero con Arch instalado
directamente. **No hay que modificar `lab10.py` para cambiar de Ubuntu a Arch.**
El script utiliza la biblioteca estándar de Python, `/sys/class/net` de Linux
y ejecutables que busca en `PATH`; no fija rutas propias de Ubuntu. El paquete
oficial de Arch conserva los nombres `airmon-ng`, `airodump-ng`, `aireplay-ng` y
`aircrack-ng`, y `python` incluye el ejecutable `python3`.
[Arch: suite](https://archlinux.org/packages/extra/x86_64/aircrack-ng/files/),
[Arch: Python](https://archlinux.org/packages/core/x86_64/python/files/).

Linux nativo permite que su controlador acceda a la tarjeta física, sin el
paso de compartirla desde Windows. Es una opción adecuada para esta práctica,
pero todavía depende de que **la tarjeta de esa laptop** soporte monitor. No
asumas que es la misma MediaTek identificada en otra computadora. La inyección,
si se autoriza y se necesita, requiere una comprobación adicional.

### A. Instalar en Arch, antes de clase

En una terminal de **Arch Linux**:

```bash
sudo pacman -Syu --needed aircrack-ng iw python pciutils
```

`-Syu` actualiza el sistema completo además de instalar los paquetes: coordina
esa actualización con el dueño de la laptop y hazla antes de la evaluación.
`--needed` evita reinstalar versiones que ya están al día. No uses los comandos
`apt` de la sección de Ubuntu en Arch. No necesitas AUR, Kali, WSL, una VM ni
paquetes de `pip` para este código.
[Paquete oficial de Aircrack-ng](https://archlinux.org/packages/extra/x86_64/aircrack-ng/).

### B. Copiar el proyecto y comprobar el equipo

Copia la carpeta completa `Lab10`, incluida la muestra `muestras/ptw.cap`.
Entra al directorio real donde quedó, por ejemplo:

```bash
# Sustituye esta ruta por la ubicación real de la carpeta en Arch.
cd "/ruta/real/Lab10"
python3 --version
python3 lab10.py comprobar
lspci -nnk
iw dev
iw list
sudo airmon-ng
```

`lspci -nnk` identifica tarjetas PCI/PCIe y sus controladores; para un adaptador
USB usa `lsusb`, incluido como dependencia de la suite. En `iw dev` busca la
interfaz Wi-Fi real, que puede llamarse `wlan0`, `wlp2s0` u otra cosa. En
`iw list`, revisa que `Supported interface modes` contenga `monitor`.
Que aparezca ese modo es el primer requisito; después hay que activarlo y
comprobar recepción. No cambies el código para forzar un nombre de interfaz.

### C. Ensayo offline, sin radio ni privilegios

```bash
sha256sum -c evidencias/muestra.sha256
python3 -m unittest -v test_lab10.py
aircrack-ng -a 1 -b 00:12:BF:12:32:29 muestras/ptw.cap
```

Deben pasar las cinco pruebas sin omisiones por falta de Aircrack-ng, y la
muestra debe devolver `1F:1F:1F:1F:1F`. Esta es la comprobación que se debe
repetir en Arch; el ensayo previo del proyecto se hizo en otro entorno Linux.

### D. Ejecución en clase

Continúa con las secciones **6 a 14**: explicación, ensayo, captura dirigida,
recuperación, restauración y evidencia. Sus comandos Linux son los mismos en
Arch; introduce la interfaz real, BSSID y canal autorizados. Las secciones de
Windows/WSL y la instalación con `apt` quedan como alternativas de consulta.

Si la única tarjeta también proporciona Internet, ponerla en monitor puede
interrumpir la conexión habitual de esa laptop. Lleva los archivos y paquetes
preparados. Si un gestor cambia el canal, revisa `sudo airmon-ng check`; no
mates todos los servicios de red automáticamente. Tras la prueba, detén
monitor con `sudo airmon-ng stop "$MON"` en la terminal que conserva esa
variable y restaura cualquier cambio manual de gestión que hayas hecho.

## 1. Lo primero: ¿sirve la laptop con su Wi-Fi integrado y WSL2?

**No lo des por hecho.** Tener Internet dentro de WSL2 no demuestra que Linux
controle la radio Wi-Fi de la laptop. La conexión virtual de WSL y una interfaz
802.11 con modo monitor son cosas distintas.

Con la tarjeta integrada habitual, administrada por Windows, WSL2 normalmente
no recibe acceso directo a su radio. Instalar Aircrack-ng, instalar Kali dentro
de WSL o cambiar la red a modo mirrored no proporciona por sí solo ese acceso.
El modo mirrored modifica la conectividad de red, no certifica monitor ni
inyección. [Red de WSL](https://learn.microsoft.com/en-us/windows/wsl/networking).

Para decidir, identifica el hardware y ejecuta las comprobaciones de la sección
4 **en la laptop que llevarás**. El diagnóstico previo de este proyecto no
certifica otra máquina. Si no aparece una radio en `iw dev` ni en `iw list`,
no podrás hacer la captura en ese entorno hasta resolver acceso/controlador.
Podrás seguir haciendo el análisis offline.

Si solo tienes la tarjeta interna, una alternativa es arrancar Linux
directamente, por ejemplo desde un USB Live, y comprobar allí su compatibilidad.
Una VM convencional también necesita acceso a una radio física: compartir la
conexión de Windows por NAT o puente no basta. El soporte depende del chipset y
del controlador, no del nombre comercial de la laptop.

### Identificar la laptop en Windows

**PowerShell de Windows**, no la terminal de Ubuntu:

```powershell
Get-NetAdapter -Physical | Format-Table Name, InterfaceDescription, Status
Get-PnpDevice -Class Net | Select-Object FriendlyName, InstanceId
wsl --list --verbose
wsl --status
```

Guarda el modelo exacto del adaptador. Un identificador que empieza por `PCI\`
indica un dispositivo PCI; `USB\` identifica uno USB. `usbipd` comparte
dispositivos USB, no convierte una tarjeta PCIe integrada en un dispositivo USB.

**Criterio para llegar preparado:** Linux reconoce la radio, el controlador
anuncia monitor y se consigue activar ese modo. La recepción del router del
aula se comprobará allí. Si además se autoriza una actividad con inyección,
esa capacidad requiere su propia comprobación.

## 2. Preparar WSL si falta en la laptop

Si WSL2 con Ubuntu ya funciona, omite la instalación. Si falta, en **PowerShell
como administrador**, siguiendo la [guía de Microsoft](https://learn.microsoft.com/en-us/windows/wsl/install):

```powershell
wsl --install -d Ubuntu
```

Reinicia si Windows lo solicita y abre Ubuntu para crear tu usuario y contraseña.
Después puedes revisar/actualizar WSL desde PowerShell:

```powershell
wsl --update
wsl --list --verbose
```

La columna `VERSION` debe indicar `2` para la distribución que utilizarás.
Esto prepara el entorno de software; no demuestra acceso a la tarjeta Wi-Fi.

## 3. Instalar herramientas en Ubuntu/Debian/Kali

Los bloques marcados `bash` se ejecutan dentro de **Linux**, no en PowerShell.

```bash
sudo apt update
sudo apt install aircrack-ng iw python3
```

`aircrack-ng` instala la suite, no solamente el programa de recuperación.
Comprueba las rutas de los ejecutables:

```bash
command -v airmon-ng
command -v airodump-ng
command -v aireplay-ng
command -v aircrack-ng
command -v iw
python3 --version
aircrack-ng --help
```

Herramientas opcionales:

```bash
sudo apt install wireshark usbutils pciutils
```

Wireshark sirve para inspección visual; `lsusb` y `lspci` ayudan a identificar
hardware. No se necesitan diccionarios, Hashcat, Nmap, paquetes de `pip` ni
compilar un programa propio de cifrado. `pdflatex` solo hace falta para
regenerar el informe, no para ejecutar el laboratorio.

Lleva la carpeta completa `Lab10`, incluidos `lab10.py`, `test_lab10.py`,
`muestras/ptw.cap`, `muestras/README.md` y `evidencias/muestra.sha256`.
Así puedes practicar sin descargar nada más. Primero entra al directorio real
donde la copiaste; por ejemplo, si está en Descargas de Windows:

```bash
# Sustituir TU_USUARIO por el usuario real de Windows:
cd "/mnt/c/Users/TU_USUARIO/Downloads/Lab10"
pwd
ls lab10.py test_lab10.py muestras/ptw.cap
```

## 4. Comprobación obligatoria antes de clase

Desde el directorio del laboratorio, en **Linux**:

```bash
uname -r
python3 lab10.py comprobar
iw dev
iw list
sudo airmon-ng
```

Interpreta el resultado:

| Resultado | Qué significa y qué hacer |
| --- | --- |
| Falta un ejecutable | Instala el paquete correspondiente de la sección 3. |
| Solo aparece `eth0`, no aparece una radio en `iw` | WSL no tiene acceso a una radio utilizable; no continúes con captura. |
| Hay radio en `iw list`, pero ninguna interfaz en `iw dev` | El controlador expone hardware, pero falta revisar su interfaz/configuración. |
| `iw list` incluye `monitor` en los modos admitidos | El controlador anuncia ese modo; falta activarlo y verificarlo. |
| No anuncia `monitor` | Ese hardware/controlador no ofrece lo necesario en la configuración actual. |
| `Operation not permitted` o error de netlink | Puede haber restricciones de permisos/entorno; no significa por sí solo incompatibilidad física. |

`lab10.py comprobar` devuelve **1** si falta una herramienta o no detecta Wi-Fi.
No confundas ese resultado con un error del recuperador offline. Un resultado
0 tampoco demuestra recepción ni inyección: es un diagnóstico preliminar.

**Si únicamente llevarás la tarjeta integrada y WSL no la expone, necesitas
cambiar de entorno o disponer de un adaptador adecuado. Esperar al día de la
prueba no resuelve esa limitación.** No se puede confirmar compatibilidad sin
el modelo y los resultados de estas comprobaciones.

## 5. Solo si consigues un adaptador USB: conectarlo a WSL2

Esta sección no soluciona una tarjeta integrada PCIe. Para un USB, Microsoft
documenta el acceso mediante [usbipd-win](https://learn.microsoft.com/en-us/windows/wsl/connect-usb).
Reconocer el dispositivo USB no garantiza que el kernel de WSL tenga el
controlador/firmware necesario para usarlo como Wi-Fi.

En **PowerShell**, instala la herramienta si falta:

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

Mantén Ubuntu abierto. En **PowerShell como administrador**, identifica el USB
y compártelo. `4-4` es un ejemplo: sustitúyelo por su `BUSID` real.

```powershell
usbipd list
usbipd bind --busid 4-4
```

En **PowerShell** adjúntalo a WSL:

```powershell
usbipd attach --wsl --busid 4-4
```

En **Linux**, repite la comprobación:

```bash
lsusb
iw dev
iw list
sudo airmon-ng
```

Mientras esté adjunto a WSL, Windows no podrá usar ese USB. Si `lsusb` lo ve
pero `iw` no muestra una radio, todavía falta soporte del controlador/firmware;
no instales controladores al azar. Al terminar, devuélvelo desde **PowerShell**:

```powershell
usbipd detach --busid 4-4
```

## 6. Entender qué estás haciendo

El flujo de trabajo es:

```text
Radio física -> modo monitor -> captura .cap -> análisis estadístico -> clave
                   airmon         airodump          aircrack
```

| Concepto | Significado para esta práctica |
| --- | --- |
| SSID | Nombre visible de la red; no identifica inequívocamente al AP. |
| BSSID | Dirección MAC del AP objetivo. Se obtiene del docente o se confirma en la observación autorizada. |
| Canal | Frecuencia sobre la que escuchas. Debe coincidir con el AP. |
| Modo managed | Uso habitual: un cliente se asocia al AP para conectarse a la red. |
| Modo monitor | Recepción de tramas 802.11 sin tener que asociarse como cliente. |
| IV | Vector de inicialización de WEP; acompaña a las tramas y aporta información al análisis estadístico. |
| `.cap` | Archivo con las tramas capturadas; permite analizar después sin radio. |
| Inyección | Transmisión de tramas construidas/reinyectadas; es distinta de escuchar. |

**Capturar no requiere conocer la clave ni conectarse primero al Wi-Fi.**
Escuchar las tramas tampoco significa poder leer inmediatamente todo su
contenido cifrado. Consulta los [modos inalámbricos de Linux](https://wireless.docs.kernel.org/en/latest/en/users/documentation/modes.html).

WEP combina un secreto compartido con un IV de 24 bits al utilizar RC4. Su
diseño permite recuperar estadísticamente el secreto con suficiente tráfico
útil. Una repetición de IV no revela automáticamente toda la clave; hacen falta
material adecuado y análisis. PTW es el método predeterminado de Aircrack-ng
para WEP: no necesita una lista de posibles contraseñas. No es el procedimiento
de handshake y diccionario usado en otras prácticas de WPA.
[Documentación de recuperación WEP](https://aircrack-ng.org/doku.php?id=aircrack-ng).

### Función de cada herramienta

- **`airmon-ng`:** preparar/restaurar monitor. No recupera la clave.
- **`airodump-ng`:** capturar y mostrar actividad. No rompe el cifrado por sí solo.
- **`aircrack-ng`:** analizar la captura y buscar la clave. No necesita una radio
  para analizar un archivo ya guardado.
- **`aireplay-ng`:** realizar pruebas activas de transmisión/reinyección. No se
  ejecuta en la ruta pasiva de esta guía ni desde el ayudante automáticamente.

## 7. Ensayo que puedes hacer ahora: muestra pública

En **Linux**, desde `Lab10`:

```bash
sha256sum -c evidencias/muestra.sha256
python3 -m unittest -v test_lab10.py
aircrack-ng -a 1 -b 00:12:BF:12:32:29 muestras/ptw.cap
```

Resultado esperado de la recuperación:

```text
KEY FOUND! [ 1F:1F:1F:1F:1F ]
Decrypted correctly: 100%
```

`-a 1` selecciona WEP, `-b` selecciona un AP y el último argumento es la
captura. No aparece `-w`: no se pasa un diccionario ni la clave conocida como
entrada. El [README oficial de Aircrack-ng](https://github.com/aircrack-ng/aircrack-ng/blob/master/README)
publica esa muestra y su clave para verificar el resultado.

En la preparación se leyeron 65,282 paquetes y se utilizaron 30,566 IVs.
**Son cifras de esta muestra, no una cantidad mínima universal ni un resultado
del aula.** Si falta Aircrack-ng, el test que lo necesita se marcará como
omitido; no debes confundir una omisión con esa prueba aprobada.

Para practicar también el ayudante y guardar la clave pública recuperada:

```bash
python3 lab10.py recuperar muestras/ptw.cap \
  --bssid 00:12:BF:12:32:29 --clave capturas/practica-01.txt
```

Si ese archivo ya existe, el ayudante lo rechaza. Usa otra ruta, por ejemplo
`capturas/practica-02.txt`. No hace falta `sudo` para estas recuperaciones.

## 8. En clase: procedimiento pasivo de principio a fin

Realiza esta sección solo después de pasar la comprobación de hardware. No
necesitas que todos tus compañeros estén conectados: necesitas tráfico útil del
AP autorizado. El docente puede disponer el tráfico de prueba.

### Terminal A: seleccionar parámetros y activar monitor

Solicita al docente BSSID y canal del router WEP. En **Bash** puedes escribirlos
sin editar comandos largos:

```bash
read -r -p 'Interfaz Wi-Fi real, por ejemplo wlan0: ' IFACE
read -r -p 'BSSID del AP autorizado: ' BSSID
read -r -p 'Canal indicado por el docente: ' CANAL
sudo airmon-ng start "$IFACE" "$CANAL"
iw dev
```

La salida debe mostrar una interfaz de tipo `monitor`. Su nombre puede cambiar;
no asumas que siempre es `wlan0mon`. Usa el nombre real en el paso siguiente.
Si no se activa, resuelve el problema antes de capturar.
[Uso de Airmon-ng](https://aircrack-ng.org/doku.php?id=airmon-ng).

```bash
read -r -p 'Nombre real de la interfaz monitor: ' MON
read -r -p 'Prefijo nuevo, por ejemplo capturas/clase01: ' PREFIJO
python3 lab10.py capturar --interfaz "$MON" \
  --bssid "$BSSID" --canal "$CANAL" --salida "$PREFIJO" --simular
```

La simulación valida argumentos y muestra el comando, sin ejecutar la captura.
Si los valores son correctos, comienza:

```bash
sudo python3 lab10.py capturar --interfaz "$MON" \
  --bssid "$BSSID" --canal "$CANAL" --salida "$PREFIJO"
```

Deja esa terminal abierta. El ayudante invoca `airodump-ng` con BSSID, canal y
filtro WEP, conservando paquetes completos y un CSV. Un prefijo como
`capturas/clase01` normalmente produce `capturas/clase01-01.cap` y su CSV;
si ya había archivos, el sufijo puede cambiar. Mira el nombre real creado.

### Terminal B: recuperar mientras continúa la captura

Abre otra terminal **Linux** en el mismo directorio `Lab10`. Las variables de
Terminal A no se comparten automáticamente: vuelve a introducir los datos.

```bash
read -r -p 'BSSID del AP autorizado: ' BSSID
read -r -p 'Ruta real de captura, por ejemplo capturas/clase01-01.cap: ' CAP
read -r -p 'Archivo NUEVO para clave, por ejemplo capturas/clave01.txt: ' CLAVE
python3 lab10.py recuperar "$CAP" --bssid "$BSSID" --clave "$CLAVE"
```

Se puede analizar mientras el archivo sigue creciendo. Si todavía no hay
material suficiente, continúa capturando y sigue la indicación de la
herramienta. Conserva paquetes completos: `--ivs` no se usa en esta ruta PTW.
El contador orienta, pero no garantiza éxito. No pases un diccionario.

### Terminal A: terminar y devolver el adaptador

Después de documentar el resultado, usa `Ctrl+C` para detener la captura.
Si el recuperador sigue trabajando, detenlo también en Terminal B.

```bash
sudo airmon-ng stop "$MON"
iw dev
```

Si cambiaste manualmente la gestión de red del adaptador, restaura ese cambio.
La guía no ejecuta `airmon-ng check kill`: puede detener gestores de red y
quitarte tu propia conexión.

## 9. Leer la pantalla y optimizar la captura

En airodump-ng, revisa que `ENC` corresponda a WEP y observa:

| Campo | Lectura práctica |
| --- | --- |
| `#Data` | En WEP representa IVs únicos, no todas las tramas guardadas. |
| `#/s` | Ritmo mostrado para datos; observarlo ayuda a detectar estancamiento. |
| `PWR` | Intensidad informada por el controlador; puede no estar disponible. |
| `RXQ` | Calidad reciente de recepción; se muestra con canal fijo. |
| `Lost` | Estimación de tramas perdidas por estación a partir de secuencias. |

Una cifra aislada no demuestra congestión ni identifica un atacante.
Consulta [captura y contadores de Airodump-ng](https://aircrack-ng.org/doku.php?id=airodump-ng).

Optimiza lo que controlas:

1. Identifica BSSID y canal antes de comenzar; reduce errores al elegir objetivo.
2. Captura en canal fijo, sin otro capturador saltando canales en la misma radio.
3. Usa una ubicación estable con buena recepción, sin manipular equipos ajenos.
4. Conserva el archivo completo y analiza en paralelo; no esperes a terminar
   toda la sesión para iniciar la recuperación.
5. Compara la tasa de IVs útiles, no solo el tamaño del archivo o los beacons.
6. Si falta tráfico, coordina tráfico legítimo del AP de pruebas con el docente.
7. Ensaya la muestra y los comandos antes; instala herramientas con antelación.

## 10. Entender el script existente

El ayudante no sustituye la suite: construye comandos reproducibles alrededor
de ella. Puedes consultar sus opciones:

```bash
python3 lab10.py --help
python3 lab10.py capturar --help
python3 lab10.py recuperar --help
```

| Parte de `lab10.py` | Qué aprender al leerla |
| --- | --- |
| `bssid`, `interfaz`, `canal` | Validar entradas antes de llamar a otra herramienta. |
| `parser` | Definir subcomandos y argumentos con `argparse`, sin dependencias externas. |
| `comprobar` | Buscar ejecutables y detectar interfaces locales; no escanea redes. |
| Rama `capturar` | Preparar los argumentos de airodump-ng con objetivo y canal fijos. |
| Rama `recuperar` | Exigir un archivo existente, seleccionar WEP y guardar una salida nueva. |
| `--simular` | Revisar el comando sin abrir la radio ni crear archivos de salida. |
| `subprocess.call(command)` | Pasar una lista de argumentos sin usar `shell=True`; retornar el estado de la herramienta. |

No cambia automáticamente el modo de la interfaz, no se asocia al AP, no expulsa
clientes y no incluye diccionarios. La secuencia manual te permite comprobar
qué hace cada herramienta. `test_lab10.py` incluye validación de entradas,
simulación, archivos, propagación de errores y recuperación real de la muestra.

## 11. Por qué expulsar/bloquear participantes no protege tu captura

Recuperar la clave WEP no te convierte en administrador del router. La clave
de la red y las credenciales del panel de administración son distintas.

Además, otro capturador puede escuchar en modo monitor sin asociarse al AP.
Bloquear nuevas asociaciones no impediría esa escucha. Expulsar clientes
también puede eliminar tráfico útil y perjudicar tu propia recuperación.
No existe un modo de hacer que las tramas emitidas por el router solo sean
visibles para tu laptop.

Esta guía no incorpora un botón ni comandos para desconectar o impedir la
participación de compañeros. Si se requiere un ensayo sin interferencia de
otros grupos, la alternativa es que el docente organice un AP/canal de pruebas
separado y las condiciones de acceso. Las condiciones adversarias se pueden
estudiar mediante efectos, observación y mediciones controladas, sin atribuir
como realizadas acciones que solo se investigaron.

## 12. Ejercicios breves para aprender antes de clase

1. Ejecuta la muestra. Explica por qué no hacen falta radio, modo monitor ni
   otras personas. **Respuesta:** las tramas ya están guardadas.
2. En una simulación de captura, cambia solo el canal. Identifica qué argumento
   cambia. **Respuesta:** `--channel` en el comando de airodump-ng.
3. Intenta simular con una MAC inválida. **Respuesta esperada:** error del
   ayudante antes de ejecutar cualquier herramienta.
4. Recupera la muestra con el ayudante y verifica la clave publicada. Repite
   con la misma salida. **Respuesta esperada:** rechazo para no sobrescribirla.
5. Explica por qué muchos beacons no garantizan la recuperación.
   **Respuesta:** hace falta material cifrado útil; anunciar una red no equivale
   a aportar suficientes IVs útiles para el análisis.
6. Explica por qué cerrar la admisión de clientes no cierra la escucha del aire.
   **Respuesta:** monitor no requiere asociación.

## 13. Fallos frecuentes

| Problema | Acción razonable |
| --- | --- |
| `No such file` | Comprueba `pwd`, que copiaste toda la carpeta y la ruta real del `.cap`. |
| `command not found` | Instala los paquetes y comprueba `command -v`. |
| `iw` no encuentra radio | Resuelve acceso físico/controlador; no inventes una interfaz `wlan0`. |
| No se activa monitor | Comprueba chipset, controlador, firmware y restricciones del entorno. |
| Aviso de canal fijo/canal cambiado | Revisa `iw dev`, el canal y `sudo airmon-ng check`; un gestor puede cambiarlo. |
| Ves beacons, pero `#Data` apenas crece | Confirma WEP, recepción y tráfico útil; coordina la prueba con el docente. |
| No encuentra la clave | Sigue reuniendo material útil y verifica objetivo/formato; no hay un umbral universal. |
| `--clave` ya existe | Selecciona otra ruta de salida, conservando la evidencia anterior. |
| Se perdió tu conexión habitual | Revisa si dejaste monitor activo o transferiste a WSL el adaptador que Windows usaba. |

## 14. Qué guardar y entregar

- Completa los carnés y sube `informe.pdf` a GES antes de la evaluación.
- Conserva esta guía y el código localmente para ejecutar la práctica.
- En clase completa [REGISTRO_CLASE.md](evidencias/REGISTRO_CLASE.md): objetivo,
  adaptador/controlador, tiempos, métricas, comandos y resultado real.
- Guarda pantalla de `iw dev`, captura del AP WEP, resultado de recuperación y
  validación del docente. Calcula el SHA-256 del `.cap` real:

```bash
# Ejemplo: sustituir por el archivo que realmente se creó.
sha256sum capturas/clase01-01.cap
```

Los archivos de captura y clave del aula se guardan en `capturas/`, ignorado por
Git. La muestra pública no sustituye la evidencia del router del laboratorio.
No compartas procedimientos o scripts con otros participantes durante la
evaluación, tal como indica el enunciado.

## 15. Alcance de la verificación de esta guía

Guía preparada con documentación oficial consultada el 20 de octubre de 2026.
Se verificaron la sintaxis de sus bloques Bash, los enlaces locales y el
SHA-256 de la muestra; se repitió su recuperación real con la clave esperada.
Los comandos de instalación y PowerShell se documentan para que los ejecutes
en la laptop: no se han instalado herramientas ni ejecutado comandos de Windows
en ella como parte de esta actualización. Tampoco se ha probado su radio ni
realizado una captura en vivo. La compatibilidad de la tarjeta integrada sigue
pendiente de identificar el modelo y hacer las comprobaciones de la sección 4.

La ruta Arch añadida se contrastó con los paquetes oficiales y con el código
existente. No se modificó el código ni se ejecutó `pacman` o una captura en la
laptop del compañero. El modelo, controlador y modo monitor de ese equipo aún
deben comprobarse allí.
