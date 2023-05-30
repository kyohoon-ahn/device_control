import astropy.units as u
import click
import tomli
from serial import Serial

from device_control.base import ConfigurableDevice
from swmain.redis import update_keys


class ArduinoError(RuntimeError):
    pass


class ArduinoTimeoutError(ArduinoError):
    pass


class VAMPIRESTrigger(ConfigurableDevice):
    def __init__(
        self,
        serial_kwargs,
        reset_port,
        delay: int = 0,  # us
        pulse_width: int = 10,  # us
        flc_offset: int = 20,  # us
        flc_enabled: bool = True,
        sweep_mode: bool = False,
        **kwargs,
    ):
        serial_kwargs = dict(
            {"baudrate": 115200, "timeout": 0.1, "write_timeout": 0.5},
            **serial_kwargs,
        )
        super().__init__(serial_kwargs=serial_kwargs, **kwargs)
        self.reset_switch = VAMPIRESInlineUSBReset(serial_kwargs=dict(port=reset_port))

        if isinstance(delay, u.Quantity):
            self.delay = int(delay.to(u.us).value)
        if isinstance(pulse_width, u.Quantity):
            self.pulse_width = int(pulse_width.to(u.us).value)
        if isinstance(flc_offset, u.Quantity):
            self.flc_offset = int(flc_offset.to(u.us).value)
        self.pulse_width = int(pulse_width)
        self.flc_offset = int(flc_offset)
        self.flc_enabled = flc_enabled
        self.sweep_mode = sweep_mode

    def send_command(self, command):
        with self.serial as serial:
            serial.write(f"{command}\n".encode())
            response = serial.readline()
            if len(response) == 0:
                raise ArduinoTimeoutError()
            if response != "OK":
                raise ArduinoError(response)

    def ask_command(self, command):
        with self.serial as serial:
            serial.write(f"{command}\n".encode())
            response = serial.readline().decode().strip()
            if len(response) == 0:
                raise ArduinoTimeoutError()
            return response

    def get_pulse_width(self) -> int:
        return self.pulse_width

    def set_pulse_width(self, value):
        if isinstance(value, u.Quantity):
            self.pulse_width = int(self.pulse_width.to(u.us).value)
        else:
            self.pulse_width = int(value)
        self.set_parameters()

    def get_flc_offset(self) -> int:
        return self.flc_offset

    def set_flc_offset(self, value):
        if isinstance(value, u.Quantity):
            self.flc_offset = int(self.flc_offset.to(u.us).value)
        else:
            self.flc_offset = int(value)
        self.set_parameters()

    def is_flc_enabled(self) -> bool:
        return self.flc_enabled

    def enable_flc(self):
        self.flc_enabled = True
        self.set_parameters()

    def disable_flc(self):
        self.flc_enabled = False
        self.set_parameters()

    def get_parameters(self):
        response = self.ask_command(0)
        tokens = response.split()
        enabled = bool(int(tokens[0]))
        self.pulse_width = int(tokens[1])
        self.flc_offset = int(tokens[2])
        trigger_mode = int(tokens[3])
        self.flc_enabled = bool(trigger_mode & 0x1)
        self.sweep_mode = bool(trigger_mode & 0x2)
        # self.update_keys()
        return {
            "enabled": enabled,
            "pulse_width": self.pulse_width,
            "flc_offset": self.flc_offset,
            "flc_enabled": self.flc_enabled,
            "sweep_mode": self.sweep_mode,
        }

    def set_parameters(self):
        trigger_mode = int(self.flc_enabled) + (int(self.sweep_mode) << 1)
        cmd = "1 {:d} {:d} {:d}".format(self.pulse_width, self.flc_offset, trigger_mode)
        self.send_command(cmd)
        # self.update_keys()

    def disable(self):
        self.send_command(2)

    def enable(self):
        self.send_command(3)

    def reset(self):
        self.reset_switch.disable()
        self.reset_switch.enable()

    def update_keys(self):
        update_keys(
            U_FLCEN="ON" if self.flc_enabled else "OFF",
            U_FLCOFF=self.flc_offset,
            U_TRIGDL=self.delay,
            U_TRIGPW=self.pulse_width,
        )

    def _extra_config(self):
        return {
            "pulse_width": self.pulse_width,
            "flc_offset": self.flc_offset,
        }

    def status(self):
        info = self.get_timing_info()
        # self.update_keys()
        return info


__doc__ = """
    vampires_trigger [-h | --help]
    vampires_trigger (disable|status)
    vampires_trigger [--flc | --no-flc]  enable [-w | --pulse-width] <width> [-o | --flc-offset] <off>

    Options:
        -h | --help                 Print this help message
        --flc | --no-flc            Enables or disables the FLC
        -w | --pulse-width <width>  Use a custom pulse width. Default is 10 us.
        -o | --flc-offset <off>     Use a custom FLC time delay (only used if FLC is enabled). Defauls is 20 us.

    Commands:
        enable      Enables the trigger.
        disable     Disables the trigger. This should not need to be called in general unless you want to physically stop triggering. For simple acquisition control prefer software measures.
        status      Returns the status of the trigger and its timing info.
"""


class VAMPIRESInlineUSBReset(ConfigurableDevice):
    def __init__(
        self,
        serial_kwargs,
        **kwargs,
    ):
        serial_kwargs = dict(
            {"baudrate": 115200},
            **serial_kwargs,
        )
        super().__init__(serial_kwargs=serial_kwargs, **kwargs)

    def enable(self):
        with self.serial as serial:
            bytes = bytearray((0x11, 0x11, 0x0, 0x0, 0x0, 0x0))
            serial.write(bytes)
            resp_bytes = bytearray(serial.read(6))
            assert resp_bytes[0] & 0x01
            assert resp_bytes[1] & 0x11

    def disable(self):
        with self.serial as serial:
            bytes = bytearray((0x01, 0x01, 0x0, 0x0, 0x0, 0x0))
            serial.write(bytes)
            resp_bytes = bytearray(serial.read(6))
            assert resp_bytes[0] & 0x01
            assert resp_bytes[1] & 0x01

    def status(self):
        with self.serial as serial:
            bytes = bytearray((0x21, 0x21, 0x0, 0x0, 0x0, 0x0))
            serial.write(bytes)
            resp_bytes = bytearray(serial.read(6))
            assert resp_bytes[0] & 0x01
        if resp_bytes[1] & 0x01:
            st = "OFF"
        elif resp_bytes[1] & 0x11:
            st = "ON"
        else:
            st = "UNKNOWN"
        return st


def main():
    pass


if __name__ == "__main__":
    main()
