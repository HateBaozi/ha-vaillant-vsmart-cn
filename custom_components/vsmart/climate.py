"""Climate platform support."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_HALVES,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VSmartUpdateCoordinator
from .vsmart import TemperatureUnit
from .const import DOMAIN
from .entity import VSmartEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities."""
    coordinator: VSmartUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        VSmartThermostat(coordinator, config_entry, device_id)
        for device_id in coordinator.data.keys()
    ]
    async_add_entities(entities)


class VSmartThermostat(VSmartEntity, ClimateEntity):
    """The main thermostat entity for a spa."""

    _attr_name = "VSmart Thermostat"
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_precision = PRECISION_HALVES
    _attr_target_temperature_step = 0.5
    _attr_max_temp = 30
    _attr_min_temp = 5

    def __init__(
        self,
        coordinator: VSmartUpdateCoordinator,
        config_entry: ConfigEntry,
        device_id: str,
    ) -> None:
        """Initialize thermostat."""
        super().__init__(coordinator, config_entry, device_id)
        self._attr_unique_id = f"{device_id}_thermostat"

    @property
    def supported_features(self):
        return self._attr_supported_features

    @property
    def hvac_mode(self) -> HVACMode | str | None:
        """Return the current mode (HEAT or OFF)."""
        if not self.device_status:
            return None
        return HVACMode.HEAT if self.device_status.heat_power else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | str | None:
        """Return the current running action (HEATING or IDLE)."""
        if not self.device_status:
            return None
        heat_on = self.device_status.heat_power
        return (
            HVACAction.HEATING if (heat_on and self.device_status.heat_temp_now < self.device_status.heat_temp_set) else HVACAction.IDLE
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if not self.device_status:
            return None
        return self.device_status.heat_temp_now

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if not self.device_status:
            return None
        return self.device_status.heat_temp_set

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        if (
            not self.device_status
            or self.device_status.temp_set_unit == TemperatureUnit.CELSIUS
        ):
            return str(TEMP_CELSIUS)
        else:
            return str(TEMP_FAHRENHEIT)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        should_heat = True if hvac_mode == HVACMode.HEAT else False
        await self.coordinator.api.set_heat(self.device_id, should_heat)
        await self.coordinator.async_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature."""
        target_temperature = kwargs.get(ATTR_TEMPERATURE)
        if target_temperature is None:
            return

        await self.coordinator.api.set_heat_temp(self.device_id, target_temperature)
        await self.coordinator.async_refresh()
