# Nasdaq pilot retirement

The official CSV Actions pilot is retired. Its workflow is archived with a
non-workflow extension outside `.github/workflows`; there is no active dispatch,
cron, reusable-workflow or other Actions collector entry point on this branch.
Historical runs remain historical records. No new Nasdaq schedule is created.

Browser collector code and offline validation remain available for reference and
synthetic tests. Do not restore the archived workflow as part of manual upload.
Use the official screener's Download CSV control manually on Sunday and the
separate private upload review feature when available. KIS daily 07:00 and all
other active workflow bytes are unchanged by this retirement.
