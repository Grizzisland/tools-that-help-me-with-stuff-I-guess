from .cisco_ios import CiscoIOSHandler
from .cisco_nxos import CiscoNXOSHandler
from .cisco_iosxr import CiscoIOSXRHandler
from .juniper_junos import JuniperJunosHandler
from .arista_eos import AristaEOSHandler
from .paloalto_panos import PaloAltoPANOSHandler

# Central Registry of Supported Platforms
VENDOR_MAP = {
    "cisco": CiscoIOSHandler,
    "cisco_ios": CiscoIOSHandler,
    "cisco_xe": CiscoIOSHandler,
    "cisco_nxos": CiscoNXOSHandler,
    "cisco_xr": CiscoIOSXRHandler,
    "cisco_iosxr": CiscoIOSXRHandler,
    "juniper": JuniperJunosHandler,
    "juniper_junos": JuniperJunosHandler,
    "arista": AristaEOSHandler,
    "arista_eos": AristaEOSHandler,
    "paloalto": PaloAltoPANOSHandler,
    "paloalto_panos": PaloAltoPANOSHandler,
}

def get_vendor_driver(vendor: str, node_name: str, ip: str):
    """Dynamically initializes and returns the right vendor class."""
    key = vendor.lower().strip()
    if key not in VENDOR_MAP:
        raise ValueError(f"Vendor '{vendor}' is not supported. Supported choices: {list(set(VENDOR_MAP.keys()))}")
    
    handler_class = VENDOR_MAP[key]
    return handler_class(node_name=node_name, ip=ip)