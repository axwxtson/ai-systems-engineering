"""
Exercise 2.3: Few-Shot Calibration
Tests sentiment classification accuracy with 0, 1, 3, and 5 examples.
"""

import anthropic
import json
from prompts import build_prompt

client = anthropic.Anthropic()

TEST_HEADLINES = [
    {"headline": "Amazon Web Services revenue surges 35% year-over-year, exceeding all forecasts",
     "expected": "bullish"},
    {"headline": "Cryptocurrency exchange FTX files for bankruptcy amid liquidity crisis",
     "expected": "bearish"},
    {"headline": "S&P 500 closes flat as investors digest mixed economic data",
     "expected": "neutral"},
    {"headline": "Nvidia announces new AI chip but faces potential export restrictions to China",
     "expected": "neutral"},
    {"headline": "Bank of England raises rates for the 14th consecutive time, says further hikes unlikely",
     "expected": "neutral"},
    {"headline": "Consumer confidence falls to lowest level since 2021 as inflation concerns persist",
     "expected": "bearish"},
    {"headline": "Unemployment claims drop to 52-week low, labour market remains tight",
     "expected": "bullish"},
    {"headline": "Gold surges 4% as global recession fears mount and investors flee to safe havens",
     "expected": "bullish"},
    {"headline": "Government announces massive stimulus package amid deepening economic crisis",
     "expected": "neutral"},
    {"headline": "Tech CEO steps down to pursue personal interests, board names interim replacement",
     "expected": "bearish"},
]


def classify_headline(headline: str, system_prompt: str) -> dict:
    """Send a headline to Claude and parse the JSON response."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        system=system_prompt,
        messages=[{"role": "user", "content": headline}]
    )

    raw = response.content[0].text.strip()

    # Try to parse JSON — handle cases where Claude wraps it in markdown
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]  # remove first line
        raw = raw.rsplit("```", 1)[0]  # remove last fence
        raw = raw.strip()

    try:
        result = json.loads(raw)
        return {
            "sentiment": result.get("sentiment", "PARSE_ERROR"),
            "confidence": result.get("confidence", 0),
            "reasoning": result.get("reasoning", ""),
            "raw": raw,
            "valid_json": True
        }
    except json.JSONDecodeError:
        return {
            "sentiment": "PARSE_ERROR",
            "confidence": 0,
            "reasoning": "",
            "raw": raw,
            "valid_json": False
        }


def run_experiment(num_examples: int) -> dict:
    """Run all test headlines against a prompt with N examples."""
    system_prompt = build_prompt(num_examples)
    
    print(f"\n{'='*60}")
    print(f"TESTING WITH {num_examples} EXAMPLES")
    print(f"{'='*60}")

    correct = 0
    valid_json = 0
    results = []

    for test in TEST_HEADLINES:
        result = classify_headline(test["headline"], system_prompt)
        
        is_correct = result["sentiment"] == test["expected"]
        if is_correct:
            correct += 1
        if result["valid_json"]:
            valid_json += 1

        status = "✓" if is_correct else "✗"
        print(f"  {status} Expected: {test['expected']:8s} | "
              f"Got: {result['sentiment']:8s} | "
              f"Conf: {result['confidence']:.2f} | "
              f"{test['headline'][:60]}...")

        results.append({
            "headline": test["headline"],
            "expected": test["expected"],
            "got": result["sentiment"],
            "correct": is_correct,
            "confidence": result["confidence"],
            "reasoning": result["reasoning"],
            "valid_json": result["valid_json"]
        })

    accuracy = correct / len(TEST_HEADLINES)
    json_rate = valid_json / len(TEST_HEADLINES)

    print(f"\n  Accuracy: {correct}/{len(TEST_HEADLINES)} ({accuracy:.0%})")
    print(f"  Valid JSON: {valid_json}/{len(TEST_HEADLINES)} ({json_rate:.0%})")

    return {
        "num_examples": num_examples,
        "accuracy": accuracy,
        "json_rate": json_rate,
        "correct": correct,
        "total": len(TEST_HEADLINES),
        "results": results
    }


def main():
    print("FEW-SHOT CALIBRATION EXPERIMENT")
    print("Testing sentiment classification with 0, 1, 3, and 5 examples")

    all_results = []
    for n in [0, 1, 3, 5]:
        result = run_experiment(n)
        all_results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Examples':>10} | {'Accuracy':>10} | {'Valid JSON':>10}")
    print(f"{'-'*10}-+-{'-'*10}-+-{'-'*10}")
    for r in all_results:
        print(f"{r['num_examples']:>10} | {r['accuracy']:>9.0%} | {r['json_rate']:>9.0%}")

    # Save detailed results
    with open("results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nDetailed results saved to results.json")


if __name__ == "__main__":
    main()