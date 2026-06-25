# Known Issues - 2026-05-17

- **bosssignal-backend may silently hang while reporting "Up" to Docker** - symptom is HTTP returns empty (curl exit 52, empty reply), container still shows `Up` in `docker ps`, no error/traceback in logs. Fix is `docker compose restart backend` (from `backends/bosssignal-backend/`). Investigate root cause when time allows.
