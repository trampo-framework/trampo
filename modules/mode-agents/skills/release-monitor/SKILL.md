---
name: release-monitor
description: Watch each finished item's systems after its release and post only a failing verdict. Use for a release-monitor tick.
---

Run `python3 ${CLAUDE_PLUGIN_ROOT}/../../core/scripts/agent.py --ws . release <monitor>`. It reads the monitoring slot's checks for the systems the definition lists, keeps one record per item under `sessions/release-monitor/` (WATCHING, FAIL or PASS) and posts only a FAIL. A system that reports no checks is a FAIL: unknown is not passing. It reads checks, never production data.
