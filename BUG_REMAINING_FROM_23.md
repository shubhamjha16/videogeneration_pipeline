# Remaining Bugs from the "23" Estimate

Date: 2026-04-13

## Clarification

The value "23" came from the upper bound of a **potential-bug estimate** (not 23 confirmed defects).

## Current calculation against that estimate

- Upper-bound estimate used: **23 potential bugs**
- Concrete bugs fixed so far: **19** (see `BUG_FIX_COUNT.md`)

### Remaining from that upper-bound estimate

**23 - 19 = 4 potential bugs remaining (estimate-based).**

## What this means

- Confirmed fixed: 19
- Remaining count above is an estimate gap, not a list of 12 confirmed defects.
- The unresolved risk is still concentrated in broad `except Exception` hotspots and needs integration/runtime validation.
