from typing import List
import logging
from .base_vendor import BaseVendorHandler

class AristaEOSHandler(BaseVendorHandler):
    def __init__(self, node_name: str, ip: str):
        super().__init__(node_name, ip, device_type="arista_eos")

    def check_config_syntax(self, config_commands: List[str]) -> tuple[bool, str]:
        """Uses EOS configuration sessions to isolate and diff changes."""
        self.connect()
        # Start a temporary named config session
        self.connection.send_command("configure session deploy_check")
        self.connection.send_config_set(config_commands, exit_config_mode=False)
        
        diff = self.connection.send_command("show session-config diff")
        
        # Session syntax verification
        syntax_check = self.connection.send_command("verify")
        
        if "%" in syntax_check or "error" in syntax_check.lower():
            self.connection.send_command("abort")
            return False, f"EOS Session Verification Error:\n{syntax_check}"

        return True, diff

    def safe_deploy_config(self, config_commands: List[str], rollback_mins: int = 5) -> str:
        is_valid, diff_or_error = self.check_config_syntax(config_commands)
        if not is_valid:
            raise RuntimeError(f"EOS Deployment Aborted:\n{diff_or_error}")

        if not self.prompt_user_approval(diff_or_error):
            logging.warning(f"[{self.node_name}] Aborting EOS config session...")
            self.connection.send_command("abort")
            return "Cancelled by operator."

        logging.info(f"[{self.node_name}] Committing EOS configuration session...")
        commit_out = self.connection.send_command("commit")
        return commit_out