#!/usr/bin/env python3
"""
AI-Based Student Assignment Checker
------------------------------------
A small, repeatable tool for checking a student assignment against a rubric:
  1. Word count range
  2. Required sections present
  3. Citation format present (basic APA in-text pattern)
  4. Similarity / plagiarism check against a folder of past submissions
  5. Basic grammar heuristics (long sentences, repeated words)
  6. Optional AI qualitative feedback (Claude API) on content & coherence

Usage:
    python assignment_checker.py --file sample_assignment.txt --rubric rubric.json --corpus-dir reference_corpus
    python assignment_checker.py --file sample_assignment.txt --rubric rubric.json --use-ai
"""

import argparse
import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional


# ---------- helpers ----------

def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def load_rubric(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


# ---------- checks ----------

def check_word_count(text: str, rubric: dict) -> dict:
    n = count_words(text)
    lo, hi = rubric.get("min_words", 0), rubric.get("max_words", 10**9)
    ok = lo <= n <= hi
    return {"name": "Word count", "passed": ok, "detail": f"{n} words (expected {lo}-{hi})"}


def check_required_sections(text: str, rubric: dict) -> dict:
    required = rubric.get("required_sections", [])
    missing = [s for s in required if s.lower() not in text.lower()]
    ok = len(missing) == 0
    detail = "All required sections found" if ok else f"Missing: {', '.join(missing)}"
    return {"name": "Required sections", "passed": ok, "detail": detail}


def check_citations(text: str, rubric: dict) -> dict:
    pattern = r"\([A-Z][A-Za-z\-]+(?:\s(?:&|and)\s[A-Z][A-Za-z\-]+)?,?\s\d{4}\)"
    matches = re.findall(pattern, text)
    min_required = rubric.get("min_citations", 1)
    ok = len(matches) >= min_required
    return {
        "name": "Citations (APA-style)",
        "passed": ok,
        "detail": f"Found {len(matches)} citation(s), required at least {min_required}",
    }


def check_similarity(text: str, corpus_dir: Optional[str], threshold: float) -> dict:
    if not corpus_dir or not os.path.isdir(corpus_dir):
        return {"name": "Similarity check", "passed": True, "detail": "Skipped (no corpus directory provided)"}

    best_ratio, best_file = 0.0, None
    for fname in os.listdir(corpus_dir):
        fpath = os.path.join(corpus_dir, fname)
        if not os.path.isfile(fpath):
            continue
        other = read_text(fpath)
        ratio = SequenceMatcher(None, text, other).ratio()
        if ratio > best_ratio:
            best_ratio, best_file = ratio, fname

    ok = best_ratio < threshold
    if best_file:
        detail = f"Highest similarity {best_ratio:.0%} vs '{best_file}' (flag threshold {threshold:.0%})"
    else:
        detail = "No reference files found in corpus directory"
    return {"name": "Similarity check", "passed": ok, "detail": detail}


def check_grammar_heuristics(text: str) -> dict:
    issues = []
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    long_sentences = [s for s in sentences if len(s.split()) > 40]
    if long_sentences:
        issues.append(f"{len(long_sentences)} sentence(s) over 40 words")
    repeats = re.findall(r"\b(\w+)\s+\1\b", text, flags=re.IGNORECASE)
    if repeats:
        issues.append(f"Repeated word(s): {', '.join(sorted(set(repeats)))}")
    ok = len(issues) == 0
    return {"name": "Grammar heuristics", "passed": ok, "detail": "; ".join(issues) if issues else "No issues found"}


# ---------- AI feedback ----------

def ai_feedback(text: str, rubric: dict) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import requests
    except ImportError:
        return "AI feedback skipped: install 'requests' (pip install requests) to enable this feature."

    prompt = (
        "You are a grading-support assistant. Read the student assignment below and the rubric. "
        "Give exactly 3 short bullet points of constructive feedback on content quality, clarity, "
        "and structure. Be concise.\n\n"
        f"RUBRIC: {json.dumps(rubric)}\n\n"
        f"ASSIGNMENT:\n{text[:6000]}"
    )
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(parts).strip() or None
    except Exception as e:
        return f"AI feedback failed: {e}"


# ---------- scoring & report ----------

def compute_score(checks: list) -> float:
    if not checks:
        return 0.0
    passed = sum(1 for c in checks if c["passed"])
    return round(100 * passed / len(checks), 1)


def run_checks(text: str, rubric: dict, corpus_dir: Optional[str]) -> list:
    return [
        check_word_count(text, rubric),
        check_required_sections(text, rubric),
        check_citations(text, rubric),
        check_similarity(text, corpus_dir, rubric.get("similarity_threshold", 0.35)),
        check_grammar_heuristics(text),
    ]


def print_summary(checks: list, score: float, feedback: Optional[str]):
    print("\n=== Assignment Check Report ===")
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"[{status}] {c['name']}: {c['detail']}")
    print(f"\nOverall rule-based score: {score}%")
    if feedback:
        print("\n--- AI Feedback ---")
        print(feedback)
    print("================================\n")


def main():
    parser = argparse.ArgumentParser(description="AI-Based Student Assignment Checker")
    parser.add_argument("--file", required=True, help="Path to the assignment text file")
    parser.add_argument("--rubric", required=True, help="Path to rubric JSON file")
    parser.add_argument("--corpus-dir", default=None, help="Folder of past submissions for similarity check")
    parser.add_argument("--use-ai", action="store_true",
                         help="Call Claude API for qualitative feedback (needs ANTHROPIC_API_KEY env var)")
    parser.add_argument("--output", default="report.json", help="Where to save the JSON report")
    args = parser.parse_args()

    text = read_text(args.file)
    rubric = load_rubric(args.rubric)
    checks = run_checks(text, rubric, args.corpus_dir)
    score = compute_score(checks)

    feedback = ai_feedback(text, rubric) if args.use_ai else None

    print_summary(checks, score, feedback)

    report = {
        "file": args.file,
        "score": score,
        "checks": checks,
        "ai_feedback": feedback,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Full report saved to {args.output}")


if __name__ == "__main__":
    main()
