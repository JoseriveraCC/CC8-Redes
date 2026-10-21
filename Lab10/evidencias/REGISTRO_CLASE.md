# Registro de la ejecución en clase

**Estado: pendiente.** Esta plantilla no acredita pruebas realizadas.

- Fecha/hora:
- Participante y carné:
- BSSID, SSID y canal autorizados por el docente:
- Alcance de pruebas activas autorizado:
- Modelo del adaptador, chipset/controlador e interfaz monitor:
- Versión de Aircrack-ng:
- Ruta del `.cap` y del `.csv`:
- Hora de inicio/fin de captura:
- Resultado de recuperación (éxito o fallo, sin inventar la clave):
- Validación del docente:

## Mediciones

Mantener BSSID, canal, duración y equipo constantes. Observar primero una ventana
de 60 s. Si el docente dispone una condición controlada, observar otros 60 s y
repetir la línea base. Registrar condiciones reales y no atribuir causalidad a
un solo contador.

| Condición | Inicio/fin | #Data inicio/fin | IVs nuevos/s | RXQ | Lost | PWR | Observaciones |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Línea base | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| Condición controlada por docente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| Retorno a línea base | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |

`IVs nuevos/s = (#Data final - #Data inicial) / segundos`. Si una métrica no está
disponible, escribir «N/D», no cero. `#Data` representa IVs únicos para WEP en
airodump-ng; el archivo puede contener muchas más tramas.

## Archivos a conservar

1. Pantalla de `iw dev` con tipo monitor y canal.
2. Pantalla de `airodump-ng` con el AP WEP autorizado y sus contadores.
3. Comando exacto de recuperación y su resultado.
4. Captura original y SHA-256 (`sha256sum capturas/clase-01.cap`).
5. Acciones competitivas realmente usadas y observaciones; escribir «no se
   ejecutaron» si solo se investigaron.

No confundir el resultado de `muestras/ptw.cap` con el router de clase. Conservar
las capturas/clave de aula en `capturas/` y entregar únicamente al docente los
archivos que solicite.
