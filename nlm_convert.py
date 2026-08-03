# -*- coding: utf-8 -*-
"""Convert the reference list to the Taylor and Francis NLM style, and number the citations.

The journal's linked style guide, version 2.2 of 30 May 2023, was read in full. What it requires:

  in text   bracketed numbers [1], assigned by order of first mention, reused on later mentions,
            runs joined with an unspaced en dash, so [2,3,4,5,7,10] is written [2-5,7,10]
            narrative citation is explicitly allowed: "Give a number even if the author is named
            in the text", as `Jones [10]`, `Jones and Smith [12]`, `Jones et al. [3]`
  list      numerical order of first appearance, not alphabetical
  authors   surname then initials, no punctuation between initials; more than three authors are
            given as the first three then et al.
  journals  ISO 4 abbreviations, no full point except at the end of the title, and single-word
            titles are not abbreviated
  form      Author AA. Title of article. Abbreviated Journal Title. Year;Volume(Issue):Pages.

Journal abbreviations are taken from the ISSN List of Title Word Abbreviations rather than written
from memory. The LTWA entries that matter for English titles are tagged eng or mul; filtering on eng
alone silently loses Operations, Management, Statistics, Information, Industrial and Analysis, which
is most of an operations research bibliography.

This runs after the body structure is frozen, because the numbers are positional.
"""
import io
import json
import os
import re
import sys

D = os.path.dirname(os.path.abspath(__file__))
LTWA = os.environ.get("LTWA_CSV", os.path.join(D, "data", "ltwa.csv"))
STOP = {"a", "an", "and", "the", "of", "in", "on", "for", "to", "with", "at", "by", "from"}
OMIT = object()


def load_ltwa(path):
    import csv
    rows = [r for r in csv.reader(io.open(path, encoding="utf-8-sig"), delimiter="\t")
            if len(r) >= 3][1:]
    entries = [(r[0].strip(), r[1].strip()) for r in rows if "eng" in r[2] or "mul" in r[2]]
    exact = {w.lower(): ab for w, ab in entries if not w.endswith("-")}
    prefix = sorted([(w[:-1].lower(), ab) for w, ab in entries
                     if w.endswith("-") and not w.startswith("-")], key=lambda x: -len(x[0]))
    return exact, prefix


def abbreviate_word(word, exact, prefix):
    lw = word.lower()
    if lw in STOP:
        return OMIT
    v = exact.get(lw)
    if v is None:
        for k, vv in prefix:
            if lw.startswith(k):
                v = vv
                break
    if v is None or v == "n.a.":
        return word                       # not listed, or listed as not abbreviated
    v = v[0].upper() + v[1:]
    # ISO 4 puts a full point only on a word that was actually shortened. A prefix entry such as
    # control- returns "control." and would otherwise put a point on an unshortened word.
    if v.rstrip(".").lower() == lw:
        return word
    # The guide is explicit: "Journal title abbreviations should not include full points, except
    # at the end of the title." The LTWA source strings carry a period on every abbreviated word
    # (that is how ISO 4 itself is written), so those internal periods are stripped here. The one
    # period the printed title needs is added once, by the caller, after every word is joined.
    return v.rstrip(".")


def abbreviate_title(title, exact, prefix):
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", title)
    if len(words) == 1:
        return title                      # single-word titles are not abbreviated
    out = []
    for tk in re.findall(r"[A-Za-z][A-Za-z'-]*|\d+[a-z]*", title):
        if re.match(r"^\d", tk):
            out.append(tk)
            continue
        a = abbreviate_word(tk, exact, prefix)
        if a is OMIT:
            continue
        out.append(a)
    return " ".join(out)


def nlm_authors(author_block):
    """'Barber, R. F., Candes, E. J., and Tibshirani, R. J.' -> 'Barber RF, Candes EJ, Tibshirani RJ'.

    Parsed by matching surname-then-initials pairs rather than by splitting on commas: the separator
    and the internal punctuation are the same character, so a comma split silently drops every author
    whose surname is followed by more than one initial. That failure is quiet, it produces a shorter
    but still well-formed list, and it changes who is credited.
    """
    # The trailing full point is kept: stripping it first makes the last initial of the last
    # author unmatchable, which drops a letter from the credit without any other symptom.
    block = re.sub(r"\s+", " ", author_block.strip())
    # A surname may be several words: a lowercase particle as in "van der Laan", or two
    # capitalised words as in "Mohajerin Esfahani". Matching only the last word silently renames
    # the author, and it did so on the most-cited reference in this list.
    pat = re.compile(r"((?:[A-Z][A-Za-zÀ-ɏ'’-]+\s+)?(?:[a-z]{2,4}\s+){0,2}"
                     r"[A-Z][A-Za-zÀ-ɏ'’-]+)"
                     r",\s*((?:[A-Z]\.?[-\s]*)+?)(?=,|\s+and|$)")
    # The particle slot also matches the list conjunction, so 'and Kuhn' arrives as a surname.
    people = [(re.sub(r'^(?:and|&)\s+', '', m.group(1).strip()), m.group(2))
              for m in pat.finditer(block)]
    if not people:
        return block
    out = [f"{sur} {''.join(re.findall(r'[A-Z]', ini))}" for sur, ini in people]
    if len(out) > 3:
        out = out[:3] + ["et al."]
    return ", ".join(out)


def sentence_case(title):
    """Only the first word, proper nouns and acronyms keep their capitals.

    Words already fully capitalised, hyphenated proper forms and anything with an internal capital
    are left alone, because those are the acronyms and names the rule protects. A hyphenated
    compound such as "Wasserstein-metric" is handled segment by segment: testing the whole token
    against PROPER missed it, because "Wasserstein-metric" as one string is not "Wasserstein", and
    the entry was silently lowercased into "wasserstein-metric" as a result.
    """
    words = title.split()
    out = []
    for i, w in enumerate(words):
        core = w.strip("(),.:;")
        if i == 0 or core.isupper() or (len(core) > 1 and any(c.isupper() for c in core[1:])):
            out.append(w)
        elif core in PROPER:
            out.append(w)
        elif "-" in core:
            segs = core.split("-")
            fixed = [s if s in PROPER else (s[0].lower() + s[1:] if s[:1].isupper() else s)
                     for s in segs]
            out.append(w.replace(core, "-".join(fixed), 1))
        else:
            out.append(w[0].lower() + w[1:] if w[:1].isupper() else w)
    return " ".join(out)


PROPER = {"Wasserstein", "Kullback-Leibler", "Bayesian", "Monte", "Carlo", "Gaussian",
          "Stein", "Wilks", "United", "States", "STARD", "European", "American", "Japanese",
          "Mexican"}


def parse_entry(raw):
    """Split one author-year entry into its parts. Returns None if it does not parse."""
    e = re.sub(r"\s+", " ", raw.strip())
    m = re.match(r"^(.*?)\s\((\d{4})\)\.\s(.*)$", e)
    if not m:
        return None
    authors, year, rest = m.groups()
    doi = None
    dm = re.search(r"https?://doi\.org/(\S+)", rest)
    if dm:
        doi = dm.group(1).rstrip(".")
        rest = rest[:dm.start()].strip()
    vm = re.search(r"\*([^*]+)\*,?\s*(.*)$", rest)
    if vm:
        title = rest[:vm.start()].strip().rstrip(".").strip()
        # "Title. In *Proceedings*, volume 30." leaves a dangling "In" glued to the article
        # title, which sentence case then lowercases into the middle of the entry.
        conf = bool(re.search(r"\bIn$", title))
        title = re.sub(r"\s*\bIn$", "", title).rstrip(".").strip()
        venue = vm.group(1).strip()
        tail = vm.group(2).strip().rstrip(".")
    else:
        # No italicised venue: an unpublished manuscript, working paper or preprint. Its
        # provenance clause ("Unpublished manuscript, Department of Statistics, Columbia
        # University, 14 November 2013") is not a title and must not be sentence-cased with it,
        # because that lowercases the institution's name along with the ordinary prose, and
        # because the clause usually ends in its own date, which would otherwise be printed a
        # second time when the year field is appended after it.
        nm = re.search(r"\.\s+((?:Unpublished manuscript|Working paper|Manuscript submitted"
                       r"|Preprint)\b.*)$", rest, flags=re.I)
        if nm:
            title = rest[:nm.start()].strip().rstrip(".").strip()
            note = nm.group(1).strip().rstrip(".")
        else:
            title, note = rest.rstrip("."), None
        venue, tail, conf = "", "", False
    return dict(authors=authors, year=year, title=title, venue=venue, tail=tail, doi=doi,
                conf=locals().get("conf", False), note=locals().get("note"))


def format_tail(tail):
    """'10(2), 455 to 482' -> '10(2):455-482'; 'volume 30' -> ''."""
    t = re.sub(r"^volume\s+", "", tail.strip(), flags=re.I).replace(" to ", "-")
    t = re.sub(r"^In\s+", "", t).strip().strip(",")
    m = re.match(r"^(\d+)\s*(\([^)]*\))?[,]?\s*(.*)$", t)
    if not m:
        return t
    vol, iss, pages = m.group(1), m.group(2) or "", m.group(3).strip().strip(",")
    pages = re.sub(r"\s+", "", pages)
    return f"{vol}{iss}" + (f":{pages}" if pages else "")


def main():
    if not os.path.exists(LTWA):
        sys.exit(f"LTWA table not found at {LTWA}; set LTWA_CSV or place the ISSN csv there")
    exact, prefix = load_ltwa(LTWA)
    src = io.open(os.path.join(D, "REFERENCES.md"), encoding="utf-8").read()
    a, b = src.find("## Reference list"), src.find("## Verification record")
    raws = [x.strip() for x in re.split(r"\n\s*\n", src[a:b].split("\n", 1)[1].strip()) if x.strip()]

    recs, bad = [], []
    for raw in raws:
        p = parse_entry(raw)
        if not p:
            bad.append(raw[:70])
            continue
        p["nlm_authors"] = nlm_authors(p["authors"])
        p["nlm_venue"] = abbreviate_title(p["venue"], exact, prefix) if p["venue"] else ""
        p["nlm_title"] = sentence_case(p["title"])
        p["nlm_tail"] = format_tail(p["tail"])
        p["key"] = p["authors"].split(",")[0].strip() + " " + p["year"]
        recs.append(p)

    print(f"parsed {len(recs)} of {len(raws)} entries")
    if bad:
        print("UNPARSED, fix by hand before relying on this:")
        for x in bad:
            print("   ", x)

    lines = []
    for i, p in enumerate(recs, 1):
        au = p['nlm_authors']
        s = f"{au}{'' if au.endswith('.') else '.'} {p['nlm_title']}."
        if p["nlm_venue"]:
            vv = p["nlm_venue"]
            s += f" {vv}{'' if vv.endswith('.') else '.'} {p['year']}"
            s += f";{p['nlm_tail']}." if p["nlm_tail"] else "."
        elif p.get("note"):
            s += f" {p['note']}."
        else:
            s += f" {p['year']}."
        if p["doi"]:
            s += f" doi: {p['doi']}"
        lines.append(f"[{i}] {s}")

    out = os.path.join(D, "REFERENCES_NLM.md")
    io.open(out, "w", encoding="utf-8").write(
        "# Reference list in NLM form, alphabetical order retained for checking\n\n"
        "*Not the submission order. The submission list is renumbered by first appearance once the\n"
        "citation placeholders in the body are resolved; this file exists so that each converted entry\n"
        "can be compared against its author-year original line by line.*\n\n"
        + "\n\n".join(lines) + "\n")
    print(f"wrote REFERENCES_NLM.md")
    print("\nfirst five converted entries:")
    for x in lines[:5]:
        print("   ", x)
    return recs


if __name__ == "__main__":
    main()
