from typing import Union

import numpy as np
import tomli

from device_control.drivers.conex import CONEXDevice
from device_control.drivers.zaber import ZaberDevice

__all__ = ["MultiDevice"]


class MultiDevice:
    def __init__(self, devices: dict, name="", configurations=None, config_file=None):
        self._devices = devices
        self._name = name
        self._configurations = configurations
        self.current_config = None
        self.config_file = config_file

    @property
    def configurations(self):
        return self._configurations

    @configurations.setter
    def configurations(self, value):
        self._configurations = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def devices(self):
        return self._devices

    @devices.setter
    def devices(self, value):
        self._devices = value
        for key, value in self._devices.items():
            setattr(self, key, value)

    @classmethod
    def from_config(__cls__, filename):
        with open(filename, "rb") as fh:
            parameters = tomli.load(fh)
        name = parameters["name"]
        devices = {}
        for device_name, device_config in parameters[name].items():
            dev_name = f"{name}_{device_name}"
            dev_type = device_config.pop("type")
            if dev_type.lower() == "conex":
                device = CONEXDevice(
                    name=dev_name, config_file=filename, **device_config
                )
            elif dev_type.lower() == "zaber":
                device = ZaberDevice(
                    name=dev_name, config_file=filename, **device_config
                )
            else:
                raise ValueError(
                    f"motion stage type not recognized: {device_config['type']}"
                )
            devices[device_name] = device

        configurations = parameters.get("configurations", None)
        return __cls__(
            devices, name=name, configurations=configurations, config_file=filename
        )

    def load_config(self, filename=None):
        if filename is None:
            filename = self.config_file
        with open(filename, "rb") as fh:
            parameters = tomli.load(fh)
        self.name = parameters["name"]
        self.devices = {}
        for device_name, device_config in parameters[self.name].items():
            dev_name = f"{self.name}_{device_name}"
            dev_type = device_config["type"].lower()
            if dev_type == "conex":
                device = CONEXDevice(
                    name=dev_name, config_file=filename, **device_config
                )
            elif dev_type == "zaber":
                device = ZaberDevice(
                    name=dev_name, config_file=filename, **device_config
                )
            else:
                raise ValueError(
                    f"motion stage type not recognized: {device_config['type']}"
                )
            self.devices[device_name] = device

        self._configurations = parameters.get("configurations", None)
        self.config_file = filename

    def stop(self):
        for device in self.devices:
            device.stop()

    def move_configuration(self, index: Union[int, str], wait=False):
        if self.configurations is None:
            raise ValueError("No configurations saved")
        if isinstance(index, int):
            return self.move_configuration_idx(index, wait=wait)
        elif isinstance(index, str):
            return self.move_configuration_name(index, wait=wait)

    def move_configuration_idx(self, idx: int, wait=False):
        for row in self.configurations:
            if row["idx"] == idx:
                self.current_config = row["value"]
                break
        else:
            raise ValueError(f"No configuration saved at index {idx}")
        for dev_name, value in self.current_config.items():
            # TODO async wait
            self.devices[dev_name].move_absolute(value, wait=wait)

    def move_configuration_name(self, name: str, wait=False):
        for row in self.configurations:
            if row["name"] == name:
                self.current_config = row["value"]
                break
        else:
            raise ValueError(f"No configuration saved with name '{name}'")
        for dev_name, value in self.current_config.items():
            # TODO async wait
            self.devices[dev_name].move_absolute(value, wait=wait)

    def get_configuration(self, tol=1e-1):
        values = {k: dev.position for k, dev in self.devices.items()}
        for row in self.configurations:
            match = True
            for key, val in values.items():
                match = match and np.abs(row["value"][key] - val) <= tol
            if match:
                return row["idx"], row["name"]
        return None, "Unknown"
