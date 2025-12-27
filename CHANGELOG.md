# Changelog

All notable changes to this project will be documented in this file.

## [v1.0.4] - 2025-12-27

### Added
- **Backend**: Implement sequential translation split logic for long text handling.
  - Introduced text splitting by punctuation in TranslationHandler to prevent LLM omissions.
  - Updated WebSocket worker to handle multiple translation segments per STT event.
  - Added regression tests.

### Fixed
- **Backend**: Fixed 12 failing test cases related to translation handling.
- **CI**: Added workflow_dispatch for manual trigger.
