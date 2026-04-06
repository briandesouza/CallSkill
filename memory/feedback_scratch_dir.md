---
name: Use scratch/ for temporary files
description: Never create temp/debug/test files in project root — use gitignored scratch/ directory
type: feedback
---

All temporary files (test scripts, debug recordings, diagnostic tools) go in `scratch/`, never the project root.

**Why:** This is an open source repo. Temp files in the root risk being committed and pushed publicly.
**How to apply:** When creating any throwaway file, put it in `scratch/`. Clean up when done.
