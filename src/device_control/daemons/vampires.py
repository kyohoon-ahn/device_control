from argparse import ArgumentParser
import os
from scxconf import PYRONS3_HOST, PYRONS3_PORT, IP_VAMPIRES
from swmain.network.pyroserver_registerable import PyroServer

from device_control.drivers.conex import CONEXDevice
from device_control.drivers.zaber import ZaberDevice
from device_control.drivers.thorlabs.filterwheel import ThorlabsWheel
from device_control.vampires import PYRO_KEYS
from device_control.multi_device import MultiDevice

parser = ArgumentParser(
    prog="vampires_daemon",
    description="Launch the daemon for the devices controlled by the VAMPIRES computer."
)

def main():
    args = parser.parse_args()

    server = PyroServer(bindTo=(IP_VAMPIRES, 0), nsAddress=(PYRONS3_HOST, PYRONS3_PORT))

    conf_dir = os.path.abspath(os.getenv("CONF_DIR", f"{os.getenv('HOME')}/src/device_control/conf/"))

    ## create device objects
    conf_paths = {
        "beamsplitter": os.path.join(conf_dir, "devices/vampires/conf_vampires_beamsplitter.toml"),
        "focus": os.path.join(conf_dir, "devices/vampires/conf_vampires_focus.toml"),
        "camfocus": os.path.join(conf_dir, "devices/vampires/conf_vampires_camfocus.toml"),
        "diffwheel": os.path.join(conf_dir, "devices/vampires/conf_vampires_diffwheel.toml"),
        "pupil": os.path.join(conf_dir, "devices/vampires/conf_vampires_pupil.toml"),
        "qwp": os.path.join(conf_dir, "devices/vampires/conf_vampires_qwp.toml"),
        "filter": os.path.join(conf_dir, "devices/vampires/conf_vampires_filter.toml"),

    }
    print("Initializing devices")
    devices = {
        "beamsplitter": CONEXDevice.from_config(conf_paths["beamsplitter"]),
        "focus": CONEXDevice.from_config(conf_paths["focus"]),
        "camfocus": ZaberDevice.from_config(conf_paths["camfocus"]),
        "diffwheel": CONEXDevice.from_config(conf_paths["diffwheel"]),
        "pupil": MultiDevice.from_config(conf_paths["pupil"]),
        "qwp": MultiDevice.from_config(conf_paths["qwp"]),
        "filter": ThorlabsWheel.from_config(conf_paths["filter"]),
    }
    ## Add to Pyro server
    print("Adding devices to pyro", end="\n  ")
    for key, device in devices.items():
        print(f"{key}: {PYRO_KEYS[key]}", end="\n  ")
        globals()[key] = device
        server.add_device(device, PYRO_KEYS[key], add_oneway_callables=True)
    print()
    ## Start server
    server.start()
    

if __name__ == "__main__":
    main()