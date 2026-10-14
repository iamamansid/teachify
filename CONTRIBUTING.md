# Contributing to Teachify

Thanks for helping people learn instead of just shipping code they can't explain.

## Best first PR: a new task

One JSON file + a test. No server code changes needed.

1. Copy `src/tasks/js-express-hello.json` to `src/tasks/<your-task>.json`.
2. Keep it to 3–7 steps. Each step: **one action, one `why`, one check, three hints**.
3. Rules:
   - The learner types every line. Never put the full solution in `instruction` or `whatToType`.
   - `hintL3` is the strongest hint — it still must not type the code for the learner.
   - Every step must be verifiable (`fileExists` / `regex` / `contains` / `all`). If you can't verify it, it's not a step — it's a lecture.
   - Quiz questions must test *understanding* (why / what-happens-if), not recall of exact code.
4. Run `npm test` — the loader validates your JSON schema.
5. Add your task id to the tasks list in `README.md`.

## Code changes

- `npm install && npm test` must stay green.
- No network calls, no API keys, no telemetry in the server. Local-first by design.
- Keep the invariants in `docs/ARCHITECTURE.md`: never the full solution, advance only on pass, hints never type code.

## Reporting issues

Include: task id, step id, what you typed (or a minimal repro), what the verifier said, and what you expected. Screenshots of the step are welcome.
