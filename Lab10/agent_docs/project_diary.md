# Project Diary

## Decisions and Lessons

- 2026-10-20: The assignment is a classroom WEP challenge, not a networking application to implement. Use the Aircrack-ng suite directly, with a small standard-library helper rather than custom cryptography.
- Public offline capture recovery is verifiable without radio: ptw.cap recovered 1F:1F:1F:1F:1F from 30,566 IVs. This does not validate the user's adapter or the classroom router.
- WSL2 exposed no Wi-Fi here; installing tools enabled offline analysis but did not provide physical monitor/injection capability.
- The assignment's sentence about tests affecting participants is incomplete. Document adversarial effects and detection, keep active AP tests conditional on instructor scope, and do not claim participant-disruption tests were executed.
