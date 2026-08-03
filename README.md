# Replication package

Code and frozen result artefacts for "Evaluating Wasserstein-robust inventory decisions: a five-gate
framework and a plant-level coal inventory study".

No absolute paths, no network access, no proprietary data. The one input not redistributed here is the
set of raw EIA-923 workbooks, about 190 MB of public agency files, whose download locations and SHA-256
digests are recorded in `analysis/eia923_hashes.json` and in Supplementary Section S4 of the paper. The
derived monthly panel those workbooks produce **is** included, so every analysis script runs without them.

## Contents

| path | what it is |
|---|---|
| `analysis/` | the analysis that produced the reported numbers, listed separately below |
| `analysis/coal_panel_2015_2024.json` | the derived monthly plant-level panel |
| `analysis/eia923_hashes.json` | SHA-256 of every raw EIA-923 archive the panel was built from |
| `data/` | the frozen result artefacts every reported number derives from, plus `MANIFEST.json` |
| `verify_data.py` | checks each artefact against the manifest on size and SHA-256 |
| `make_numbers.py` | regenerates `NUMBERS.md`, the single source of truth for reported figures |
| `make_tables.py` | regenerates `TABLES.md` |
| `figures/` | scripts for Figures 1 to 4 and the graphical abstract, as PDF and 600 dpi PNG |
| `build_manuscript.py` | assembles the named and anonymous manuscripts and the supplement |
| `make_submission.py` | rebuilds every artefact and assembles the submission package |
| `verify_operator_lp400.py` | the 400-case independent linear-programme check of the worst-case exceedance operator |
| `lag_sensitivity.py` | the publication-lag bracketing reported in Section 4.2 |
| `measure_gate_cost.py` | the per-gate timing reported in Section 5.2 |

### `analysis/`

The scripts that produced the paper's numbers, as opposed to those that build the document. They read
`coal_panel_2015_2024.json` from the working directory, so run them from inside `analysis/`.

| file | what it does |
|---|---|
| `build_panel.py` | builds the derived panel from the raw `sched2345_YYYY.xlsx` workbooks |
| `basestock_dro.py` | the type-1 Wasserstein service-form solver |
| `backtest_onefold.py` | the single-fold rolling-origin backtest |
| `backtest_full.py` | the full rolling-origin backtest behind the frontiers |
| `backtest_v2.py` | the confirmatory backtest run after the operator correction |
| `gate2_bootstrap.py` | the Gate 2 screen and its block bootstrap |
| `strict_controllability.py` | the inventory-identity closure check |
| `verify_operator_lp.py` | the linear-programme cross-check of the worst-case operator |

## Reproducing

```
python verify_data.py                       # integrity first; stop if it fails
cd analysis && python backtest_full.py && cd ..
python make_numbers.py
python make_tables.py
cd figures && python fig1_five_gate_protocol.py && python figs_data.py && python graphical_abstract.py && cd ..
python build_manuscript.py
```

`verify_operator_lp400.py`, `lag_sensitivity.py` and `measure_gate_cost.py` are independent of that order.
Rebuilding the panel from the raw workbooks with `analysis/build_panel.py` requires downloading them
first; their digests are in `analysis/eia923_hashes.json`.

Requires Python 3.10 or later with `numpy`, `scipy`, `pandas`, `matplotlib`, `openpyxl`, `statsmodels`,
`python-docx`, `python-pptx` and `Pillow`. Tested on numpy 2.4.6, scipy 1.17.1.

## What the data are

Public agency data, EIA Form 923 Schedules 2 to 5. Supplementary Section S4 of the paper gives the
download location, retrieval date and SHA-256 digest of every source archive, so the raw inputs can be
re-obtained and checked independently. No suppressed cell is reconstructed and no early-release file
contributes to a reported number.

## Integrity note

`data/MANIFEST.json` is self-describing and unsigned. It detects accidental corruption, truncation and
substitution of an artefact, but not an edit that changes an artefact and its manifest entry together. The
digest of this archive as deposited is the external anchor for that.

## Licence

Code under the MIT licence, see `LICENSE`. The agency data are public domain works of the United States
government.
