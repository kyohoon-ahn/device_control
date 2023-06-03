import sys
from typing import Union
import os

import numpy as np
import tomli
from docopt import docopt

from device_control import conf_dir
from device_control.multi_device import MultiDevice
from device_control.vampires import PYRO_KEYS
from swmain.network.pyroclient import (  # Requires scxconf and will fetch the IP addresses there.
    connect,
)
from swmain.redis import update_keys


class VAMPIRESMaskWheel(MultiDevice):
    format_str = "{0:2d}: {1:17s} {{x={2:6.3f} mm, y={3:6.3f} mm, th={4:6.2f} deg}}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.devices["x"]._update_keys = lambda p: update_keys(U_MASKX=p)
        self.devices["y"]._update_keys = lambda p: update_keys(U_MASKY=p)
        self.devices["theta"]._update_keys = lambda p: update_keys(U_MASKTH=p)

    def _update_keys(self, positions):
        _, name = self.get_configuration(positions=positions)
        update_keys(U_MASK=name)

    def help_message(self):
        configurations = "\n".join(
            f"    {VAMPIRESMaskWheel.format_str.format(c['idx'], c['name'], c['value']['x'], c['value']['y'], c['value']['theta'])}"
            for c in self.configurations
        )
        return f"""Usage:
    vampires_mask [-h | --help]
    vampires_mask [-h | --help] status
    vampires_mask [-w | --wait] x (status|position|home|goto|nudge|stop|reset) [<pos>]
    vampires_mask [-w | --wait] y (status|position|home|goto|nudge|stop|reset) [<pos>]
    vampires_mask [-w | --wait] theta (status|position|home|goto|nudge|stop|reset) [<pos>]
    vampires_mask [-w | --wait] <configuration>

Options:
    -h, --help   Show this screen
    -w, --wait   Block command until position has been reached, for applicable commands

Stage commands:
    status          Returns the status of the stage
    position        Returns the current position of the stage
    home            Homes the stage
    goto  <pos>     Move the stage to the given angle
    nudge <pos>     Move the stage relatively by the given angle
    stop            Stop the stage
    reset           Reset the stage

Configurations:
{configurations}"""


# setp 4. action
def main():
    if os.getenv("WHICHCOMP") == "V":
        vampires_mask = VAMPIRESMaskWheel.from_config(
            conf_dir / "vampires" / "conf_vampires_mask.toml"
        )
    else:
        vampires_mask = connect(PYRO_KEYS["mask"])
    __doc__ = vampires_mask.help_message()
    args = docopt(__doc__, options_first=True)
    if len(sys.argv) == 1:
        print(__doc__)
    elif len(sys.argv) == 2 and args["status"]:
        idx, name = vampires_mask.get_configuration()
        if idx is None:
            idx = -1
        x = vampires_mask.get_position("x")
        y = vampires_mask.get_position("y")
        th = vampires_mask.get_position("theta")
        print(VAMPIRESMaskWheel.format_str.format(idx, name, x, y, th))
        vampires_mask.update_keys((x, y, th))
        return
    elif args["x"]:
        substage = "x"
    elif args["y"]:
        substage = "y"
    elif args["theta"]:
        substage = "theta"
    elif args["<configuration>"]:
        index = int(args["<configuration>"])
        return vampires_mask.move_configuration_idx(index)
    if args["status"] or args["position"]:
        print(vampires_mask.get_position(substage))
    elif args["home"]:
        vampires_mask.home(substage)
    elif args["goto"]:
        pos = float(args["<pos>"])
        if args["theta"]:
            vampires_mask.move_absolute(substage, pos % 360)
        else:
            vampires_mask.move_absolute(substage, pos)
    elif args["nudge"]:
        rel_pos = float(args["<pos>"])
        vampires_mask.move_relative(substage, rel_pos)
    elif args["stop"]:
        vampires_mask.stop(substage)
    elif args["reset"]:
        substage.reset()
    vampires_mask.update_keys()


if __name__ == "__main__":
    main()
