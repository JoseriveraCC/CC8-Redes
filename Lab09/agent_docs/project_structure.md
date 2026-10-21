# Project Structure

## Directory Layout

- `speedtest.py` — raw IPv4/TCP client, packet helpers, state handling,
  measurements, and command-line entry point.
- `server.py` — one-connection TCP receiver; validates ten equal 1000-byte
  blocks and writes the verified byte stream.
- `tests/test_speedtest.py` — packet, state-machine, and receiver unit tests.
- `tests/integration.py` — isolated end-to-end raw-TCP upload.
- `archivo_1kb.bin` and `Laboratorio_-_SpeedTest.pdf` — input fixture and
  assignment source.
- `Makefile` and `README.md` — development, verification, packaging, and user
  instructions. `Lab09_SpeedTest.zip` is the generated submission archive.
- `agent_docs/` — durable project context and deployment records.

## Interfaces and Boundaries

The client and receiver communicate through one TCP byte stream: ten exact
copies of the input, totaling 10,000 bytes. TCP reads have no file boundaries;
the receiver buffers to EOF and checks size and block equality. `server.py`
imports shared size/count constants and CLI validators from `speedtest.py`.
The receiver does not send application data that would affect upload timing.

## Tests and Supporting Assets

`make test` runs the unit suite without raw-socket privileges. The integration
test exercises the real client and receiver inside a temporary network
namespace. Bytecode caches, CSV results, received output, and the ZIP archive
are generated artifacts ignored by `.gitignore`.
