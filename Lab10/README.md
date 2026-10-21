# Laboratorio 10 — Captura el Router

Preparación para Ciencias de la Computación VIII (Redes y Protocolos).
Autores solicitados: **Jose Rivera** y **Erick Mejia**; carnés pendientes.

Para preparar otra laptop desde cero y aprender el procedimiento, consulta
**[GUIA_LAPTOP.md](GUIA_LAPTOP.md)**. Comienza con la ruta actual para
**Arch Linux nativo**; también conserva las alternativas de Windows/WSL y
Ubuntu y explica el ayudante. `lab10.py` no requiere cambios para Arch.

El documento para subir a GES es **[informe.pdf](informe.pdf)**. Su fuente editable
es [informe.tex](informe.tex): completa las dos líneas de carné y recompila antes
de entregarlo. El enunciado establece una competencia individual; la portada
incluye los dos nombres solicitados, sin cambiar esa modalidad de evaluación.

Se verificó la recuperación **offline de una muestra pública**, sin diccionario.
La captura del router y las condiciones adversarias reales se probarán en clase.
Los registros actuales no se presentan como resultados de ese router.

## Herramientas y equipo

En **Arch Linux**, instala desde los repositorios oficiales:

```bash
sudo pacman -Syu --needed aircrack-ng iw python pciutils
```

Este comando también actualiza el sistema; coordínalo con el dueño de la laptop
antes de clase. Después usa los mismos comandos `python3`, `iw` y Aircrack-ng
de esta guía, sustituyendo los nombres de interfaz por los reales de Arch.

En Ubuntu/Debian, el paquete `aircrack-ng` incluye `airmon-ng`, `airodump-ng`,
`aireplay-ng` y `aircrack-ng`:

```bash
sudo apt update
sudo apt install aircrack-ng iw python3
```

La suite e `iw` ya estaban disponibles al terminar la verificación de este trabajo.
Wireshark es opcional para inspeccionar las capturas (`sudo apt install wireshark`).
No hacen falta diccionarios, Hashcat, Nmap ni un programa propio de cifrado.

Para capturar necesitas un adaptador Wi-Fi físico con modo monitor; para las
pruebas activas, también soporte de inyección. Una interfaz Ethernet virtual no
lo sustituye. El entorno revisado es **WSL2 sin Wi-Fi expuesto**. Puedes hacer la
prueba offline aquí; para radio, usa Linux con acceso al adaptador o una VM con
el adaptador USB conectado directamente a ella. WSL permite conectar USB mediante
[USB/IP](https://learn.microsoft.com/en-us/windows/wsl/connect-usb), pero eso no
garantiza un controlador compatible con monitor/inyección.

## Probar ahora, sin otras personas ni router

Desde este directorio:

```bash
python3 -m unittest -v test_lab10.py
python3 lab10.py comprobar
sha256sum -c evidencias/muestra.sha256
aircrack-ng -a 1 -b 00:12:BF:12:32:29 muestras/ptw.cap
```

La suite tiene doce pruebas; la de recuperación real se omite explícitamente si
no está instalado `aircrack-ng`. Con la herramienta instalada, la salida esperada
de la muestra es `KEY FOUND! [ 1F:1F:1F:1F:1F ]`. No necesitas `sudo` para recuperar
una clave desde un archivo. `comprobar` devuelve **1** si falta alguna herramienta
o no detecta Wi-Fi: en este WSL2 ese resultado es esperado, aunque funcione el
análisis offline. Su resultado no certifica compatibilidad del hardware.

Para revisar el comando de captura sin ejecutarlo:

```bash
python3 lab10.py capturar --interfaz wlan0mon \
  --bssid 02:11:22:33:44:55 --canal 6 --simular
```

La MAC anterior es ilustrativa; no identifica al router de clase.

## En clase: captura y recuperación

El docente debe identificar el BSSID/canal del router WEP autorizado. Sustituye
los cuatro valores siguientes por los reales. `MON` es el nombre que reporte
`airmon-ng`, no necesariamente `wlan0mon`.

```bash
IFACE=wlan0
MON=wlan0mon
BSSID=02:11:22:33:44:55
CANAL=6

sudo airmon-ng
iw list
sudo airmon-ng start "$IFACE" "$CANAL"
iw dev
sudo python3 lab10.py capturar --interfaz "$MON" \
  --bssid "$BSSID" --canal "$CANAL" --salida capturas/clase
```

Deja esa terminal capturando. En otra terminal, con el BSSID real y el nombre de
archivo que efectivamente se creó:

```bash
python3 lab10.py recuperar capturas/clase-01.cap \
  --bssid 02:11:22:33:44:55 --clave capturas/clave-clase.txt
```

La herramienta puede analizar mientras crece el archivo. Si reinicias la captura,
el sufijo puede cambiar a `-02`, etc.; usa la ruta mostrada por `airodump-ng`.
No uses `--ivs`: se conservan paquetes completos para PTW. La clave hexadecimal
recuperada y la validación del docente son la evidencia de éxito; la cantidad de
IVs necesaria y el tiempo no están garantizados.

Para terminar, `Ctrl+C` en los procesos activos y, en la terminal que conserva
`MON`:

```bash
sudo airmon-ng stop "$MON"
```

El [informe](informe.pdf) contiene los comandos manuales equivalentes, la ruta
activa opcional de reinyección ARP sobre el AP autorizado, restauración y
diagnóstico. Las pruebas activas dependen del alcance fijado por el docente.

## Subcomandos de `lab10.py`

| Subcomando | Qué hace |
|---|---|
| `comprobar` | diagnóstico local de herramientas y Wi-Fi |
| `monitor` | activa (`--canal`) o detiene (`--detener`) el modo monitor |
| `escanear` | lista APs WEP para hallar BSSID/canal |
| `inyectar` | genera IVs: `--modo arpreplay\|chopchop\|fragment\|fakeauth` |
| `capturar` | captura pasiva del AP autorizado |
| `deauth` | desautentica clientes del AP (`--cliente`, `--cantidad`) |
| `bloquear` | aísla a un host por ARP spoofing (`--objetivo`, `--gateway`) |
| `recuperar` | recupera la clave WEP de una captura (PTW) |

Todos los subcomandos activos aceptan `--simular`, que valida argumentos y
muestra el comando **sin ejecutarlo**.

### Fase adversarial (competencia autorizada)

Los subcomandos `deauth`, `bloquear` y la inyección activa degradan la captura de
otros participantes o los aíslan de la red. **Están pensados exclusivamente para
el entorno autorizado por el docente**: red aislada, solo los participantes del
laboratorio, sobre el router WEP de la práctica. `deauth` desconecta clientes y
`bloquear` deniega acceso; úsalos solo bajo ese alcance. La estrategia, los
comandos y —lo que el enunciado califica— **cómo detectarlos y mitigarlos** están
en [estrategia_adversarial.md](estrategia_adversarial.md).

## Evidencia y entrega

- [Pruebas locales](evidencias/pruebas_locales.txt): cinco pruebas aprobadas.
- [Recuperación real de muestra pública](evidencias/recuperacion_muestra.txt):
  65,282 paquetes leídos, 30,566 IVs y clave esperada encontrada.
- [Diagnóstico](evidencias/diagnostico.txt): herramientas presentes, sin Wi-Fi visible.
- [Origen de la muestra](muestras/README.md) y [SHA-256](evidencias/muestra.sha256).
- [Registro para clase](evidencias/REGISTRO_CLASE.md): completar con mediciones,
  capturas de pantalla y resultado del router. Actualmente está pendiente.

`capturas/` está ignorado por Git y es la salida predeterminada para capturas y
claves de clase. Los archivos de `evidencias/` actuales corresponden a la muestra
pública o a comprobaciones locales.

Para regenerar el PDF después de completar los carnés (requiere `pdflatex`, ya
disponible en el entorno revisado):

```bash
mkdir -p /tmp/lab10-pdf
pdflatex -interaction=nonstopmode -halt-on-error \
  -output-directory=/tmp/lab10-pdf informe.tex
pdflatex -interaction=nonstopmode -halt-on-error \
  -output-directory=/tmp/lab10-pdf informe.tex
cp /tmp/lab10-pdf/informe.pdf informe.pdf
```

Sube `informe.pdf` a GES **antes de la evaluación**, como exige el enunciado.
Conserva el código y la muestra para practicar; no compartas procedimientos ni
scripts durante la competencia. El documento previo incluye evidencia offline
real y distingue los resultados que solo podrán obtenerse en clase.
