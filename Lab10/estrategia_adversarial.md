# Estrategia adversarial — Laboratorio 10

> Material para integrar en `informe.pdf`. Todo lo descrito aquí se ejecuta en el
> **entorno autorizado por el docente**: red inalámbrica aislada, solo los
> participantes del laboratorio, sobre el router WEP dispuesto para la práctica.
> Fuera de ese entorno estas técnicas no son legítimas.

El enunciado califica dos cosas: **recuperar la clave primero** y **degradar la
eficiencia de los rivales**. La ventaja no está en un ataque aislado, sino en
combinarlos: volverte autosuficiente para generar tus propios IVs y, a la vez,
secar la fuente de datos de quien depende de captura pasiva.

## Flujo completo con `lab10.py`

```bash
# 0. Diagnóstico
python3 lab10.py comprobar

# 1. Modo monitor en el canal del AP
sudo python3 lab10.py monitor --interfaz wlan0 --canal 6

# 2. Localizar el objetivo (BSSID/canal)
sudo python3 lab10.py escanear --interfaz wlan0mon

# 3. Capturar (deja esta terminal abierta)
sudo python3 lab10.py capturar --interfaz wlan0mon --bssid <BSSID> --canal 6 --salida capturas/clase

# 4. Asociarte y generar IVs sin depender del tráfico ajeno
sudo python3 lab10.py inyectar --interfaz wlan0mon --bssid <BSSID> --modo fakeauth --mac <TU_MAC>
sudo python3 lab10.py inyectar --interfaz wlan0mon --bssid <BSSID> --modo fragment
sudo python3 lab10.py inyectar --interfaz wlan0mon --bssid <BSSID> --modo arpreplay

# 5. Recuperar (PTW, mientras crece la captura)
python3 lab10.py recuperar capturas/clase-01.cap --bssid <BSSID>
```

## Técnicas de ventaja y cómo afectan a la captura

### 1. Inyección: ser autosuficiente en IVs
WEP filtra un *vector de inicialización* (IV) por paquete; `aircrack-ng` necesita
decenas de miles para el ataque PTW. Quien solo escucha depende de que haya
tráfico. Con **fakeauth** te asocias al AP, y con **fragment** o **chopchop**
obtienes keystream *aunque la red esté casi vacía*; con ese keystream forjas un
ARP y **arpreplay** lo reinyecta miles de veces. Resultado: generas tus propios
IVs a ritmo constante sin esperar a nadie.

- Efecto en ti: aceleras tu recuperación de minutos a segundos.
- Efecto en rivales: tu reinyección también llena *sus* capturas — por eso el
  siguiente punto es clave para no regalarles IVs.

### 2. Deauth: secar la captura pasiva del rival
`aireplay-ng --deauth` expulsa a los clientes del AP. Un cliente desconectado deja
de generar tráfico, así que **quien captura de forma pasiva se queda sin IVs**.

```bash
# a un cliente concreto
sudo python3 lab10.py deauth --interfaz wlan0mon --bssid <BSSID> --cliente <MAC_RIVAL> --cantidad 0
# a todos los clientes del AP
sudo python3 lab10.py deauth --interfaz wlan0mon --bssid <BSSID> --cantidad 0
```

- Efecto: congestión y pérdida de asociación; la tasa de IVs del rival cae a cero.
- Matiz táctico: mientras haces deauth continuo sobre el canal, tu propia captura
  pasiva también sufre. La jugada fuerte es **deauth + inyección propia**: tú no
  necesitas clientes (generas IVs por fragmentación), ellos sí.

### 3. Bloqueo de acceso: ARP spoofing tras recuperar la clave
Una vez tienes la clave y te unes a la red, `lab10.py bloquear` envenena la caché
ARP del rival y del gateway (sockets raw, sin dependencias externas). Como no
activas reenvío de IP, el tráfico del rival llega a tu equipo y se descarta: queda
**aislado de la red**. `Ctrl+C` restaura el ARP correcto.

```bash
sudo python3 lab10.py bloquear --interfaz wlan0 --objetivo <IP_RIVAL> --gateway <IP_ROUTER>
```

- Efecto: denegación de servicio a nivel de enlace, selectiva sobre un host.
- Alcance: solo tiene sentido en la red aislada del laboratorio; no acelera tu
  propio crackeo, es puramente para degradar al rival.

## Cómo identificar y mitigar estos ataques (lo que el enunciado pide explicar)

| Ataque | Cómo detectarlo | Mitigación |
|---|---|---|
| Deauth / desautenticación | Oleadas de *frames* de deauth en Wireshark (`wlan.fc.type_subtype == 0x0c`); picos de reconexión en `airodump-ng` | 802.11w (Management Frame Protection); migrar a WPA2/WPA3 |
| Inyección masiva de ARP | Mismo paquete ARP repetido a altísima tasa desde una MAC; crecimiento anómalo de IVs | Desactivar WEP (vulnerable por diseño); detección de reinyección |
| ARP spoofing / MITM | Dos IP con la misma MAC en la tabla ARP; `arp -n` o IDS detectan el cambio de MAC del gateway | Entradas ARP estáticas; *dynamic ARP inspection* en el switch; cifrado extremo a extremo |
| Congestión de canal | Caída de *throughput*, aumento de reintentos y ruido en el espectro | Cambiar de canal; monitoreo de RF |

## Conclusión defensiva
Todas estas técnicas funcionan **porque WEP está roto**: IVs cortos y reutilizados,
sin protección de integridad ni de *frames* de gestión. La mitigación real no es
parchear WEP, sino **abandonarlo**: WPA2/WPA3 con 802.11w cierra tanto la
recuperación de clave como los ataques de desautenticación aquí demostrados.
