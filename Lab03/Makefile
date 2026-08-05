CC = gcc
JAVAC = javac
JAVA = java
JAVA_BIN := $(shell command -v $(JAVA))

CFLAGS = -O2 -Wall -Wextra

SRC = lab_3.c
OUT = udp_test
DNS_MAIN = DnsServer

all: $(OUT)

$(OUT): $(SRC)
	$(CC) $(CFLAGS) -o $(OUT) $(SRC)

run: $(OUT)
	./$(OUT)

javadns:
	$(JAVAC) $(DNS_MAIN).java

rundns: javadns
	$(JAVA) $(DNS_MAIN) $(ARGS)

rundns53: javadns
	sudo $(JAVA_BIN) $(DNS_MAIN) $(ARGS)

runjava:
	javac UdpBroadcastSender.java && java UdpBroadcastSender

runbroadcast:
	$(JAVAC) UdpBroadcastSender.java && $(JAVA) UdpBroadcastSender

killudp:
	sudo kill -9 $(sudo lsof -t -iUDP:9999)

clean:
	rm -f $(OUT)
	rm -f *.class
