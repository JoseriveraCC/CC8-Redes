import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class DnsServer {
    private static final int DEFAULT_PORT = 53;
    private static final int DEFAULT_THREADS = 4;
    private static final int MAX_DNS_PACKET = 512;
    private static final int DNS_TIMEOUT_MS = 3000;
    private static final int TTL_SECONDS = 300;
    private static final int TYPE_A = 1;
    private static final int TYPE_SOA = 6;
    private static final int TYPE_PTR = 12;
    private static final int TYPE_AAAA = 28;
    private static final int CLASS_IN = 1;
    private static final int RCODE_FORMAT_ERROR = 1;
    private static final int RCODE_SERVER_FAILURE = 2;
    private static final int RCODE_NAME_ERROR = 3;
    private static final DateTimeFormatter LOG_DATE_FORMAT =
            DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss");

    private static final String[] UPSTREAM_DNS = {"1.1.1.1", "8.8.8.8"};
    private static final Map<String, String> A_RECORDS = new HashMap<>();
    private static final Map<String, String> AAAA_RECORDS = new HashMap<>();
    private static final Map<String, String> PTR_RECORDS = new HashMap<>();

    static {
        A_RECORDS.put("lab.local", "127.0.0.1");
        A_RECORDS.put("www.lab.local", "127.0.0.1");
        A_RECORDS.put("ns.lab.local", "127.0.0.1");
        A_RECORDS.put("server.lab.local", "192.168.1.53");

        AAAA_RECORDS.put("lab.local", "::1");
        AAAA_RECORDS.put("www.lab.local", "::1");
        AAAA_RECORDS.put("ns.lab.local", "::1");
        AAAA_RECORDS.put("server.lab.local", "fd00::53");

        PTR_RECORDS.put("1.0.0.127.in-addr.arpa", "localhost");
        PTR_RECORDS.put("53.1.168.192.in-addr.arpa", "server.lab.local");
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> options = parseArgs(args);
        int port = parseInt(options.get("-port"), DEFAULT_PORT);
        int threads = parseInt(options.get("-threads"), DEFAULT_THREADS);

        ExecutorService pool = Executors.newFixedThreadPool(threads);
        try (DatagramSocket socket = new DatagramSocket(port)) {
            System.out.printf("DNS server listening on UDP:%d with %d threads%n", port, threads);
            while (true) {
                byte[] buffer = new byte[MAX_DNS_PACKET];
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                socket.receive(packet);
                byte[] request = Arrays.copyOfRange(packet.getData(), packet.getOffset(),
                        packet.getOffset() + packet.getLength());
                InetSocketAddress client = new InetSocketAddress(packet.getAddress(), packet.getPort());
                pool.execute(() -> handleRequest(socket, request, client));
            }
        }
    }

    private static void handleRequest(DatagramSocket serverSocket, byte[] request, InetSocketAddress client) {
        int id = request.length >= 2 ? readUnsignedShort(request, 0) : 0;
        try {
            DnsMessage message = parseRequest(request);
            log(">", client.getAddress().getHostAddress(), client.getPort(), id, summarize(message.questions));

            byte[] response = buildLocalResponse(message, request);
            if (response == null) {
                response = forwardToUpstream(request);
            }

            if (response == null) {
                response = buildErrorResponse(request, RCODE_SERVER_FAILURE);
            }

            sendResponse(serverSocket, response, client);
            log("<", client.getAddress().getHostAddress(), client.getPort(), id,
                    response.length + " bytes");
        } catch (DnsFormatException exception) {
            sendQuietly(serverSocket, buildErrorResponse(request, RCODE_FORMAT_ERROR), client);
            log("!", client.getAddress().getHostAddress(), client.getPort(), id,
                    "format error: " + exception.getMessage());
        } catch (Exception exception) {
            sendQuietly(serverSocket, buildErrorResponse(request, RCODE_SERVER_FAILURE), client);
            log("!", client.getAddress().getHostAddress(), client.getPort(), id,
                    "server error: " + exception.getMessage());
        }
    }

    private static DnsMessage parseRequest(byte[] packet) throws DnsFormatException {
        if (packet.length < 12) {
            throw new DnsFormatException("packet shorter than DNS header");
        }

        DnsMessage message = new DnsMessage();
        message.id = readUnsignedShort(packet, 0);
        message.flags = readUnsignedShort(packet, 2);
        int questionCount = readUnsignedShort(packet, 4);
        int offset = 12;

        for (int index = 0; index < questionCount; index++) {
            NameResult name = readName(packet, offset);
            offset = name.nextOffset;
            if (offset + 4 > packet.length) {
                throw new DnsFormatException("truncated question");
            }

            DnsQuestion question = new DnsQuestion();
            question.name = normalizeName(name.name);
            question.type = readUnsignedShort(packet, offset);
            question.qclass = readUnsignedShort(packet, offset + 2);
            question.offset = offset;
            message.questions.add(question);
            offset += 4;
        }

        message.questionEndOffset = offset;
        return message;
    }

    private static byte[] buildLocalResponse(DnsMessage message, byte[] request) throws Exception {
        List<ResourceRecord> answers = new ArrayList<>();
        boolean localDomainQuery = false;

        for (DnsQuestion question : message.questions) {
            List<ResourceRecord> records = localRecordsFor(question);
            answers.addAll(records);
            localDomainQuery = localDomainQuery || isLocalDomain(question.name);
        }

        if (answers.isEmpty() && !localDomainQuery) {
            return null;
        }

        int rcode = answers.isEmpty() ? RCODE_NAME_ERROR : 0;
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        writeShort(out, message.id);
        writeShort(out, responseFlags(message.flags, rcode));
        writeShort(out, message.questions.size());
        writeShort(out, answers.size());
        writeShort(out, 0);
        writeShort(out, 0);
        out.write(request, 12, message.questionEndOffset - 12);

        for (ResourceRecord answer : answers) {
            writeName(out, answer.name);
            writeShort(out, answer.type);
            writeShort(out, CLASS_IN);
            writeInt(out, TTL_SECONDS);
            writeShort(out, answer.data.length);
            out.write(answer.data);
        }

        return out.toByteArray();
    }

    private static List<ResourceRecord> localRecordsFor(DnsQuestion question) throws Exception {
        List<ResourceRecord> records = new ArrayList<>();
        if (question.qclass != CLASS_IN) {
            return records;
        }

        if (question.type == TYPE_A && A_RECORDS.containsKey(question.name)) {
            records.add(new ResourceRecord(question.name, TYPE_A,
                    InetAddress.getByName(A_RECORDS.get(question.name)).getAddress()));
        } else if (question.type == TYPE_AAAA && AAAA_RECORDS.containsKey(question.name)) {
            records.add(new ResourceRecord(question.name, TYPE_AAAA,
                    InetAddress.getByName(AAAA_RECORDS.get(question.name)).getAddress()));
        } else if (question.type == TYPE_PTR && PTR_RECORDS.containsKey(question.name)) {
            records.add(new ResourceRecord(question.name, TYPE_PTR, encodeName(PTR_RECORDS.get(question.name))));
        } else if (question.type == TYPE_SOA && isLocalDomain(question.name)) {
            records.add(new ResourceRecord(question.name, TYPE_SOA, encodeSoaRecord()));
        }

        return records;
    }

    private static byte[] forwardToUpstream(byte[] request) {
        for (String upstream : UPSTREAM_DNS) {
            try (DatagramSocket socket = new DatagramSocket()) {
                socket.setSoTimeout(DNS_TIMEOUT_MS);
                InetAddress address = InetAddress.getByName(upstream);
                DatagramPacket query = new DatagramPacket(request, request.length, address, 53);
                socket.send(query);

                byte[] buffer = new byte[MAX_DNS_PACKET];
                DatagramPacket response = new DatagramPacket(buffer, buffer.length);
                socket.receive(response);
                return Arrays.copyOfRange(response.getData(), response.getOffset(),
                        response.getOffset() + response.getLength());
            } catch (SocketTimeoutException exception) {
                System.err.printf("Upstream DNS %s timed out%n", upstream);
            } catch (IOException exception) {
                System.err.printf("Upstream DNS %s failed: %s%n", upstream, exception.getMessage());
            }
        }
        return null;
    }

    private static byte[] buildErrorResponse(byte[] request, int rcode) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        int id = request.length >= 2 ? readUnsignedShort(request, 0) : 0;
        int requestFlags = request.length >= 4 ? readUnsignedShort(request, 2) : 0;
        int qdCount = request.length >= 6 ? readUnsignedShort(request, 4) : 0;
        int questionEnd = Math.min(request.length, findQuestionEnd(request, qdCount));

        writeShort(out, id);
        writeShort(out, responseFlags(requestFlags, rcode));
        writeShort(out, questionEnd >= 12 ? qdCount : 0);
        writeShort(out, 0);
        writeShort(out, 0);
        writeShort(out, 0);
        if (questionEnd > 12) {
            out.write(request, 12, questionEnd - 12);
        }
        return out.toByteArray();
    }

    private static int findQuestionEnd(byte[] packet, int count) {
        try {
            int offset = 12;
            for (int index = 0; index < count; index++) {
                offset = readName(packet, offset).nextOffset + 4;
            }
            return offset;
        } catch (Exception exception) {
            return 12;
        }
    }

    private static NameResult readName(byte[] packet, int startOffset) throws DnsFormatException {
        StringBuilder name = new StringBuilder();
        int offset = startOffset;
        int nextOffset = -1;
        int jumps = 0;

        while (true) {
            if (offset >= packet.length) {
                throw new DnsFormatException("name exceeds packet length");
            }

            int length = packet[offset] & 0xff;
            if ((length & 0xc0) == 0xc0) {
                if (offset + 1 >= packet.length) {
                    throw new DnsFormatException("truncated compression pointer");
                }
                if (nextOffset == -1) {
                    nextOffset = offset + 2;
                }
                offset = ((length & 0x3f) << 8) | (packet[offset + 1] & 0xff);
                if (++jumps > 20) {
                    throw new DnsFormatException("too many compression jumps");
                }
            } else if (length == 0) {
                offset++;
                if (nextOffset == -1) {
                    nextOffset = offset;
                }
                break;
            } else {
                offset++;
                if (offset + length > packet.length) {
                    throw new DnsFormatException("truncated label");
                }
                if (name.length() > 0) {
                    name.append('.');
                }
                name.append(new String(packet, offset, length, StandardCharsets.US_ASCII));
                offset += length;
            }
        }

        return new NameResult(name.toString(), nextOffset);
    }

    private static byte[] encodeSoaRecord() throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        out.write(encodeName("ns.lab.local"));
        out.write(encodeName("hostmaster.lab.local"));
        writeInt(out, 2026072801L);
        writeInt(out, 3600);
        writeInt(out, 600);
        writeInt(out, 86400);
        writeInt(out, 300);
        return out.toByteArray();
    }

    private static byte[] encodeName(String name) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        writeName(out, name);
        return out.toByteArray();
    }

    private static void writeName(ByteArrayOutputStream out, String name) throws IOException {
        String cleanName = normalizeName(name);
        if (cleanName.isEmpty()) {
            out.write(0);
            return;
        }
        for (String label : cleanName.split("\\.")) {
            byte[] bytes = label.getBytes(StandardCharsets.US_ASCII);
            out.write(bytes.length);
            out.write(bytes);
        }
        out.write(0);
    }

    private static void sendResponse(DatagramSocket socket, byte[] response, InetSocketAddress client)
            throws IOException {
        DatagramPacket packet = new DatagramPacket(response, response.length,
                client.getAddress(), client.getPort());
        synchronized (socket) {
            socket.send(packet);
        }
    }

    private static void sendQuietly(DatagramSocket socket, byte[] response, InetSocketAddress client) {
        try {
            sendResponse(socket, response, client);
        } catch (IOException ignored) {
        }
    }

    private static Map<String, String> parseArgs(String[] args) {
        Map<String, String> options = new HashMap<>();
        for (int index = 0; index < args.length; index += 2) {
            if (index + 1 >= args.length) {
                break;
            }
            options.put(args[index].toLowerCase(Locale.ROOT), args[index + 1]);
        }
        return options;
    }

    private static int parseInt(String value, int defaultValue) {
        if (value == null) {
            return defaultValue;
        }
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException exception) {
            return defaultValue;
        }
    }

    private static int responseFlags(int requestFlags, int rcode) {
        return 0x8000 | (requestFlags & 0x0100) | 0x0080 | (rcode & 0x000f);
    }

    private static boolean isLocalDomain(String name) {
        return name.equals("lab.local") || name.endsWith(".lab.local")
                || PTR_RECORDS.containsKey(name);
    }

    private static String normalizeName(String name) {
        String lower = name.toLowerCase(Locale.ROOT);
        return lower.endsWith(".") ? lower.substring(0, lower.length() - 1) : lower;
    }

    private static String summarize(List<DnsQuestion> questions) {
        List<String> parts = new ArrayList<>();
        for (DnsQuestion question : questions) {
            parts.add(question.name + " " + typeName(question.type));
        }
        return String.join(", ", parts);
    }

    private static String typeName(int type) {
        return switch (type) {
            case TYPE_A -> "A";
            case TYPE_AAAA -> "AAAA";
            case TYPE_PTR -> "PTR";
            case TYPE_SOA -> "SOA";
            default -> "TYPE" + type;
        };
    }

    private static void log(String direction, String host, int port, int id, String message) {
        String dateTime = LocalDateTime.now().format(LOG_DATE_FORMAT);
        System.out.printf("%s %s:%d [%s] DNS id=%d %s%n", direction, host, port, dateTime, id, message);
    }

    private static int readUnsignedShort(byte[] data, int offset) {
        return ((data[offset] & 0xff) << 8) | (data[offset + 1] & 0xff);
    }

    private static void writeShort(ByteArrayOutputStream out, int value) {
        out.write((value >>> 8) & 0xff);
        out.write(value & 0xff);
    }

    private static void writeInt(ByteArrayOutputStream out, long value) {
        out.write((int) ((value >>> 24) & 0xff));
        out.write((int) ((value >>> 16) & 0xff));
        out.write((int) ((value >>> 8) & 0xff));
        out.write((int) (value & 0xff));
    }

    private static class DnsMessage {
        int id;
        int flags;
        int questionEndOffset;
        List<DnsQuestion> questions = new ArrayList<>();
    }

    private static class DnsQuestion {
        String name;
        int type;
        int qclass;
        int offset;
    }

    private static class ResourceRecord {
        String name;
        int type;
        byte[] data;

        ResourceRecord(String name, int type, byte[] data) {
            this.name = name;
            this.type = type;
            this.data = data;
        }
    }

    private static class NameResult {
        String name;
        int nextOffset;

        NameResult(String name, int nextOffset) {
            this.name = name;
            this.nextOffset = nextOffset;
        }
    }

    private static class DnsFormatException extends Exception {
        DnsFormatException(String message) {
            super(message);
        }
    }
}
