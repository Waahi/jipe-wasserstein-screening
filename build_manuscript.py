# -*- coding: utf-8 -*-
"""Build MANUSCRIPT.md and SUPPLEMENT.md for the six-section JIPE structure.

Replaces assemble.py, which built the nine-section draft. The journal mandates exactly
1 Introduction, 2 Literature Review, 3 Methods or Problem Description, 4 Results, 5 Discussion,
6 Concluding Remarks, with everything else folded in and every section numbered, and it excludes
the abstract, references, figures, tables and supplementary material from the 9,000-word count.
That exclusion is what makes the appendices affordable: they move to the supplement whole.

Display items, per COMPLIANCE_PLAN.md D.3:

  main text   Table 1 diagnostic contract, Table 2 equivalence verdicts, Table 3 cross-study gates,
              Figures 1 to 4
  supplement  the controlled study's decision rules, the in-reach paired differences, and the
              historical-support detail, which were Tables 2, 3 and 5 of the nine-section draft

Supplement sections map one to one onto the old appendices, S1 to S5, plus S6 for the full statement
of the prospective hypothesis. The body cites them by those numbers, so the mapping is asserted here
rather than left to memory.

The main and supplementary reference lists are separate and separately numbered, per C.4: a work
cited in both appears in both. Numbering itself happens at the NLM conversion, which must run after
this build because numbers are assigned by order of first appearance.
"""
import io
import os
import re

D = os.path.dirname(os.path.abspath(__file__))
# The named file is the one carrying the title page. Naming it so is accurate, and it also lets
# the pre-submission gate tell the two manuscript files apart: its heuristic treats any file whose
# name contains "manuscript" as the anonymous one, so a named MANUSCRIPT.md produced eighteen
# identity FAILs against the file that is supposed to carry identities.
OUT = os.path.join(D, "MANUSCRIPT_TITLE_PAGE.md")
SUP = os.path.join(D, "SUPPLEMENT.md")

# Working notes never reach either output. Matched by content, because a note can sit anywhere.
NOTE_HEADS = ("## Trimming note", "## Revision record", "## Citation provenance record",
              "## Citation record", "## Reading note", "### Two items to resolve",
              "### One claim deliberately")
LEAK_PATTERNS = (
    # "word count" on its own is too wide: the journal's checklist requires a word count stated in
    # the paper, so only the author-scaffolding form, "(word count 3.1: about 470)", is a leak.
    r"\(word count", r"budget from", r"trimming note", r"\bCodex\b", r"thread 019",
    r"revision \d", r"at the end of this file", r"verification record",
    r"authoritative reference list", r"paywalled", r"deliberately not made",
    r"provenance record", r"an earlier project note", r"do not edit by hand",
    r"review ruling", r"citation placeholders", r"spelling stays British",
)


def load(name):
    return io.open(os.path.join(D, name), encoding="utf-8").read()


def after_rule(text):
    """Drop the leading working-note block: everything up to the first horizontal rule."""
    parts = text.split("\n---\n", 1)
    body = parts[1] if len(parts) == 2 else text
    cut = len(body)
    for h in NOTE_HEADS:
        i = body.find("\n" + h)
        if i != -1:
            cut = min(cut, i)
    body = re.sub(r"\n{3,}", "\n\n", body[:cut])
    return body.strip()


def section(text, start, end=None):
    i = text.find(start)
    if i == -1:
        raise SystemExit(f"heading not found: {start!r}")
    j = text.find(end, i + len(start)) if end else len(text)
    return text[i:(j if end and j != -1 else len(text))].strip()


def counted(s):
    """Body prose only: the journal excludes tables, captions and table notes.

    A caption is a block, not a line. Filtering only the line that opens with the label leaves its
    continuation lines in the count, which is worth 270 words across three tables here and is exactly
    the kind of silent overshoot that puts a paper over a hard ceiling.
    """
    keep, in_caption = [], False
    for ln in s.split("\n"):
        st = ln.strip()
        if re.match(r"\*\*(Table|Figure) \d", st):
            in_caption = True
            continue
        if in_caption:
            if st == "":
                in_caption = False
            continue
        if st.startswith("|") or st.startswith("*Note") or st.startswith("_Note"):
            continue
        keep.append(ln)
    return len(re.findall(r"\b[\w'-]+\b", "\n".join(keep)))


def table(name, marker):
    """Pull one generated table body out of TABLES.md by its id."""
    t = load("TABLES.md")
    ids = re.findall(r"<!--TABLE:([a-z_]+)-->", t)
    if marker not in ids:
        raise SystemExit(f"table id not found in TABLES.md: {marker}")
    k = ids.index(marker)
    start = t.find(f"<!--TABLE:{marker}-->") + len(f"<!--TABLE:{marker}-->")
    end = t.find(f"<!--TABLE:{ids[k+1]}-->") if k + 1 < len(ids) else len(t)
    body = t[start:end].strip()
    # the generated bodies carry their own old numbering in the caption
    # One caption form throughout: the generated bodies use a heading for some tables and bold for
    # others, and a paper that mixes the two is a paper that mixes them in the proofs as well.
    body = re.sub(r"^(?:#+ |\*\*)Table \d+\.?\*?\*?", f"**{name}.**", body, count=1)
    return body


s12 = after_rule(load("DRAFT_S1_S2_NEW.md"))
s3 = after_rule(load("DRAFT_S3_METHODS.md"))
s4 = after_rule(load("DRAFT_S4_RESULTS.md"))
s5 = after_rule(load("DRAFT_S5_DISCUSSION.md"))
s6 = after_rule(load("DRAFT_S6_CONCLUDING.md"))

# Table 1 is written by hand inside the methods draft rather than generated, because it is a
# contract rather than a result. Extract it so the build fails loudly if it is ever lost.
_s34 = load("DRAFT_S3_S4.md")
_i = _s34.find("**Table 1.**")
if _i == -1:
    raise SystemExit("Table 1, the diagnostic contract, not found in DRAFT_S3_S4.md")
_j = _s34.find("\n\n", _s34.rfind("|", _i, _i + 4000))
TABLE1 = _s34[_i:_j].strip()
if "CERTIFY REDUNDANT" not in TABLE1 or TABLE1.count("\n|") < 5:
    raise SystemExit("Table 1 extraction failed: contract body incomplete")

_t5 = load("DRAFT_TABLE5.md")
_a, _b = _t5.find("**Table 6.**"), _t5.find("## Reading note")
if _a == -1 or _b == -1 or _b <= _a:
    raise SystemExit("cross-study table extraction failed")
TABLE3 = _t5[_a:_b].strip().replace("**Table 6.**", "**Table 3.**", 1)
if "CERTIFY REDUNDANT" not in TABLE3:
    raise SystemExit("cross-study table body not captured")

TABLE2 = table("Table 2", "equivalence")

# One definition, used by the manuscript and by the supplement's "Supplement to ..." line. It was
# written out twice before, which is how a title change drifts: the paper says one thing and its own
# supplement cites another.
#
# The co-authors' title, adopted by the corresponding author. Its wording is theirs and is not to be
# edited here; only the casing is this journal's, sentence case, which the Crossref-registered titles of
# the JIPE papers this manuscript cites establish (Gómez-Rocha et al. 2024 is decisive: lower-case "a"
# after the colon). Flip this one string back to Title Case if the co-authors want that instead.
#
# The title carries no phase claim, which is what dissolves the earlier "before solving" over-claim on
# gates 4 and 5. Three things it stops carrying are therefore carried elsewhere, by design and not by
# accident: the ordering claim moved to Section 1 and the abstract, the type-1 scope bound to the
# abstract and keywords, and "framework" is now defined in Section 1 against "protocol" because the
# body used the latter sixteen times and the former never. See
# review_rounds/round-title-adopted/adjudication.md and MODIFICATION_PLAN_TITLE_ADOPTED.md.
TITLE = ("Evaluating Wasserstein-robust inventory decisions: a five-gate framework and a plant-level "
         "coal inventory study")

blocks = [
    f"""# {TITLE}

**Tengfei Shao**^a^ (corresponding author), **Kotomichi Matsuno**^b^, **Masayuki Goto**^c^

^a^ Global Education Center, Waseda University, Tokyo, Japan. tengfei.shao@toki.waseda.jp
ORCID 0000-0003-3089-5696
^b^ Faculty of Business Administration, Rissho University, Tokyo, Japan
ORCID 0000-0002-7061-7204
^c^ Institute for Mathematical Science and Engineering, Waseda University, Tokyo, Japan
ORCID 0000-0003-1929-9359

""" + load("ABSTRACT.md").strip(),
    section(s12, "# 1. Introduction", "# 2. Literature Review"),
    section(s12, "# 2. Literature Review"),
    s3 + "\n\n" + TABLE1,
    s4 + "\n\n" + TABLE2,
    s5 + "\n\n" + TABLE3,
    s6,
    """# Declarations

**Funding.** This work was supported by JSPS KAKENHI Grant-in-Aid for Scientific Research (A), Grant
Number B1K401870601.

**Use of generative artificial intelligence.** Claude was used for English language polishing only. All
analysis and results are the genuine work of the authors, who take full responsibility for the content.

**Competing interests.** One author serves on an editorial board of this journal and has taken no part
in the editorial handling or peer review of this manuscript. The board membership is disclosed in full
to the editors in the submission system and the cover letter, and is named in the title page file only,
so that it does not reach referees under double-blind review. The other authors declare no competing
interests.

**Ethics.** Ethics approval and informed consent were not required, because the study uses publicly
available agency data together with simulated data and involves no human participants, no animals and no
identifiable personal information.

**CRediT author statement.** **Tengfei Shao:** Conceptualization; Methodology; Software; Validation;
Formal analysis; Investigation; Data curation; Writing - original draft; Writing - review and editing;
Visualization. **Kotomichi Matsuno:** Methodology; Writing - review and editing. **Masayuki Goto:**
Supervision; Project administration; Funding acquisition; Writing - review and editing. All authors read
and approved the final manuscript.

**Data availability.** The agency data are public. Supplementary Section S4 gives the download location,
retrieval date and SHA-256 digest of every input file, together with the sample flow. The build and
analysis code is archived and its DOI, digest and release condition are recorded in Supplementary
Section S4. No
suppressed cell is reconstructed and no early-release file contributes to a reported number, so the
early-release aggregation restriction is not engaged.""",
]

# Biographical notes are a checklist item and they name their authors, so they belong in the
# title-page file and nowhere else. They are pulled from BIOS_DRAFT.md rather than pasted here, so
# that the authors correct one file and the build follows.
_bios_src = load("BIOS_DRAFT.md")
_ba = _bios_src.index("## Tengfei Shao")
_bb = _bios_src.index("## Three items to confirm or correct")
_bios = re.sub(r"\n\*\(\d+ words\)\*", "", _bios_src[_ba:_bb])
_bios = re.sub(r"^-{3,}\s*$", "", _bios, flags=re.M).strip()
_bios = re.sub(r"^## (.+)$", r"**\1.** ", _bios, flags=re.M)
_bios = re.sub(r"\*\* \n", "** ", _bios)
if _bios.count("Shao") == 0 or _bios.count("Matsuno") == 0 or _bios.count("Goto") == 0:
    raise SystemExit("biographical notes not extracted; check the headings in BIOS_DRAFT.md")
blocks.append("# Notes on contributors\n\n" + _bios)

# ---------------------------------------------------------------- NLM numbering
# The style numbers by first mention, so numbers can only be assigned once the body is in its final
# order. Placeholders carry a short key; the mapping to the reference list is by first-author surname
# and, where one surname appears twice, by year.
import nlm_convert as NC

_ALIAS = {"MEK": "Mohajerin Esfahani", "LKM": "Lee", "VdL": "Van der Laan", "GK": "Gupta",
          "Dacrema": "Ferrari Dacrema", "deRuiter": "de Ruiter", "vanBeesten": "van Beesten",
          "vanderHaar": "van der Haar", "Barber2021": "Barber", "Barber2023": "Barber",
          # REFERENCES.md now spells the surname with its diacritic, Gómez-Rocha, to match the
          # Crossref-registered author name; the body placeholder key stays plain ASCII so the
          # in-text citation markers do not need to change.
          "Gomez-Rocha": "Gómez-Rocha"}
_YEAR = {"Barber2021": "2021", "Barber2023": "2023"}

_exact, _prefix = NC.load_ltwa(NC.LTWA)
_src = load("REFERENCES.md")
_a, _b = _src.find("## Reference list"), _src.find("## Verification record")
if _a == -1 or _b == -1 or _b <= _a:
    raise SystemExit("reference-list extraction failed")
_raws = [x.strip() for x in re.split(r"\n\s*\n", _src[_a:_b].split("\n", 1)[1].strip()) if x.strip()]
_recs = [NC.parse_entry(r) for r in _raws]
if any(r is None for r in _recs):
    raise SystemExit("a reference entry failed to parse; run nlm_convert.py to see which")


def _lookup(key):
    sur = _ALIAS.get(key, key)
    yr = _YEAR.get(key)
    hits = [r for r in _recs if r["authors"].startswith(sur) and (yr is None or r["year"] == yr)]
    if len(hits) != 1:
        raise SystemExit(f"citation key {key!r} matched {len(hits)} reference entries")
    return hits[0]


def _render(rec):
    au = NC.nlm_authors(rec["authors"])
    s = f"{au}{'' if au.endswith('.') else '.'} {NC.sentence_case(rec['title'])}."
    if rec["venue"]:
        vv = NC.abbreviate_title(rec["venue"], _exact, _prefix)
        tail = NC.format_tail(rec["tail"])
        if rec.get("conf"):
            s += f" In: {vv}{'' if vv.endswith('.') else '.'} {rec['year']}"
            s += f";{tail}." if tail else "."
        else:
            s += f" {vv}{'' if vv.endswith('.') else '.'} {rec['year']}"
            s += f";{tail}." if tail else "."
    elif rec.get("note"):
        # An unpublished work's provenance clause is printed verbatim: it is not a title, and it
        # already carries its own date, so the year field is not appended a second time after it.
        s += f" {rec['note']}."
    else:
        s += f" {rec['year']}."
    if rec["doi"]:
        s += f" doi: {rec['doi']}"
    return s


def _compress(nums):
    """[2,3,4,5,7,10] becomes '2-5,7,10', joined with an unspaced en dash as the guide requires.

    A run of exactly two consecutive integers used to fall into the "not worth a range" branch but
    was then printed as a single number rather than two: `out.append(str(nums[i]))` inside a branch
    reached for run lengths 0 and 1 (j - i < 2 means the run has one or two members), which silently
    dropped the second number of every such pair. Six references in this paper, each the second
    half of a two-item `[refs A; B]` group, were sitting in the numbered list with no citation
    marker anywhere in the body as a result: a real orphan reference, not a false positive from the
    checker. Verified against the guide's own worked example, [2,3,4,5,7,10] -> "2-5,7,10", which
    this form reproduces exactly.
    """
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:                          # three or more in a row: compress to a range
            out.append(f"{nums[i]}–{nums[j]}")
        else:                                   # one or two: list every number, drop none
            out.extend(str(x) for x in nums[i:j + 1])
        i = j + 1
    return ",".join(out)


_body = "\n\n---\n\n".join(blocks)
_order, _seen = [], {}


def _sub(m):
    nums = []
    for k in (x.strip().replace("ref ", "") for x in m.group(1).split(";")):
        if k not in _seen:
            _seen[k] = len(_order) + 1
            _order.append(k)
        nums.append(_seen[k])
    return "[" + _compress(nums) + "]"


_body = re.sub(r"\[refs? ([^\]]+)\]", _sub, _body)
_left = re.findall(r"\[refs? [^\]]+\]", _body)
if _left:
    raise SystemExit(f"unresolved citation placeholders: {_left[:5]}")

_cited = [_lookup(k) for k in _order]
_numbered = "\n\n".join(f"[{i}] {_render(r)}" for i, r in enumerate(_cited, 1))
_uncited = [r for r in _recs if r not in _cited]

# Figures are uploaded as separate files, so their captions have to travel in the manuscript or the
# referee sees four images with no legend. They are kept in their own source file rather than inline in
# the body, because the body's figure mentions are cross-references ("Figure 2 reports the comparison")
# and a caption placed there would read as a second, competing description of the same display item.
_figcaps = after_rule(load("FIGURE_CAPTIONS.md")).strip()
_n_caps = len(re.findall(r"^\*\*Figure \d+\.\*\*", _figcaps, flags=re.M))
_n_figrefs = len(set(re.findall(r"\bFigure (\d+)", _body)))
if _n_caps != _n_figrefs:
    raise SystemExit(f"{_n_caps} figure captions but {_n_figrefs} figures cited in the body")

txt = (_body + "\n\n---\n\n" + "# References\n\n" + _numbered
       + "\n\n---\n\n# Figure captions\n\n" + _figcaps + "\n")

# The checklist asks for a word count in the paper. It is stated on the basis the editors confirmed,
# and labelled as such, so that a reader comparing it with a word processor's gross count can see why
# the two differ rather than suspecting the lower number.
_wc_stamp = counted(txt[txt.find("# 1. Introduction"):txt.find("# Declarations")])
txt = txt.replace(
    "\n\n---\n\n# 1. Introduction",
    f"\n\n**Word count.** {_wc_stamp:,} words of body text, sections 1 to 6, excluding the abstract, "
    "the references, figures, tables and their captions, and the supplementary material."
    "\n\n---\n\n# 1. Introduction", 1)
io.open(OUT, "w", encoding="utf-8").write(txt)

# ---------------------------------------------------------------- anonymous file
# The journal is double blind, so two manuscript files are required. The anonymous one must lose
# more than the author block: a single fixed grant number is searchable and identifies the group,
# the CRediT statement names everyone, and the competing-interest sentence identifies an author by
# describing their role at this journal. All of it is restored in the title-page file, which the
# system marks editor-only, and at publication.
ANON = os.path.join(D, "MANUSCRIPT_ANON.md")
_anon = txt
_a = _anon.find("**Tengfei Shao**")
_b = _anon.find("**Abstract.**")
if _a == -1 or _b == -1 or _b <= _a:
    raise SystemExit("title-page block not found; the anonymous file cannot be built safely")
_anon = _anon[:_a] + _anon[_b:]

# The biographical notes are a whole section that names every author. Anything appended to the
# named build after this point must be handled here too, or it reaches referees: adding the notes
# without this cut leaked nine identity terms into the anonymous file, and the gate below caught it.
_bio_a = _anon.find("# Notes on contributors")
if _bio_a != -1:
    _bio_b = _anon.find("\n\n---\n\n", _bio_a)
    if _bio_b == -1:
        raise SystemExit("biographical notes found but their end marker was not; refusing to guess")
    _anon = _anon[:_bio_a] + _anon[_bio_b + len("\n\n---\n\n"):]

_decl_a = _anon.find("# Declarations")
_decl_b = _anon.find("\n\n---\n\n", _decl_a)
if _decl_a == -1 or _decl_b == -1:
    raise SystemExit("declarations block not found; the anonymous file cannot be built safely")
_anon = _anon[:_decl_a] + """# Declarations

**Funding.** Funding information is given in the title page file, which is not shared with referees.

**Use of generative artificial intelligence.** Claude was used for English language polishing only. All
analysis and results are the genuine work of the authors, who take full responsibility for the content.

**Competing interests.** A competing-interest declaration has been made to the editors in the title page
file and in the submission system.

**Ethics.** Ethics approval and informed consent were not required, because the study uses publicly
available agency data together with simulated data and involves no human participants, no animals and no
identifiable personal information.

**CRediT author statement.** Author contributions are given in the title page file.

**Data availability.** The agency data are public. Supplementary Section S4 gives the download location,
retrieval date and SHA-256 digest of every input file, together with the sample flow. The build and
analysis code is archived and its DOI, digest and release condition are recorded in Supplementary
Section S4. No suppressed
cell is reconstructed and no early-release file contributes to a reported number, so the early-release
aggregation restriction is not engaged.""" + _anon[_decl_b:]

DENY = ["Shao", "Tengfei", "Matsuno", "Kotomichi", "Goto", "Masayuki", "Waseda", "Rissho",
        "toki.waseda", "0000-0003-3089-5696", "0000-0002-7061-7204", "0000-0003-1929-9359",
        "B1K401870601", "JSPS", "KAKENHI", "Global Education Center",
        "serves on an editorial board"]
_leaks = [d for d in DENY if re.search(re.escape(d), _anon, re.I)]
if _leaks:
    raise SystemExit(f"identity terms survived into the anonymous file: {_leaks}")
io.open(ANON, "w", encoding="utf-8").write(_anon)
print(f"wrote MANUSCRIPT_ANON.md, identity layer clean against {len(DENY)} terms")
print(f"citations numbered: {len(_order)} works cited of {len(_recs)} in the list")
if _uncited:
    print(f"  not cited in the body, so not in the submitted list: {len(_uncited)}")
    for r in _uncited:
        print("    ", r["authors"].split(",")[0], r["year"])

# ---------------------------------------------------------------- supplement
SMAP = [("S1", "APPENDIX_A.md", "Proofs", 11),
        ("S2", "APPENDIX_B.md", "The worst-case exceedance operator", 7),
        ("S3", "APPENDIX_C.md", "Extreme-value and seasonal-variant sensitivities", 3),
        ("S4", "APPENDIX_D.md", "Data provenance and compliance", 5),
        ("S5", "APPENDIX_E.md", "The superseded analysis", 4)]

sup = [f"""# Supplementary material

Supplement to "{TITLE}".

This supplement carries the proofs, the operator verification, the sensitivity analyses, the data
provenance, the superseded analysis and the full statement of the prospective hypothesis, together with
three tables of detail that the main text reports in summary. Its reference list is separate from the
main one and separately numbered, so a work cited in both appears in both."""]

# S4 quotes the deposit's digest and file count. Those were hand-written, and a hand-written
# digest is a digest that goes stale: the archive gained ten files on 2026-08-03 and the
# appendix would have kept naming the old one, so the paper would have pointed a reader at a
# checksum that no longer matched the file they downloaded. Substitute from the builder's own
# output instead, and fail rather than ship an unresolved placeholder.
_dig = os.path.join(D, "DEPOSIT_DIGEST.txt")
if not os.path.exists(_dig):
    raise SystemExit("DEPOSIT_DIGEST.txt absent; run make_deposit.py before building the supplement")
_dtxt = io.open(_dig, encoding="utf-8").read()
_DEPOSIT = {
    "DEPOSIT_SHA256": re.match(r"([0-9a-f]{64})", _dtxt).group(1),
    "DEPOSIT_NFILES": re.search(r"(\d+) files", _dtxt).group(1),
}

for tag, fname, title, nsub in SMAP:
    body = load(fname).split("\n", 1)[1].strip()
    for _k, _v in _DEPOSIT.items():
        body = body.replace("{{%s}}" % _k, _v)
    if "{{" in body:
        raise SystemExit(f"{fname} has an unresolved placeholder: "
                         + re.search(r"\{\{[^}]*\}\}", body).group(0))
    # APPENDIX_E carries both a file title and its own section heading, so dropping only the first
    # line leaves a stray "# Appendix E" inside S5.
    body = re.sub(r"\A#\s*Appendix\s+[A-E][^\n]*\n+", "", body).strip()
    letter = fname.split("_")[1][0]
    missing = [i for i in range(1, nsub) if f"## {letter}.{i}" not in body]
    if missing:
        raise SystemExit(f"{fname} incomplete: {letter}.{missing} absent")
    body = re.sub(rf"^## {letter}\.(\d+)", lambda m: f"## {tag}.{m.group(1)}", body, flags=re.M)
    body = re.sub(rf"\b{letter}\.(\d+)\b", lambda m: f"{tag}.{m.group(1)}", body)
    sup.append(f"# Supplementary Section {tag}. {title}\n\n" + body)

sup.append("# Supplementary Section S6. The prospective hypothesis in full\n\n"
           "Section 5 states a preregistrable hypothesis for subsequent work in brief. Its estimand is\n"
           "the marginal reduction in expected shortfall per unit of additional cushion, conditional on a\n"
           "unit's history,\n\n"
           "    m_i(c̄, Δ) = E[ (X_i − c̄)_+ − (X_i − c̄ − Δ)_+ | H_i ] / Δ,\n\n"
           "evaluated at the cushion the planner intends to hold rather than at zero. The prediction is\n"
           "that cross-unit dispersion in `m_i` predicts when a targeted allocation beats a uniform one at\n"
           "matched inventory, and that dispersion in violation frequency does not. A refutation is a panel\n"
           "in which `m_i` disperses materially while the matched-inventory comparison shows no material\n"
           "advantage for targeting, or the converse. The controls the design requires are homogeneous,\n"
           "stationary heterogeneous and non-persistent heterogeneous panels, with the activation rate and\n"
           "the margin fixed before any cell is run, which is the condition the second positive control of\n"
           "Section 4 did not meet.")

sup.append("# Supplementary Tables\n\n"
           + table("Supplementary Table S1", "controlled_gates") + "\n\n"
           + table("Supplementary Table S2", "inreach") + "\n\n"
           + table("Supplementary Table S3", "support"))

# The supplement carries its own list, numbered from [1] independently of the main text, so a work
# cited in both appears in both. Its citations are still narrative in the appendix sources, so they
# are matched by surname and year and converted in place.
_stxt = "\n\n---\n\n".join(sup)
_snar = sorted(set(re.findall(r"([A-Z][A-Za-zÀ-ɏ'’-]+(?:\s+and\s+[A-Z][A-Za-zÀ-ɏ'’-]+)?)"
                              r"\s+\((\d{4})\)", _stxt)))
_sup_cited, _sup_map = [], {}
for name, yr in _snar:
    first = name.split()[0]
    hits = [r for r in _recs if r["authors"].startswith(first) and r["year"] == yr]
    if len(hits) != 1:
        raise SystemExit(f"supplement citation {name} ({yr}) matched {len(hits)} entries")
    _sup_cited.append(hits[0])
    _sup_map[(name, yr)] = len(_sup_cited)
for (name, yr), n in _sup_map.items():
    _stxt = re.sub(re.escape(name) + r"\s+\(" + yr + r"\)", f"{name} [{n}]", _stxt)
sup = [_stxt, "# Supplementary References\n\n"
       "*Numbered independently of the main reference list, by order of first appearance in this\n"
       "supplement. A work cited in both lists appears in both.*\n\n"
       + "\n\n".join(f"[{i}] {_render(r)}" for i, r in enumerate(_sup_cited, 1))]
print(f"supplement citations numbered: {len(_sup_cited)}")

stxt = "\n\n---\n\n".join(sup) + "\n"
io.open(SUP, "w", encoding="utf-8").write(stxt)

# ---------------------------------------------------------------- report and gates
heads = re.findall(r"^# .+$", txt, flags=re.M)
print(f"wrote {os.path.basename(OUT)}  ({len(re.findall(chr(92) + 'b[' + chr(92) + 'w' + chr(39) + '-]+' + chr(92) + 'b', txt)):,} words gross)")
body_only = txt[txt.find("# 1. Introduction"):txt.find("# Declarations")]
print(f"  counted body prose: {counted(body_only):,}   ceiling 9,000")
print(f"wrote SUPPLEMENT.md  ({len(re.findall(chr(92) + 'b[' + chr(92) + 'w' + chr(39) + '-]+' + chr(92) + 'b', stxt)):,} words, not counted)")
print("\nmain-text sections:")
for h in heads:
    print("   ", h)

for pat in ("PLACEHOLDER",):
    n = txt.count(pat) + stxt.count(pat)
    if n:
        raise SystemExit(f"{n} {pat} left in the build")

leaks = []
for pat in LEAK_PATTERNS:
    for m in re.finditer(pat, txt + "\n" + stxt, flags=re.I):
        leaks.append(pat)
if leaks:
    print("\nSCAFFOLDING LEAK, fix the stripper before using these files:")
    for x in sorted(set(leaks)):
        print("   ", x)
    raise SystemExit(1)
print("\nscaffolding check: clean")
