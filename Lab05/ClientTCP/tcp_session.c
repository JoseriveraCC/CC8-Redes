#include "tcp_session.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/time.h>

#include "ip_header.h"
#include "tcp_header.h"
#include "checksum.h"
#include "raw_socket.h"

#define MAX_PACKET_SIZE 4096
#define WIRESHARK_LINK_HEADER_LEN 14

static void format_flags(uint8_t flags, char *out, size_t out_size)
{
    int first = 1;
    out[0] = '\0';

    struct {
        uint8_t bit;
        const char *name;
    } flag_names[] = {
        {TCP_SYN, "SYN"},
        {TCP_PSH, "PSH"},
        {TCP_FIN, "FIN"},
        {TCP_RST, "RST"},
        {TCP_ACK, "ACK"},
        {TCP_URG, "URG"},
    };

    for (size_t i = 0; i < sizeof(flag_names) / sizeof(flag_names[0]); i++) {
        if (!(flags & flag_names[i].bit)) continue;
        snprintf(out + strlen(out), out_size - strlen(out), "%s%s",
                 first ? "" : ", ", flag_names[i].name);
        first = 0;
    }
}

static void print_data(const uint8_t *data, int data_len)
{
    printf(" DATA=\"");
    for (int i = 0; i < data_len; i++) {
        if (data[i] == '\n') printf("\\n");
        else if (data[i] == '\r') printf("\\r");
        else if (data[i] >= 32 && data[i] <= 126) putchar(data[i]);
        else printf("\\x%02x", data[i]);
    }
    printf("\"");
}

static void log_segment(const char *from, const char *to, uint8_t flags,
                        const tcp_session_t *s, uint32_t seq, uint32_t ack,
                        uint16_t src_port, uint16_t dst_port, uint16_t window,
                        uint16_t checksum, int packet_len, int data_len,
                        const uint8_t *data)
{
    char flags_text[64];
    struct timeval now;
    double elapsed;
    uint32_t rel_seq = seq;
    uint32_t rel_ack = ack;

    (void)to;
    format_flags(flags, flags_text, sizeof(flags_text));

    if (!strcmp(from, "Client")) {
        rel_seq = seq - s->client_isn;
        if ((flags & TCP_ACK) && s->has_server_isn) rel_ack = ack - s->server_isn;
    } else {
        if (s->has_server_isn) rel_seq = seq - s->server_isn;
        if (flags & TCP_ACK) rel_ack = ack - s->client_isn;
    }

    gettimeofday(&now, NULL);
    elapsed = (double)(now.tv_sec - s->start_time.tv_sec) +
              (double)(now.tv_usec - s->start_time.tv_usec) / 1000000.0;

    printf("%-4u %-10.6f %-15s %-15s %-8s %-6d %u -> %u [%-9s] Seq=%u",
           s->segment_no, elapsed,
           !strcmp(from, "Client") ? s->local_ip : s->server_ip,
           !strcmp(from, "Client") ? s->server_ip : s->local_ip,
           "TCP", packet_len + WIRESHARK_LINK_HEADER_LEN, src_port, dst_port,
           flags_text, rel_seq);
    if (flags & TCP_ACK) printf(" Ack=%u", rel_ack);
    printf(" Win=%u Len=%d Checksum=0x%04x", window, data_len, checksum);
    if (data && data_len > 0) print_data(data, data_len);
    printf("\n");
}

static void print_session_header(void)
{
    printf("==================== TCP SESSION ====================\n");
    printf("%-4s %-10s %-15s %-15s %-8s %-6s %s\n",
           "No.", "Time", "Source", "Destination", "Protocol", "Length", "Info");
}

static void print_section(const char *title)
{
    printf("-------------------- %-28s\n", title);
}

static int build_packet(uint8_t *packet, const tcp_session_t *s, uint8_t flags,
                        const char *data, size_t data_len)
{
    ip_header_t *iph = (ip_header_t *)packet;
    tcp_header_t *tcph = (tcp_header_t *)(packet + sizeof(ip_header_t));
    uint8_t *payload = packet + sizeof(ip_header_t) + sizeof(tcp_header_t);

    if (data && data_len) memcpy(payload, data, data_len);

    uint16_t tcp_len = (uint16_t)(sizeof(tcp_header_t) + data_len);

    build_tcp_header(tcph, s->local_port, s->server_port, s->seq, s->ack, flags, 5840);
    build_ip_header(iph, s->local_ip, s->server_ip, tcp_len);

    iph->checksum = calculate_checksum((uint16_t *)iph, sizeof(ip_header_t));
    tcph->checksum = calculate_tcp_checksum(iph->src_addr, iph->dst_addr, (uint8_t *)tcph, tcp_len);

    return (int)(sizeof(ip_header_t) + tcp_len);
}

static int wait_for_packet(tcp_session_t *s, uint8_t flags_mask, uint8_t flags_value,
                           tcp_header_t *out_tcph, uint8_t *out_payload,
                           int max_payload, int *out_payload_len,
                           int *out_packet_len, int timeout_sec)
{
    static uint8_t buffer[MAX_PACKET_SIZE];
    time_t start = time(NULL);

    while (difftime(time(NULL), start) < timeout_sec) {
        int len = receive_packet(s->sockfd, buffer, sizeof(buffer), 200);
        if (len < (int)(sizeof(ip_header_t) + sizeof(tcp_header_t))) continue;

        ip_header_t *iph = (ip_header_t *)buffer;
        if (iph->protocol != IPPROTO_TCP) continue;

        int ip_len = (iph->ihl_version & 0x0F) * 4;
        if (len < ip_len + (int)sizeof(tcp_header_t)) continue;

        tcp_header_t *tcph = (tcp_header_t *)(buffer + ip_len);
        struct in_addr addr = {.s_addr = iph->src_addr};

        if (strcmp(inet_ntoa(addr), s->server_ip) != 0) continue;
        if (ntohs(tcph->src_port) != s->server_port) continue;
        if (ntohs(tcph->dst_port) != s->local_port) continue;
        if ((tcph->flags & flags_mask) != flags_value) continue;

        memcpy(out_tcph, tcph, sizeof(*out_tcph));

        int tcp_header_len = ((tcph->data_offset_reserved >> 4) & 0x0F) * 4;
        int payload_offset = ip_len + tcp_header_len;
        int payload_len = len - payload_offset;

        if (payload_len < 0) payload_len = 0;

        if (out_payload && max_payload > 0) {
            int copy_len = payload_len < max_payload ? payload_len : max_payload;
            memcpy(out_payload, buffer + payload_offset, copy_len);
            *out_payload_len = copy_len;
        } else {
            *out_payload_len = payload_len;
        }

        if (out_packet_len) *out_packet_len = len;

        return 0;
    }

    return -1;
}

static int send_control(tcp_session_t *s, uint8_t flags)
{
    uint8_t packet[MAX_PACKET_SIZE];
    int len = build_packet(packet, s, flags, NULL, 0);

    if (send_packet(s->sockfd, packet, len, s->server_ip) < 0) return -1;

    tcp_header_t *tcph = (tcp_header_t *)(packet + sizeof(ip_header_t));

    s->segment_no++;
    log_segment("Client", "Server", flags, s, s->seq, s->ack,
                s->local_port, s->server_port, 5840, ntohs(tcph->checksum),
                len, 0, NULL);
    return 0;
}

int tcp_session_open(tcp_session_t *s, const char *local_ip, const char *server_ip,
                     uint16_t local_port, uint16_t server_port, const char *capture_interface)
{
    memset(s, 0, sizeof(*s));

    strncpy(s->local_ip, local_ip, sizeof(s->local_ip) - 1);
    strncpy(s->server_ip, server_ip, sizeof(s->server_ip) - 1);

    s->server_port = server_port;
    s->local_port = local_port ? local_port : (uint16_t)(40000 + rand() % 10000);
    s->seq = (uint32_t)rand();
    s->client_isn = s->seq;
    s->has_server_isn = 0;
    s->segment_no = 0;
    gettimeofday(&s->start_time, NULL);
    s->server_closed = 0;

    printf("[*] Local port: %u\n", s->local_port);

    s->sockfd = create_raw_socket(capture_interface);
    return s->sockfd < 0 ? -1 : 0;
}

int tcp_session_handshake(tcp_session_t *s, int timeout_sec)
{
    uint8_t packet[MAX_PACKET_SIZE];
    tcp_header_t recv_tcph;
    int recv_payload_len;
    int recv_packet_len;

    print_session_header();
    print_section("HANDSHAKE");

    int len = build_packet(packet, s, TCP_SYN, NULL, 0);
    if (send_packet(s->sockfd, packet, len, s->server_ip) < 0) return -1;
    tcp_header_t *send_tcph = (tcp_header_t *)(packet + sizeof(ip_header_t));
    s->segment_no++;
    log_segment("Client", "Server", TCP_SYN, s, s->seq, s->ack,
                s->local_port, s->server_port, 5840, ntohs(send_tcph->checksum),
                len, 0, NULL);

    printf("[*] Waiting for SYN+ACK...\n");

    if (wait_for_packet(s, TCP_SYN | TCP_ACK, TCP_SYN | TCP_ACK,
                        &recv_tcph, NULL, 0, &recv_payload_len,
                        &recv_packet_len, timeout_sec) != 0) {
        fprintf(stderr, "[!] SYN+ACK timeout\n");
        return -1;
    }

    uint32_t server_seq = ntohl(recv_tcph.seq_num);
    uint32_t server_ack = ntohl(recv_tcph.ack_num);
    s->server_isn = server_seq;
    s->has_server_isn = 1;
    s->segment_no++;
    log_segment("Server", "Client", recv_tcph.flags, s, server_seq, server_ack,
                ntohs(recv_tcph.src_port), ntohs(recv_tcph.dst_port),
                ntohs(recv_tcph.window), ntohs(recv_tcph.checksum), recv_packet_len,
                0, NULL);

    s->seq++;
    s->ack = server_seq + 1;

    return send_control(s, TCP_ACK) < 0 ? -1 : 0;
}

int tcp_session_send_message(tcp_session_t *s, const char *message)
{
    char buffer[TCP_SESSION_MAX_MSG + 2];
    size_t len = strlen(message);

    if (len > TCP_SESSION_MAX_MSG - 1) len = TCP_SESSION_MAX_MSG - 1;

    memcpy(buffer, message, len);

    if (len == 0 || buffer[len - 1] != '\n') buffer[len++] = '\n';

    print_section("DATA");

    uint8_t packet[MAX_PACKET_SIZE];
    int packet_len = build_packet(packet, s, TCP_PSH | TCP_ACK, buffer, len);

    if (send_packet(s->sockfd, packet, packet_len, s->server_ip) < 0) return -1;

    tcp_header_t *tcph = (tcp_header_t *)(packet + sizeof(ip_header_t));

    s->segment_no++;
    log_segment("Client", "Server", TCP_PSH | TCP_ACK, s, s->seq, s->ack,
                s->local_port, s->server_port, 5840, ntohs(tcph->checksum),
                packet_len, (int)len, (const uint8_t *)buffer);
    s->seq += (uint32_t)len;
    return 0;
}

int tcp_session_receive_message(tcp_session_t *s, char *out_buf,
                                size_t out_buf_size, int timeout_sec)
{
    uint8_t payload[TCP_SESSION_MAX_MSG + 1];
    tcp_header_t recv_tcph;
    int payload_len;
    int packet_len;
    time_t start = time(NULL);

    while (difftime(time(NULL), start) < timeout_sec) {
        if (wait_for_packet(s, TCP_ACK, TCP_ACK, &recv_tcph, payload,
                            TCP_SESSION_MAX_MSG, &payload_len, &packet_len, 2) != 0)
            continue;

        uint32_t seq = ntohl(recv_tcph.seq_num);
        uint32_t ack = ntohl(recv_tcph.ack_num);
        int has_fin = recv_tcph.flags & TCP_FIN;
        s->segment_no++;
        log_segment("Server", "Client", recv_tcph.flags, s, seq, ack,
                    ntohs(recv_tcph.src_port), ntohs(recv_tcph.dst_port),
                    ntohs(recv_tcph.window), ntohs(recv_tcph.checksum), packet_len,
                    payload_len, payload_len > 0 ? payload : NULL);

        if (seq != s->ack) {
            if (payload_len > 0 || has_fin) send_control(s, TCP_ACK);
            continue;
        }

        if (payload_len == 0 && !has_fin) continue;

        if (payload_len > 0) {
            payload[payload_len] = '\0';
            if (out_buf && out_buf_size > 0) {
                strncpy(out_buf, (char *)payload, out_buf_size - 1);
                out_buf[out_buf_size - 1] = '\0';
            }
        }

        s->ack += (uint32_t)payload_len;
        if (has_fin) {
            s->ack++;
            s->server_closed = 1;
        }

        send_control(s, TCP_ACK);
        return has_fin ? 1 : 0;
    }

    fprintf(stderr, "[!] Server response timeout\n");
    return -1;
}

int tcp_session_drain_until_close(tcp_session_t *s, char *out_buf,
                                  size_t out_buf_size, int timeout_sec)
{
    uint8_t payload[TCP_SESSION_MAX_MSG + 1];
    tcp_header_t recv_tcph;
    int payload_len;
    int packet_len;
    time_t start = time(NULL);

    printf("[*] Waiting for server response and close...\n");

    while (difftime(time(NULL), start) < timeout_sec) {
        if (wait_for_packet(s, TCP_ACK, TCP_ACK, &recv_tcph, payload,
                            TCP_SESSION_MAX_MSG, &payload_len, &packet_len, 2) != 0)
            continue;

        uint32_t seq = ntohl(recv_tcph.seq_num);
        uint32_t ack = ntohl(recv_tcph.ack_num);
        int has_fin = recv_tcph.flags & TCP_FIN;
        s->segment_no++;
        log_segment("Server", "Client", recv_tcph.flags, s, seq, ack,
                    ntohs(recv_tcph.src_port), ntohs(recv_tcph.dst_port),
                    ntohs(recv_tcph.window), ntohs(recv_tcph.checksum), packet_len,
                    payload_len, payload_len > 0 ? payload : NULL);

        if (seq != s->ack) {
            if (payload_len > 0 || has_fin) send_control(s, TCP_ACK);
            continue;
        }

        if (payload_len == 0 && !has_fin) continue;

        if (payload_len > 0) {
            payload[payload_len] = '\0';

            if (out_buf && out_buf_size > 0) {
                strncpy(out_buf, (char *)payload, out_buf_size - 1);
                out_buf[out_buf_size - 1] = '\0';
            }
        }

        s->ack += (uint32_t)payload_len;
        if (has_fin) {
            s->ack++;
            s->server_closed = 1;
        }

        send_control(s, TCP_ACK);

        if (has_fin) {
            return 1;
        }
    }

    printf("[!] Server close timeout\n");
    return 0;
}

void tcp_session_close(tcp_session_t *s, int timeout_sec)
{
    tcp_header_t recv_tcph;
    int payload_len;
    int packet_len;

    print_section("CLOSE");

    send_control(s, TCP_FIN | TCP_ACK);
    s->seq++;

    if (wait_for_packet(s, TCP_ACK, TCP_ACK, &recv_tcph, NULL, 0,
                        &payload_len, &packet_len, timeout_sec) == 0) {
        s->segment_no++;
        log_segment("Server", "Client", recv_tcph.flags, s, ntohl(recv_tcph.seq_num),
                    ntohl(recv_tcph.ack_num), ntohs(recv_tcph.src_port),
                    ntohs(recv_tcph.dst_port), ntohs(recv_tcph.window),
                    ntohs(recv_tcph.checksum), packet_len, payload_len, NULL);
    }

    close_raw_socket(s->sockfd);
    printf("================== CONNECTION CLOSED =================\n");
}

void tcp_session_abort(tcp_session_t *s)
{
    close_raw_socket(s->sockfd);
}
