# Project Progress

## Goal
Implement Lab09 SpeedTest from `Laboratorio_-_SpeedTest.pdf` using the Medium route.

## Overall Progress
Complete. Implemented the PDF's upload option and packaged the submission.

## Current Position
Deployment `lab09-speedtest-20261018`: implementation and verification complete.
The Linux/Python RAW client uploads ten copies of a 1000-byte file over one
connection to the ordinary TCP receiver. README and Makefile provide execution,
isolated integration testing and ZIP packaging. No changes to sibling labs.

## Acceptance and Verification
- Passed all twelve packet/state/receiver tests, including the PDF's 125 Kbps example.
- Passed real RAW integration in isolated user/network namespaces: 10,000 exact
  bytes, ten samples, one connection, SYN/ACK and FIN/ACK, zero retransmissions.
- Generated `Lab09_SpeedTest.zip`; extracted it to a temporary directory and
  passed the same twelve tests from the extracted submission.
- Full measurement evidence and limitations are canonical in `latest_session_work.md`.

## Next Milestone
User can run `make integration-user` or the manual README procedure and submit
`Lab09_SpeedTest.zip` through GES. Uploading to GES is outside this workspace task.
