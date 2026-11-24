# Tasks

## 1. Setup and compatibility

- [x] 1.1 Harden the setup probe and verify refusal, timeout, empty and malformed replies, short valid replies, fixed fallback, retry, and duplicate handling with mocks.
- [x] 1.2 Modernize first refresh and timeouts; verify unsuccessful startup raises `ConfigEntryNotReady` and never forwards platforms.

## 2. Entity and service compatibility

- [x] 2.1 Modernize entity APIs and action metadata without changing IDs or value limits; verify sensor routing attributes, unknown switch state, and existing control behavior.
