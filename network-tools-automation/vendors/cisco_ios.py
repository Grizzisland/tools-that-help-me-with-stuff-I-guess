from .base_vendor import BaseVendorHandler

class CiscoIOSHandler(BaseVendorHandler):
    def __init__(self, node_name: str, ip: str, username: str, password: str):
        super().__init__(node_name, ip, username, password, device_type="cisco_ios")

    def get_interface_brief(self) -> str:
        return self.run_command("show ip interface brief")

    def get_bgp_summary(self) -> str:
        return self.run_command("show ip bgp summary")
    
    def save_config((self) -> str:
        return self.run_command("write memory")