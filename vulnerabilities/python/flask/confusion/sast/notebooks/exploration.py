#!/usr/bin/env python3
"""Interactive exploration script for confusion SAST.

Run with:
    cd sast/
    .venv/bin/ipython -i notebooks/exploration.py

Or in Jupyter:
    %run notebooks/exploration.py
"""

from confusion_sast.notebook import *  # noqa: F401, F403

t = targets()

print("Confusion SAST - Interactive Explorer")
print("=" * 50)
print(t)
print()

print("Quick start:")
print("  g = load(t.r01.e01)          # extract and cache graph")
print("  g.stats()                    # graph summary")
print("  r = scan(t.r01.e01)          # scan with all rules")
print("  show(r.findings)             # display findings")
print()

print("Auto-loading r01/e01...")
g = load(t.r01.e01)
print(g)
print()

r = scan(t.r01.e01)
print(r)
show(r.findings)
