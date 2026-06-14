"""Tests for verification.oracle — admission filter."""

import pytest

from verification.oracle import admit


def _oracle(passing):
    passing = set(passing)
    return lambda url: url in passing


def test_admits_killable_drops_equivalent():
    ref = "http://ref"
    candidates = [("m1", "http://m1"), ("m2", "http://m2")]
    # Reference passes; m2 still passes (equivalent); m1 is killed.
    run = _oracle({ref, "http://m2"})
    assert admit(candidates, run, ref) == [("m1", "http://m1")]


def test_all_killable_admitted_in_order():
    ref = "http://ref"
    candidates = [("m1", "http://m1"), ("m2", "http://m2")]
    run = _oracle({ref})  # only the reference passes
    assert admit(candidates, run, ref) == candidates


def test_none_admitted_when_all_equivalent():
    ref = "http://ref"
    candidates = [("m1", "http://m1")]
    run = _oracle({ref, "http://m1"})
    assert admit(candidates, run, ref) == []


def test_raises_when_reference_fails():
    run = _oracle(set())
    with pytest.raises(RuntimeError):
        admit([("m1", "http://m1")], run, "http://ref")
