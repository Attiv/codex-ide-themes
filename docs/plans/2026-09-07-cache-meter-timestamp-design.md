# Cache Meter Hook Timestamp Design

**Date:** 2026-09-07

## Goal

Append the time at which the cache-meter Stop Hook generated its usage summary.
The timestamp should use the machine's local timezone and the fixed
`YYYY-MM-DD HH:MM:SS` format, for example `2026-09-07 18:59:52`.

## Design

In `hooks/cache-meter/cache-meter.py`, after all existing usage, pricing, and
model lines have been assembled, append one line containing the formatted local
current time. Use Python's standard-library `datetime.now().strftime(...)` so
no external dependency or timezone configuration is required. Keep the existing
JSON `systemMessage` contract unchanged.

## Error handling

The timestamp is generated only after a valid usage summary exists, so the
existing silent-exit behavior for missing or unreadable transcript data remains
unchanged.

## Testing

Add focused unit tests for the hook output that inject a deterministic local
clock and verify that the timestamp is present as the final summary line in the
requested format. Existing theme tests and the hook's manual example command
remain unchanged.
