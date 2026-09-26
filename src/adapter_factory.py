"""The single swap point: INVERTER_VENDOR in .env picks the adapter.

Vendor modules are imported lazily, only when selected, so a missing or broken adapter for
one vendor cannot stop the others from loading. Call get_adapter() once at startup: an
unknown vendor must fail there (command_contract.md section 5), not at the first command.
"""
import importlib
import os

# INVERTER_VENDOR value -> (module in src/, class name)
ADAPTERS = {
    "mock_cloud": ("mock_cloud_adapter", "MockCloudAdapter"),  # Gina
    "bridge": ("bridge_adapter", "BridgeAdapter"),             # Matthew
    "sma": ("sma_adapter", "SmaAdapter"),                      # stretch
    "victron": ("victron_adapter", "VictronAdapter"),          # stub, raises
}


def get_adapter():
    vendor = os.getenv("INVERTER_VENDOR", "mock_cloud").strip().lower()
    if vendor not in ADAPTERS:
        raise ValueError(
            f"unknown INVERTER_VENDOR={vendor!r}; expected one of {sorted(ADAPTERS)}"
        )
    module_name, class_name = ADAPTERS[vendor]
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name != module_name:
            raise  # the adapter exists but one of ITS imports is missing - show that
        raise ModuleNotFoundError(
            f"INVERTER_VENDOR={vendor} needs src/{module_name}.py, which is not written yet"
        ) from e
    return getattr(module, class_name)()
