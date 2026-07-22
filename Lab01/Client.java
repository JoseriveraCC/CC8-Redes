import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Scanner;

/**
 * Cliente del Laboratorio #01: sockets TCP y UDP.
 *
 * Ejemplos:
 *   java Client protocol TCP server 127.0.0.1 port 3001
 *   java Client port 3001 server 127.0.0.1 protocol UDP
 */
public class Client {
    private static final String DEFAULT_PROTOCOL = "TCP";
    private static final String DEFAULT_SERVER = "127.0.0.1";
    private static final int DEFAULT_PORT = 3001;
    private static final int UDP_TIMEOUT_MS = 5000;
    private static final int UDP_BUFFER_SIZE = 4096;
    private static final DateTimeFormatter LOG_DATE_FORMAT =
            DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss");

    public static void main(String[] args) {
        Map<String, String> arguments = parseArguments(args);
        String protocol = arguments.getOrDefault("protocol", DEFAULT_PROTOCOL)
                .toUpperCase(Locale.ROOT);
        String server = arguments.getOrDefault("server", DEFAULT_SERVER);
        int port = parsePort(arguments.get("port"), DEFAULT_PORT);

        if (!protocol.equals("TCP") && !protocol.equals("UDP")) {
            System.err.println("Error: protocol debe ser TCP o UDP.");
            printUsage();
            return;
        }

        System.out.printf("Cliente iniciado -> protocolo=%s, servidor=%s, puerto=%d%n",
                protocol, server, port);

        try {
            if (protocol.equals("TCP")) {
                runTcpClient(server, port);
            } else {
                runUdpClient(server, port);
            }
        } catch (IOException exception) {
            System.err.println("Error de comunicación: " + exception.getMessage());
        }
    }

    private static void runTcpClient(String server, int port) throws IOException {
        InetAddress serverAddress = InetAddress.getByName(server);

        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(serverAddress, port), 5000);

            try (BufferedReader networkInput = new BufferedReader(
                         new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
                 PrintWriter networkOutput = new PrintWriter(
                         new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8), true);
                 Scanner keyboard = new Scanner(System.in, StandardCharsets.UTF_8)) {

                String localIp = socket.getLocalAddress().getHostAddress();
                String remoteIp = socket.getInetAddress().getHostAddress();

                while (true) {
                    System.out.print("Ingrese la operación a realizar: ");
                    if (!keyboard.hasNextLine()) {
                        break;
                    }

                    String request = keyboard.nextLine().trim();
                    if (request.isEmpty()) {
                        System.out.println("Error: la operación no puede estar vacía.");
                        continue;
                    }

                    networkOutput.println(request);
                    log("<", localIp, "client", "TCP", request);

                    String response = networkInput.readLine();
                    if (response == null) {
                        System.err.println("El servidor cerró la conexión sin enviar respuesta.");
                        break;
                    }

                    log(">", remoteIp, "server", "TCP", response);
                    System.out.println("Resultado: " + response);

                    if (request.equalsIgnoreCase("EXIT") || response.equalsIgnoreCase("EXIT")) {
                        break;
                    }
                }
            }
        }
    }

    private static void runUdpClient(String server, int port) throws IOException {
        InetAddress serverAddress = InetAddress.getByName(server);

        try (DatagramSocket socket = new DatagramSocket();
             Scanner keyboard = new Scanner(System.in, StandardCharsets.UTF_8)) {

            socket.connect(serverAddress, port);
            socket.setSoTimeout(UDP_TIMEOUT_MS);

            String localIp = socket.getLocalAddress().getHostAddress();
            String remoteIp = serverAddress.getHostAddress();

            while (true) {
                System.out.print("Ingrese la operación a realizar: ");
                if (!keyboard.hasNextLine()) {
                    break;
                }

                String request = keyboard.nextLine().trim();
                if (request.isEmpty()) {
                    System.out.println("Error: la operación no puede estar vacía.");
                    continue;
                }

                byte[] requestBytes = request.getBytes(StandardCharsets.UTF_8);
                DatagramPacket requestPacket = new DatagramPacket(requestBytes, requestBytes.length);
                socket.send(requestPacket);
                log("<", localIp, "client", "UDP", request);

                try {
                    byte[] responseBuffer = new byte[UDP_BUFFER_SIZE];
                    DatagramPacket responsePacket =
                            new DatagramPacket(responseBuffer, responseBuffer.length);
                    socket.receive(responsePacket);

                    String response = new String(
                            responsePacket.getData(),
                            responsePacket.getOffset(),
                            responsePacket.getLength(),
                            StandardCharsets.UTF_8);

                    log(">", remoteIp, "server", "UDP", response);
                    System.out.println("Resultado: " + response);

                    if (request.equalsIgnoreCase("EXIT") || response.equalsIgnoreCase("EXIT")) {
                        break;
                    }
                } catch (SocketTimeoutException exception) {
                    System.err.printf("Tiempo de espera agotado: el servidor no respondió en %d ms.%n",
                            UDP_TIMEOUT_MS);
                }
            }
        }
    }

    private static Map<String, String> parseArguments(String[] args) {
        Map<String, String> values = new HashMap<>();

        for (int index = 0; index < args.length; index += 2) {
            if (index + 1 >= args.length) {
                System.err.println("Advertencia: se ignoró el argumento sin valor: " + args[index]);
                break;
            }

            String key = args[index].toLowerCase(Locale.ROOT);
            String value = args[index + 1];

            if (key.equals("protocol") || key.equals("server") || key.equals("port")) {
                values.put(key, value);
            } else {
                System.err.println("Advertencia: argumento desconocido ignorado: " + key);
            }
        }

        return values;
    }

    private static int parsePort(String value, int defaultPort) {
        if (value == null) {
            return defaultPort;
        }

        try {
            int port = Integer.parseInt(value);
            if (port < 1 || port > 65535) {
                throw new NumberFormatException("fuera de rango");
            }
            return port;
        } catch (NumberFormatException exception) {
            System.err.printf("Advertencia: puerto inválido '%s'; se utilizará %d.%n",
                    value, defaultPort);
            return defaultPort;
        }
    }

    private static void log(
            String direction,
            String host,
            String socketType,
            String protocol,
            String description) {

        String dateTime = LocalDateTime.now().format(LOG_DATE_FORMAT);
        System.out.printf("%s %s %s [%s] %s: %s%n",
                direction, host, socketType, dateTime, protocol, description);
    }

    private static void printUsage() {
        System.out.println("Uso: java Client protocol <TCP|UDP> server <IP> port <PUERTO>");
        System.out.println("Valores por defecto: protocol TCP server 127.0.0.1 port 3001");
    }
}
