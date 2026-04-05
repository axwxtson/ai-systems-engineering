"""
Exercise 5.2: Temperature and Sampling Lab — Sampling Engine

Sends the same prompt to Claude at different temperature/top-p settings,
runs multiple trials at each setting, and collects the outputs for analysis.

Uses claude-haiku-3.5 to keep costs low — we're testing sampling behaviour,
not model intelligence.
"""

import anthropic
import time


# ─── Test Prompts ───────────────────────────────────────────────────
# Three prompt types to test how sampling parameters affect different tasks.

TEST_PROMPTS = {
    "factual": {
        "prompt": "What is the capital of Australia?",
        "label": "Factual Q&A",
        "why": "Factual questions should converge on the same answer regardless of temperature. "
               "If they don't, it reveals how temperature introduces noise even on simple tasks.",
        "max_tokens": 100,
    },
    "creative": {
        "prompt": "Write a one-sentence tagline for a cryptocurrency trading platform.",
        "label": "Creative Writing",
        "why": "Creative tasks should show high variance at high temperatures — that's the point. "
               "Low temperatures will produce repetitive, safe outputs.",
        "max_tokens": 100,
    },
    "analytical": {
        "prompt": "List exactly 3 risks of investing in Bitcoin. Be concise — one sentence each.",
        "label": "Analytical / Structured",
        "why": "Structured analytical tasks should be somewhat consistent (same risks cited) but "
               "with wording variation. Tests the middle ground between factual and creative.",
        "max_tokens": 200,
    },
}


# ─── Temperature and Top-p Settings ────────────────────────────────

TEMPERATURE_SETTINGS = [0, 0.3, 0.7, 1.0]

# Additional top-p experiment at fixed temperature
TOP_P_SETTINGS = [
    {"temperature": 1.0, "top_p": 0.5, "label": "temp=1.0, top_p=0.5"},
    {"temperature": 1.0, "top_p": 0.9, "label": "temp=1.0, top_p=0.9"},
    {"temperature": 1.0, "top_p": 1.0, "label": "temp=1.0, top_p=1.0 (no filter)"},
]

RUNS_PER_SETTING = 10
MODEL = "claude-haiku-4-5-20251001"


def run_single_call(
    client: anthropic.Anthropic,
    prompt: str,
    temperature: float,
    max_tokens: int,
    top_p: float | None = None,
) -> dict:
    """
    Make a single API call and return the response with metadata.
    
    Note: Claude requires exactly one of temperature or top_p — not both.
    When top_p is specified, we omit temperature (defaults to 1.0).
    
    Returns dict with: text, input_tokens, output_tokens, latency_ms
    """
    kwargs = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if top_p is not None:
        kwargs["top_p"] = top_p
    else:
        kwargs["temperature"] = temperature

    start = time.time()
    response = client.messages.create(**kwargs)
    latency_ms = (time.time() - start) * 1000

    text = response.content[0].text if response.content else ""

    return {
        "text": text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_ms": latency_ms,
    }


def run_temperature_experiment(
    client: anthropic.Anthropic,
    prompt_key: str,
    runs: int = RUNS_PER_SETTING,
    callback=None,
) -> dict:
    """
    Run a full temperature experiment for one prompt type.
    
    For each temperature setting, runs `runs` trials and collects all outputs.
    
    Args:
        client: Anthropic client
        prompt_key: Key from TEST_PROMPTS
        runs: Number of runs per setting
        callback: Optional function called after each API call with (setting_label, run_number)
    
    Returns:
        Dict mapping temperature -> list of result dicts
    """
    prompt_info = TEST_PROMPTS[prompt_key]
    results = {}

    for temp in TEMPERATURE_SETTINGS:
        setting_label = f"temp={temp}"
        results[setting_label] = []

        for i in range(runs):
            if callback:
                callback(setting_label, i + 1, runs)

            result = run_single_call(
                client=client,
                prompt=prompt_info["prompt"],
                temperature=temp,
                max_tokens=prompt_info["max_tokens"],
            )
            results[setting_label].append(result)

            # Small delay to avoid rate limiting
            time.sleep(0.2)

    return results


def run_top_p_experiment(
    client: anthropic.Anthropic,
    prompt_key: str,
    runs: int = RUNS_PER_SETTING,
    callback=None,
) -> dict:
    """
    Run top-p experiment for one prompt type at fixed temperature=1.0.
    
    Tests how top-p filtering affects output diversity independently of temperature.
    """
    prompt_info = TEST_PROMPTS[prompt_key]
    results = {}

    for setting in TOP_P_SETTINGS:
        label = setting["label"]
        results[label] = []

        for i in range(runs):
            if callback:
                callback(label, i + 1, runs)

            result = run_single_call(
                client=client,
                prompt=prompt_info["prompt"],
                temperature=setting["temperature"],
                max_tokens=prompt_info["max_tokens"],
                top_p=setting["top_p"],
            )
            results[label].append(result)

            time.sleep(0.2)

    return results