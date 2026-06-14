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

# neurons.validator imports torch only for forward()'s tensor bookkeeping, which
# these funnel tests don't exercise; a light stub keeps the import torch-free.
sys.modules.setdefault(
    "torch",
    SimpleNamespace(
        zeros=lambda *a, **k: [0.0] * (a[0] if a else 0),
        tensor=lambda *a, **k: list(a[0]) if a else [],
        long=int,
    ),
)

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from neurons import validator as validator_module  # noqa: E402
from neurons.validator import Validator  # noqa: E402
from template.base.validator import BaseValidatorNeuron  # noqa: E402
from verification.plagiarism import FirstSubmitterRegistry  # noqa: E402
from verification.static_gate import GateResult  # noqa: E402
from verification.weighting import to_weights  # noqa: E402


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
    validator.config = SimpleNamespace(
        neuron=SimpleNamespace(full_path=str(tmp_path))
    )
    validator.first_submitter_registry = FirstSubmitterRegistry()
    return validator


def make_fake_run(returncodes):
    """Return (fake_run, calls) where fake_run keys off env['TARGET_URL']."""
    calls = []

    def fake_run(cmd, **kwargs):
        url = kwargs["env"]["TARGET_URL"]
        calls.append(url)
        return Completed(returncodes.get(url, 1))

    return fake_run, calls


def _pass_gate(monkeypatch):
    monkeypatch.setattr(
        validator_module, "analyze", lambda script: GateResult(True, ())
    )


def _fixed_reference_time(monkeypatch, seconds=5.0):
    perf = iter([100.0, 100.0 + seconds])
    monkeypatch.setattr(
        validator_module.time, "perf_counter", lambda: next(perf)
    )


REF = "http://ref"
BK = "http://blunt-killer"
MUTS = ["http://m1", "http://m2", "http://m3"]


def test_full_funnel_scores_genuine_miner(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    _pass_gate(monkeypatch)
    returncodes = {REF: 0, BK: 1, **{u: 1 for u in MUTS}}  # passes, kills all
    fake_run, calls = make_fake_run(returncodes)
    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)
    _fixed_reference_time(monkeypatch, seconds=5.0)  # within soft budget

    score = validator.evaluate_miner(
        VALID_PLAYWRIGHT_SCRIPT,
        reference_url=REF,
        blunt_killer_url=BK,
        mutant_urls=MUTS,
    )

    assert score == pytest.approx(1.0)  # P_clean=1, K/N=1, E_i=1
    assert calls == [REF, BK] + MUTS  # reference, trap, then the horde


def test_tautology_trap_zeroes_happy_path_ghost(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    _pass_gate(monkeypatch)
    # Ghost passes on the clean app AND on the blunt killer.
    fake_run, calls = make_fake_run({REF: 0, BK: 0})
    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)
    _fixed_reference_time(monkeypatch)

    score = validator.evaluate_miner(
        VALID_PLAYWRIGHT_SCRIPT,
        reference_url=REF,
        blunt_killer_url=BK,
        mutant_urls=MUTS,
    )

    assert score == 0.0
    assert calls == [REF, BK]  # horde never runs once trapped


def test_reference_gate_false_positive_zeroes(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    _pass_gate(monkeypatch)
    fake_run, calls = make_fake_run({REF: 1})  # fails the clean app
    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)
    _fixed_reference_time(monkeypatch)

    score = validator.evaluate_miner(
        VALID_PLAYWRIGHT_SCRIPT,
        reference_url=REF,
        blunt_killer_url=BK,
        mutant_urls=MUTS,
    )

    assert score == 0.0
    assert calls == [REF]  # nothing runs after a false positive


def test_partial_kills_scale_score(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    _pass_gate(monkeypatch)
    # Kills m1 and m3, misses m2 -> 2/3.
    returncodes = {
        REF: 0,
        BK: 1,
        "http://m1": 1,
        "http://m2": 0,
        "http://m3": 1,
    }
    fake_run, _calls = make_fake_run(returncodes)
    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)
    _fixed_reference_time(monkeypatch)

    score = validator.evaluate_miner(
        VALID_PLAYWRIGHT_SCRIPT,
        reference_url=REF,
        blunt_killer_url=BK,
        mutant_urls=MUTS,
    )

    assert score == pytest.approx(2.0 / 3.0)


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


def test_cross_epoch_duplicate_is_zeroed_before_scoring(monkeypatch, tmp_path):
    validator = make_validator(tmp_path)
    validator.first_submitter_registry.register(
        "first-hotkey", VALID_PLAYWRIGHT_SCRIPT, 1.0
    )

    calls = []
    _pass_gate(monkeypatch)
    monkeypatch.setattr(
        validator_module.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert (
        validator.evaluate_miner(
            VALID_PLAYWRIGHT_SCRIPT, submitter_id="second-hotkey"
        )
        == 0.0
    )
    assert calls == []


def test_weighting_survives_ema_and_l1_normalization():
    neuron = ConcreteValidator.__new__(ConcreteValidator)
    neuron.config = SimpleNamespace(
        neuron=SimpleNamespace(moving_average_alpha=0.5)
    )
    neuron.scores = np.zeros(4, dtype=np.float32)

    rewards = np.array([0.1, 0.2, 0.3, 1.0], dtype=np.float32)
    expected_epoch_weights = to_weights(rewards)

    neuron.update_scores(rewards, np.array([0, 1, 2, 3]))
    l1_weights = neuron.scores / np.linalg.norm(neuron.scores, ord=1)

    assert l1_weights == pytest.approx(expected_epoch_weights)
    assert l1_weights[-1] > 0.98


def test_first_submitter_registry_persists_with_validator_state(tmp_path):
    neuron = ConcreteValidator.__new__(ConcreteValidator)
    neuron.config = SimpleNamespace(
        neuron=SimpleNamespace(full_path=str(tmp_path))
    )
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
        restored.first_submitter_registry.first_submitter(
            VALID_PLAYWRIGHT_SCRIPT
        )
        == "first-hotkey"
    )
