from typing import List
import logging
from .base_vendor import BaseVendorHandler

class CiscoIOSXRHandler(BaseVendorHandler):
    def __init__(self, node_name: str, ip: str):
        super().__init__(node_name, ip, device_type="cisco_xr")

    def check_config_syntax(self, config_commands: List[str]) -> tuple[bool, str]:
        """Runs 'show configuration merge' and 'commit dry-run'."""
        self.connect()
        self.connection.config_mode()
        self.connection.send_config_set(config_commands, exit_config_mode=False)
        
        diff = self.connection.send_command("show configuration merge")
        dry_run = self.connection.send_command("commit dry-run")
        
        # Check for errors in dry run output
        if "error" in dry_run.lower() or "failed" in dry_run.lower():
            self.connection.send_command("abort")
            return False, f"IOS-XR Dry Run Failed:\n{dry_run}"

        return True, diff

    def safe_deploy_config(self, config_commands: List[str], rollback_mins: int = 5) -> str:
        is_valid, diff_or_error = self.check_config_syntax(config_commands)
        if not is_valid:
            raise RuntimeError(f"Deployment aborted:\n{diff_or_error}")

        if not self.prompt_user_approval(diff_or_error):
            logging.warning(f"[{self.node_name}] Deployment cancelled by operator. Aborting...")
            self.connection.send_command("abort")
            return "Cancelled by operator."

        logging.info(f"[{self.node_name}] Committing configuration...")
        output = self.connection.commit(comment="Safe Deployment via NetOps Tool")
        self.connection.exit_config_mode()
        return output