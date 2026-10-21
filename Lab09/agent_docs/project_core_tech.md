# Project Core Technologies

## Languages and Runtime

Python 3.9 or later with the standard library, on Linux. No third-party Python
packages are required.

## Networking

The client uses Linux IPv4 `SOCK_RAW` with `IP_HDRINCL` to construct TCP
segments, sequence and acknowledge the upload, and measure confirmations. It
needs `CAP_NET_RAW` or equivalent privilege. The receiver uses an ordinary
TCP socket. A narrowly scoped RST firewall rule is needed for a manually run
client because Linux's kernel TCP stack does not own the raw connection.

## Build and Verification

`make` runs Python syntax compilation; `make test` uses the standard-library
`unittest` runner. `make integration-user` additionally needs `unshare` and
`ip` to create an isolated test network; the README documents alternatives and
environment requirements.

## Technical Constraints

- Linux-specific raw sockets and firewall commands; macOS is unsupported.
- The client checks incoming IPv4 headers and constructs both outgoing
  checksums. It does not validate incoming TCP checksums because local checksum
  offload can require packet metadata unavailable through its raw IPv4 socket.
- This educational client omits general TCP features such as congestion
  control, zero-window persist, and application-data reception. Its duplicate
  FIN wait is one second rather than the general 2×MSL TIME-WAIT.
- The reported speed follows the assignment's formula and is affected by
  processing, scheduling, delayed ACKs, and retransmission waits; it does not
  represent maximum link capacity.
