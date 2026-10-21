# Project Diary

## Decisions and Lessons

- The PDF permits another language and a separate counterpart. Use Python's
  standard library on Linux: Lab01 is a line-based calculator, not a binary
  upload receiver, and the installed Java environment has no `javac`.
- Use 1000 bytes for 1 KB to match the PDF's explicit numerical example. Ten
  copies share one connection; TCP stream reads do not preserve file boundaries.
- RAW TCP does not suppress the kernel TCP stack. Restrict the RST-drop rule
  to the client's endpoint pair. Integration tests create their own network
  namespace so they do not change the host firewall.
- Unprivileged user/network namespaces allow a complete RAW test without
  interactive sudo on this machine. A user-namespace root cannot necessarily
  read `/proc/1/ns/net`; pass the original namespace ID before entering instead.
- Local TCP checksum offload can expose unfinished incoming TCP checksums.
  Outgoing checksums are constructed and tested; incoming IPv4 is checked, but
  validating incoming TCP would also require offload metadata. This educational
  scope and the one-second TIME-WAIT are explicit in README.
- The PDF estimate adds handshake latency to the average data confirmation
  time. Do not count the data RTT a second time or describe this stop-and-wait
  estimate as the maximum link capacity.
