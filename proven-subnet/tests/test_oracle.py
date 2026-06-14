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


def test_admitted_set_is_a_fully_killable_ceiling():
    # m1/m3 are oracle-killable; m2 is equivalent (oracle still passes).
    ref = "http://ref"
    candidates = [("m1", "u1"), ("m2", "u2"), ("m3", "u3")]
    run = _oracle({ref, "u2"})

    admitted = admit(candidates, run, ref)
    n_mut = len(admitted)
    # A miner whose coverage matches the oracle kills exactly the admitted set.
    kills = sum(1 for _mutant, url in admitted if not run(url))

    assert n_mut == 2
    assert kills == n_mut  # K_i / N_mut == 1 is achievable
