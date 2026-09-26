"""Victron - deliberately NOT built.

Victron's remote path is the VRM portal, which speaks MQTT (read and write over the VRM
broker), not the REST poll-and-POST shape our other two adapters have. Building it means a
second transport inside an adapter, and we have no VRM account or Victron hardware to test
against. It exists so INVERTER_VENDOR=victron fails loudly and says why, instead of looking
like a typo. See docs/command_contract.md section 6.
"""
from adapter import InverterAdapter


class VictronAdapter(InverterAdapter):
    name = "victron"

    def pull(self) -> dict:
        raise NotImplementedError("Victron (VRM MQTT) adapter is not built - no account, no hardware")

    def push(self, command: dict) -> dict:
        raise NotImplementedError("Victron (VRM MQTT) adapter is not built - no account, no hardware")
