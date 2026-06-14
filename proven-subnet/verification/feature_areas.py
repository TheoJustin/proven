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

import random
from dataclasses import dataclass
from pathlib import Path

from verification.mutation import Operator

_HOMEPAGE_RELPATH = "src/html/index.html"
_REGISTER_RELPATH = "src/html/register.html"
_SONGS_RELPATH = "src/html/songs.html"
_ABOUT_RELPATH = "src/html/about-us.html"
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


def _op_for(relpath):
    """Build an operator factory bound to one page's relpath."""

    def op(name, kind, find, replace, description=""):
        return Operator(
            name=name,
            kind=kind,
            target_file=relpath,
            find=find,
            replace=replace,
            description=description,
        )

    return op


_op = _op_for(_HOMEPAGE_RELPATH)
_reg_op = _op_for(_REGISTER_RELPATH)
_songs_op = _op_for(_SONGS_RELPATH)
_about_op = _op_for(_ABOUT_RELPATH)


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


# --- Register page -------------------------------------------------------

_REGISTER_SELECTORS = (
    SelectorEntry(name="name_input", selector="#TxtName", role="textbox"),
    SelectorEntry(name="email_input", selector="#TxtEmail", role="textbox"),
    SelectorEntry(
        name="password_input",
        selector="#TxtPassword",
        role="textbox",
        attributes={"type": "password"},
    ),
    SelectorEntry(
        name="submit_button",
        selector="#submit-button",
        role="button",
        accessible_name="Submit",
    ),
)

_REGISTER_OPERATORS = (
    _reg_op(
        "swap_title",
        "swap_text",
        "<title>Willify | Register</title>",
        "<title>Willifing | Register</title>",
        "Document title changed.",
    ),
    _reg_op(
        "swap_register_heading",
        "swap_text",
        "<h1>Register Here!</h1>",
        "<h1>Register Now!</h1>",
        "Register heading text changed.",
    ),
    _reg_op(
        "rename_form_id",
        "rename_attr",
        'id="register-form"',
        'id="register-forms"',
        "Register form id renamed.",
    ),
    _reg_op(
        "rename_name_input_id",
        "rename_attr",
        'id="TxtName"',
        'id="TxtNames"',
        "Name input id renamed.",
    ),
    _reg_op(
        "rename_email_input_id",
        "rename_attr",
        'id="TxtEmail"',
        'id="TxtEmails"',
        "Email input id renamed.",
    ),
    _reg_op(
        "change_password_type",
        "rewrite_attr",
        'type="password"',
        'type="text"',
        "Password field no longer masks input.",
    ),
    _reg_op(
        "change_age_type",
        "rewrite_attr",
        'type="number"',
        'type="text"',
        "Age field no longer numeric.",
    ),
    _reg_op(
        "rename_submit_id",
        "rename_attr",
        'id="submit-button"',
        'id="submit-btn"',
        "Submit button id renamed.",
    ),
    _reg_op(
        "swap_submit_text",
        "swap_text",
        'id="submit-button">Submit</button>',
        'id="submit-button">Send</button>',
        "Submit button label changed.",
    ),
    _reg_op(
        "remove_male_radio",
        "remove_element",
        '<input type="radio" name="gender" id="male" value="Male"'
        ' class="link radio-input">',
        "",
        "Male gender radio removed.",
    ),
)

_REGISTER_BLUNT_OPERATORS = (
    _reg_op(
        "blank_submit",
        "remove_element",
        '<button type="submit" class="link show-modal"'
        ' id="submit-button">Submit</button>',
        "",
        "Blank submit button.",
    ),
    _reg_op(
        "blank_name_input",
        "remove_element",
        '<input type="text" name="" id="TxtName" class="input-box link">',
        "",
        "Blank name input.",
    ),
    _reg_op(
        "blank_email_input",
        "remove_element",
        '<input type="text" name="" id="TxtEmail" class="input-box link">',
        "",
        "Blank email input.",
    ),
    _reg_op(
        "blank_register_heading",
        "remove_element",
        "<h1>Register Here!</h1>",
        "<h1></h1>",
        "Blank register heading.",
    ),
)

WILLIFY_REGISTER = FeatureArea(
    name="willify_register",
    target_path="/src/html/register.html",
    reference_relpath=_REGISTER_RELPATH,
    spec_type="user_story",
    requirement_content=(
        "The Willify register page shows a form with Name, Email, masked "
        "Password and numeric Age fields, gender radios, and a 'Submit' "
        "button."
    ),
    selectors=_REGISTER_SELECTORS,
    operators=_REGISTER_OPERATORS,
    blunt_operators=_REGISTER_BLUNT_OPERATORS,
    oracle_suite=str(_ORACLE_DIR / "register_oracle.py"),
)


# --- Songs page ----------------------------------------------------------

_SONGS_SELECTORS = (
    SelectorEntry(
        name="songs_heading",
        selector=".hero-section h1",
        role="heading",
        accessible_name="Songs to Play",
    ),
    SelectorEntry(
        name="songs_subheading",
        selector=".hero-section h3",
        role="heading",
        accessible_name="Top Recommended Songs for You!",
    ),
    SelectorEntry(
        name="read_more_button",
        selector="#read-more-button",
        role="button",
        accessible_name="Read More",
        state={"visible": True},
    ),
)

_SONGS_OPERATORS = (
    _songs_op(
        "swap_title",
        "swap_text",
        "<title>Willify | Songs</title>",
        "<title>Willifing | Songs</title>",
        "Document title changed.",
    ),
    _songs_op(
        "swap_hero_heading",
        "swap_text",
        "<h1>Songs to Play</h1>",
        "<h1>Songs to Pause</h1>",
        "Songs hero heading changed.",
    ),
    _songs_op(
        "swap_hero_subheading",
        "swap_text",
        "<h3>Top Recommended Songs for You!</h3>",
        "<h3>Top Recommended Songs for Me!</h3>",
        "Songs hero subheading changed.",
    ),
    _songs_op(
        "remove_read_more_button",
        "remove_element",
        '<button id="read-more-button" class="link">Read More</button>',
        "",
        "Read More button removed.",
    ),
    _songs_op(
        "rename_read_more_button_id",
        "rename_attr",
        'id="read-more-button"',
        'id="read-more-btn"',
        "Read More button id renamed.",
    ),
    _songs_op(
        "rename_read_more_section_id",
        "rename_attr",
        'id="read-more-section"',
        'id="read-more-sections"',
        "Read-more section id renamed.",
    ),
    _songs_op(
        "rename_rnb_text_id",
        "rename_attr",
        'id="rnb-text"',
        'id="rnb-texts"',
        "R&B genre id renamed.",
    ),
    _songs_op(
        "rename_pop_text_id",
        "rename_attr",
        'id="pop-text"',
        'id="pop-texts"',
        "Pop genre id renamed.",
    ),
    _songs_op(
        "rename_kpop_text_id",
        "rename_attr",
        'id="kpop-text"',
        'id="kpop-texts"',
        "K-Pop genre id renamed.",
    ),
    _songs_op(
        "swap_first_song_title",
        "swap_text",
        "<h3>Tip Toe</h3>",
        "<h3>Tip Tap</h3>",
        "First song title changed.",
    ),
)

_SONGS_BLUNT_OPERATORS = (
    _songs_op(
        "blank_hero_heading",
        "remove_element",
        "<h1>Songs to Play</h1>",
        "<h1></h1>",
        "Blank songs hero heading.",
    ),
    _songs_op(
        "blank_hero_subheading",
        "remove_element",
        "<h3>Top Recommended Songs for You!</h3>",
        "<h3></h3>",
        "Blank songs hero subheading.",
    ),
    _songs_op(
        "blank_read_more_button",
        "remove_element",
        '<button id="read-more-button" class="link">Read More</button>',
        "",
        "Blank Read More button.",
    ),
)

WILLIFY_SONGS = FeatureArea(
    name="willify_songs",
    target_path="/src/html/songs.html",
    reference_relpath=_SONGS_RELPATH,
    spec_type="user_story",
    requirement_content=(
        "The Willify songs page shows the hero heading 'Songs to Play', a "
        "visible 'Read More' button, and R&B / Pop / K-Pop genre sections."
    ),
    selectors=_SONGS_SELECTORS,
    operators=_SONGS_OPERATORS,
    blunt_operators=_SONGS_BLUNT_OPERATORS,
    oracle_suite=str(_ORACLE_DIR / "songs_oracle.py"),
)


# --- About Us page -------------------------------------------------------

_ABOUT_SELECTORS = (
    SelectorEntry(
        name="about_heading",
        selector=".hero-section h1",
        role="heading",
        accessible_name="Who We Are?",
    ),
    SelectorEntry(
        name="about_subheading",
        selector=".hero-section h3",
        role="heading",
        accessible_name="Get to Know Willify",
    ),
    SelectorEntry(
        name="read_more_button",
        selector="#read-more-button",
        role="button",
        accessible_name="Read More",
        state={"visible": True},
    ),
    SelectorEntry(
        name="uvp_seamless",
        selector="#uvp-one",
        accessible_name="Seamless",
    ),
)

_ABOUT_OPERATORS = (
    _about_op(
        "swap_title",
        "swap_text",
        "<title>Willify | About Us</title>",
        "<title>Willifing | About Us</title>",
        "Document title changed.",
    ),
    _about_op(
        "swap_hero_heading",
        "swap_text",
        "<h1>Who We Are?</h1>",
        "<h1>Who Are We?</h1>",
        "About hero heading changed.",
    ),
    _about_op(
        "swap_hero_subheading",
        "swap_text",
        "<h3>Get to Know Willify</h3>",
        "<h3>Get to Know Willifing</h3>",
        "About hero subheading changed.",
    ),
    _about_op(
        "remove_read_more_button",
        "remove_element",
        '<button id="read-more-button" class="link">Read More</button>',
        "",
        "Read More button removed.",
    ),
    _about_op(
        "rename_read_more_button_id",
        "rename_attr",
        'id="read-more-button"',
        'id="read-more-btn"',
        "Read More button id renamed.",
    ),
    _about_op(
        "rename_biography_section_id",
        "rename_attr",
        'id="read-more-section"',
        'id="read-more-sections"',
        "Biography section id renamed.",
    ),
    _about_op(
        "swap_biography_heading",
        "swap_text",
        "<h1>What is Willify?</h1>",
        "<h1>What is Willifing?</h1>",
        "Biography heading changed.",
    ),
    _about_op(
        "swap_uvp_one",
        "swap_text",
        ">Seamless</h1>",
        ">Flawless</h1>",
        "UVP card text changed.",
    ),
    _about_op(
        "rename_uvp_one_id",
        "rename_attr",
        'id="uvp-one"',
        'id="uvp-1"',
        "UVP card id renamed.",
    ),
    _about_op(
        "swap_history_2006",
        "swap_text",
        "<h1>2006</h1>",
        "<h1>2007</h1>",
        "History year changed.",
    ),
    _about_op(
        "rename_history_one_id",
        "rename_attr",
        'id="history-one"',
        'id="history-1"',
        "History card id renamed.",
    ),
)

_ABOUT_BLUNT_OPERATORS = (
    _about_op(
        "blank_hero_heading",
        "remove_element",
        "<h1>Who We Are?</h1>",
        "<h1></h1>",
        "Blank about hero heading.",
    ),
    _about_op(
        "blank_hero_subheading",
        "remove_element",
        "<h3>Get to Know Willify</h3>",
        "<h3></h3>",
        "Blank about hero subheading.",
    ),
    _about_op(
        "blank_read_more_button",
        "remove_element",
        '<button id="read-more-button" class="link">Read More</button>',
        "",
        "Blank Read More button.",
    ),
    _about_op(
        "blank_biography_heading",
        "remove_element",
        "<h1>What is Willify?</h1>",
        "<h1></h1>",
        "Blank biography heading.",
    ),
)

WILLIFY_ABOUT = FeatureArea(
    name="willify_about",
    target_path="/src/html/about-us.html",
    reference_relpath=_ABOUT_RELPATH,
    spec_type="user_story",
    requirement_content=(
        "The Willify About Us page shows the hero heading 'Who We Are?', a "
        "visible 'Read More' button, a biography section, UVP cards, and a "
        "history timeline."
    ),
    selectors=_ABOUT_SELECTORS,
    operators=_ABOUT_OPERATORS,
    blunt_operators=_ABOUT_BLUNT_OPERATORS,
    oracle_suite=str(_ORACLE_DIR / "about_oracle.py"),
)


FEATURE_AREAS = {
    area.name: area
    for area in (
        WILLIFY_HOMEPAGE,
        WILLIFY_REGISTER,
        WILLIFY_SONGS,
        WILLIFY_ABOUT,
    )
}

_ROTATE_SENTINELS = {"", "rotate", "all", "random", None}


def get_feature_area(name) -> FeatureArea:
    """Return the catalogue entry for *name* (raises KeyError if unknown)."""
    return FEATURE_AREAS[name]


def select_feature_area(name=None, rng=None) -> FeatureArea:
    """Resolve a configured Feature Area, or pick one at random to rotate.

    A concrete catalogue name pins that area; a rotation sentinel
    (``""``/``"rotate"``/``"all"``/``"random"``/``None``) picks a random area
    each epoch (per ADR-0002). An unknown concrete name raises KeyError so
    config typos surface loudly.
    """
    if name not in _ROTATE_SENTINELS:
        return FEATURE_AREAS[name]
    return (rng or random).choice(list(FEATURE_AREAS.values()))


def load_reference_files(area: FeatureArea, reference_root) -> dict:
    """Read the area's mutatable file(s) from *reference_root* into a map."""
    root = Path(reference_root)
    return {
        area.reference_relpath: (root / area.reference_relpath).read_text(
            encoding="utf-8"
        )
    }
