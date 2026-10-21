# Latest Session Work

2026-10-20: Prepared the Lab10 submission under deployment `lab10-entrega-20261020`, Medium route.

## Detailed Current State

The user can test radio only in class. Submission authors are Jose Rivera and Erick Mejia, with student IDs left blank. The assignment is a one-page authorized WEP router competition requiring a document before evaluation. Preparatory work is complete; live classroom results remain pending.

## Session Changes

- informe.pdf / informe.tex: seven-page submission with commands, public-sample evidence, adversarial-condition analysis, references, and honest pending-classroom status.
- lab10.py: local diagnosis, passive BSSID/channel capture, and offline recovery; --simular validates without execution. No automatic active radio tests.
- test_lab10.py: five local checks, including genuine recovery of the official sample when Aircrack-ng is installed.
- muestras/ptw.cap plus provenance; evidencias/ stores real local outputs and REGISTRO_CLASE.md for future measurements.
- README.md provides installation, offline checks, classroom commands, and PDF regeneration. .gitignore preserves its workflow block and additionally excludes __pycache__/ and capturas/.

## Verification

- python3 -m unittest -v test_lab10.py: five passed (evidencias/pruebas_locales.txt).
- Real helper recovery: exit 0, 65,282 packets, 30,566 IVs, expected key 1F:1F:1F:1F:1F; no dictionary or radio transmission (evidencias/recuperacion_muestra.txt).
- sha256sum -c evidencias/muestra.sha256: passed.
- python3 lab10.py comprobar: exit 1, all required tools found but no Wi-Fi interface (evidencias/diagnostico.txt).
- pdflatex: exit 0; PDF has seven A4 pages, expected authors/results/references, no Overfull warnings; visually inspected pages 1, 3, 4, 5, 6, 7 (evidencias/documento.txt).
- Git is a parent repository; this Lab10 directory is untracked. Existing untracked sibling Lab08/Lab09 directories were left untouched. No Git mutations or classroom radio operations were performed.

## Pending Work and Blockers

Fill student IDs, submit PDF to GES, obtain compatible physical monitor/injection hardware, and record the actual classroom capture and recovery. Active testing scope affecting others needs instructor clarification because the source sentence is incomplete. No classroom evidence is fabricated.

## Next Entry Point

Open README.md for commands; fill IDs in informe.tex and regenerate the PDF. In class, confirm the authorized BSSID/channel and complete evidencias/REGISTRO_CLASE.md. Offline practice is immediately runnable with the included public capture.
