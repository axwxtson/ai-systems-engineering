"""
rubric.py — scoring rubric for the framework survey.

Six criteria, each scored 1–5 (higher is better for the final display,
which means `abstraction_tax` is inverted before display).

The rubric is deliberately opinionated. The point of the exercise isn't
to produce an objective ranking — there isn't one — it's to force you
to commit to a defensible judgement per criterion, with a one-sentence
rationale. An interviewer who reads your rubric output should be able
to disagree with any specific score but should never be confused about
what you meant.
"""

from dataclasses import dataclass


CRITERIA = [
    "lines_of_code",
    "dependencies",
    "debuggability",
    "feature_access",
    "abstraction_tax",
    "typing_quality",
]

CRITERIA_DESCRIPTIONS = {
    "lines_of_code": (
        "How much code does it take to express the task? "
        "Lower is better; score 5 = <40 LoC, 4 = 40-50, 3 = 50-65, "
        "2 = 65-80, 1 = 80+."
    ),
    "dependencies": (
        "How many transitive dependencies does the import footprint add? "
        "Lower is better; score 5 = <15 deps, 4 = 15-25, 3 = 25-45, "
        "2 = 45-70, 1 = 70+."
    ),
    "debuggability": (
        "When something goes wrong, how hard is it to find out why? "
        "Score 5 = you can read the entire control flow top to bottom "
        "in one file; 1 = you have to read library internals."
    ),
    "feature_access": (
        "How easy is it to use Anthropic-specific features — prompt "
        "caching, extended thinking, cache-aware token counts, "
        "beta headers? Score 5 = trivial; 1 = effectively impossible."
    ),
    "abstraction_tax": (
        "How much does the framework's abstraction get in the way when "
        "you need behaviour it didn't anticipate? Score 5 = no tax; "
        "1 = heavy tax. (Note: internally stored inverted — low tax "
        "score in source maps to high display score.)"
    ),
    "typing_quality": (
        "How well-typed is the code end-to-end? Score 5 = every boundary "
        "is a typed object; 1 = dict soup with optional keys."
    ),
}


@dataclass
class RubricScore:
    implementation: str
    lines_of_code: int
    dependencies: int
    debuggability: int
    feature_access: int
    abstraction_tax: int
    typing_quality: int

    @property
    def total(self) -> int:
        return (
            self.lines_of_code
            + self.dependencies
            + self.debuggability
            + self.feature_access
            + self.abstraction_tax
            + self.typing_quality
        )


def score_loc(loc: int) -> int:
    if loc < 40:
        return 5
    if loc < 50:
        return 4
    if loc < 65:
        return 3
    if loc < 80:
        return 2
    return 1


def score_deps(deps: int) -> int:
    if deps < 15:
        return 5
    if deps < 25:
        return 4
    if deps < 45:
        return 3
    if deps < 70:
        return 2
    return 1


def invert_tax(raw_tax: int) -> int:
    """Convert raw abstraction tax (1=none, 5=heavy) to display score."""
    return 6 - raw_tax


def score_baseline(loc: int) -> RubricScore:
    """
    The baseline rubric. The scores reflect my opinions on the hand-rolled
    SDK implementation; they're not propaganda for it. If anything, the
    baseline LOSES on `dependencies` at a low score because the Anthropic
    SDK itself brings a handful of deps, and it loses mildly on `typing`
    because the raw SDK returns messages that aren't fully typed.
    """
    return RubricScore(
        implementation="SDK Baseline (hand-rolled)",
        lines_of_code=score_loc(loc),
        dependencies=5,        # anthropic + colorama, very light
        debuggability=5,       # you can read the entire loop top to bottom
        feature_access=5,      # every Anthropic feature is one line away
        abstraction_tax=invert_tax(1),  # no framework tax
        typing_quality=3,      # SDK message content isn't fully typed
    )


def score_sketch(sketch) -> RubricScore:
    """Build a RubricScore from a FrameworkSketch's estimated fields."""
    return RubricScore(
        implementation=sketch.name,
        lines_of_code=score_loc(sketch.estimated_loc),
        dependencies=score_deps(sketch.estimated_deps),
        debuggability=sketch.debuggability,
        feature_access=sketch.feature_access,
        abstraction_tax=invert_tax(sketch.abstraction_tax),
        typing_quality=sketch.typing_quality,
    )