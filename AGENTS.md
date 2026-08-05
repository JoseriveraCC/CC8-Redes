# AGENTS.md

## Repository Shape
- This repo is three independent networking labs, not one buildable project: `Lab01/` Java TCP/UDP calculator, `Lab02/` Java web server, `Lab03/` UDP/DNS lab scaffold in C plus a Java broadcast sender.
- There is no root build, CI, formatter, or test runner. Run commands from the lab directory you are changing.

## Lab01
- Build from `Lab01/`: `javac Client.java Server.java`.
- Run server/client in separate terminals; args are `KEY VALUE` pairs in any order, without leading dashes: `java Server protocol TCP port 5030` and `java Client port 5030 server 127.0.0.1 protocol TCP`.
- Defaults are protocol `TCP`, server `127.0.0.1`, port `3001`; send `EXIT` to stop both sides.

## Lab02
- Build from `Lab02/`: `make` or `make classes`; run with `make run ARGS="-port 1000 -threads 3 -delay 5"`; clean with `make clean`.
- The actual entrypoint is `Lab02` (`Makefile` sets `MAIN = Lab02`), even though README text also shows `java Server`.
- `Request.getData(...)` and `Response.sendData(...)` are the intended extension points; keep their signatures because `ThreadServer` calls them directly.
- `FormatterWebServer.java`, `ThreadServer.java`, and `Server.java` are marked as non-editable by the lab README; avoid changing them unless the task explicitly requires it.
- Run from `Lab02/`: `Response` reads `./www/index.html` and `ThreadServer` writes `logs/` using relative paths.
- If adding Java source files used by Lab02, add them to the `CLASSES` list in `Lab02/Makefile`.

## Lab03
- Build/run the C scaffold from `Lab03/`: `make` builds `udp_test`, `make run` executes it, `make clean` removes the binary.
- Build/run the Java DNS server from `Lab03/`: `make javadns`, then `sudo make rundns` for UDP port `53`, or `make rundns ARGS="-port 5353 -threads 4"` for unprivileged local testing.
- The C scaffold listens on UDP port `9999`, forks, and sends one loopback test packet after 5 seconds; stop the listener manually after verification.
- Run the Java broadcast sender from `Lab03/` with `make runjava` or `make runbroadcast`; it sends to `255.255.255.255:9999` until input `EXIT`.
- `make killudp` targets UDP port `9999` using `sudo`; prefer checking/asking before using it in automated flows.
- The README objective describes a DNS server on UDP port `53`; binding that port normally requires elevated privileges on Linux.

## Generated Files
- Compiled artifacts are already present in some labs (`*.class`, `Lab03/udp_test`) and there is no `.gitignore`; avoid treating them as source changes unless the task asks for compiled outputs.
