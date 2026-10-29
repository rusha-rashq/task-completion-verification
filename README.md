# When Is a Coding Task Actually Complete? — Pilot

Pilot study for our CS 59300 project, *When Is a Coding Task Actually Complete? Beyond Test-Based Verification in LLM Coding Agents* (Fortwendel, Chi, Dhar).

**Question:** Does asking a coding agent to verify each requirement with evidence before declaring completion change whether its completion claims are accurate, especially for requirements that tests don't check?

This pilot runs **one task under two prompting conditions** to test the full pipeline end to end before scaling up.

## What was done

1. **Built a task filter** (`filter_tasks.py`). It scans all 500 SWE-bench Verified tasks and keeps those whose gold patch touches non-code artifacts (docs, changelogs, config, error messages). Only **10 of 500** matched (`candidates.csv`).
2. **Selected a task.** First choice `pylint-dev__pylint-4661` was dropped because its 2021 dependencies don't run on Python 3.11. Used `pallets__flask-5014` ("Require a non-empty name for Blueprints") instead.
3. **Set up two identical copies of the repo** at commit `7ee9ceb7`, each with its own Python 3.11 virtual environment. Required pins: `werkzeug<3`, `pytest<8`. Confirmed 59/59 existing tests pass in both.
4. **Wrote a ground-truth requirement checklist** (6 requirements) from the issue, gold patch, and repo conventions, before running the agent. 3 of 6 are not checked by the SWE-bench tests.
5. **Ran Claude Code** (v2.1.312, Claude Sonnet 5.5) once per condition in a fresh session:
   - **Baseline:** issue text plus "state whether the task is complete"
   - **Verification:** same, plus instructions to list requirements, cite evidence for each, and keep working on unsupported ones
6. **Scored both runs** against the checklist, and checked the verification run's evidence against its actual diff.

## Results

| | Baseline | Verification |
|---|---|---|
| Requirements fully met | 4 / 6 | 5 / 6 |
| Missed | regression test, changelog | none |
| Partial | none | changelog (wrong issue number) |
| Claimed done | Yes | Yes |
| Actually done | No | Partial |
| Tests pass | 59/59 | 60/60 |

## Observations

1. **Baseline knowingly skipped work.** It said it hadn't added a test or changelog entry, then declared the task complete anyway.
2. **Verification closed most of the gap**, adding the regression test and a changelog entry.
3. **Verification fabricated a reference.** It wrote `:issue:5023` and flagged it as a guess, though the issue text says `#4944`, and still declared completion.
4. **Possible data contamination.** The verification run's new test is identical to the gold test patch, suggesting the model may have seen this fix in training.
5. **Small task pool.** Few SWE-bench Verified gold patches include non-code changes, so checklists must also draw on issue text and repo conventions.
6. **Setup cost.** Older repos need dependency pins or older Python versions.

## Files

| File | Contents |
|---|---|
| `filter_tasks.py` | Filters SWE-bench Verified for tasks touching non-code artifacts |
| `candidates.csv` | The 10 matching tasks, with issue text, gold patch, and test patch |
| `prompt_baseline.txt` | Baseline prompt, filled in for flask-5014 |
| `prompt_verify.txt` | Verification prompt, filled in for flask-5014 |
| `prompts_and_scoring.md` | Prompt templates, checklist, scoring sheet, and observations |
| `baseline.diff` / `verify.diff` | Code changes made by the agent in each condition |
| `baseline_final.txt` / `verify_final.txt` | Agent's final completion message in each condition |

## Reproducing

```
pip install datasets
python filter_tasks.py

git clone https://github.com/pallets/flask baseline
cd baseline && git checkout 7ee9ceb71e868944a46e1ff00b506772a53a4f1d
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e . "werkzeug<3" "pytest<8"
python -m pytest tests/test_blueprints.py -q   # expect 59 passed
```

Repeat in a second folder (`verify`) with its own fresh virtual environment, then run `claude` in each folder with the matching prompt.

## Next steps

- Scale to 30–50 tasks, possibly including newer benchmarks (e.g. Senior SWE-Bench) to reduce contamination
- Two annotators per checklist, with agreement reported
- Multiple runs per condition; paired statistical tests
- Record turns and token cost per run
