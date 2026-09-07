# Cache Meter Hook Timestamp Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Append the Hook generation time to the end of the token-usage summary in local `YYYY-MM-DD HH:MM:SS` format.

**Architecture:** Keep the existing JSON `systemMessage` output contract and usage logic unchanged. Add a small standard-library helper for formatting the local current time, append its result after the model line, and test the helper plus the output ordering with a deterministic clock.

**Tech Stack:** Python 3.9+, standard library `datetime`, `unittest`, existing JSONL fixture.

---

### Task 1: Add failing timestamp tests

**Files:**
- Create: `tests/test_cache_meter.py`
- Test fixture: `hooks/cache-meter/example-rollout.jsonl`

**Step 1: Write the failing test**

Add tests that import `hooks/cache-meter/cache-meter.py` and verify:

- a fixed datetime formats as `YYYY-MM-DD HH:MM:SS`;
- running `main()` with the example transcript emits JSON whose `systemMessage` ends with `时间：2026-09-07 18:59:52`.

Patch the module's clock source with a deterministic datetime value so the test does not depend on wall-clock time.

**Step 2: Run it to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cache_meter -v
```

Expected: FAIL because the Hook has no timestamp helper/output yet.

### Task 2: Implement the minimal timestamp output

**Files:**
- Modify: `hooks/cache-meter/cache-meter.py`

**Step 1: Add the standard-library clock import/helper**

Use `datetime.now().strftime("%Y-%m-%d %H:%M:%S")` for local time.

**Step 2: Append the timestamp after existing summary lines**

After the optional model line and before JSON serialization, append:

```text
时间：YYYY-MM-DD HH:MM:SS
```

Do not change early exits or the existing usage and pricing calculations.

**Step 3: Run the focused tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cache_meter -v
```

Expected: PASS.

### Task 3: Verify the complete repository

**Files:**
- No additional files.

**Step 1: Run all tests**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 2: Run the manual Hook fixture**

```bash
printf '%s\n' '{"transcript_path":"hooks/cache-meter/example-rollout.jsonl"}' \
  | python3 hooks/cache-meter/cache-meter.py
```

Expected: valid JSON with the timestamp as the final line of `systemMessage`.

**Step 3: Review the diff and status**

```bash
git diff --check
git status --short
git diff -- hooks/cache-meter/cache-meter.py tests/test_cache_meter.py
```

Confirm only the intended implementation, test, and plan files changed.
