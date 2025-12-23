#!/usr/bin/env python3
"""Convert a Python-style dict file to valid JSON.

Usage:
  python scraper/tools/fix_aa_json.py

This reads `scraper/src/sources/otodom/sell/apartment/aa.json` (which contains a
Python literal using single quotes/None/True/False), parses it with
ast.literal_eval and writes `aa.json.fixed` next to the original file.
"""
from pathlib import Path
import ast
import json

SRC = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "sources"
    / "otodom"
    / "sell"
    / "apartment"
    / "aa.json"
)
OUT = SRC.with_name("aa.json.fixed")

if not SRC.exists():
    raise SystemExit(f"Source file not found: {SRC}")

s = SRC.read_text(encoding="utf-8")
try:
    obj = ast.literal_eval(s)
except Exception as e:
    print("ast.literal_eval failed:", e)
    # Best-effort replacements and retry
    s2 = s.replace("None", "null").replace("True", "true").replace("False", "false")
    try:
        obj = ast.literal_eval(s2)
    except Exception as e2:
        raise SystemExit("Failed to parse Python literal. Run manual inspection.")

OUT.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote fixed JSON to: {OUT}")
