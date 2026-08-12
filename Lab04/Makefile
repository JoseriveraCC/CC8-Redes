CC = gcc
CFLAGS = -O2 -Wall -Wextra -std=c11
LDLIBS = -lm

SRC = ntp_client.c
OUT = ntp_client

all: $(OUT)

$(OUT): $(SRC)
	$(CC) $(CFLAGS) -o $(OUT) $(SRC) $(LDLIBS)

run: $(OUT)
	./$(OUT) $(ARGS)

# Ejecucion rapida para pruebas de laboratorio: intervalo corto y pocas iteraciones.
test: $(OUT)
	./$(OUT) --threshold-ms 500 --interval 2 --max-iterations 3 --timeout-ms 3000

# Ejemplo usando una fecha interna local Guatemala muy desfasada.
demo-old-date: $(OUT)
	./$(OUT) --date '2020-09-01 21:00:17.123' --threshold-ms 10 --interval 2 --max-iterations 4 --timeout-ms 3000

clean:
	rm -f $(OUT)
