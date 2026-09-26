"""The swap point - adapter_factory.get_adapter() and the InverterAdapter interface.

mock_cloud_adapter, bridge_adapter and sma_adapter are other people's modules (Gina, Matthew,
stretch) and are not written yet. The routing tests put a stand-in module into sys.modules
under the real name, so they test the factory's wiring without anyone stubbing a teammate's
file in src/. Once the real module lands the stand-in still shadows it here; its own test
file is where the real class gets exercised.
"""
import sys
import types

import pytest

import adapter_factory
from adapter import InverterAdapter
from victron_adapter import VictronAdapter

PENDING = [
    ("mock_cloud", "mock_cloud_adapter", "MockCloudAdapter"),
    ("bridge", "bridge_adapter", "BridgeAdapter"),
    ("sma", "sma_adapter", "SmaAdapter"),
]

COMMAND = {
    "command_id": "c3f1a2b4-7d9e-4c8a-9f01-2b3c4d5e6f70",
    "command": "set_power_limit_pct",
    "value": 60,
    "site_id": "demo_site_001",
    "requested_at": "2026-11-10T19:05:00Z",
    "dry_run": False,
}


def install_standin(monkeypatch, module_name, class_name):
    cls = type(class_name, (InverterAdapter,), {
        "name": module_name,
        "pull": lambda self: {},
        "push": lambda self, command: {},
    })
    module = types.ModuleType(module_name)
    setattr(module, class_name, cls)
    monkeypatch.setitem(sys.modules, module_name, module)
    return cls


@pytest.mark.parametrize("vendor,module_name,class_name", PENDING)
def test_vendor_returns_its_adapter(monkeypatch, vendor, module_name, class_name):
    cls = install_standin(monkeypatch, module_name, class_name)
    monkeypatch.setenv("INVERTER_VENDOR", vendor)
    got = adapter_factory.get_adapter()
    assert type(got) is cls
    assert isinstance(got, InverterAdapter)


def test_default_is_mock_cloud(monkeypatch):
    cls = install_standin(monkeypatch, "mock_cloud_adapter", "MockCloudAdapter")
    monkeypatch.delenv("INVERTER_VENDOR", raising=False)
    assert type(adapter_factory.get_adapter()) is cls


def test_value_is_trimmed_and_case_insensitive(monkeypatch):
    cls = install_standin(monkeypatch, "bridge_adapter", "BridgeAdapter")
    monkeypatch.setenv("INVERTER_VENDOR", "  Bridge ")
    assert type(adapter_factory.get_adapter()) is cls


@pytest.mark.parametrize("bad", ["solaredge", "", "mock-cloud"])
def test_unknown_vendor_raises_value_error(monkeypatch, bad):
    monkeypatch.setenv("INVERTER_VENDOR", bad)
    with pytest.raises(ValueError, match="unknown INVERTER_VENDOR"):
        adapter_factory.get_adapter()


def test_unwritten_adapter_says_which_file_is_missing(monkeypatch):
    monkeypatch.delitem(sys.modules, "sma_adapter", raising=False)
    monkeypatch.setenv("INVERTER_VENDOR", "sma")
    with pytest.raises(ModuleNotFoundError, match="src/sma_adapter.py"):
        adapter_factory.get_adapter()


def test_victron_is_returned_and_refuses_to_push(monkeypatch):
    monkeypatch.setenv("INVERTER_VENDOR", "victron")
    got = adapter_factory.get_adapter()
    assert isinstance(got, VictronAdapter)
    with pytest.raises(NotImplementedError):
        got.push(COMMAND)
    with pytest.raises(NotImplementedError):
        got.pull()


def test_interface_cannot_be_half_implemented():
    class PullOnly(InverterAdapter):
        def pull(self):
            return {}

    with pytest.raises(TypeError):
        PullOnly()
