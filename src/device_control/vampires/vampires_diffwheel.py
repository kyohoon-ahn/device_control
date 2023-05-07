from docopt import docopt
import os
import sys

from swmain.network.pyroclient import connect # Requires scxconf and will fetch the IP addresses there.
from device_control.vampires import PYRO_KEYS

vampires_diffwheel = connect(PYRO_KEYS["diffwheel"])
configurations = "\n".join(f"    {c['idx']}: {c['name']:21s} {{{c['value']} {vampires_diffwheel.unit}}}" for c in vampires_diffwheel.configurations)

__doc__ = f"""Usage:
    vampires_diffwheel [-h | --help]
    vampires_diffwheel [-w | --wait] (status|target|home|goto|nudge|stop|reset) [<angle>]
    vampires_diffwheel [-w | --wait] <configuration>

Options:
    -h, --help   Show this screen
    -w, --wait   Block command until position has been reached, for applicable commands

Wheel commands:
    status          Returns the current position of the differential filter wheel, in deg
    target          Returns the target position of the differential filter wheel, in deg
    home            Homes the differential filter wheel
    goto  <angle>   Move the differential filter wheel to the given angle, in deg
    nudge <angle>   Move the differential filter wheel relatively by the given angle, in deg
    stop            Stop the differential filter wheel
    reset           Reset the differential filter wheel
        
Configurations (cam1 / cam2):
{configurations}"""

# setp 4. action
def main():
    args = docopt(__doc__, options_first=True)
    if len(sys.argv) == 1:
        print(__doc__)
    if args["status"]:
        print(vampires_diffwheel.position)
    elif args["target"]:
        print(vampires_diffwheel.target_position)
    elif args["home"]:
        vampires_diffwheel.home(wait=args["--wait"])
    elif args["goto"]:
        angle = float(args["<angle>"])
        vampires_diffwheel.move_absolute(angle, wait=args["--wait"])
    elif args["nudge"]:
        rel_angle = float(args["<angle>"])
        vampires_diffwheel.move_relative(rel_angle, wait=args["--wait"])
    elif args["stop"]:
        vampires_diffwheel.stop()
    elif args["reset"]:
        vampires_diffwheel.reset()
    elif args["<configuration>"]:
        index = int(args["<configuration>"])
        vampires_diffwheel.move_configuration(index, wait=args["--wait"])

if __name__ == "__main__":
    main()