# PrismGuard 0.1.9

**Date:** 2026-07-20  
**Theme:** Windows CLI fix for `prismguard caps`

## Fix

- `prismguard caps` crashed on Windows (cp1252) with `UnicodeEncodeError` on arrows/dashes in capability notes.
- CLI output is now ASCII-safe (`->`, `-`); `format_capabilities` / `_safe_print` harden stdout.

## Install

```bash
pip install -U "prismguard[guard-model]==0.1.9"
prismguard caps --profile light
```
