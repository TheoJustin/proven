"""E2ETestingSynapse protocol contract — feature_area threading.

template.protocol imports bittensor at module load, so stub it (and torch, since
importing the template package pulls the base neuron). Assertions use setattr +
class defaults so they hold regardless of the stubbed Synapse __init__.
"""

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
sys.modules.setdefault(
    "torch",
    SimpleNamespace(
        zeros=lambda *a, **k: [0.0] * (a[0] if a else 0),
        tensor=lambda *a, **k: list(a[0]) if a else [],
        long=int,
    ),
)

from template.protocol import E2ETestingSynapse  # noqa: E402


def test_feature_area_is_a_declared_field_with_default():
    assert "feature_area" in E2ETestingSynapse.__annotations__
    assert E2ETestingSynapse.feature_area == ""


def test_existing_spec_fields_still_present():
    syn = E2ETestingSynapse()
    assert syn.spec_type == ""
    assert syn.requirement_content == ""
    assert syn.target_url == "http://localhost:8080"
    assert syn.selector_manifest is None
    assert syn.playwright_script is None


def test_deserialize_round_trips_feature_area_and_fields():
    syn = E2ETestingSynapse()
    syn.spec_type = "user_story"
    syn.feature_area = "willify_homepage"
    syn.selector_manifest = {
        "feature_area": "willify_homepage",
        "elements": [],
    }

    out = syn.deserialize()

    assert out is syn
    assert out.feature_area == "willify_homepage"
    assert out.spec_type == "user_story"
    assert out.selector_manifest["feature_area"] == "willify_homepage"
