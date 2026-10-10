"""Tools for transparent virtual-fence pre-training simulations.

The headline API is re-exported here. Figure and animation helpers stay in their
own modules so that ``import vf_training`` never needs matplotlib.
"""

from .metrics import DaySummary, daily_summary, group_pulse_rate
from .model import (
    ARM_NAMES,
    Arm,
    Interaction,
    SimulationParameters,
    SimulationResult,
    simulate_group,
)
from .power import PowerResult, PowerScenario, estimate_power, minimum_attainable_p

__all__ = [
    "ARM_NAMES",
    "Arm",
    "DaySummary",
    "Interaction",
    "PowerResult",
    "PowerScenario",
    "SimulationParameters",
    "SimulationResult",
    "daily_summary",
    "estimate_power",
    "group_pulse_rate",
    "minimum_attainable_p",
    "simulate_group",
]
