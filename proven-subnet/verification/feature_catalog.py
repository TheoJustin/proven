"""Willify feature-area catalogue used by validator task generation."""

from __future__ import annotations

import hashlib

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class FeatureArea:
    name: str
    spec_template: str
    reference_html: str
    mutation_operators: tuple[str, ...]
    oracle: Callable[[dict[str, str]], bool]


def _homepage_oracle(tree: dict[str, str]) -> bool:
    text = "\n".join(tree.values()).lower()
    return (
        "read more" in text
        and "sign" in text
        and ("willify" in text or "music" in text)
    )


def _songs_oracle(tree: dict[str, str]) -> bool:
    text = "\n".join(tree.values()).lower()
    return "song" in text and ("play" in text or "music" in text)


def willify_catalog(reference_root: str | Path | None = None) -> dict[str, FeatureArea]:
    root = (
        Path(reference_root)
        if reference_root
        else Path(__file__).resolve().parents[1]
        / "docker"
        / "reference"
        / "src"
        / "html"
    )
    return {
        "homepage": FeatureArea(
            name="homepage",
            spec_template="Check Willify homepage hero text, Read More button, and register link behavior.",
            reference_html=str(root / "index.html"),
            mutation_operators=(
                "text_swap",
                "attribute_remove",
                "href_rewrite",
                "element_remove",
            ),
            oracle=_homepage_oracle,
        ),
        "songs": FeatureArea(
            name="songs",
            spec_template="Check Willify songs listing navigation and visible song controls.",
            reference_html=str(root / "songs.html"),
            mutation_operators=(
                "text_swap",
                "attribute_rename",
                "href_rewrite",
                "js_logic_flip",
            ),
            oracle=_songs_oracle,
        ),
    }


def choose_feature_area(
    seed: int | str, reference_root: str | Path | None = None
) -> FeatureArea:
    catalog = willify_catalog(reference_root)
    names = sorted(catalog)
    digest = hashlib.sha256(str(seed).encode()).hexdigest()
    index = int(digest, 16) % len(names)
    return catalog[names[index]]
