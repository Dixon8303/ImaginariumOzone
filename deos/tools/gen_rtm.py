#!/usr/bin/env python3
"""Generate docs/architecture/REQUIREMENT_TRACEABILITY_MATRIX.md from the requirement headings.

    python3 deos/tools/gen_rtm.py          # rewrite the matrix
    python3 deos/tools/gen_rtm.py --check  # exit 1 if the committed matrix is stale

A requirement is a `### REQ-PREFIX-nnn: Title` heading (DEOS.md section 3.2). Each row names the
source document, the implementing component, and the verification test `TEST_<PREFIX>_<nnn>`;
the EESS-lineage requirements keep their historical test names.
"""
from __future__ import annotations
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = os.path.join(ROOT, "docs")
OUT = os.path.join(DOCS, "architecture", "REQUIREMENT_TRACEABILITY_MATRIX.md")

MODULES = [  # (directory, document id, name, implemented-in)
    ("01_Core", "DEOS-CORE", "DEOS-Core", "Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*`"),
    ("02_ECS", "DEOS-ECS", "DEOS-ECS", "ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer"),
    ("03_Runtime", "DEOS-RT", "DEOS-Runtime", "Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings"),
    ("04_Protocol", "DEOS-PROTO", "DEOS-Protocol", "Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission"),
    ("05_Play", "DEOS-PLAY", "DEOS-Play", "Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand`"),
    ("06_Prototype", "DEOS-MVS", "DEOS-MVS", "MVS build: `deos-run`, parity harness, First Playable Host"),
]
LEGACY_TESTS = {
    "REQ-LAW-001": "TEST_EnergyConservation", "REQ-LAW-002": "TEST_EntropyIncrease",
    "REQ-MATH-001": "TEST_Q32_Arithmetic", "REQ-MATH-002": "TEST_FluxEvaluation",
    "REQ-ARCH-001": "TEST_HeadlessBuild", "REQ-ARCH-002": "TEST_BufferSwap",
    "REQ-ENT-001": "TEST_EntityIDUnpack", "REQ-LOOP-001": "TEST_PipelineSequence",
    "REQ-DAT-001": "TEST_CacheAlignment", "REQ-DAT-002": "TEST_ZeroAllocations",
}
HEAD = re.compile(r"^#{2,4}\s+(REQ-([A-Z]+)-(\d{3})):\s*(.+?)\s*$")


def collect():
    rows = []
    for d, doc_id, name, impl in MODULES:
        path = os.path.join(DOCS, d)
        if not os.path.isdir(path):
            continue
        for f in sorted(os.listdir(path)):
            if not f.endswith(".md") or f.startswith("LEGACY_"):
                continue
            with open(os.path.join(path, f), encoding="utf-8") as fh:
                for line in fh:
                    m = HEAD.match(line)
                    if m:
                        rid, prefix, num, title = m.groups()
                        rows.append((doc_id, name, impl, rid, prefix, int(num), title))
    return rows


def render(rows):
    out = ["# Requirement Traceability Matrix (RTM)", "",
           "Generated from every `### REQ-PREFIX-nnn:` heading under `docs/` by `python3 deos/tools/gen_rtm.py`; do not edit by hand. "
           "`python3 deos/tools/gen_rtm.py --check` fails when this file is stale, and `tools/spec_lint.py` fails when a defined requirement is missing here. "
           "The verification test of a requirement is `TEST_<PREFIX>_<nnn>` (tests/SPEC_CONSISTENCY_TEST_PLAN.md section 3), except the EESS-lineage requirements, which keep their historical names.", ""]
    total = 0
    for d, doc_id, name, impl in MODULES:
        mod_rows = [r for r in rows if r[0] == doc_id]
        if not mod_rows:
            continue
        mod_rows.sort(key=lambda r: (r[4], r[5]))
        out += [f"## {name} ({doc_id}) — {len(mod_rows)} requirements", "",
                "| Requirement ID | Description | Source Document | Implemented In | Verification Test |",
                "| :--- | :--- | :--- | :--- | :--- |"]
        for doc_id_, name_, impl_, rid, prefix, num, title in mod_rows:
            test = LEGACY_TESTS.get(rid, f"TEST_{prefix}_{num:03d}")
            out.append(f"| **{rid}** | {title} | `{doc_id_}` | {impl_} | `{test}` |")
        out.append("")
        total += len(mod_rows)
    out += [f"**Total: {total} requirements across {len({r[0] for r in rows})} modules.**", ""]
    return "\n".join(out)


def main(argv):
    rows = collect()
    ids = [r[3] for r in rows]
    dups = {i for i in ids if ids.count(i) > 1}
    if dups:
        print("ERROR duplicate requirement definitions:", ", ".join(sorted(dups)))
        return 1
    text = render(rows)
    if "--check" in argv:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if current != text:
            print("ERROR traceability matrix is stale; run python3 deos/tools/gen_rtm.py")
            return 1
        print(f"RTM up to date: {len(rows)} requirements")
        return 0
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(rows)} requirements")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
