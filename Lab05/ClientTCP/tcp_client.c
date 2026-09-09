/*
 * tcp_client.c
 *
 * Entry point for the raw TCP client.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "tcp_client.h"
#include "tcp_session.h"

static const option_t options[] = {
    {"-l", "--local", OPT_LOCAL},
    {"-s", "--server", OPT_SERVER},
    {"-p", "--port", OPT_PORT},
    {"-P", "--local-port", OPT_LOCAL_PORT},
    {"-m", "--message", OPT_MESSAGE},
    {"-i", "--interface", OPT_INTERFACE},
};

void print_usage(const char *prog, const cli_options_t *o)
{
    printf("\nUsage: %s [options]\n\n", prog);
    printf("  -l, --local IP       Local IP (default: %s)\n", o->local_ip);
    printf("  -s, --server IP      Server IP (default: %s)\n", o->server_ip);
    printf("  -p, --port PORT      Server port (default: %u)\n", o->server_port);
    printf("  -P, --local-port P   Fixed local port (default: random ephemeral port)\n");
    printf("  -m, --message MSG    Send one message and exit (default: interactive mode)\n");
    printf("  -i, --interface IF   Network interface (default: %s)\n", o->interface ? o->interface : "not specified");
    printf("                       Linux: lo, eth0 | macOS: lo0, en0\n");
    printf("  -h, --help           Show this help\n\n");
}

const option_t *find_option(const char *arg)
{
    for (size_t i = 0; i < sizeof(options) / sizeof(options[0]); i++)
        if (!strcmp(arg, options[i].short_name) || !strcmp(arg, options[i].long_name))
            return &options[i];

    return NULL;
}

int parse_cli(int argc, char **argv, cli_options_t *o)
{
    for (int i = 1; i < argc; i++) {
        const char *arg = argv[i];

        if (!strcmp(arg, "-h") || !strcmp(arg, "--help")) {
            print_usage(argv[0], o);
            return 1;
        }

        const option_t *option = find_option(arg);
        if (!option) {
            fprintf(stderr, "Unknown argument: %s\n", arg);
            return -1;
        }

        if (++i >= argc) {
            fprintf(stderr, "Missing value for: %s\n", arg);
            return -1;
        }

        const char *value = argv[i];

        switch (option->id) {
        case OPT_LOCAL: o->local_ip = value; break;
        case OPT_SERVER: o->server_ip = value; break;
        case OPT_PORT: o->server_port = (uint16_t)atoi(value); break;
        case OPT_LOCAL_PORT: o->local_port = (uint16_t)atoi(value); break;
        case OPT_MESSAGE: o->message = value; break;
        case OPT_INTERFACE: o->interface = value; break;
        }
    }

    return 0;
}

int run_session(const cli_options_t *o)
{
    tcp_session_t session;
    char response[TCP_SESSION_MAX_MSG + 1] = {0};

    if (tcp_session_open(&session, o->local_ip, o->server_ip,
                         o->local_port, o->server_port, o->interface) != 0)
        return 1;

    if (tcp_session_handshake(&session, 10) != 0) {
        tcp_session_abort(&session);
        return 1;
    }

    if (o->message) {
        if (tcp_session_send_message(&session, o->message) != 0) {
            tcp_session_abort(&session);
            return 1;
        }

        if (strstr(o->message, "EXIT")) {
            tcp_session_drain_until_close(&session, response, sizeof(response), 10);
        } else {
            tcp_session_receive_message(&session, response, sizeof(response), 10);
        }
    } else {
        char message[TCP_SESSION_MAX_MSG + 1];

        while (!session.server_closed) {
            printf("\nIngrese un mensaje (use EXIT OFF para apagar el servidor): ");
            fflush(stdout);

            if (!fgets(message, sizeof(message), stdin)) break;
            message[strcspn(message, "\n")] = '\0';

            if (tcp_session_send_message(&session, message) != 0) {
                tcp_session_abort(&session);
                return 1;
            }

            if (strstr(message, "EXIT")) {
                tcp_session_drain_until_close(&session, response, sizeof(response), 10);
                break;
            }

            if (tcp_session_receive_message(&session, response, sizeof(response), 10) != 0) break;
        }
    }

    tcp_session_close(&session, 5);

    return 0;
}

int main(int argc, char **argv)
{
    cli_options_t opts = {
        .local_ip = "127.0.0.1",
        .server_ip = "127.0.0.1",
        .server_port = 5001,
        .local_port = 0,
        .message = NULL,
        .interface = NULL,
    };

    int rc = parse_cli(argc, argv, &opts);
    if (rc != 0) return rc > 0 ? 0 : 1;

    srand((unsigned)time(NULL));
    return run_session(&opts);
}
