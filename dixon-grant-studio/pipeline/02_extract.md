# 02 — RFP Extraction: The Requirements Matrix

Purpose: before a single word of narrative is drafted, the RFP/NOFO gets
taken apart into a **requirements matrix** — a single table that becomes
the spine of the entire application. Every later pipeline step
(`03_draft.md`, `04_selfcheck.md`, `05_package.md`) works off this matrix,
not off the RFP itself. If it isn't in the matrix, it doesn't get written,
and if it's in the matrix, it must show up in the final package.

## Matrix columns

| Column | What goes here |
|---|---|
| **ID** | Short code, e.g. `N1`, `B2`, `A3` (Narrative / Budget / Attachment) |
| **Requirement** | Exact language or close paraphrase of what's being asked |
| **Source** | Page/section number in the RFP |
| **Point value** | Points this item is worth on the funder's rubric, if scored |
| **Limit** | Page limit, word limit, character limit, or "none stated" |
| **Eligibility / Compliance flag** | Yes/No — is this a pass/fail eligibility item rather than a scored one? |
| **Mapped section** | Which deliverable section answers this (see `03_draft.md`) |
| **Status** | Not started / Drafted / Self-checked / Final |

## Extraction procedure

1. **Read the whole RFP once, cover to cover, before extracting anything.**
   Funders bury requirements in appendices, footnotes, and budget
   instructions as often as in the narrative section. A matrix built from
   a skim will miss points.
2. **Pull every scored narrative question or section** into its own row,
   with the exact point value and any sub-criteria the rubric lists
   separately (e.g., if "Program Design" is worth 20 points split across
   3 bullet criteria, that's 3 rows, not 1).
3. **Pull every eligibility requirement** (organization type, geographic
   service area, population served, minimum years of operation, prior
   grant history restrictions) as compliance-flag rows. These are
   pass/fail gates — get them wrong and the score never matters.
4. **Pull every required attachment** (990, budget, letters of support,
   org chart, MOUs, insurance certificates, board list) as its own row,
   even if unscored — missing attachments are the most common reason a
   compliant, well-written application is rejected without review.
5. **Pull every formatting constraint**: font, margin, page limit, file
   naming convention, file format, page order. Funders enforce these
   literally; a reviewer who never reads past the page limit still
   disqualifies the application.
6. **Pull the deadline** — date, time, time zone, and submission method —
   as the final row. Confirm whether "received by" or "postmarked by"
   governs.
7. **Cross-check the matrix against the RFP a second time**, row by row,
   confirming nothing scored was missed. This second pass is not
   optional — first passes miss on average one scored item per RFP.

## Handling an RFP that hasn't been released yet

When a client wants to start drafting before the current cycle's RFP is
published (common with annually recurring funders), build the matrix
from the **most recently released prior-year RFP**, flag every row with
`[PRIOR-YEAR — CONFIRM]`, and re-run the extraction against the live
document the moment it's released — before `04_selfcheck.md`, never
after. Never deliver a final package scored against a prior-year matrix
without confirming no material change against the current release.

## Output

The completed matrix is the deliverable of this step. It should be
reviewable in one sitting and should let anyone on the team answer "does
this application cover requirement X" in seconds, without re-reading the
RFP.
