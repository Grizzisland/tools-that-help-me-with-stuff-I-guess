from typing import List, Dict, Any
import logging
from .base_vendor import BaseVendorHandler

class JuniperJunosHandler(BaseVendorHandler):
    def __init__(self, node_name: str, ip: str):
        super().__init__(node_name, ip, device_type="juniper_junos")

    def check_config_syntax(self, config_commands: List[str]) -> tuple[bool, str]:
        """Loads candidate config and performs 'commit check' and 'show pipe compare'."""
        self.connect()
        self.connection.config_mode()
        
        # Load commands into candidate buffer
        self.connection.send_config_set(config_commands, exit_config_mode=False)
        
        # Fetch diff
        diff = self.connection.send_command("show pipe compare")
        
        # Perform dry-run syntax validation
        check_output = self.connection.send_command("commit check")
        
        is_valid = "configuration check succeeds" in check_output.lower()
        if not is_valid:
            logging.error(f"[{self.node_name}] Pre-Commit Syntax Check Failed: {check_output}")
            self.connection.send_command("rollback 0") # Clear candidate buffer
            self.connection.exit_config_mode()
            return False, f"Syntax Error: {check_output}"

        return True, diff

    def safe_deploy_config(self, config_commands: List[str], rollback_mins: int = 5) -> str:
        """Runs pre-commit check, displays diff, requests approval, and executes commit confirmed."""
        is_valid, diff_or_error = self.check_config_syntax(config_commands)
        if not is_valid:
            raise RuntimeError(f"Deployment aborted. Pre-commit check failed:\n{diff_or_error}")

        if not self.prompt_user_approval(diff_or_error):
            logging.warning(f"[{self.node_name}] Deployment cancelled by operator. Rolling back candidate config...")
            self.connection.send_command("rollback 0")
            self.connection.exit_config_mode()
            return "Cancelled by operator."

        logging.info(f"[{self.node_name}] Pre-commit check passed. Executing 'commit confirmed {rollback_mins}'...")
        commit_out = self.connection.commit(confirm=True, confirm_delay=rollback_mins)
        self.connection.exit_config_mode()
        return commit_out