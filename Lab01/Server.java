import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.math.BigDecimal;
import java.math.MathContext;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Servidor del Laboratorio #01: sockets TCP y UDP.
 *
 * Ejemplos:
 *   java Server protocol TCP port 3001
 *   java Server port 3001 protocol UDP
 */
public class Server {
    private static final String DEFAULT_PROTOCOL = "TCP";
    private static final int DEFAULT_PORT = 3001;
    private static final int UDP_BUFFER_SIZE = 4096;
    private static final DateTimeFormatter LOG_DATE_FORMAT =
            DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss");
    private static final MathContext MATH_CONTEXT = MathContext.DECIMAL64;

    private static final Pattern OPERATION_PATTERN = Pattern.compile(
            "^\\s*([+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+))\\s*([+\\-*/%])\\s*" +
            "([+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+))\\s*$");

    public static void main(String[] args) {
        Map<String, String> arguments = parseArguments(args);
        String protocol = arguments.getOrDefault("protocol", DEFAULT_PROTOCOL)
                .toUpperCase(Locale.ROOT);
        int port = parsePort(arguments.get("port"), DEFAULT_PORT);

        if (!protocol.equals("TCP") && !protocol.equals("UDP")) {
            System.err.println("Error: protocol debe ser TCP o UDP.");
            printUsage();
            return;
        }

        System.out.printf("Servidor iniciado -> protocolo=%s, puerto=%d%n", protocol, port);
        System.out.println("El servidor finalizará cuando reciba EXIT.");

        try {
            if (protocol.equals("TCP")) {
                runTcpServer(port);
            } else {
                runUdpServer(port);
            }
        } catch (IOException exception) {
            System.err.println("Error del servidor: " + exception.getMessage());
        }
    }

    private static void runTcpServer(int port) throws IOException {
        try (ServerSocket serverSocket = new ServerSocket(port)) {
            boolean running = true;

            while (running) {
                System.out.println("Esperando cliente TCP...");

                try (Socket clientSocket = serverSocket.accept();
                     BufferedReader networkInput = new BufferedReader(
                             new InputStreamReader(
                                     clientSocket.getInputStream(), StandardCharsets.UTF_8));
                     PrintWriter networkOutput = new PrintWriter(
                             new OutputStreamWriter(
                                     clientSocket.getOutputStream(), StandardCharsets.UTF_8), true)) {

                    String clientIp = clientSocket.getInetAddress().getHostAddress();
                    String serverIp = resolveServerIp(clientSocket.getLocalAddress());
                    System.out.println("Cliente TCP conectado: " + clientIp);

                    String request;
                    while ((request = networkInput.readLine()) != null) {
                        request = request.trim();
                        log(">", clientIp, "client", "TCP", request);

                        String response;
                        if (request.equalsIgnoreCase("EXIT")) {
                            response = "EXIT";
                            running = false;
                        } else {
                            response = evaluateOperation(request);
                        }

                        networkOutput.println(response);
                        log("<", serverIp, "server", "TCP", response);

                        if (!running) {
                            break;
                        }
                    }
                }
            }
        }

        System.out.println("Servidor TCP finalizado.");
    }

    private static void runUdpServer(int port) throws IOException {
        try (DatagramSocket socket = new DatagramSocket(port)) {
            boolean running = true;
            String serverIp = resolveServerIp(socket.getLocalAddress());

            while (running) {
                byte[] requestBuffer = new byte[UDP_BUFFER_SIZE];
                DatagramPacket requestPacket =
                        new DatagramPacket(requestBuffer, requestBuffer.length);
                socket.receive(requestPacket);

                String request = new String(
                        requestPacket.getData(),
                        requestPacket.getOffset(),
                        requestPacket.getLength(),
                        StandardCharsets.UTF_8).trim();

                String clientIp = requestPacket.getAddress().getHostAddress();
                log(">", clientIp, "client", "UDP", request);

                String response;
                if (request.equalsIgnoreCase("EXIT")) {
                    response = "EXIT";
                    running = false;
                } else {
                    response = evaluateOperation(request);
                }

                byte[] responseBytes = response.getBytes(StandardCharsets.UTF_8);
                DatagramPacket responsePacket = new DatagramPacket(
                        responseBytes,
                        responseBytes.length,
                        requestPacket.getAddress(),
                        requestPacket.getPort());
                socket.send(responsePacket);
                log("<", serverIp, "server", "UDP", response);
            }
        }

        System.out.println("Servidor UDP finalizado.");
    }

    private static String evaluateOperation(String expression) {
        Matcher matcher = OPERATION_PATTERN.matcher(expression);
        if (!matcher.matches()) {
            return "ERROR: formato inválido. Use número operador número, por ejemplo 8%5.";
        }

        try {
            BigDecimal left = new BigDecimal(matcher.group(1));
            BigDecimal right = new BigDecimal(matcher.group(3));
            char operator = matcher.group(2).charAt(0);

            BigDecimal result = switch (operator) {
                case '+' -> left.add(right, MATH_CONTEXT);
                case '-' -> left.subtract(right, MATH_CONTEXT);
                case '*' -> left.multiply(right, MATH_CONTEXT);
                case '/' -> {
                    validateNonZero(right, "división");
                    yield left.divide(right, MATH_CONTEXT);
                }
                case '%' -> {
                    validateNonZero(right, "módulo");
                    yield left.remainder(right, MATH_CONTEXT);
                }
                default -> throw new IllegalArgumentException("Operador no soportado");
            };

            return formatNumber(result);
        } catch (ArithmeticException exception) {
            return "ERROR: " + exception.getMessage() + ".";
        } catch (NumberFormatException exception) {
            return "ERROR: número inválido.";
        }
    }

    private static void validateNonZero(BigDecimal value, String operationName) {
        if (value.compareTo(BigDecimal.ZERO) == 0) {
            throw new ArithmeticException(operationName + " entre cero");
        }
    }

    private static String formatNumber(BigDecimal value) {
        BigDecimal normalized = value.stripTrailingZeros();
        if (normalized.compareTo(BigDecimal.ZERO) == 0) {
            return "0";
        }
        return normalized.toPlainString();
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

            if (key.equals("protocol") || key.equals("port")) {
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

    private static String resolveServerIp(InetAddress boundAddress) {
        if (boundAddress != null && !boundAddress.isAnyLocalAddress()) {
            return boundAddress.getHostAddress();
        }

        try {
            return InetAddress.getLocalHost().getHostAddress();
        } catch (IOException exception) {
            return boundAddress == null ? "0.0.0.0" : boundAddress.getHostAddress();
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
        System.out.println("Uso: java Server protocol <TCP|UDP> port <PUERTO>");
        System.out.println("Valores por defecto: protocol TCP port 3001");
    }
}
