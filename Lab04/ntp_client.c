/*
 * Laboratorio 04 - Cliente NTP manual
 * Ciencias de la Computacion VIII
 *
 * Objetivo:
 *   - Construir manualmente paquetes NTP de 48 bytes.
 *   - Enviar solicitudes UDP a multiples servidores NTP.
 *   - Calcular T1, T2, T3, T4, offset y delay segun RFC 5905.
 *   - Sincronizar un reloj interno simulado hasta quedar bajo un umbral configurable.
 *
 * Compilar:
 *   make
 *
 * Ejecutar ejemplo:
 *   make run ARGS="--date '2020-09-01 21:00:17.123' --threshold-ms 5 --interval 3"
 */

#define _GNU_SOURCE

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <netdb.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#define NTP_PACKET_SIZE 48
#define NTP_PORT "123"
#define NTP_UNIX_EPOCH_DELTA 2208988800ULL
#define MAX_SERVERS 32
#define DEFAULT_TIMEOUT_MS 2500
#define DEFAULT_INTERVAL_SECONDS 60
#define DEFAULT_THRESHOLD_MS 5.0
#define DEFAULT_MAX_ITERATIONS 10

static volatile sig_atomic_t keep_running = 1;

static const char *DEFAULT_SERVERS[] = {
    "time.google.com",
    "time.apple.com",
    "time.windows.com",
    "time.cloudflare.com",
    "time.nist.gov",
    "time-a.nist.gov",
    "pool.ntp.org"
};

static void handle_sigint(int sig) {
    (void)sig;
    keep_running = 0;
}

static double real_now_unix(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1000000000.0;
}

static double monotonic_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1000000000.0;
}

static uint32_t read_be32(const unsigned char *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static void write_be32(unsigned char *p, uint32_t value) {
    p[0] = (unsigned char)((value >> 24) & 0xFF);
    p[1] = (unsigned char)((value >> 16) & 0xFF);
    p[2] = (unsigned char)((value >> 8) & 0xFF);
    p[3] = (unsigned char)(value & 0xFF);
}

static double ntp_to_unix_from_bytes(const unsigned char *p) {
    uint32_t seconds = read_be32(p);
    uint32_t fraction = read_be32(p + 4);
    double ntp_seconds = (double)seconds + (double)fraction / 4294967296.0;
    return ntp_seconds - (double)NTP_UNIX_EPOCH_DELTA;
}

static void unix_to_ntp_bytes(double unix_time, unsigned char *p) {
    double ntp_time = unix_time + (double)NTP_UNIX_EPOCH_DELTA;
    if (ntp_time < 0) {
        ntp_time = 0;
    }

    double seconds_part = floor(ntp_time);
    double fraction_part = ntp_time - seconds_part;
    uint64_t fraction64 = (uint64_t)llround(fraction_part * 4294967296.0);

    if (fraction64 >= 4294967296ULL) {
        seconds_part += 1.0;
        fraction64 = 0;
    }

    write_be32(p, (uint32_t)((uint64_t)seconds_part & 0xFFFFFFFFULL));
    write_be32(p + 4, (uint32_t)fraction64);
}

static void format_unix_utc(double unix_time, char *out, size_t out_size) {
    time_t seconds = (time_t)floor(unix_time);
    int millis = (int)llround((unix_time - floor(unix_time)) * 1000.0);
    if (millis >= 1000) {
        seconds += 1;
        millis -= 1000;
    }

    struct tm tm_utc;
    gmtime_r(&seconds, &tm_utc);
    char base[32];
    strftime(base, sizeof(base), "%Y-%m-%d %H:%M:%S", &tm_utc);
    snprintf(out, out_size, "%s.%03d UTC", base, millis);
}

static void format_unix_gt(double unix_time, char *out, size_t out_size) {
    /* Guatemala no usa DST actualmente: UTC-6. */
    double gt = unix_time - 6.0 * 3600.0;
    time_t seconds = (time_t)floor(gt);
    int millis = (int)llround((gt - floor(gt)) * 1000.0);
    if (millis >= 1000) {
        seconds += 1;
        millis -= 1000;
    }

    struct tm tm_utc_minus_6;
    gmtime_r(&seconds, &tm_utc_minus_6);
    char base[32];
    strftime(base, sizeof(base), "%Y-%m-%d %H:%M:%S", &tm_utc_minus_6);
    snprintf(out, out_size, "%s.%03d Guatemala (UTC-6)", base, millis);
}

static bool parse_guatemala_datetime(const char *input, double *unix_out) {
    int year, month, day, hour, minute;
    double second;
    if (sscanf(input, "%d-%d-%d %d:%d:%lf", &year, &month, &day, &hour, &minute, &second) != 6) {
        return false;
    }

    int sec_int = (int)floor(second);
    double frac = second - (double)sec_int;

    struct tm gt_tm;
    memset(&gt_tm, 0, sizeof(gt_tm));
    gt_tm.tm_year = year - 1900;
    gt_tm.tm_mon = month - 1;
    gt_tm.tm_mday = day;
    gt_tm.tm_hour = hour;
    gt_tm.tm_min = minute;
    gt_tm.tm_sec = sec_int;
    gt_tm.tm_isdst = 0;

    /* Interpretamos la fecha escrita como Guatemala UTC-6. Para llevarla a UTC,
       sumamos 6 horas antes de usar timegm. */
    time_t as_if_utc = timegm(&gt_tm);
    if (as_if_utc == (time_t)-1) {
        return false;
    }
    *unix_out = (double)as_if_utc + 6.0 * 3600.0 + frac;
    return true;
}

static void build_ntp_request(unsigned char packet[NTP_PACKET_SIZE], double t1_unix) {
    memset(packet, 0, NTP_PACKET_SIZE);
    /* LI = 0, VN = 4, Mode = 3 (cliente) => 00 100 011 = 0x23 */
    packet[0] = 0x23;
    packet[1] = 0;      /* Stratum, cliente sin sincronizar */
    packet[2] = 6;      /* Poll = 2^6 = 64 segundos */
    packet[3] = 0xEC;   /* Precision aproximada: -20 */
    /* Transmit Timestamp del cliente. El servidor lo copiara como Originate Timestamp. */
    unix_to_ntp_bytes(t1_unix, packet + 40);
}

typedef struct {
    const char *name;
    int sockfd;
    struct addrinfo *addrinfo;
    double t1;
    double mono_sent;
    bool sent;
    bool received;
    bool failed;
    char error[160];
    double t2;
    double t3;
    double t4;
    double mono_recv;
    double offset;
    double delay;
    int stratum;
    int version;
    int mode;
    char ip[INET6_ADDRSTRLEN];
} ServerQuery;

static void close_query(ServerQuery *q) {
    if (q->sockfd >= 0) {
        close(q->sockfd);
        q->sockfd = -1;
    }
    if (q->addrinfo) {
        freeaddrinfo(q->addrinfo);
        q->addrinfo = NULL;
    }
}

static int resolve_and_send(ServerQuery *q, const char *port, double internal_time_at_send) {
    q->sockfd = -1;
    q->t1 = internal_time_at_send;
    q->mono_sent = monotonic_now();
    q->sent = false;
    q->received = false;
    q->failed = false;
    q->error[0] = '\0';
    q->ip[0] = '\0';

    struct addrinfo hints;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_DGRAM;

    int rc = getaddrinfo(q->name, port, &hints, &q->addrinfo);
    if (rc != 0) {
        snprintf(q->error, sizeof(q->error), "getaddrinfo: %s", gai_strerror(rc));
        q->failed = true;
        return -1;
    }

    struct addrinfo *selected = NULL;
    for (struct addrinfo *ai = q->addrinfo; ai != NULL; ai = ai->ai_next) {
        int fd = socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);
        if (fd < 0) {
            continue;
        }

        int flags = fcntl(fd, F_GETFL, 0);
        if (flags >= 0) {
            fcntl(fd, F_SETFL, flags | O_NONBLOCK);
        }

        if (connect(fd, ai->ai_addr, ai->ai_addrlen) == 0 || errno == EINPROGRESS) {
            q->sockfd = fd;
            selected = ai;
            break;
        }
        close(fd);
    }

    if (q->sockfd < 0 || selected == NULL) {
        snprintf(q->error, sizeof(q->error), "no se pudo crear/conectar socket UDP");
        q->failed = true;
        return -1;
    }

    void *addr_ptr = NULL;
    if (selected->ai_family == AF_INET) {
        addr_ptr = &((struct sockaddr_in *)selected->ai_addr)->sin_addr;
    } else if (selected->ai_family == AF_INET6) {
        addr_ptr = &((struct sockaddr_in6 *)selected->ai_addr)->sin6_addr;
    }
    if (addr_ptr) {
        inet_ntop(selected->ai_family, addr_ptr, q->ip, sizeof(q->ip));
    }

    unsigned char packet[NTP_PACKET_SIZE];
    build_ntp_request(packet, q->t1);
    ssize_t sent = send(q->sockfd, packet, sizeof(packet), 0);
    if (sent != NTP_PACKET_SIZE) {
        snprintf(q->error, sizeof(q->error), "send fallo: %s", strerror(errno));
        q->failed = true;
        return -1;
    }

    q->sent = true;
    return 0;
}

static int collect_responses(ServerQuery queries[], int count, int timeout_ms, double internal_time_at_send) {
    int received = 0;
    double deadline = monotonic_now() + (double)timeout_ms / 1000.0;

    while (keep_running && monotonic_now() < deadline) {
        fd_set readfds;
        FD_ZERO(&readfds);
        int maxfd = -1;

        for (int i = 0; i < count; i++) {
            if (queries[i].sent && !queries[i].received && !queries[i].failed && queries[i].sockfd >= 0) {
                FD_SET(queries[i].sockfd, &readfds);
                if (queries[i].sockfd > maxfd) {
                    maxfd = queries[i].sockfd;
                }
            }
        }

        if (maxfd < 0) {
            break;
        }

        double remaining = deadline - monotonic_now();
        if (remaining < 0) {
            break;
        }

        struct timeval tv;
        tv.tv_sec = (time_t)remaining;
        tv.tv_usec = (suseconds_t)((remaining - (double)tv.tv_sec) * 1000000.0);

        int rc = select(maxfd + 1, &readfds, NULL, NULL, &tv);
        if (rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            perror("select");
            break;
        }
        if (rc == 0) {
            break;
        }

        for (int i = 0; i < count; i++) {
            ServerQuery *q = &queries[i];
            if (!(q->sent && !q->received && !q->failed && q->sockfd >= 0 && FD_ISSET(q->sockfd, &readfds))) {
                continue;
            }

            unsigned char packet[NTP_PACKET_SIZE];
            ssize_t n = recv(q->sockfd, packet, sizeof(packet), 0);
            double mono_recv = monotonic_now();
            if (n < NTP_PACKET_SIZE) {
                snprintf(q->error, sizeof(q->error), "respuesta incompleta (%zd bytes)", n);
                q->failed = true;
                continue;
            }

            (void)internal_time_at_send;
            q->t4 = q->t1 + (mono_recv - q->mono_sent);
            q->mono_recv = mono_recv;
            q->version = (packet[0] >> 3) & 0x07;
            q->mode = packet[0] & 0x07;
            q->stratum = packet[1];
            q->t2 = ntp_to_unix_from_bytes(packet + 32); /* Receive Timestamp */
            q->t3 = ntp_to_unix_from_bytes(packet + 40); /* Transmit Timestamp */
            q->delay = (q->t4 - q->t1) - (q->t3 - q->t2);
            q->offset = ((q->t2 - q->t1) + (q->t3 - q->t4)) / 2.0;
            q->received = true;
            received++;
        }
    }

    for (int i = 0; i < count; i++) {
        if (queries[i].sent && !queries[i].received && !queries[i].failed) {
            snprintf(queries[i].error, sizeof(queries[i].error), "timeout sin respuesta");
            queries[i].failed = true;
        }
    }

    return received;
}

static void print_usage(const char *program) {
    printf("Uso:\n");
    printf("  %s [opciones]\n\n", program);
    printf("Opciones:\n");
    printf("  --date 'YYYY-MM-DD HH:MM:SS.mmm'  Fecha inicial LOCAL Guatemala UTC-6.\n");
    printf("                                      Si se omite, usa la hora actual.\n");
    printf("  --threshold-ms N                   Offset meta en milisegundos (default %.1f).\n", DEFAULT_THRESHOLD_MS);
    printf("  --interval N                       Segundos entre iteraciones (default %d).\n", DEFAULT_INTERVAL_SECONDS);
    printf("  --timeout-ms N                     Timeout por ronda NTP (default %d).\n", DEFAULT_TIMEOUT_MS);
    printf("  --max-iterations N                 Maximo de iteraciones (default %d).\n", DEFAULT_MAX_ITERATIONS);
    printf("  --server HOST                      Agrega servidor NTP. Puede repetirse.\n");
    printf("  --port PORT                        Puerto NTP (default 123).\n");
    printf("  --help                             Mostrar ayuda.\n\n");
    printf("Ejemplo:\n");
    printf("  %s --date '2020-09-01 21:00:17.123' --threshold-ms 5 --interval 3\n", program);
}

int main(int argc, char **argv) {
    signal(SIGINT, handle_sigint);

    const char *servers[MAX_SERVERS];
    int server_count = 0;
    const char *port = NTP_PORT;
    const char *date_arg = NULL;
    double threshold_ms = DEFAULT_THRESHOLD_MS;
    int interval_seconds = DEFAULT_INTERVAL_SECONDS;
    int timeout_ms = DEFAULT_TIMEOUT_MS;
    int max_iterations = DEFAULT_MAX_ITERATIONS;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            print_usage(argv[0]);
            return 0;
        } else if (strcmp(argv[i], "--date") == 0 && i + 1 < argc) {
            date_arg = argv[++i];
        } else if (strcmp(argv[i], "--threshold-ms") == 0 && i + 1 < argc) {
            threshold_ms = atof(argv[++i]);
        } else if (strcmp(argv[i], "--interval") == 0 && i + 1 < argc) {
            interval_seconds = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--timeout-ms") == 0 && i + 1 < argc) {
            timeout_ms = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--max-iterations") == 0 && i + 1 < argc) {
            max_iterations = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--server") == 0 && i + 1 < argc) {
            if (server_count >= MAX_SERVERS) {
                fprintf(stderr, "Demasiados servidores. Maximo: %d\n", MAX_SERVERS);
                return 1;
            }
            servers[server_count++] = argv[++i];
        } else if (strcmp(argv[i], "--port") == 0 && i + 1 < argc) {
            port = argv[++i];
        } else {
            fprintf(stderr, "Argumento no reconocido o incompleto: %s\n", argv[i]);
            print_usage(argv[0]);
            return 1;
        }
    }

    if (server_count == 0) {
        int defaults = (int)(sizeof(DEFAULT_SERVERS) / sizeof(DEFAULT_SERVERS[0]));
        for (int i = 0; i < defaults; i++) {
            servers[server_count++] = DEFAULT_SERVERS[i];
        }
    }

    if (server_count < 7) {
        fprintf(stderr, "Error: el laboratorio requiere al menos 7 servidores NTP. Configurados: %d\n", server_count);
        fprintf(stderr, "Use --server HOST varias veces o use los valores por defecto.\n");
        return 1;
    }
    if (threshold_ms < 0.0 || interval_seconds < 0 || timeout_ms <= 0 || max_iterations <= 0) {
        fprintf(stderr, "Error: parametros numericos invalidos.\n");
        return 1;
    }

    double internal_clock;
    if (date_arg) {
        if (!parse_guatemala_datetime(date_arg, &internal_clock)) {
            fprintf(stderr, "No se pudo interpretar --date. Use formato: YYYY-MM-DD HH:MM:SS.mmm\n");
            return 1;
        }
    } else {
        internal_clock = real_now_unix();
    }

    char gt_buf[80], utc_buf[80];
    format_unix_gt(internal_clock, gt_buf, sizeof(gt_buf));
    format_unix_utc(internal_clock, utc_buf, sizeof(utc_buf));

    printf("============================================================\n");
    printf(" Laboratorio 04 - Cliente NTP manual (RFC 5905)\n");
    printf("============================================================\n");
    printf("Reloj interno inicial: %s | %s\n", gt_buf, utc_buf);
    printf("Servidores configurados (%d):\n", server_count);
    for (int i = 0; i < server_count; i++) {
        printf("  %2d. %s:%s\n", i + 1, servers[i], port);
    }
    printf("Umbral de sincronizacion: %.3f ms\n", threshold_ms);
    printf("Intervalo entre verificaciones: %d s\n", interval_seconds);
    printf("Timeout por ronda: %d ms\n", timeout_ms);
    printf("Maximo de iteraciones: %d\n", max_iterations);
    printf("Formula offset: theta = ((T2 - T1) + (T3 - T4)) / 2\n");
    printf("Formula delay : delta = (T4 - T1) - (T3 - T2)\n");

    bool synchronized = false;
    double internal_anchor_mono = monotonic_now();

    for (int iteration = 1; keep_running && iteration <= max_iterations; iteration++) {
        double now_mono = monotonic_now();
        internal_clock += now_mono - internal_anchor_mono;
        internal_anchor_mono = now_mono;

        double real_round_start = internal_anchor_mono;
        double internal_round_start = internal_clock;
        format_unix_gt(internal_round_start, gt_buf, sizeof(gt_buf));
        format_unix_utc(internal_round_start, utc_buf, sizeof(utc_buf));

        printf("\n---------------- Iteracion %d ----------------\n", iteration);
        printf("Reloj interno antes de consultar: %s | %s\n", gt_buf, utc_buf);
        printf("Enviando solicitudes UDP NTP de 48 bytes al mismo tiempo...\n");

        ServerQuery queries[MAX_SERVERS];
        memset(queries, 0, sizeof(queries));
        for (int i = 0; i < server_count; i++) {
            queries[i].name = servers[i];
            queries[i].sockfd = -1;
            queries[i].addrinfo = NULL;
            double elapsed = monotonic_now() - real_round_start;
            double t1 = internal_round_start + elapsed;
            resolve_and_send(&queries[i], port, t1);
        }

        int responses = collect_responses(queries, server_count, timeout_ms, internal_round_start);
        printf("Respuestas recibidas: %d/%d\n", responses, server_count);

        int best = -1;
        double best_delay = 0.0;
        printf("\n%-24s %-15s %-8s %-14s %-14s %-10s\n", "Servidor", "IP", "Stratum", "Offset(ms)", "Delay(ms)", "Estado");
        printf("%-24s %-15s %-8s %-14s %-14s %-10s\n", "------------------------", "---------------", "--------", "----------", "---------", "----------");

        for (int i = 0; i < server_count; i++) {
            ServerQuery *q = &queries[i];
            if (q->received) {
                double offset_ms = q->offset * 1000.0;
                double delay_ms = q->delay * 1000.0;
                printf("%-24s %-15s %-8d %14.3f %14.3f %-10s\n", q->name, q->ip[0] ? q->ip : "?", q->stratum, offset_ms, delay_ms, "OK");
                if (best < 0 || fabs(q->delay) < fabs(best_delay)) {
                    best = i;
                    best_delay = q->delay;
                }
            } else {
                printf("%-24s %-15s %-8s %-14s %-14s %-10s (%s)\n", q->name, q->ip[0] ? q->ip : "?", "-", "-", "-", "ERROR", q->error);
            }
        }

        if (best < 0) {
            printf("\nNo hubo respuestas validas en esta iteracion. No se puede ajustar el reloj interno.\n");
            for (int i = 0; i < server_count; i++) {
                close_query(&queries[i]);
            }
            break;
        }

        ServerQuery *b = &queries[best];
        char t1s[80], t2s[80], t3s[80], t4s[80];
        format_unix_utc(b->t1, t1s, sizeof(t1s));
        format_unix_utc(b->t2, t2s, sizeof(t2s));
        format_unix_utc(b->t3, t3s, sizeof(t3s));
        format_unix_utc(b->t4, t4s, sizeof(t4s));

        printf("\nMejor servidor por menor delay: %s (%s)\n", b->name, b->ip[0] ? b->ip : "IP no disponible");
        printf("T1 cliente envia     : %s\n", t1s);
        printf("T2 servidor recibe   : %s\n", t2s);
        printf("T3 servidor responde : %s\n", t3s);
        printf("T4 cliente recibe    : %s\n", t4s);
        printf("Calculo delay  = (T4-T1)-(T3-T2) = %.6f s = %.3f ms\n", b->delay, b->delay * 1000.0);
        printf("Calculo offset = ((T2-T1)+(T3-T4))/2 = %.6f s = %.3f ms\n", b->offset, b->offset * 1000.0);

        /* Sincronizacion simulada: ajustamos el reloj interno por el offset seleccionado. */
        internal_clock = b->t4 + b->offset;
        internal_anchor_mono = b->mono_recv;

        /* Mostramos la hora ya ajustada al instante actual, no al instante pasado en que llego
           la respuesta. Esto evita que el reloj interno quede atrasado mientras esperamos
           respuestas lentas o timeouts de otros servidores. */
        now_mono = monotonic_now();
        internal_clock += now_mono - internal_anchor_mono;
        internal_anchor_mono = now_mono;

        format_unix_gt(internal_clock, gt_buf, sizeof(gt_buf));
        format_unix_utc(internal_clock, utc_buf, sizeof(utc_buf));
        printf("Reloj interno DESPUES del ajuste: %s | %s\n", gt_buf, utc_buf);

        if (fabs(b->offset * 1000.0) <= threshold_ms) {
            printf("\nSINCRONIZADO: |offset| %.3f ms <= umbral %.3f ms\n", fabs(b->offset * 1000.0), threshold_ms);
            synchronized = true;
            for (int i = 0; i < server_count; i++) {
                close_query(&queries[i]);
            }
            break;
        }

        printf("Aun no sincronizado: |offset| %.3f ms > umbral %.3f ms\n", fabs(b->offset * 1000.0), threshold_ms);
        for (int i = 0; i < server_count; i++) {
            close_query(&queries[i]);
        }

        if (iteration < max_iterations && keep_running) {
            printf("Esperando %d segundo(s) para la siguiente verificacion...\n", interval_seconds);
            for (int s = 0; s < interval_seconds && keep_running; s++) {
                sleep(1);
            }
        }
    }

    printf("\n============================================================\n");
    printf(" Resultado final\n");
    printf("============================================================\n");
    format_unix_gt(internal_clock, gt_buf, sizeof(gt_buf));
    format_unix_utc(internal_clock, utc_buf, sizeof(utc_buf));
    printf("Reloj interno final: %s | %s\n", gt_buf, utc_buf);
    printf("Estado: %s\n", synchronized ? "SINCRONIZADO" : "NO SINCRONIZADO dentro del limite configurado");
    printf("Nota: el reloj del sistema operativo NO se modifica; la sincronizacion es simulada en una variable interna.\n");

    return synchronized ? 0 : 2;
}
