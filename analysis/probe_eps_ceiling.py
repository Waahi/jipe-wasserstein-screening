# -*- coding: utf-8 -*-
"""Codex Q3 audit: is W1-DRO's 58.8d pooled ceiling a REAL inner-eps ceiling, or a truncation of
the EPSGRID upper bound? For the ceiling-defining alpha=0.02, compare inner_eps selection + resulting
k under the CURRENT grid vs an EXTENDED grid (still inner-selected only, never outer-tuned).
If selected eps piles at the grid max AND k keeps rising with a larger grid -> ceiling is an artifact.
"""
import numpy as np
import backtest_v2 as bt
import buffer_frontier as bf

GRID_CUR = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
GRID_EXT = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.75, 1.0, 1.5, 2.0]
ALPHA = 0.02

def main():
    cells_by_origin = bf.build_cells()
    # flatten cells with Z
    cells = [c for oc in cells_by_origin for c in oc]
    print(f"total cells with Z: {len(cells)}")
    # sample for speed but cover: take every 6th cell (~1000)
    samp = cells[::6]
    print(f"probing {len(samp)} cells at alpha={ALPHA}\n")

    sel_cur, sel_ext, k_cur, k_ext = [], [], [], []
    at_max_cur = at_max_ext = 0
    for c in samp:
        Z = c['Z']
        e_cur = bt.inner_eps(Z, ALPHA, GRID_CUR)
        e_ext = bt.inner_eps(Z, ALPHA, GRID_EXT)
        sel_cur.append(e_cur); sel_ext.append(e_ext)
        k_cur.append(bt.dro_k(Z, ALPHA, e_cur) * 30.0)
        k_ext.append(bt.dro_k(Z, ALPHA, e_ext) * 30.0)
        if e_cur >= GRID_CUR[-1] - 1e-9:
            at_max_cur += 1
        if e_ext >= GRID_EXT[-1] - 1e-9:
            at_max_ext += 1

    sel_cur = np.array(sel_cur); sel_ext = np.array(sel_ext)
    k_cur = np.array(k_cur); k_ext = np.array(k_ext)
    print("=== selected eps distribution (current grid) ===")
    for e in GRID_CUR:
        print(f"   eps={e:<5}: {int((np.abs(sel_cur-e)<1e-9).sum()):4d}  ({(np.abs(sel_cur-e)<1e-9).mean()*100:.1f}%)")
    print(f"   AT GRID MAX (0.30): {at_max_cur} ({at_max_cur/len(samp)*100:.1f}%)")
    print("\n=== selected eps distribution (extended grid) ===")
    for e in GRID_EXT:
        print(f"   eps={e:<5}: {int((np.abs(sel_ext-e)<1e-9).sum()):4d}  ({(np.abs(sel_ext-e)<1e-9).mean()*100:.1f}%)")
    print(f"   AT GRID MAX (2.0): {at_max_ext} ({at_max_ext/len(samp)*100:.1f}%)")

    print("\n=== pooled mean k (days) at alpha=0.02 on the sample ===")
    print(f"   current grid : {k_cur.mean():.2f}d")
    print(f"   extended grid: {k_ext.mean():.2f}d   (delta = {k_ext.mean()-k_cur.mean():+.2f}d)")
    rise = k_ext - k_cur
    print(f"   cells whose k rose with extended grid: {(rise>0.1).sum()} ({(rise>0.1).mean()*100:.1f}%); "
          f"mean rise among those: {rise[rise>0.1].mean() if (rise>0.1).any() else 0:.2f}d")

    # VERDICT logic
    frac_atmax_cur = at_max_cur/len(samp)
    delta = k_ext.mean()-k_cur.mean()
    print("\n=== VERDICT ===")
    if frac_atmax_cur < 0.10 and delta < 0.5:
        print("REAL CEILING: few cells pin the grid max and extending eps barely moves k -> 58.8d ceiling is honest.")
    elif delta >= 0.5:
        print(f"TRUNCATION RISK: extending eps raises pooled k by {delta:.2f}d -> ceiling was grid-limited; must recompute with extended grid or report radius only partially identified.")
    else:
        print(f"MIXED: {frac_atmax_cur*100:.0f}% pin grid max but pooled k rise only {delta:.2f}d -> report target/radius partially identified, no hard ceiling claim.")

if __name__ == '__main__':
    main()
