import sys
from types import SimpleNamespace


class _Logging:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class _StubBase:
    def __init__(self, *args, **kwargs):
        pass


class _Synapse(_StubBase):
    def copy(self):
        return self


sys.modules.setdefault(
    "bittensor",
    SimpleNamespace(
        logging=_Logging(),
        Dendrite=_StubBase,
        MockSubtensor=_StubBase,
        Metagraph=_StubBase,
        Synapse=_Synapse,
        Axon=_StubBase,
        AxonInfo=_StubBase,
        Subtensor=_StubBase,
        Wallet=_StubBase,
        MockWallet=_StubBase,
    ),
)

import numpy as np
import pytest

from neurons import validator as validator_module
from neurons.validator import Validator
from template.base.validator import BaseValidatorNeuron
from verification.plagiarism import FirstSubmitterRegistry
from verification.static_gate import GateResult
from verification.weighting import to_weights


class ConcreteValidator(BaseValidatorNeuron):
    async def forward(self):
        return None


VALID_PLAYWRIGHT_SCRIPT = """
from playwright.sync_api import Page, expect


def test_home(page: Page):
    page.goto("/")
    expect(page.locator("h1")).to_be_visible()
"""


class Completed:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


def make_validator(tmp_path):
    validator = Validator.__new__(Validator)
    validator.config = SimpleNamespace(neuron=SimpleNamespace(full_path=str(tmp_path)))
    validator.first_submitter_registry = FirstSubmitterRegistry()
    return validator


def test_static_gate_short_circuits_before_pytest(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    calls = []

    monkeypatch.setattr(
        validator_module,
        "analyze",
        lambda script: GateResult(False, ("disallowed import: subprocess",)),
    )
    monkeypatch.setattr(
        validator_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert validator.evaluate_miner(VALID_PLAYWRIGHT_SCRIPT) == 0.0
    assert calls == []


def test_evaluate_miner_uses_real_scoring_and_efficiency(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    calls = []

    monkeypatch.setattr(
        validator_module,
        "analyze",
        lambda script: GateResult(True, ()),
    )

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs["env"]["TARGET_URL"]))
        return Completed(0 if len(calls) == 1 else 1)

    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)
    perf_times = iter([100.0, 112.0])
    monkeypatch.setattr(validator_module.time, "perf_counter", lambda: next(perf_times))

    score = validator.evaluate_miner(VALID_PLAYWRIGHT_SCRIPT)

    assert score == pytest.approx(0.964)
    assert calls == [
        (
            [
                "pytest",
                calls[0][0][1],
                "--tb=short",
                "--browser",
                "chromium",
            ],
            "http://localhost:8080",
        ),
        (
            [
                "pytest",
                calls[1][0][1],
                "--tb=short",
                "--browser",
                "chromium",
            ],
            "http://localhost:8081",
        ),
    ]


def test_cross_epoch_duplicate_is_zeroed_before_scoring(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    validator.first_submitter_registry.register(
        "first-hotkey", VALID_PLAYWRIGHT_SCRIPT, 1.0
    )

    calls = []
    monkeypatch.setattr(
        validator_module,
        "analyze",
        lambda script: GateResult(True, ()),
    )
    monkeypatch.setattr(
        validator_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert (
        validator.evaluate_miner(VALID_PLAYWRIGHT_SCRIPT, submitter_id="second-hotkey")
        == 0.0
    )
    assert calls == []


def test_blunt_killer_survivor_scores_zero(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    calls = []
    monkeypatch.setattr(
        validator_module,
        "analyze",
        lambda script: GateResult(True, ()),
    )

    def fake_run(cmd, **kwargs):
        calls.append(kwargs["env"]["TARGET_URL"])
        return Completed(0)

    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)
    perf_times = iter([1.0, 2.0])
    monkeypatch.setattr(validator_module.time, "perf_counter", lambda: next(perf_times))

    score = validator.evaluate_miner(
        VALID_PLAYWRIGHT_SCRIPT, blunt_killer_url="http://localhost:8099"
    )

    assert score == 0.0
    assert calls == ["http://localhost:8080", "http://localhost:8099"]


def test_mutant_horde_counts_multiple_admitted_mutants(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    monkeypatch.setattr(
        validator_module,
        "analyze",
        lambda script: GateResult(True, ()),
    )
    returncodes = iter([0, 1, 0, 1])
    seen_urls = []

    def fake_run(cmd, **kwargs):
        seen_urls.append(kwargs["env"]["TARGET_URL"])
        return Completed(next(returncodes))

    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)
    perf_times = iter([100.0, 101.0])
    monkeypatch.setattr(validator_module.time, "perf_counter", lambda: next(perf_times))

    score = validator.evaluate_miner(
        VALID_PLAYWRIGHT_SCRIPT,
        mutant_urls=[
            "http://localhost:8081",
            "http://localhost:8082",
            "http://localhost:8083",
        ],
    )

    assert score == pytest.approx(2 / 3)
    assert seen_urls == [
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:8083",
    ]


def test_weighting_survives_ema_and_l1_normalization():
    neuron = ConcreteValidator.__new__(ConcreteValidator)
    neuron.config = SimpleNamespace(neuron=SimpleNamespace(moving_average_alpha=0.5))
    neuron.scores = np.zeros(4, dtype=np.float32)

    rewards = np.array([0.1, 0.2, 0.3, 1.0], dtype=np.float32)
    expected_epoch_weights = to_weights(rewards)

    neuron.update_scores(rewards, np.array([0, 1, 2, 3]))
    l1_weights = neuron.scores / np.linalg.norm(neuron.scores, ord=1)

    assert l1_weights == pytest.approx(expected_epoch_weights)
    assert l1_weights[-1] > 0.98


def test_first_submitter_registry_persists_with_validator_state(tmp_path):
    neuron = ConcreteValidator.__new__(ConcreteValidator)
    neuron.config = SimpleNamespace(neuron=SimpleNamespace(full_path=str(tmp_path)))
    neuron.step = 7
    neuron.scores = np.array([0.25, 0.75], dtype=np.float32)
    neuron.hotkeys = ["first-hotkey", "second-hotkey"]
    neuron.first_submitter_registry = FirstSubmitterRegistry()
    neuron.first_submitter_registry.register(
        "first-hotkey", VALID_PLAYWRIGHT_SCRIPT, 1.0
    )

    neuron.save_state()

    restored = ConcreteValidator.__new__(ConcreteValidator)
    restored.config = neuron.config
    restored.load_state()

    assert restored.step == 7
    assert restored.scores == pytest.approx([0.25, 0.75])
    assert restored.hotkeys == ["first-hotkey", "second-hotkey"]
    assert (
        restored.first_submitter_registry.first_submitter(VALID_PLAYWRIGHT_SCRIPT)
        == "first-hotkey"
    )
