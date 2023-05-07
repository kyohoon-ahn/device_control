import logging
from serial import Serial
import time

from ..base import MotionDevice

__all__ = ["CONEXDevice"]

# CONEX programmer manual
# https://www.newport.com/mam/celum/celum_assets/resources/CONEX-AGP_-_Controller_Documentation.pdf

class CONEXState:

    def __init__(self, previous=None):
        self.previous = previous

    def __repr__(self):
        output = f"{self.__class__.__name__}"
        if self.previous is not None:
            output += f" from {self.previous}"
        return output

class NotReferenced(CONEXState): pass
class Configuration(CONEXState): pass
class Homing(CONEXState): pass
class Moving(CONEXState): pass
class Ready(CONEXState): pass
class Disable(CONEXState): pass
class Reset(CONEXState): pass

CONEX_STATES = {
    " a": NotReferenced(Reset()),
    " b": NotReferenced(Homing()),
    " c": NotReferenced(Configuration()),
    " d": NotReferenced(Disable()),
    " e": NotReferenced(Ready()),
    " f": NotReferenced(Moving()),
    "1 ": NotReferenced("no parameters"),
    "14": Configuration(),
    "1e": Homing(),
    "28": Moving(),
    "32": Ready(Homing()),
    "33": Ready(Moving()),
    "34": Ready(Disable()),
    "3c": Disable(Ready()),
    "3d": Disable(Moving()),
}

class CONEXDevice(MotionDevice):
    def __init__(
        self,
        device_address=1,
        delay=0.1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if device_address < 1 or device_address > 31:
            raise ValueError(f"controller address must be between 1 and 31, got {device_address}")
        self.device_address = device_address
        self.delay = delay
        self.logger = logging.getLogger(self.__class__.__name__)

    def send_command(self, command: str, returns=False):
        cmd = f"{self.device_address}{command}\r\n"
        self.logger.debug(f"sending command: {cmd[:-2]}")
        with Serial(port=self.address, **self.serial_kwargs) as serial:
            serial.write(cmd.encode())
            if returns:
                retval = serial.read_until(b"\r\n").decode()
                self.logger.debug(f"received: {retval[:-2]}")
                # strip command and \r\n from string
                return retval[3:-2]

    @property
    def stage_identifier(self) -> str:
        return self.send_command("ID?", returns=True)

    @stage_identifier.setter
    def stage_identifier(self, value: str):
        self.send_command(f"ID{value}")

    @property
    def rs485_address(self) -> int:
        return int(self.send_command("SA?", returns=True))

    @rs485_address.setter
    def rs485_address(self, value: int):
        self.send_command(f"SA{value}")

    @property
    def lower_limit(self) -> float:
        return float(self.send_command("SA?", returns=True))

    @lower_limit.setter
    def lower_limit(self, value: float):
        self.send_command(f"SA{value}")

    @property
    def upper_limit(self) -> float:
        return float(self.send_command("SR?", returns=True))

    @upper_limit.setter
    def upper_limit(self, value: float):
        self.send_command(f"SR{value}")

    @property
    def encoder_increment(self) -> float:
        return float(self.send_command("SU?", returns=True))

    @encoder_increment.setter
    def encoder_increment(self, value: float):
        self.send_command(f"SU{value}")

    @property
    def enabled(self) -> bool:
        return not isinstance(self.state, Disable)

    @property
    def moving(self) -> bool:
        return isinstance(self.state, Moving)

    @property
    def homing(self) -> bool:
        return isinstance(self.state, Homing)

    @property
    def state(self) -> CONEXState:
        return CONEX_STATES[self.send_command("MM?", returns=True)]

    def disable(self):
        self.send_command("MM0")

    def enable(self):
        self.send_command("MM1")

    def home(self, wait=False):
        self.send_command("OR")
        if wait:
            while self.homing:
                time.sleep(self.delay)

    def move_absolute(self, value: float, wait=False):
        val = value - self.offset
        self.send_command(f"PA{val}")
        if wait:
            while self.moving:
                time.sleep(self.delay)

    def move_relative(self, value: float, wait=False):
        self.send_command(f"PR{value}")
        if wait:
            while self.moving:
                time.sleep(self.delay)

    def reset(self):
        self.send_command("RS")

    def reset_address(self, value: int):
        self.send_command(f"RS{value}")

    @property
    def _target_position(self) -> float:
        return float(self.send_command("TH?", returns=True))

    @property
    def _position(self) -> float:
        return float(self.send_command("TP", returns=True))

    def stop(self):
        self.send_command("ST")

    def error_string(self, code: str):
        return self.send_command(f"TB{code}", returns=True)

    @property
    def last_command_error(self) -> str:
        err = self.send_command("TE", returns=True)
        return self.error_string(err)