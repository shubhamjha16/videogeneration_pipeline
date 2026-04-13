# Remaining Potential Bugs (Current Snapshot)

Date: 2026-04-13

After the latest remediation pass, the earlier 12-item hotspot list has been reduced.

## Remaining potential bugs to investigate next

1. `autonomous_graph.py` — many fallback branches still catch broad `Exception` and continue; this is safer now with richer telemetry, but integration testing is still needed to ensure no quality regressions under repeated provider failures.
2. `api_bridge.py` — callers currently rely on `_save_jobs()` side effects; now that `_save_jobs()` raises on persistence failure, endpoint-level error mapping should be validated under disk-full / read-only conditions.
3. `autonomous_graph.py` — fallback to `render_mode="presentation"` is now set on explainer/heygen failures, but graph-routing behavior after that state mutation should be validated with fault-injection tests.
4. End-to-end retry policy consistency is still uneven across nodes (some fail-fast, some fallback, some retry), and needs one unified policy pass.

## Status update

- Previous high-priority list size: 12
- Resolved in this pass: 8
- Remaining potential hotspots: 4
