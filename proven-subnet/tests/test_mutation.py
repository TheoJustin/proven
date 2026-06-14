"""Tests for verification.mutation — Mutation Engine + blunt killer."""

from verification.mutation import (
    Operator,
    apply_operators,
    blunt_killer,
    generate_mutants,
)

_REF = {
    "page.html": (
        "<title>App</title>"
        '<h1 id="hero">Welcome</h1>'
        '<button id="go">Go</button>'
        '<a href="next.html" id="next">Next</a>'
    )
}

_OPS = [
    Operator(
        "rename_hero",
        "rename_attr",
        "page.html",
        'id="hero"',
        'id="heroes"',
        "rename hero id",
    ),
    Operator(
        "swap_welcome",
        "swap_text",
        "page.html",
        ">Welcome<",
        ">Goodbye<",
        "swap welcome text",
    ),
    Operator(
        "remove_go",
        "remove_element",
        "page.html",
        '<button id="go">Go</button>',
        "",
        "remove go button",
    ),
    Operator(
        "rewrite_next",
        "rewrite_href",
        "page.html",
        'href="next.html"',
        'href="wrong.html"',
        "rewrite next href",
    ),
]


def test_generate_is_deterministic_for_seed():
    a = generate_mutants(_REF, _OPS, seed=7, n=3)
    b = generate_mutants(_REF, _OPS, seed=7, n=3)
    assert [m.name for m in a] == [m.name for m in b]


def test_generate_changes_html_and_only_touched_files():
    mutants = generate_mutants(_REF, _OPS, seed=1, n=4)
    assert len(mutants) == 4
    for m in mutants:
        assert set(m.files) == {"page.html"}
        assert m.files["page.html"] != _REF["page.html"]


def test_different_seeds_can_differ():
    orders = {
        tuple(m.name for m in generate_mutants(_REF, _OPS, seed=s, n=4))
        for s in range(10)
    }
    assert len(orders) > 1


def test_n_caps_and_excess_returns_all_eligible():
    assert len(generate_mutants(_REF, _OPS, seed=1, n=2)) == 2
    assert len(generate_mutants(_REF, _OPS, seed=1, n=99)) == 4


def test_inapplicable_operator_skipped():
    op = Operator(
        "missing", "swap_text", "page.html", "NOPE", "x", "no anchor"
    )
    assert generate_mutants(_REF, [op], seed=1, n=1) == []


def test_apply_operators_composes():
    out = apply_operators(_REF, _OPS)["page.html"]
    assert 'id="heroes"' in out
    assert ">Goodbye<" in out
    assert '<button id="go">' not in out
    assert 'href="wrong.html"' in out


def test_blunt_killer_blanks_targets():
    blank = [
        Operator(
            "blank_hero",
            "remove_element",
            "page.html",
            '<h1 id="hero">Welcome</h1>',
            "",
            "remove hero",
        ),
        Operator(
            "blank_go",
            "remove_element",
            "page.html",
            '<button id="go">Go</button>',
            "",
            "remove go",
        ),
    ]
    bk = blunt_killer(_REF, blank)
    assert bk.operator == "blunt_killer"
    out = bk.files["page.html"]
    assert "Welcome" not in out
    assert '<button id="go">' not in out


# ---------------------------------------------------------------------------
# operator library: each operator type produces an observable diff
# ---------------------------------------------------------------------------


def _apply_one(content, kind, find, replace, target="p.html"):
    op = Operator("op", kind, target, find, replace, "")
    return apply_operators({target: content}, [op])[target]


def test_operator_attribute_rename():
    out = _apply_one('<div id="a">x</div>', "rename_attr", 'id="a"', 'id="b"')
    assert 'id="b"' in out and 'id="a"' not in out


def test_operator_attribute_removal():
    out = _apply_one(
        '<a href="x.html" class="c">L</a>',
        "remove_attr",
        ' href="x.html"',
        "",
    )
    assert "href" not in out


def test_operator_href_rewrite():
    out = _apply_one(
        '<a href="x.html">L</a>',
        "rewrite_href",
        'href="x.html"',
        'href="y.html"',
    )
    assert 'href="y.html"' in out


def test_operator_target_rewrite():
    out = _apply_one(
        '<a target="_self">L</a>',
        "rewrite_target",
        'target="_self"',
        'target="_blank"',
    )
    assert 'target="_blank"' in out


def test_operator_element_removal():
    out = _apply_one(
        '<button id="g">Go</button>',
        "remove_element",
        '<button id="g">Go</button>',
        "",
    )
    assert "<button" not in out


def test_operator_text_swap():
    out = _apply_one("<h1>Hello</h1>", "swap_text", ">Hello<", ">Bye<")
    assert ">Bye<" in out


def test_operator_js_logic_flip():
    out = _apply_one(
        "if (width >= 1000) { big(); }",
        "js_logic_flip",
        ">= 1000",
        "< 1000",
        target="app.js",
    )
    assert "< 1000" in out and ">= 1000" not in out
