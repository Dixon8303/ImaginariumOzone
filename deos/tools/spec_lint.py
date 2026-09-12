#!/usr/bin/env python3
"""DEOS specification linter.

Enforces the identifier rules of DEOS.md §3 and the no-placeholder rule of
CONTRIBUTING.md across the deos/ tree. Run from anywhere:

    python3 deos/tools/spec_lint.py            # lint the whole tree
    python3 deos/tools/spec_lint.py --warn     # also print warnings

Exit status 1 on any error. Warnings never fail the run.
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = os.path.join(ROOT, "docs")

# Requirement prefixes reserved per module (DEOS.md §3.2). Paths are relative
# to deos/docs.
PREFIX_OWNER = {
    "LAW": "01_Core", "MATH": "01_Core", "PRNG": "01_Core", "TICK": "01_Core", "ORD": "01_Core",
    "ENT": "02_ECS", "CMP": "02_ECS", "DAT": "02_ECS", "MUT": "02_ECS",
    "ARCH": "03_Runtime", "LOOP": "03_Runtime", "THR": "03_Runtime", "HASH": "03_Runtime", "SNAP": "03_Runtime",
    "COG": "04_Protocol", "SOC": "04_Protocol", "XL": "04_Protocol", "EVT": "04_Protocol",
    "PLAY": "05_Play", "CAT": "05_Play", "SES": "05_Play",
    "MVS": "06_Prototype",
}

DOC_IDS = {
    "DEOS", "DEOS-F01", "DEOS-F02", "DEOS-F03", "DEOS-F04", "DEOS-F05", "DEOS-F06",
    "DEOS-CORE", "DEOS-ECS", "DEOS-RT", "DEOS-PROTO", "DEOS-PLAY", "DEOS-MVS", "DEOS-1.0",
}

REQ_RE = re.compile(r"\bREQ-([A-Z]+)-(\d{3})\b")
REQ_DEF_RE = re.compile(r"^#{2,4}\s+(REQ-[A-Z]+-\d{3})\b")
EESS_RE = re.compile(r"\bEESS-\d{4}\b")
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|FIXME|XXX)\b|\bplaceholder\b|\[insert\b", re.IGNORECASE)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(#[^)]*)?\)")
DOC_ID_ROW_RE = re.compile(r"^\|\s*\*\*Document ID\*\*\s*\|\s*([^|]+?)\s*\|")
CONST_ROW_RE = re.compile(r"^\|\s*`([A-Z_]+)`\s*\|\s*([^|]+?)\s*\|")

# High-signal banned synonyms (DEOS-F04 and DEOS.md §4). Warnings only.
BANNED_SYNONYMS = {
    r"\bGameObject\b": "Entity",
    r"\bworld checksum\b": "Tick Hash",
    r"\bsave game\b": "Input Log",
    r"\bfast-forward\b": "Acceleration",
    r"\baction points\b": "Catalyst Budget",
    r"\bnews feed\b": "Chronicle",
    r"\bgod power\b": "Catalyst Action",
}


def md_files():
    for base, _dirs, files in os.walk(ROOT):
        if "/.git" in base:
            continue
        for f in sorted(files):
            if f.endswith(".md"):
                yield os.path.join(base, f)


def rel(path):
    return os.path.relpath(path, ROOT)


def main(argv):
    show_warn = "--warn" in argv
    errors, warnings = [], []
    definitions = {}            # REQ id -> file
    references = defaultdict(set)
    defined_in_module = defaultdict(set)
    rtm_text = ""
    constants = {}

    files = list(md_files())
    texts = {p: open(p, encoding="utf-8").read() for p in files}

    # Registry constants from DEOS.md §5.1
    deos_md = os.path.join(ROOT, "DEOS.md")
    if deos_md in texts:
        in_consts = False
        for line in texts[deos_md].splitlines():
            if line.startswith("### 5.1"):
                in_consts = True
            elif line.startswith("### 5.2"):
                in_consts = False
            if in_consts:
                m = CONST_ROW_RE.match(line)
                if m and m.group(1) not in ("Constant",):
                    constants[m.group(1)] = m.group(2).strip()

    for path in files:
        text = texts[path]
        r = rel(path)
        is_legacy = os.path.basename(path).startswith("LEGACY_")
        is_template = "/templates/" in path
        lines = text.splitlines()

        # Document ID validity (specs only)
        for line in lines:
            m = DOC_ID_ROW_RE.match(line)
            if m:
                did = m.group(1).strip().strip("`")
                if is_template or is_legacy:
                    continue
                if did not in DOC_IDS:
                    errors.append(f"{r}: unknown Document ID '{did}' (allowed: DEOS.md §3.1)")

        for ln, line in enumerate(lines, 1):
            # Requirement definitions
            m = REQ_DEF_RE.match(line)
            if m and not is_legacy and not is_template:
                rid = m.group(1)
                if rid in definitions:
                    errors.append(f"{r}:{ln}: duplicate definition of {rid} (first in {definitions[rid]})")
                definitions[rid] = f"{r}:{ln}"
                prefix = rid.split("-")[1]
                owner = PREFIX_OWNER.get(prefix)
                module_dir = os.path.relpath(os.path.dirname(path), DOCS).split(os.sep)[0]
                if owner is None:
                    errors.append(f"{r}:{ln}: {rid} uses unreserved prefix '{prefix}' (DEOS.md §3.2)")
                elif module_dir != owner:
                    errors.append(f"{r}:{ln}: {rid} defined outside its owning module ({prefix} belongs to docs/{owner})")
                defined_in_module[module_dir].add(rid)
            # Requirement references (templates carry example IDs; skip them)
            if not is_template:
                for rm in REQ_RE.finditer(line):
                    references[f"REQ-{rm.group(1)}-{rm.group(2)}"].add(r)

            # Retired EESS ids
            if EESS_RE.search(line) and not is_legacy:
                allowed = (
                    os.path.basename(path) in ("DEOS.md", "CHANGELOG.md")
                    or "Supersedes" in line or "supersedes" in line or "absorbs" in line
                    or "EESS →" in line or "lineage" in line.lower()
                )
                if not allowed:
                    errors.append(f"{r}:{ln}: retired EESS identifier outside a lineage/Supersedes context")

            # Placeholders
            if not is_template and not is_legacy and PLACEHOLDER_RE.search(line):
                if "spec_lint" in line or "PLACEHOLDER_RE" in line:
                    continue
                errors.append(f"{r}:{ln}: placeholder text: {line.strip()[:80]}")

            # Relative links must resolve
            for lm in LINK_RE.finditer(line):
                target = lm.group(1)
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                tp = os.path.normpath(os.path.join(os.path.dirname(path), target))
                if not os.path.exists(tp):
                    errors.append(f"{r}:{ln}: broken link '{target}'")

            # Banned synonyms (warn)
            if not is_legacy and "Banned" not in line and not line.startswith("|"):
                for pat, canon in BANNED_SYNONYMS.items():
                    if re.search(pat, line, re.IGNORECASE):
                        warnings.append(f"{r}:{ln}: banned synonym {pat!r}; use '{canon}'")

            # Constant value drift (warn): `NAME` = value on a line outside DEOS.md
            if path != deos_md and not is_legacy:
                for cm in re.finditer(r"`([A-Z_]{4,})`\s*(?:=|is|of)\s*([0-9][0-9,]*)", line):
                    name, val = cm.group(1), cm.group(2)
                    if name in constants:
                        reg = re.search(r"[0-9][0-9,]*", constants[name])
                        if reg and reg.group(0) != val and reg.group(0).replace(",", "") != val.replace(",", ""):
                            warnings.append(f"{r}:{ln}: `{name}` = {val} disagrees with registry value '{constants[name]}'")

        if os.path.basename(path) == "REQUIREMENT_TRACEABILITY_MATRIX.md":
            rtm_text = text

    # Every reference resolves to a definition (legacy files excluded from both)
    for rid, where in sorted(references.items()):
        if rid not in definitions:
            src = sorted(w for w in where if not os.path.basename(w).startswith("LEGACY_"))
            if src:
                errors.append(f"{rid} referenced in {', '.join(src)} but never defined as a '### {rid}: ...' heading")

    # Every definition appears in the RTM
    if rtm_text:
        for rid in sorted(definitions):
            if rid not in rtm_text:
                errors.append(f"{rid} ({definitions[rid]}) missing from docs/architecture/REQUIREMENT_TRACEABILITY_MATRIX.md")
    else:
        errors.append("docs/architecture/REQUIREMENT_TRACEABILITY_MATRIX.md not found")

    for e in errors:
        print(f"ERROR   {e}")
    if show_warn:
        for w in warnings:
            print(f"WARNING {w}")
    print(f"\n{len(definitions)} requirements defined across {len(defined_in_module)} modules; "
          f"{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
