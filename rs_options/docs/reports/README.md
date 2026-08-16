# Research reports

Each research CLI (`mve.backtest`, `mve.walkforward`, `mve.exit_study`,
`mve.hypotheses`, `mve.intraday_study`) saves its printed summary here as
`<name>.txt`, overwriting the previous run — git history keeps old ones.

Purpose: the operator commits and pushes this folder after a run so the
cloud Claude session can read results straight from the repo instead of
pasted terminal output.

```bash
git add docs/reports && git commit -m "research reports" && git push
```

Aggregate statistics only — never keys, account values, or raw vendor
data (the `data/` store stays local and uncommitted).
