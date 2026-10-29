"""
Find SWE-bench Verified tasks whose real fix (gold patch) touched more than
code: docs, changelogs, config files, or error messages. These are the
requirements that tests often don't check.

Usage:
    pip install datasets
    python filter_tasks.py

Output:
    candidates.csv  - all matching tasks, easiest/smallest first
    prints the top 20 to the terminal
"""

import csv
import re
from datasets import load_dataset

DOC_EXT = (".rst", ".md", ".txt")
CONFIG_EXT = (".cfg", ".toml", ".ini", ".yaml", ".yml", ".json")
CHANGELOG_HINTS = ("changelog", "changes", "whatsnew", "release", "news")


def files_in_patch(patch: str):
    return re.findall(r"^diff --git a/(\S+) b/", patch, flags=re.MULTILINE)


def classify(path: str):
    p = path.lower()
    tags = set()
    if any(h in p for h in CHANGELOG_HINTS):
        tags.add("changelog")
    if p.endswith(DOC_EXT) or p.startswith("doc/") or p.startswith("docs/") or "/docs/" in p:
        tags.add("docs")
    if p.endswith(CONFIG_EXT) or p.endswith("setup.py"):
        tags.add("config")
    return tags


def changes_error_message(patch: str):
    """Rough check: does the fix add a raise/warn with a message string?"""
    added = [l for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
    return any(re.search(r"\b(raise \w+\(|warnings\.warn\()\s*[fr]?['\"]", l) for l in added)


def main():
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    rows = []
    for ex in ds:
        files = files_in_patch(ex["patch"])
        tags = set()
        for f in files:
            tags |= classify(f)
        if changes_error_message(ex["patch"]):
            tags.add("error_message")
        if not tags:
            continue
        rows.append({
            "instance_id": ex["instance_id"],
            "repo": ex["repo"],
            "base_commit": ex["base_commit"],
            "difficulty": ex.get("difficulty", ""),
            "non_code_types": ",".join(sorted(tags)),
            "files_changed": len(files),
            "patch_lines": len(ex["patch"].splitlines()),
            "files": " ".join(files),
            "issue_text": ex["problem_statement"],
            "gold_patch": ex["patch"],
            "test_patch": ex["test_patch"],
        })

    # Prefer easy, small fixes: quicker to understand and write a checklist for
    diff_rank = {"<15 min fix": 0, "15 min - 1 hour": 1, "1-4 hours": 2, ">4 hours": 3}
    rows.sort(key=lambda r: (diff_rank.get(r["difficulty"], 9), r["patch_lines"]))

    with open("candidates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} of {len(ds)} tasks touch docs/config/changelog/error messages\n")
    for r in rows[:20]:
        print(f"{r['instance_id']:45} {r['difficulty']:16} {r['non_code_types']:30} {r['patch_lines']} lines")
    print("\nFull list saved to candidates.csv")


if __name__ == "__main__":
    main()
