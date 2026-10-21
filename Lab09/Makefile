PYTHON ?= python3
SERVER_ARGS ?=
CLIENT_ARGS ?=

.PHONY: all check test server client integration integration-user zip clean

all: check

# Python no necesita compilador externo; verifica sintaxis y genera bytecode.
check:
	$(PYTHON) -m py_compile speedtest.py server.py tests/test_speedtest.py tests/integration.py

test: check
	$(PYTHON) -m unittest discover -s tests -v

server:
	$(PYTHON) server.py $(SERVER_ARGS)

client:
	$(PYTHON) speedtest.py $(CLIENT_ARGS)

# Se llama con sudo; las reglas temporales solo existen dentro de esta red.
integration: check
	LAB09_PARENT_NETNS=$$(readlink /proc/self/ns/net) unshare --net $(PYTHON) tests/integration.py

# Alternativa sin sudo cuando Linux permite user namespaces sin privilegios.
integration-user: check
	LAB09_PARENT_NETNS=$$(readlink /proc/self/ns/net) unshare --user --map-root-user --net $(PYTHON) tests/integration.py

zip: check
	$(PYTHON) -c 'from zipfile import ZipFile, ZIP_DEFLATED; files = ["speedtest.py", "server.py", "Makefile", "README.md", "archivo_1kb.bin", "tests/test_speedtest.py", "tests/integration.py", "Laboratorio_-_SpeedTest.pdf"]; archive = ZipFile("Lab09_SpeedTest.zip", "w", ZIP_DEFLATED); [archive.write(name, "Lab09/" + name) for name in files]; archive.close()'

clean:
	$(PYTHON) -c 'import shutil; from pathlib import Path; [shutil.rmtree(path) for path in (Path("__pycache__"), Path("tests/__pycache__")) if path.exists()]'
