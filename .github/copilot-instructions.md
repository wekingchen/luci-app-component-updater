# Repository-level GitHub Copilot guidance

**Before coding read and follow ../AGENTS.md**, then docs/project-governance.md and docs/acceptance-gates.md. Source, tests and main-branch audit records outrank GitHub Wiki. Do not invent hardware validation.

- Only explicitly supported devices and package owners may be modified; never install IPK on APK or vice versa, never enable writes for unknown APK hardware.
- Preserve native opkg/IPK and AX6S APKv3 update, integrity verification, configuration/backup, rollback and interruption safety. Do not restart PassWall.
- Never call GitHub SHA256 digests "independent signing". Keep API-proxy trust warnings.
- Manager IPK and APK must share the same version and release; never bypass AX6S real-hardware acceptance for automatic publishing or mark an untested RC as stable.
- Chinese LuCI, working actions, mobile/desktop layouts and dangerous-action confirmation are product constraints.
- Update docs/ plus wiki-src/ for changed facts, then run python3 tools/check_docs.py and the full CI suite.
