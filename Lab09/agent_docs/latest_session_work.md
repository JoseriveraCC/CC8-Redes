# Latest Session Work

## Deployment

`lab09-speedtest-20261018` — complete, Medium route. Implement Lab09 according
to all three pages of `Laboratorio_-_SpeedTest.pdf`; related labs inspected
read-only. User selected Medium and provided Lab01/03/04 paths.

## Implementation and Deliverable

- `speedtest.py`: manual IPv4/TCP upload using SOCK_RAW and IP_HDRINCL, checksums,
  handshake, MSS/window-aware stop-and-wait sends, timeouts/retries, sequence
  wraparound, FIN/ACK, ten CSV measurements and the PDF speed estimate.
- `server.py`: one ordinary TCP connection; buffers bounded to 10,001 bytes,
  rejects short/excess/mismatched copies and saves the verified upload.
- `archivo_1kb.bin`: generated random 1000-byte input. SHA-256:
  `2ddec3bf488518c5ded7663cd9aaa4e69d504469e0fd19816596e67ebb185304`.
- `Makefile`, Spanish `README.md`, twelve unit checks and isolated RAW integration.
- `Lab09_SpeedTest.zip`: eight delivery files under `Lab09/`, including the PDF.
  Generated outputs are ignored; the workflow-owned `.gitignore` block is intact.

## Verification Evidence

- `make test`: twelve tests passed. Covers known checksum vector, binary/odd
  payloads, malformed/truncated headers, MSS options, the 125 Kbps PDF example,
  SEQ wraparound, split/combined FIN, duplicate ACK/FIN, retransmission without
  duplicate data, timeout/RST/zero-window failures, fragmented stream reads and
  incomplete/excess/changed uploads.
- `make integration-user` outside the restricted sandbox passed in an isolated
  user/network namespace. One SYN, ten 1000-byte PSH/ACK packets and one FIN;
  all ten ACK measurements positive, zero retransmissions, clean FIN/ACK.
  Receiver output matched the input repeated ten times (10,000 bytes), SHA-256
  `0623158adfbe1a722b00e0c949701e1490a757dd9889ce126b66f870aef2394e`.
- That loopback run measured handshake latency 0.111849 ms, mean data
  confirmation time 0.064987 ms and PDF speed estimate 45239.708262 Kbps.
  These are local measurements, not a network bandwidth claim. Ten individual
  samples were written and validated in a temporary CSV by the integration test.
- `make zip`: generated archive passed ZipFile integrity checking. Extracted
  to `/tmp/lab09-package-xzgqamof/Lab09`; `make test` passed all twelve tests there.
- CLI help for both programs works. `git diff --check` passed for tracked changes;
  Lab09 itself was untracked at intake, so that check does not cover new files.

## Environment and Limits

Sandbox denied `unshare`. Escalated `sudo -n` required interactive authentication;
user/network namespaces succeeded without sudo. The integration test compares
its namespace against a pre-entry ID and removes its own temporary RST rule.
No main-network firewall rules or sibling files were changed.

The anydoc conversion command could not reach npm (EAI_AGAIN); local `pdftotext`
read all PDF pages and the TCP diagram on page 2 was inspected as a rendered image.
Python 3.14.4 and OpenJDK 25 runtime are available; no `javac` was found.
Only Linux is supported/tested. No external-machine, macOS, congested-link or
complete general-purpose TCP-stack validation is claimed; see README scope.

## Git Handoff and Continuation

No commits, staging or pushes requested or performed. At intake Git showed
untracked `../Lab08/` and `./`; preserve both. All intended task writes are
inside Lab09. User may regenerate with `make zip`, rerun `make integration-user`
on compatible Linux or follow README's two-terminal procedure. Submission to
GES remains a user action; there is no implementation blocker.
