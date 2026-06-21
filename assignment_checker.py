#!/usr/bin/env python3
"""
AI-Based Student Assignment Checker

"""
import argparse, json, os, urllib.request, urllib.error

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

def build_prompt(submission, rubric):
    return f"""You are grading a student assignment against a rubric.

RUBRIC:
{rubric}

STUDENT SUBMISSION:
{submission}

Evaluate the submission against EACH rubric line. Respond with ONLY valid JSON
(no markdown fences, no preamble) in exactly this shape:
{{
  "total_score": <number out of the rubric's max points>,
  "max_score": <number>,
  "criteria": [
    {{"criterion": "<rubric line>", "points_earned": <number>, "points_possible": <number>, "comment": "<one sentence>"}}
  ],
  "strengths": ["<short point>", "..."],
  "improvements": ["<short point>", "..."],
  "overall_feedback": "<2-3 sentences of feedback the student would read directly>"
}}"""

def call_claude(prompt):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY environment variable not set.")
    payload = json.dumps({"model": MODEL, "max_tokens": 1500,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(API_URL, data=payload, headers={
        "Content-Type": "application/json", "x-api-key": api_key,
        "anthropic-version": "2023-06-01"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API error {e.code}: {e.read().decode()}")
    text = "".join(b["text"] for b in body["content"] if b["type"] == "text")
    text = text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)

def mock_response():
    return {"total_score": 62, "max_score": 100, "criteria": [
        {"criterion": "Sample criterion", "points_earned": 15, "points_possible": 20, "comment": "Example comment."}],
        "strengths": ["Example strength"], "improvements": ["Example improvement"],
        "overall_feedback": "This is mock output for testing without an API call."}

def print_report(result):
    print(f"SCORE: {result['total_score']}/{result['max_score']}\n")
    for c in result["criteria"]:
        print(f"- [{c['points_earned']}/{c['points_possible']}] {c['criterion']}")
        print(f"    {c['comment']}")
    print("\nStrengths:")
    for s in result["strengths"]: print(f"  + {s}")
    print("\nImprovements:")
    for i in result["improvements"]: print(f"  - {i}")
    print(f"\nOverall: {result['overall_feedback']}")

def main():
    parser = argparse.ArgumentParser(description="AI-based assignment checker.")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--rubric", required=True)
    parser.add_argument("--output")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    submission, rubric = open(args.submission).read(), open(args.rubric).read()
    result = mock_response() if args.mock else call_claude(build_prompt(submission, rubric))
    print_report(result)
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved to {args.output}")

if __name__ == "__main__":
    main()
