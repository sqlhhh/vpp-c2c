"""The one interface every inverter adapter implements.

Nothing upstream of an adapter (poller, originator, dashboard) may import a vendor module.
They call adapter_factory.get_adapter() and talk to whatever comes back through these two
methods. That is what makes "any brand fits" true: a new vendor is one new subclass plus one
line in the factory, and nothing else in the repo changes.

Shapes are fixed by the contracts, not by this file:
  pull()  -> the 11-field reading in docs/team1_contract.md section 4
  push()  -> takes a docs/command_contract.md section 2 command,
             returns a section 3 result
"""
from abc import ABC, abstractmethod


class InverterAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def pull(self) -> dict:
        """Return one reading in the 11-field schema of team1_contract.md section 4."""

    @abstractmethod
    def push(self, command: dict) -> dict:
        """Accept a command_contract.md command; return a command_contract.md result.

        Never raises: a failed write is a result with success false and the reason in detail.
        """
