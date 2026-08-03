# -*- coding: utf-8 -*-
"""Check the frozen result artefacts in data/ against data/MANIFEST.json.

Run this before regenerating NUMBERS.md, TABLES.md or the figures. If a digest has changed,
every numeral downstream of it has changed too, silently, and the manuscript must not be
rebuilt until the discrepancy is explained.
"""
import hashlib, json, os, sys

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
man = json.load(open(os.path.join(D, "MANIFEST.json"), encoding="utf-8"))
bad = []
for name, rec in sorted(man.items()):
    p = os.path.join(D, name)
    if not os.path.exists(p):
        bad.append(f"MISSING  {name}"); continue
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    size = os.path.getsize(p)
    okd = h.hexdigest() == rec["sha256"]
    oks = size == rec["bytes"]
    if not oks:
        bad.append(f"SIZE     {name}: manifest {rec['bytes']:,} bytes, found {size:,}")
    if not okd:
        bad.append(f"DIGEST   {name}\n         expected {rec['sha256']}\n         found    {h.hexdigest()}")
    if okd and oks:
        print(f"ok  {name}  {size:,} bytes")
if bad:
    print("\n".join(bad)); sys.exit("data integrity check FAILED")
print(f"\nall {len(man)} artefacts match the manifest on size and digest")
print("Note: the manifest is self-describing and unsigned. It detects accidental corruption,")
print("truncation and substitution of an artefact, but not an edit that changes an artefact and")
print("its manifest entry together. Guarding against that needs an external trust anchor, such")
print("as the digest recorded in the deposited archive's own metadata.")
