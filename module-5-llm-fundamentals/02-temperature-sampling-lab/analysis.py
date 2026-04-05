"""
Exercise 5.2: Temperature and Sampling Lab — Analysis

Computes diversity metrics for outputs collected at different sampling settings:
- Unique output count (exact string match)
- Average pairwise edit distance (Levenshtein)
- Average word-level Jaccard similarity
- Output length statistics
- Token usage and cost

These metrics together tell the full story:
- Unique count: how many distinct outputs did we get?
- Edit distance: how different are they character-by-character?
- Jaccard similarity: how much do they share the same words?
"""

import Levenshtein
import numpy as np
from itertools import combinations


def unique_output_count(results: list[dict]) -> int:
    """
    Count how many distinct outputs were produced.
    
    Exact string match — even a single character difference counts as unique.
    This is the coarsest diversity measure.
    """
    texts = [r["text"].strip() for r in results]
    return len(set(texts))


def unique_output_ratio(results: list[dict]) -> float:
    """
    Fraction of outputs that are unique: unique_count / total_count.
    
    1.0 = every output was different (maximum diversity)
    1/n = every output was identical (minimum diversity)
    """
    return unique_output_count(results) / len(results)


def average_pairwise_edit_distance(results: list[dict]) -> float:
    """
    Average Levenshtein edit distance between all pairs of outputs.
    
    Levenshtein distance = minimum number of single-character edits
    (insertions, deletions, substitutions) to transform one string into another.
    
    Higher = more diverse outputs.
    """
    texts = [r["text"].strip() for r in results]
    if len(texts) < 2:
        return 0.0

    distances = []
    for a, b in combinations(texts, 2):
        distances.append(Levenshtein.distance(a, b))

    return np.mean(distances)


def normalised_edit_distance(results: list[dict]) -> float:
    """
    Average edit distance normalised by average output length.
    
    This makes distances comparable across prompts with different
    output lengths. A normalised distance of 0.5 means outputs differ
    by about half their characters on average.
    """
    texts = [r["text"].strip() for r in results]
    if len(texts) < 2:
        return 0.0

    avg_len = np.mean([len(t) for t in texts])
    if avg_len == 0:
        return 0.0

    return average_pairwise_edit_distance(results) / avg_len


def average_jaccard_similarity(results: list[dict]) -> float:
    """
    Average word-level Jaccard similarity between all pairs.
    
    Jaccard = |intersection| / |union| of word sets.
    
    1.0 = identical word sets (same words, possibly different order)
    0.0 = completely different words
    
    This captures semantic similarity better than edit distance —
    "The capital is Canberra" and "Canberra is the capital" have
    high Jaccard but moderate edit distance.
    """
    texts = [r["text"].strip() for r in results]
    if len(texts) < 2:
        return 1.0

    similarities = []
    for a, b in combinations(texts, 2):
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        union = words_a | words_b
        if not union:
            similarities.append(1.0)
            continue
        intersection = words_a & words_b
        similarities.append(len(intersection) / len(union))

    return np.mean(similarities)


def output_length_stats(results: list[dict]) -> dict:
    """
    Statistics on output length (in characters).
    
    High variance in length suggests the model is exploring
    different response strategies, not just different words.
    """
    lengths = [len(r["text"].strip()) for r in results]
    return {
        "mean": np.mean(lengths),
        "std": np.std(lengths),
        "min": int(np.min(lengths)),
        "max": int(np.max(lengths)),
        "cv": np.std(lengths) / np.mean(lengths) if np.mean(lengths) > 0 else 0,  # coefficient of variation
    }


def token_usage_stats(results: list[dict]) -> dict:
    """
    Token usage statistics across runs.
    """
    input_tokens = [r["input_tokens"] for r in results]
    output_tokens = [r["output_tokens"] for r in results]
    latencies = [r["latency_ms"] for r in results]

    return {
        "total_input_tokens": sum(input_tokens),
        "total_output_tokens": sum(output_tokens),
        "avg_output_tokens": np.mean(output_tokens),
        "avg_latency_ms": np.mean(latencies),
    }


def analyse_setting(results: list[dict]) -> dict:
    """
    Run all analyses on a single setting's results.
    
    Returns a dict with all metrics for display.
    """
    return {
        "runs": len(results),
        "unique_count": unique_output_count(results),
        "unique_ratio": unique_output_ratio(results),
        "avg_edit_distance": average_pairwise_edit_distance(results),
        "normalised_edit_distance": normalised_edit_distance(results),
        "avg_jaccard_similarity": average_jaccard_similarity(results),
        "length_stats": output_length_stats(results),
        "token_stats": token_usage_stats(results),
    }


def analyse_experiment(experiment_results: dict) -> dict:
    """
    Analyse all settings in an experiment.
    
    Args:
        experiment_results: Dict mapping setting_label -> list of result dicts
    
    Returns:
        Dict mapping setting_label -> analysis dict
    """
    analyses = {}
    for setting_label, results in experiment_results.items():
        analyses[setting_label] = analyse_setting(results)
    return analyses


# ─── Cost Calculation ───────────────────────────────────────────────

HAIKU_INPUT_PER_MILLION = 0.80
HAIKU_OUTPUT_PER_MILLION = 4.00


def calculate_experiment_cost(all_analyses: dict) -> dict:
    """
    Calculate total cost across all settings in an experiment.
    """
    total_input = 0
    total_output = 0

    for analysis in all_analyses.values():
        total_input += analysis["token_stats"]["total_input_tokens"]
        total_output += analysis["token_stats"]["total_output_tokens"]

    input_cost = (total_input / 1_000_000) * HAIKU_INPUT_PER_MILLION
    output_cost = (total_output / 1_000_000) * HAIKU_OUTPUT_PER_MILLION
    total_cost = input_cost + output_cost

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }