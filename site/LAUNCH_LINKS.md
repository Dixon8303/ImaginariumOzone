# 10-Day Launch — the exact links to post

Copy the link for the day and platform you're posting on. Nothing else to set up.

Every link below is already tagged, so GA4 can tell you which post produced which
click. **An untagged link still works for the reader — it just shows up in GA4 as
"direct" and you lose the ability to tell Day 3 from Day 6.**

Campaign name on every link: `what_history_buried_paperback_launch`

---

## Read this first — it affects Days 1, 3 and 6

The `amazon_click` metric fires **on our site**, at the moment someone taps an
Amazon button here. A post that links *straight to Amazon* never touches the
site, so **no `amazon_click` is recorded and GA4 sees nothing.**

The calendar currently sends Facebook and LinkedIn straight to Amazon on Day 1,
and offers "bio / Amazon" on Day 6. Those variants would be invisible in GA4.

**Decided: every Amazon post routes through the site.** Post → `#acquire` →
Amazon. It costs the buyer one extra tap and it is the only version that can be
measured. Use the links below as written; there is nothing to choose per post.

| | Buyer's path | What you can measure |
|---|---|---|
| **What we're doing** — route through the site | one extra tap: post → `#acquire` → Amazon | `amazon_click` with source, format and placement — plus anyone who buys the PDF or Companion instead of the paperback |
| ~~Link straight to Amazon~~ | shortest path | nothing at all in GA4, unless an **Amazon Attribution** tag is created in the Amazon Ads console |

Worth knowing rather than acting on: the extra tap also puts the format chooser
in front of every Amazon-bound buyer, so Days 1, 3 and 6 can produce PDF and
Companion sales that a direct Amazon link would never have given you.

---

## Day 1 · Announcement — "It's here."

Instagram (bio hub):
```
https://dixon8303.github.io/ImaginariumOzone/book/links.html?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d01_announce
```
Facebook:
```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=facebook&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d01_announce#acquire
```
LinkedIn:
```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=linkedin&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d01_announce#acquire
```
Email 1:
```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=email&utm_medium=email&utm_campaign=what_history_buried_paperback_launch&utm_content=d01_announce#acquire
```

## Day 2 · The work — "It begins with questions."

```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d02_thework
```
Facebook — swap `instagram` for `facebook`.

## Day 3 · The milestone — "My second published book."

```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d03_milestone#acquire
```
Email 2 — swap `instagram&utm_medium=social` for `email&utm_medium=email`.

## Day 4 · The question — no link

Comments only. Nothing to tag.

## Day 5 · Spotlight — "Mansa Musa was not worth $400 billion."

```
https://dixon8303.github.io/ImaginariumOzone/book/erasure.html?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d05_casefile01
```
Email 3 — swap `instagram&utm_medium=social` for `email&utm_medium=email`.

**Send Day 5 to the briefing, not to `#free-chapter`** — decided, use the link
above. That headline is question one of the briefing word for word: the reader
commits to the $400 billion figure, then watches it struck through against
al-ʿUmari's 1337 account. The page ends in the same free-chapter signup, so the
`lead` is unchanged, and the shareable score card is added on the one spotlight
day of the campaign.

## Day 6 · The physical book — "From the archive to your hands."

```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d06_physical#acquire
```
Email 4 — swap `instagram&utm_medium=social` for `email&utm_medium=email`.

## Day 7 · The companion — "Read the book. Test what you know."

```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d07_companion#acquire
```
Facebook — swap `instagram` for `facebook`.

In GA4 the Companion shows up as `buy_click` with `format = study_companion`;
the PDF is `format = pdf_direct`. That is how you tell Day 7 worked.

## Day 8 · The series — "This is Volume One."

```
https://dixon8303.github.io/ImaginariumOzone/book/unlearn.html?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d08_series
```
Or straight to the signup:
```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d08_series#free-chapter
```
Email 5 — swap `instagram&utm_medium=social` for `email&utm_medium=email`.

## Day 9 · Readers

```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d09_readers
```

## Day 10 · Second push — "Have you read it yet?"

Re-use whichever of Days 1–3 produced the most `amazon_click`, with a new tag:
```
https://dixon8303.github.io/ImaginariumOzone/book/?utm_source=instagram&utm_medium=social&utm_campaign=what_history_buried_paperback_launch&utm_content=d10_secondpush#acquire
```

---

## Where to look in GA4

Reports → Engagement → Events, filtered to
`utm_campaign = what_history_buried_paperback_launch`.

| Day | Look for |
|---|---|
| 1, 3, 6 | `amazon_click`, broken down by `campaign_source` |
| 2, 7 | `acquire_view` — how many people reached the format chooser |
| 5, 8 | `lead` — Recovery List signups |
| 7 | `buy_click` where `format = study_companion` |

One-time setup, or these columns read as `(not set)`: register `format`,
`placement` and `retailer` as **event-scoped custom dimensions** (Admin → Custom
definitions), and mark `amazon_click`, `buy_click` and `lead` as **key events**.
