from logging import getLogger
from pathlib import Path
from typing import Union

import numpy as np
import tomli
import tomli_w
from serial import Serial

__all__ = ["MotionDevice"]

# Interface for hardware devices- all subclasses must
# implement this!


class ConfigurableDevice:
    def __init__(
        self,
        name=None,
        configurations=None,
        config_file=None,
        serial_kwargs=None,
        **kwargs,
    ):
        self.serial_kwargs = serial_kwargs
        self.serial = Serial(**self.serial_kwargs)
        self.configurations = configurations
        self.config_file = config_file
        self.name = name
        self.logger = getLogger(self.__class__.__name__)

    @classmethod
    def from_config(__cls__, filename):
        with open(filename, "rb") as fh:
            parameters = tomli.load(fh)
        serial_kwargs = parameters.pop("serial", None)
        return __cls__(serial_kwargs=serial_kwargs, **parameters)

    def save_config(self, filename=None):
        if filename is None:
            filename = self.config_file
        path = Path(filename)

        config = {
            "name": self.name,
            "configurations": self.configurations,
            "serial": self.serial_kwargs,
        }
        config.update(self._config_extras())
        with path.open("wb") as fh:
            tomli_w.dump(config, fh)
        self.logger.info(f"saved configuration to {path.absolute()}")

    def _config_extras(self):
        raise NotImplementedError()

    def get_configurations(self):
        return self.configurations

    def set_configurations(self, value):
        self.configurations = value

    def get_name(self):
        return self.name

    def set_name(self, value: str):
        self.name = value


class MotionDevice(ConfigurableDevice):
    def __init__(
        self,
        unit=None,
        offset=0,
        **kwargs,
    ):
        super().__init__(self, **kwargs)
        self.unit = unit
        self.offset = offset
        self.position = None

    def get_unit(self):
        return self.unit

    def set_unit(self, value):
        self.unit = value

    def get_offset(self):
        return self.offset

    def set_offset(self, value):
        self.offset = value

    def _config_extras(self):
        return {"unit": self.unit, "offset": self.offset}

    def get_position(self):
        pos = self._get_position() + self.offset
        return pos

    def _get_position(self):
        raise NotImplementedError()

    def get_target_position(self):
        pos = self._get_target_position() + self.offset
        return pos

    def _get_target_position(self):
        raise NotImplementedError()

    def home(self, wait=False):
        raise NotImplementedError()

    def move_absolute(self, value, **kwargs):
        return self._move_absolute(value - self.offset, **kwargs)

    def _move_absolute(self, value, wait=False):
        raise NotImplementedError()

    def move_relative(self, value, wait=False):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def move_configuration_idx(self, idx: int, wait=False):
        for row in self.configurations:
            if row["idx"] == idx:
                return self.move_absolute(row["value"], wait=wait)
        raise ValueError(f"No configuration saved at index {idx}")

    def move_configuration_name(self, name: str, wait=False):
        for row in self.configurations:
            if row["name"] == name:
                return self.move_absolute(row["value"], wait=wait)
        raise ValueError(f"No configuration saved with name '{name}'")

    def get_configuration(self, tol=1e-1):
        position = self.get_position()
        for row in self.configurations:
            if np.abs(position - row["value"]) <= tol:
                return row["idx"], row["name"]
        return None, "Unknown"

    def save_configuration(self, index=None, name=None, tol=1e-1, **kwargs):
        position = self.get_position()
        current_config = self.get_configuration(tol=tol)
        if index is None:
            if current_config[0] is None:
                raise RuntimeError(
                    "Cannot save to an unknown configuration. Please provide index."
                )
            index = current_config[0]
            if name is None:
                name = current_config[1]

        # see if existing configuration
        for row in self.configurations:
            if row["idx"] == index:
                if name is not None:
                    row["name"] = name
                row["value"] = position
                self.logger.info(
                    f"updated configuration {index} '{row['name']}' to value {row['value']}"
                )
        else:
            if name is None:
                raise ValueError("Must provide name for new configuration")
            self.configurations.append(dict(idx=index, name=name, value=position))
            self.logger.info(
                f"added new configuration {index} '{name}' with value {position}"
            )

        # sort configurations dictionary in-place by index
        self.configurations.sort(key=lambda d: d["idx"])
        # save configurations to file
        self.save_config(**kwargs)
