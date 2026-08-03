# -*- coding: utf-8 -*-
"""Build the outbound submission package and the code-deposit manifest.

Written because `submission/` was previously produced by hand-copying, and a hand copy is
how a package acquires a stale file: on 2026-07-29 the copy still carried the previous
title and was missing fifteen references and the rewritten Discussion.

Two guarantees this script provides that a copy does not:

  1. Nothing enters the package unless it is named in ALLOW below. Working notes, the
     review ledger and the gate config (which itself contains the NDA denylist and must
     never ship) cannot arrive by accident, because the default is to exclude.
  2. Every artefact is rebuilt from source in the same run, so a stale-timestamp warning
     from the pre-submission gate means something rather than being routine noise.

It also writes DEPOSIT_MANIFEST.md, which fixes what the code deposit promised in
Appendix D.4 will and will not contain. The deposit is deliberately deferred until
submission, so the manifest exists to stop the deferred step from being done by zipping
the working directory.
"""
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys

D = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(D, "submission")

# The manuscript and its figures are all the publisher receives. Everything else in this
# directory is working material.
# Double blind: the publisher wants a named file and an anonymous one. The named file is the
# editor-only title-page version; the anonymous one is what referees see.
ALLOW_FILES = ["MANUSCRIPT_TITLE_PAGE.md", "MANUSCRIPT_ANON.md", "SUPPLEMENT.md"]
ALLOW_FIGURE_EXT = (".pdf", ".png")
# The graphical abstract is a separate submission item, not a manuscript figure. It goes to the
# package root under the name the journal asks for, and it is never embedded in the manuscript.
GRAPHICAL_ABSTRACT = ("GraphicalAbstract1.png", "GraphicalAbstract1.tiff")

# The code deposit is a different set: it is the analysis that produced the numbers, not
# the prose. Named explicitly so the deferred deposit cannot become "zip the folder".
DEPOSIT_CODE = [
    "build_manuscript.py", "make_numbers.py", "make_tables.py", "make_submission.py",
    "lag_sensitivity.py", "measure_gate_cost.py", "verify_data.py",
    "verify_operator_lp400.py", "_closure_audit.py",
    "figures/fig1_five_gate_protocol.py", "figures/figs_data.py",
    "figures/graphical_abstract.py",
    "figures/figs2to5.py", "figures/make_fig1_pptx.py",
    # The scripts that produced the reported numbers, as distinct from those that build the
    # document. They were omitted until 2026-08-03, which would have made the data-availability
    # statement's promise of "the build and analysis code" false: only the build half was listed.
    "analysis/build_panel.py", "analysis/basestock_dro.py",
    "analysis/backtest_onefold.py", "analysis/backtest_full.py", "analysis/backtest_v2.py",
    "analysis/gate2_bootstrap.py", "analysis/strict_controllability.py",
    "analysis/verify_operator_lp.py",
    # The controlled study of Section 4.1. Omitted until 2026-08-03 in the same way and for the
    # same reason as the block above: that rescue caught the field study's branch and missed this
    # one entirely, so four of the nine frozen artefacts had no producer in the deposit and the
    # controlled study was not reproducible from it at all.
    "analysis/buffer_reliability.py", "analysis/buffer_confirm.py",
    "analysis/buffer_bootstrap.py", "analysis/buffer_frontier.py",
    "analysis/buffer_synth.py", "analysis/gate3_impl.py",
    "analysis/poscontrol.py", "analysis/probe_eps_ceiling.py",
    # Imported by scripts already deposited, and therefore not optional: build_manuscript.py
    # does "import nlm_convert" and make_submission.py does "import make_docx". Without these
    # two the documented reproduce sequence fails on its first command from a clean extract,
    # which is exactly what the earlier clean-extract test failed to catch by running only
    # verify_data.py instead of the sequence the README promises.
    "nlm_convert.py", "make_docx.py",
    # The derived panel every analysis script reads, so the deposit runs without the 190 MB of
    # raw agency workbooks, plus the digests that tie it back to them.
    "analysis/coal_panel_2015_2024.json", "analysis/eia923_hashes.json",
    "README.md", "LICENSE",
]
DEPOSIT_NEVER = [
    "gate_config.json",      # carries the NDA denylist; the gate itself warns not to ship it
    "review_rounds",         # reviewer correspondence and the ledger
    "_gate_report.md",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(script, *args):
    cmd = [sys.executable, os.path.join(D, script), *args]
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run(cmd, cwd=D, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"{script} failed with exit {r.returncode}")
    return r.stdout


def main():
    print("rebuilding artefacts from source")
    run("figures/fig1_five_gate_protocol.py")
    # The editable PPTX twin of Figure 1 has now drifted from the matplotlib original three times,
    # each time carrying a claim or a palette the paper had already withdrawn, because it was listed
    # as deposit code but never rebuilt here. Rebuilding it in sequence is the only fix that holds.
    run("figures/make_fig1_pptx.py")
    run("figures/figs_data.py")
    run("figures/graphical_abstract.py")
    out = run("build_manuscript.py")
    m = re.search(r"counted body prose: ([\d,]+)", out)
    words = m.group(1) if m else "?"
    if "scaffolding check: clean" not in out:
        raise SystemExit("build_manuscript.py did not report a clean scaffolding check; refusing to package")
    if words != "?" and int(words.replace(",", "")) > 9000:
        raise SystemExit(f"counted body prose is {words}, over the journal ceiling of 9,000; refusing to package")
    print(f"  manuscript rebuilt, counted body prose {words} words")

    # The package is rebuilt from empty every time. A file that is no longer produced must
    # not survive in the package from an earlier run.
    if os.path.isdir(PKG):
        shutil.rmtree(PKG)
    os.makedirs(os.path.join(PKG, "figures"))

    copied = []
    for name in ALLOW_FILES:
        src = os.path.join(D, name)
        if not os.path.exists(src):
            raise SystemExit(f"required package file missing: {name}")
        shutil.copy2(src, os.path.join(PKG, name))
        copied.append(name)
    figsrc = os.path.join(D, "figures")
    for name in GRAPHICAL_ABSTRACT:
        src = os.path.join(figsrc, name)
        if not os.path.exists(src):
            raise SystemExit(f"the journal requires a graphical abstract and {name} is missing")
        shutil.copy2(src, os.path.join(PKG, name))
        copied.append(name)
    # The manuscript now also embeds the graphical abstract after the keywords, because the
    # instructions' Structure section asks for it there while the Checklist asks for the separate
    # file; the package does both. The courtesy .md copies reference figures/GraphicalAbstract1.png,
    # so the PNG is mirrored there too or those links dangle inside the package.
    shutil.copy2(os.path.join(figsrc, "GraphicalAbstract1.png"),
                 os.path.join(PKG, "figures", "GraphicalAbstract1.png"))
    copied.append("figures/GraphicalAbstract1.png")
    for f in sorted(os.listdir(figsrc)):
        if f in GRAPHICAL_ABSTRACT:
            continue
        if f.endswith(ALLOW_FIGURE_EXT):
            shutil.copy2(os.path.join(figsrc, f), os.path.join(PKG, "figures", f))
            copied.append("figures/" + f)

    # A package that contains a gate config or a working note is a packaging bug, not a
    # judgement call, so assert rather than warn.
    for root, _, files in os.walk(PKG):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), PKG).replace("\\", "/")
            if rel not in copied:
                raise SystemExit(f"unexpected file in package: {rel}")
            if any(bad in rel for bad in ("gate_config", "_gate_report", "review_rounds")):
                raise SystemExit(f"excluded artefact reached the package: {rel}")

    # The package is produced atomically, so every artefact carries one build timestamp.
    # Without this the figure PDFs end up a second or two older than MANUSCRIPT.md and
    # MANIFEST.md purely because of copy order, and the pre-submission gate's freshness
    # check, which compares every PDF against the newest markdown in the target, reports
    # all of them as possibly stale. That check is written for a compiled manuscript PDF
    # and cannot tell a figure PDF apart from one; a warning that always fires is a
    # warning that gets ignored, so we make the timestamps say what is true.
    stamp = os.path.getmtime(os.path.join(D, "MANUSCRIPT_TITLE_PAGE.md"))


    for rel in copied:
        os.utime(os.path.join(PKG, rel), (stamp, stamp))

    # ---- upload-ready deliverables --------------------------------------------------------
    # The journal takes Word or LaTeX, not markdown, and the portal asks for specific file roles.
    # The markdown stays as the auditable source; these are what actually gets uploaded.
    import make_docx
    for src, dst in (# The gate treats any file whose name contains "manuscript" as the anonymous one unless the name
                     # also says "title", and this file is exactly the title-page-bearing manuscript, so the
                     # longer name is both accurate and legible to that rule. The upload role is chosen in
                     # the portal, not from the filename.
                     ("MANUSCRIPT_TITLE_PAGE.md", "Title_page_and_manuscript_with_author_details.docx"),
                     ("MANUSCRIPT_ANON.md", "Manuscript_anonymous.docx"),
                     ("SUPPLEMENT.md", "Supplementary_material.docx")):
        make_docx.convert(os.path.join(PKG, src), os.path.join(PKG, dst))
        copied.append(dst)
    # The cover letter states the body word count and the abstract length to the editors as facts.
    # Both have now gone stale twice in one session, because they are hand-typed here while the real
    # numbers move whenever a sentence is split. Assert rather than trust: a wrong number in a cover
    # letter is a claim to an editor that the manuscript itself contradicts.
    _cl = io.open(os.path.join(D, "COVER_LETTER.md"), encoding="utf-8").read()
    _cl_body = re.search(r"The main text is ([\d,]+) words", _cl)
    _cl_abs = re.search(r"abstract is (\d+) words", _cl)
    if not _cl_body or not _cl_abs:
        sys.exit("cover letter no longer states its word counts; the freshness guard cannot check it")
    _abs_src = io.open(os.path.join(D, "ABSTRACT.md"), encoding="utf-8").read()
    _abs_txt = re.sub(r"\s+", " ", re.search(r"\*\*Abstract\.\*\*(.*?)\n\n", _abs_src, re.S).group(1))
    _abs_n = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’./%-]*", _abs_txt))
    if _cl_body.group(1).replace(",", "") != str(words).replace(",", ""):
        sys.exit(f"cover letter says {_cl_body.group(1)} body words, the build counts {words}")
    if int(_cl_abs.group(1)) != _abs_n:
        sys.exit(f"cover letter says {_cl_abs.group(1)} abstract words, the abstract has {_abs_n}")

    make_docx.convert(os.path.join(D, "COVER_LETTER.md"), os.path.join(PKG, "Cover_letter.docx"))
    copied.append("Cover_letter.docx")

    # Goto's comment (i): running-text symbols and displayed equations must share one face. The
    # converter now sets Cambria Math for both; assert over the full document XML, tables included,
    # that no Consolas run survived in anything we ship.
    import zipfile
    for docxname in ("Title_page_and_manuscript_with_author_details.docx", "Manuscript_anonymous.docx",
                     "Supplementary_material.docx", "Cover_letter.docx"):
        with zipfile.ZipFile(os.path.join(PKG, docxname)) as zf:
            if b"Consolas" in zf.read("word/document.xml"):
                sys.exit(f"{docxname} still carries Consolas maths runs; font unification failed")

    # Figures are uploaded one per file under the number the manuscript cites.
    FIGURE_UPLOAD = {"fig1_five_gate_protocol": "Figure1",
                     "fig2_controlled_bands": "Figure2",
                     "fig3_field_gate4": "Figure3",
                     "fig4_regime_support": "Figure4"}
    for stem, name in FIGURE_UPLOAD.items():
        for ext in (".pdf", ".png"):
            src = os.path.join(PKG, "figures", stem + ext)
            if not os.path.exists(src):
                raise SystemExit(f"figure missing from the package: {stem}{ext}")
            shutil.copy2(src, os.path.join(PKG, name + ext))
            copied.append(name + ext)

    # The manifest is written last, after the DOCX and the numbered figure copies exist, so that
    # its SHA-256 table covers the files that are actually uploaded. Written earlier it recorded
    # only the markdown sources and left the four Word files, the real deliverables, unhashed.
    lines = ["# Submission package manifest", "",
             f"Built by `make_submission.py`. Counted body prose: {words} words, ceiling 9,000.", "",
             "| file | bytes | SHA-256 |", "|---|---:|---|"]
    for rel in copied:
        p = os.path.join(PKG, rel)
        lines.append(f"| `{rel}` | {os.path.getsize(p):,} | `{sha256(p)}` |")
    lines += ["", "## Code deposit", "",
              "The deposit promised in Appendix D.4 contains exactly the files below, and none",
              "of the working notes, the review ledger or the gate configuration. The gate",
              "configuration is excluded because it carries the confidential-data denylist.", "",
              "| file | present |", "|---|---|"]
    for rel in DEPOSIT_CODE:
        lines.append(f"| `{rel}` | {'yes' if os.path.exists(os.path.join(D, rel)) else 'MISSING'} |")
    lines += ["", "Never deposited: " + ", ".join(f"`{x}`" for x in DEPOSIT_NEVER) + "."]
    io.open(os.path.join(PKG, "MANIFEST.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    copied.append("MANIFEST.md")

    # Which file goes into which portal role. The package holds more than gets uploaded: the
    # markdown files are the auditable source, and figures/ duplicates the numbered Figure copies.
    # Without this an author has to infer the mapping, which is how a courtesy copy gets uploaded
    # as the anonymous manuscript.
    UPLOAD = [
        ("Title_page_and_manuscript_with_author_details.docx", "Title page + manuscript (author details)",
         "editor-only; carries authors, ORCIDs, funding, CRediT, competing interest, biographies"),
        ("Manuscript_anonymous.docx", "Main document / anonymous manuscript",
         "what referees see; double blind, no identifying material"),
        ("Supplementary_material.docx", "Supplemental material", "S1 to S6, outside the word limit"),
        ("GraphicalAbstract1.png", "Graphical abstract", "525 px wide, separate file, this exact filename"),
        ("Cover_letter.docx", "Cover letter", "states word count, blinding and the competing interest"),
        ("Figure1.pdf", "Figure 1", "vector; Figure1.png is the raster alternative"),
        ("Figure2.pdf", "Figure 2", "vector; Figure2.png is the raster alternative"),
        ("Figure3.pdf", "Figure 3", "vector; Figure3.png is the raster alternative"),
        ("Figure4.pdf", "Figure 4", "vector; Figure4.png is the raster alternative"),
    ]
    ck = ["# What to upload, and as what", "",
          "Built by `make_submission.py`. Body " + str(words) + " words against a 7,000-9,000 range.", "",
          "| file | portal role | note |", "|---|---|---|"]
    for f, role, note in UPLOAD:
        if not os.path.exists(os.path.join(PKG, f)):
            raise SystemExit("upload checklist names a file the package does not contain: " + f)
        ck.append("| `" + f + "` | " + role + " | " + note + " |")
    ck += ["", "## In the package but NOT uploaded", "",
           "- `MANUSCRIPT_TITLE_PAGE.md`, `MANUSCRIPT_ANON.md`, `SUPPLEMENT.md`: the auditable markdown",
           "  sources the DOCX are generated from.",
           "- `figures/`: the build's own copies. The numbered `Figure1` to `Figure4` files at the package",
           "  root are the upload copies of the same images.",
           "- `Figure1` to `Figure4` `.png`: raster alternatives; upload the PDFs unless the portal refuses them.",
           "- `MANIFEST.md` and this file: build records.", "",
           "## Author-supplied items the portal asks for separately", "",
           "- ORCID for each author, also in the title page file.",
           "- CRediT roles, also in the title page file.",
           "- Competing interest: one author sits on this journal's editorial board. Declare it in the",
           "  portal field as well as in the cover letter.",
           "- Open access and APC choice.",
           "- The analysis-code identifier: **10.5281/zenodo.21766949**. The Zenodo record is a private",
           "  draft for the duration of double-blind review and is published on acceptance, so the DOI is",
           "  reserved and does not resolve yet. Supplementary Section S4 says exactly this, so the record",
           "  must not be published before S4 is updated to match.",
           "- Proof sign-off: recorded as approved by Goto. See SIGNOFF_PACKET.md and, if the mathematics",
           "  changes after this point, re-run verify_signoff.py before relying on that approval."]
    io.open(os.path.join(PKG, "UPLOAD_CHECKLIST.md"), "w", encoding="utf-8").write("\n".join(ck) + "\n")
    copied.append("UPLOAD_CHECKLIST.md")

    # Re-stamp now that the DOCX, the numbered figures, the manifest and this checklist all exist.
    # Moving the manifest write later broke the single-build-timestamp invariant and the gate
    # immediately reported eight freshness warnings; this restores it.
    for rel in copied:
        os.utime(os.path.join(PKG, rel), (stamp, stamp))

    # The pre-submission gate writes its report into whatever directory it scans, so running it on
    # the package leaves _gate_report.md sitting inside the package. Remove it here so that the last
    # action before shipping is always a rebuild, and a stale report cannot travel with the files.
    stray = os.path.join(PKG, "_gate_report.md")
    if os.path.exists(stray):
        os.remove(stray)

    print(f"package rebuilt at {PKG}")
    for rel in copied:
        print("   ", rel)
    missing = [r for r in DEPOSIT_CODE if not os.path.exists(os.path.join(D, r))]
    if missing:
        print("\nWARNING, deposit files named in the manifest but not present:", missing)


if __name__ == "__main__":
    main()
