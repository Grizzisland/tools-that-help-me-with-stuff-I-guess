import os
import logging
import difflib
from dotenv import load_dotenv
from netmiko import ConnectHandler

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class BaseVendorHandler:
    def __init__(self, node_name: str, ip: str, device_type: str):
        self.node_name = node_name
        
        username = os.getenv("SSH_USERNAME")
        password = os.getenv("SSH_PASSWORD")
        key_file = os.getenv("SSH_KEY_FILE")
        secret = os.getenv("ENABLE_SECRET", "")

        if not username:
            raise ValueError("CRITICAL: SSH_USERNAME is not set in .env file!")

        self.device_info = {
            "device_type": device_type,
            "host": ip,
            "username": username,
            "fast_cli": False,
        }

        if key_file and os.path.exists(key_file):
            self.device_info["use_keys"] = True
            self.device_info["key_file"] = key_file
        elif password:
            self.device_info["password"] = password
        else:
            raise ValueError("CRITICAL: Neither SSH_PASSWORD nor SSH_KEY_FILE found in .env")

        if secret:
            self.device_info["secret"] = secret

        self.connection = None

    def connect(self):
        if not self.connection:
            logging.info(f"[{self.node_name}] Connecting via SSH ({self.device_info['device_type']})...")
            self.connection = ConnectHandler(**self.device_info)
            if "secret" in self.device_info:
                self.connection.enable()
            logging.info(f"[{self.node_name}] Connected successfully.")

    def disconnect(self):
        if self.connection:
            self.connection.disconnect()
            self.connection = None

    def run_command(self, command: str) -> str:
        self.connect()
        return self.connection.send_command(command)

    def run_structured(self, command: str):
        self.connect()
        return self.connection.send_command(command, use_textfsm=True)

    def prompt_user_approval(self, diff_text: str) -> bool:
        """Displays diff to human engineer and requests manual confirmation."""
        print("\n=================== 🔍 PROPOSED CONFIG DIFF 🔍 ===================")
        print(diff_text if diff_text.strip() else "(No visual diff available / Line-by-line deployment)")
        print("=================================================================\n")
        
        confirm = input(f"⚠️ Do you want to commit these changes to [{self.node_name}]? (yes/no): ").strip().lower()
        return confirm in ["y", "yes"]

    def check_config_syntax(self, config_commands: list) -> tuple[bool, str]:
        """Must be implemented by subclasses to perform pre-commit dry runs."""
        raise NotImplementedError

    def safe_deploy_config(self, config_commands: list, rollback_mins: int = 5) -> str:
        """Must be implemented by subclasses to execute deployment with safety checks."""
        raise NotImplementedError