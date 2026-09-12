import math
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

@dataclass
class BatteryStorageConfig:
    """Configuration parameters defining physical and economic BESS characteristics."""
    power_capacity_mw: float = 100.0          # Max charge/discharge rate (MW)
    energy_capacity_mwh: float = 400.0        # Rated usable energy storage capacity (MWh)
    round_trip_efficiency: float = 0.90       # AC-to-AC round-trip efficiency (0.90 = 90%)
    min_soc_pct: float = 10.0                 # Lower reserve limit to avoid deep-discharge degradation (%)
    max_soc_pct: float = 90.0                 # Upper limit to prevent overcharging stress (%)
    initial_soc_pct: float = 20.0             # Starting state of charge (%)
    degradation_cost_inr_per_kwh: float = 0.80 # Battery life wear cost per kWh cycled (INR)

    @property
    def one_way_charge_efficiency(self) -> float:
        """One-way charging efficiency sqrt(RTE)."""
        return math.sqrt(self.round_trip_efficiency)

    @property
    def one_way_discharge_efficiency(self) -> float:
        """One-way discharging efficiency sqrt(RTE)."""
        return math.sqrt(self.round_trip_efficiency)

    @property
    def min_energy_mwh(self) -> float:
        """Minimum allowable energy storage volume (MWh)."""
        return (self.min_soc_pct / 100.0) * self.energy_capacity_mwh

    @property
    def max_energy_mwh(self) -> float:
        """Maximum allowable energy storage volume (MWh)."""
        return (self.max_soc_pct / 100.0) * self.energy_capacity_mwh


class StateOfChargeTracker:
    """
    Simulates dynamic state of charge (SoC) evolution, conversion thermal losses,
    and cumulative cycle degradation.
    """

    def __init__(self, config: BatteryStorageConfig):
        self.config = config
        self.eta_c = config.one_way_charge_efficiency
        self.eta_d = config.one_way_discharge_efficiency
        self.min_e = config.min_energy_mwh
        self.max_e = config.max_energy_mwh

        # Initialize state
        self.current_energy_mwh = (config.initial_soc_pct / 100.0) * config.energy_capacity_mwh
        self.current_energy_mwh = max(self.min_e, min(self.max_e, self.current_energy_mwh))

        self.total_charged_mwh: float = 0.0
        self.total_discharged_mwh: float = 0.0
        self.thermal_losses_mwh: float = 0.0
        self.equivalent_full_cycles: float = 0.0

    @property
    def soc_pct(self) -> float:
        """Current state of charge percentage (0-100%)."""
        return (self.current_energy_mwh / self.config.energy_capacity_mwh) * 100.0

    def available_charge_headroom_mwh(self) -> float:
        """Energy in MWh that can be accepted before hitting max SoC."""
        net_headroom = max(0.0, self.max_e - self.current_energy_mwh)
        return net_headroom / self.eta_c  # In terms of input electrical energy

    def available_discharge_capacity_mwh(self) -> float:
        """Energy in MWh that can be extracted before hitting min SoC."""
        net_stored = max(0.0, self.current_energy_mwh - self.min_e)
        return net_stored * self.eta_d  # In terms of delivered electrical energy

    def step(
        self,
        charge_mw: float,
        discharge_mw: float,
        dt_hours: float = 1.0
    ) -> Dict[str, float]:
        """
        Execute one operational time step, updating energy stored and tracking losses.
        """
        charge_mw = max(0.0, min(self.config.power_capacity_mw, charge_mw))
        discharge_mw = max(0.0, min(self.config.power_capacity_mw, discharge_mw))

        # Enforce non-simultaneous charging and discharging
        if charge_mw > 0 and discharge_mw > 0:
            if charge_mw >= discharge_mw:
                charge_mw -= discharge_mw
                discharge_mw = 0.0
            else:
                discharge_mw -= charge_mw
                charge_mw = 0.0

        # Physical energy addition & extraction
        gross_energy_in = charge_mw * dt_hours
        net_energy_stored = gross_energy_in * self.eta_c

        gross_energy_out = discharge_mw * dt_hours
        net_energy_depleted = gross_energy_out / self.eta_d if self.eta_d > 0 else gross_energy_out

        # Check bounds
        projected_energy = self.current_energy_mwh + net_energy_stored - net_energy_depleted

        # Clamp to bounds and adjust actual flows if constrained
        if projected_energy > self.max_e:
            excess = projected_energy - self.max_e
            net_energy_stored -= excess
            gross_energy_in = net_energy_stored / self.eta_c
            charge_mw = gross_energy_in / dt_hours
            projected_energy = self.max_e
        elif projected_energy < self.min_e:
            deficit = self.min_e - projected_energy
            net_energy_depleted -= deficit
            gross_energy_out = net_energy_depleted * self.eta_d
            discharge_mw = gross_energy_out / dt_hours
            projected_energy = self.min_e

        # Thermal conversion loss = difference between grid flows and stored delta
        delta_stored = projected_energy - self.current_energy_mwh
        step_loss = max(0.0, (gross_energy_in - gross_energy_out) - delta_stored)

        # Update cumulative state
        self.current_energy_mwh = projected_energy
        self.total_charged_mwh += gross_energy_in
        self.total_discharged_mwh += gross_energy_out
        self.thermal_losses_mwh += step_loss
        self.equivalent_full_cycles = self.total_discharged_mwh / self.config.energy_capacity_mwh if self.config.energy_capacity_mwh > 0 else 0.0

        return {
            "effective_charge_mw": round(charge_mw, 3),
            "effective_discharge_mw": round(discharge_mw, 3),
            "stored_energy_mwh": round(self.current_energy_mwh, 3),
            "soc_pct": round(self.soc_pct, 2),
            "step_loss_mwh": round(step_loss, 3),
            "equivalent_full_cycles": round(self.equivalent_full_cycles, 4)
        }
