# Project Structure

## Deliverables and Tools

- `informe.tex` / `informe.pdf`: editable source and seven-page submission.
- `README.md`: installation, offline verification, classroom procedure, and PDF regeneration.
- `lab10.py`: minimal command-line helper; `test_lab10.py`: five `unittest` checks.
- `muestras/ptw.cap` and `muestras/README.md`: public offline capture and provenance.
- `evidencias/`: local test, diagnostic, sample-recovery, checksum, and document records; `REGISTRO_CLASE.md` is the unfilled worksheet for future classroom results.
- `agent_docs/`: durable project and deployment handoff documentation.

## Interfaces and Outputs

Run from this directory. The helper exposes `comprobar`, `capturar`, and `recuperar`; `--simular` previews the latter two commands. Captures and recovered keys default to `capturas/`, which is Git-ignored. Build the report with `pdflatex` as described in `README.md`.
