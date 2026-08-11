from typing import List
import logging
from .base_vendor import BaseVendorHandler

class CiscoNXOSHandler(BaseVendorHandler):
    def __init__(self, node_name: str, ip: str):
        super().__init__(node_name, ip, device_type="cisco_nxos")

    def check_config_syntax(self, config_commands: List[str]) -> tuple[bool, str]:
        """Validates configuration lines through NX-OS configuration session."""
        self.connect()
        self.connection.send_command("configure session name deploy_test")
        out = self.connection.send_config_set(config_commands, exit_config_mode=False)
        
        diff = self.connection.send_command("show configuration session deploy_test diff")
        
        if "%" in out or "invalid" in out.lower():
            self.connection.send_command("abort")
            return False, f"NX-OS Syntax Error detected in session:\n{out}"

        return True, diff

    def safe_deploy_config(self, config_commands: List[str], rollback_mins: int = 5) -> str:
        is_valid, diff_or_error = self.check_config_syntax(config_commands)
        if not is_valid:
            raise RuntimeError(f"NX-OS Deployment Aborted:\n{diff_or_error}")

        if not self.prompt_user_approval(diff_or_error):
            self.connection.send_command("abort")
            return "Cancelled by operator."

        # Create checkpoint before committing session
        self.connection.send_command("checkpoint netops_pre_deploy")
        commit_out = self.connection.send_command("commit")
        return commit_out