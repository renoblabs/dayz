"""dayzstack-tools — operator-facing CLI utilities.

Wraps the intel snapshots into useful, stand-alone reports:
  - `dayz-stack health <server-name-pattern>` — single-server stack health check
  - `dayz-stack compare <pattern> <pattern>...` — cross-server stack comparator

Pulls from the local intel.* tables (latest available snapshot).
"""
