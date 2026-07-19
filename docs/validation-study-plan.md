# Genius Index — validation study plan

This is written and committed **before** any analysis has been run on real completions,
specifically so the thresholds and exclusion rules below can't drift to fit whatever the
data happens to show. If this document is ever revised after looking at results, that
revision should say so plainly, with a reason, rather than silently rewrite history.

Until every section below is actually complete, the book's own framing stays the
governing one: **a mirror for reflection, read against your own line — never a verdict.**
Nothing here should be read as "the instrument is validated" until each piece is done and
the numbers are reported, good or bad.

---

## What's being validated, and why 130 (or any single number) isn't the answer

A "formal validation study" is really four separate questions, each with its own data
requirement. Lumping them into one target sample size hides that some are close and some
aren't:

| Question | What it needs | Rough minimum |
|---|---|---|
| **Internal consistency** — do items in a domain actually correlate with each other? | First-time completions only | ~100–200 respondents for a stable per-domain alpha |
| **Test–retest reliability** — do scores hold steady for the same person over time? | The *same* people, twice, weeks apart | ~100+ retest **pairs** (so ~200+ sessions from a smaller pool who complete both) |
| **Factor structure** — do the nine domains hold up as distinct factors (EFA/CFA on the 81 items)? | First-time completions, item-level | 400–800+ (rule of thumb: 5–10 respondents per item; 81 items make this the largest requirement by far) |
| **Predictive validity** — do scores predict real-world performance? | First-time completions **plus** an external, independently-measured criterion | Not primarily a sample-size problem — the criterion doesn't exist yet and has to be designed first |

Fabricated or synthetically-generated "completions" cannot substitute for any of these —
they only reproduce whatever assumptions were used to generate them. Every number below
assumes real, honestly-completed submissions from real people.

## Exclusion criteria (decided now, applied uniformly, never adjusted per-analysis)

A completion is excluded from the validation dataset (but never from the taker's own
results — they always see their real chart regardless) if, at the time of analysis:

- **Total time is under 8 minutes** for a full 81-item + 9-station + forced-rank run.
  This threshold is a placeholder until the `minutes` column's real distribution is
  looked at (once there's enough data to see where a "too fast to have engaged" cutoff
  actually falls) — but it must be set by looking at the *distribution shape*, not by
  which cutoff produces the cleanest-looking alpha.
- **Any station was skipped AND the domain's self-report (A) and disposition (C) scores
  are both at the scale ceiling (max or near-max on every item).** This is what the
  existing high-rater / SDR-flag machinery is already designed to catch — flagged rows
  are **not silently dropped**: report the flagged rate, and run key analyses both with
  and without them as a sensitivity check, rather than picking one silently.
- **Missing more than 20% of inventory items** (shouldn't be structurally possible given
  how the flow is gated, but included as a defensive rule in case of a future bug).

Exclusions must be logged (count and reason), not just applied invisibly — a validation
report that doesn't say how many rows it dropped and why isn't trustworthy.

## Thresholds decided in advance

- **Internal consistency (Cronbach's alpha):** α ≥ 0.70 per domain counts as acceptable,
  ≥ 0.80 as good, consistent with standard psychometric convention (not chosen after
  seeing the data). A domain that comes in under 0.70 should be reported as such, not
  reframed or excluded from the write-up.
- **Test–retest correlation:** r ≥ 0.70 per domain over the ~90-day window counts as
  acceptable stability, matching common reliability conventions for a trait-like measure
  over a multi-week gap.
- **Factor structure:** a confirmatory model is only attempted once the sample clears the
  ~400 threshold above. Below that, any exploratory factor analysis run is reported as
  exploratory and preliminary, explicitly not confirmatory, no matter how clean it looks.

## Demographics — what they're for, and their limits

The optional demographics screen (age range, gender, education, region — each
independently skippable, see `data-collection-setup.md`) exists for exactly one purpose:
checking whether the instrument's reliability and structure hold up **across** different
groups, not within any single one. They are not used to build norms, percentiles, or
any comparative scoring — that would be new infrastructure with its own separate design
and consent considerations, not something this data collection silently backs into.

Because every field is optional, expect a nontrivial nonresponse rate. A demographic
breakdown with heavy nonresponse in one field doesn't invalidate the rest of the
dataset — report the response rate per field alongside any subgroup analysis.

## Test–retest recruitment

Test–retest data does not accumulate as a side effect of more first-time completions —
it requires deliberately inviting people back. The retest-reminder calendar feature
(an `.ics` download offered on the results page, ~90 days out) is the mechanism for
this, but it only works if it's actually offered and people actually use it — track:

- How many first-time completions download the reminder.
- Of those, how many actually retake within a reasonable window of the reminder date
  (the site cannot detect calendar-app opens, only actual retakes — a returning retake
  is identified by the taker completing the assessment again, optionally matched to
  their prior baseline via the same participant code if one was set).

If the reminder's uptake turns out too low to reach ~100 pairs organically, that's a
finding in itself — worth revisiting (a direct email/SMS invitation would need real
infrastructure and explicit consent to contact, neither of which exists today, and
would be a deliberate, separate decision, not an default fallback).

## What "validated" does not mean, even once this is complete

- A completed validation study describes **this specific version** of the instrument.
  Any future change to items, scoring weights, or band cutoffs re-opens the question —
  validity doesn't transfer automatically across versions.
- Predictive validity in particular may never be fully answerable without a real,
  ethically-designed external criterion — if that piece never gets built, the honest
  claim is "internally reliable and structurally sound," not "predicts real-world
  performance," and the two should never be blurred together in any public-facing copy.
