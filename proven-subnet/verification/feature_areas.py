"""Feature Area catalogue for the Willify reference app.

A Feature Area bundles everything the validator needs to run one epoch against a
slice of the app: the page under test, a spec to broadcast, a structured
Selector Manifest (behaviour-first hints so miners test behaviour instead of
mining selectors), the Golden Oracle Suite that defines killability, the
mutation operators that inject faults, and the blunt-killer operators that blank
the area for the Tautology Trap.

Every mutation operator is paired with a Golden Oracle assertion (see
``oracles/homepage_oracle.py``): the oracle fails on each single-operator mutant,
so the Oracle admission filter keeps it (no equivalent mutants inflate N_mut).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from verification.mutation import Operator

_HOMEPAGE_RELPATH = "src/html/index.html"
_ORACLE_DIR = Path(__file__).resolve().parent / "oracles"


@dataclass(frozen=True)
class SelectorEntry:
    """One behaviour-first manifest element: selector + a11y + expected state."""

    name: str
    selector: str
    role: str = ""
    accessible_name: str = ""
    attributes: dict | None = None
    state: dict | None = None


@dataclass(frozen=True)
class FeatureArea:
    name: str
    target_path: str  # URL path appended to the base, e.g. /src/html/index.html
    reference_relpath: str  # file the engine mutates, e.g. src/html/index.html
    spec_type: str
    requirement_content: str
    selectors: tuple
    operators: tuple
    blunt_operators: tuple
    oracle_suite: str

    def manifest(self) -> dict:
        """Structured Selector Manifest broadcast to miners (ADR-0003)."""
        return {
            "feature_area": self.name,
            "elements": [
                {
                    "name": e.name,
                    "selector": e.selector,
                    "role": e.role,
                    "accessible_name": e.accessible_name,
                    "attributes": e.attributes or {},
                    "state": e.state or {},
                }
                for e in self.selectors
            ],
        }


def _op(name, kind, find, replace, description):
    return Operator(
        name=name,
        kind=kind,
        target_file=_HOMEPAGE_RELPATH,
        find=find,
        replace=replace,
        description=description,
    )


_HOMEPAGE_SELECTORS = (
    SelectorEntry(
        name="read_more_button",
        selector="#read-more-button",
        role="button",
        accessible_name="Read More",
        state={"visible": True},
    ),
    SelectorEntry(
        name="homepage_heading",
        selector="h3",
        role="heading",
        accessible_name="Where Music Meets Comfort",
    ),
    SelectorEntry(
        name="register_link",
        selector="#sign-up",
        role="link",
        accessible_name="Register",
        attributes={"href": "register.html"},
    ),
)

# Each operator is killed by a matching assertion in the Golden Oracle Suite.
_HOMEPAGE_OPERATORS = (
    _op(
        "swap_hero_subheading",
        "swap_text",
        "<h3>Where Music Meets Comfort</h3>",
        "<h3>Where Music Meets Discomfort</h3>",
        "Hero subheading text changed.",
    ),
    _op(
        "swap_hero_title",
        "swap_text",
        "<h1>Willify</h1>",
        "<h1>Willifing</h1>",
        "Hero H1 brand text changed.",
    ),
    _op(
        "remove_read_more_button",
        "remove_element",
        '<button id="read-more-button" class="link">Read More</button>',
        "",
        "Read More button removed.",
    ),
    _op(
        "rename_read_more_button_id",
        "rename_attr",
        'id="read-more-button"',
        'id="read-more-btn"',
        "Read More button id renamed (breaks #read-more-button).",
    ),
    _op(
        "swap_read_more_text",
        "swap_text",
        ">Read More</button>",
        ">Read Less</button>",
        "Read More button label changed.",
    ),
    _op(
        "rewrite_register_href",
        "rewrite_href",
        'href="register.html"',
        'href="wrong.html"',
        "Register link href changed.",
    ),
    _op(
        "rename_register_id",
        "rename_attr",
        'id="sign-up"',
        'id="signup"',
        "Register link id renamed (breaks #sign-up).",
    ),
    _op(
        "swap_register_text",
        "swap_text",
        'id="sign-up">Register</a>',
        'id="sign-up">Sign Up</a>',
        "Register link label changed.",
    ),
    _op(
        "rename_read_more_section_id",
        "rename_attr",
        'id="read-more-section"',
        'id="read-more-sections"',
        "Read-more scroll target id renamed.",
    ),
    _op(
        "rename_mobile_menu_id",
        "rename_attr",
        'id="mobile-menu"',
        'id="mobile_menu"',
        "Mobile menu id renamed (breaks JS hook).",
    ),
    _op(
        "swap_feature_heading",
        "swap_text",
        ">Why Choose Willify?</h1>",
        ">Why Choose Willifing?</h1>",
        "Feature section heading text changed.",
    ),
    _op(
        "swap_title",
        "swap_text",
        "<title>Willify | Home</title>",
        "<title>Willifing | Home</title>",
        "Document title changed.",
    ),
    _op(
        "rename_home_nav_id",
        "rename_attr",
        'id="home-page"',
        'id="home_page"',
        "Home nav link id renamed.",
    ),
)

# Blank the manifest elements so a genuine test fails but a ghost still passes.
_HOMEPAGE_BLUNT_OPERATORS = (
    _op(
        "blank_read_more_button",
        "remove_element",
        '<button id="read-more-button" class="link">Read More</button>',
        "",
        "Blank Read More button.",
    ),
    _op(
        "blank_hero_subheading",
        "remove_element",
        "<h3>Where Music Meets Comfort</h3>",
        "<h3></h3>",
        "Blank hero subheading.",
    ),
    _op(
        "blank_hero_title",
        "remove_element",
        "<h1>Willify</h1>",
        "<h1></h1>",
        "Blank hero title.",
    ),
    _op(
        "blank_register_link",
        "remove_element",
        '<a href="register.html" class="button link" id="sign-up">Register</a>',
        "",
        "Blank register link.",
    ),
)


WILLIFY_HOMEPAGE = FeatureArea(
    name="willify_homepage",
    target_path="/src/html/index.html",
    reference_relpath=_HOMEPAGE_RELPATH,
    spec_type="user_story",
    requirement_content=(
        "On the Willify homepage, the hero shows the heading 'Where Music "
        "Meets Comfort' and a visible 'Read More' button, and the navigation "
        "exposes a 'Register' link pointing to register.html."
    ),
    selectors=_HOMEPAGE_SELECTORS,
    operators=_HOMEPAGE_OPERATORS,
    blunt_operators=_HOMEPAGE_BLUNT_OPERATORS,
    oracle_suite=str(_ORACLE_DIR / "homepage_oracle.py"),
)


FEATURE_AREAS = {WILLIFY_HOMEPAGE.name: WILLIFY_HOMEPAGE}


def get_feature_area(name) -> FeatureArea:
    """Return the catalogue entry for *name* (raises KeyError if unknown)."""
    return FEATURE_AREAS[name]


def load_reference_files(area: FeatureArea, reference_root) -> dict:
    """Read the area's mutatable file(s) from *reference_root* into a map."""
    root = Path(reference_root)
    return {
        area.reference_relpath: (root / area.reference_relpath).read_text(
            encoding="utf-8"
        )
    }
