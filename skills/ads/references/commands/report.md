# /ads report [run ids | latest] [--client]

Goal: a clean report the user can send to a client, built from finalized runs.

## Steps
1. `ads.py status` to list runs. Default: the latest finalized audit/monitor per platform in the period the user asks about.
2. `ads.py start report --from RUN_A,RUN_B` → carries over sources, findings (with `run:` provenance), pacing, gaps.
3. Analyst pass for the client audience:
   - `summary.headline`: plain language, outcome first.
   - Key metrics with period and comparison if a prior run exists (label deltas as observed; don't invent prior values).
   - Keep every limitation that changes how the numbers should be read (stale data, tracking breaks, partial runs). Do not hide gaps in client reports.
   - Remove internal jargon (check ids stay as references only).
4. Finalize, then `ads.py render RUN_ID --audience client` → `report.client.md` / `report.client.html` (omits internal doc list; keeps limits).
5. If the user wants a shareable page or doc, offer to publish the HTML or put it in their docs tool. Reply with a 3-line summary and the file paths.
