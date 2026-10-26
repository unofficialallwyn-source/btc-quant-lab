# One-click bounded BTC historical backfill

This workflow is **manual-only** and requires a deliberate `execute=true` opt-in. It never places trades or enables a schedule.

The orchestrator repeatedly invokes the existing strict gap-aware 28-day collector under Azure OIDC, respecting a hard **32-batch default** and a **240-minute soft runtime budget** checked between batches (the GitHub job has a 330-minute hard timeout). No trading is involved. Both dates are UTC; end is exclusive, default today UTC midnight.

Each batch performs one full SHA-256 audit at its start, targeted checks per uploaded day, and one full SHA-256 audit at its end. Completed days and separate retryable source-gap day records persist in Azure. A failed batch stops subsequent work; the orchestrator writes durable JSON progress checkpoints and the workflow archives all existing reports with `if: always()`.

Results distinguish:
- `fully_complete`: all target minutes exist in SHA256-verified manifest-backed data.
- `all_eligible_days_attempted`: no further currently eligible days remain, but registered source gaps may make full coverage impossible. This is **not** full historical completion.
- `batch_limit_reached`, `runtime_budget_reached`: more runs needed.
- `failed`: a network, Azure authorization, integrity or other fatal error stopped collection; inspect the artifact.

**Safe rollout:** First dispatch the workflow with `execute=false`, `max_batches=1`; inspect the artifact. Then dispatch with `execute=true`, `max_batches=8` for a bounded production test. Only then use `max_batches=32`. GitHub's manual run UI is required to launch; this change does not trigger it by itself.

Future data after the UTC cutoff requires a separate run. Older recorded source-gap days are *not* retried by this orchestrator; they need an explicit gap-repair workflow after the historical pass. The whole-day source gap policy remains conservative.
