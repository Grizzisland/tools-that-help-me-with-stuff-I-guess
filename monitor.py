# pip install netmiko python-dotenv ntc-templates requests
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dotenv import load_dotenv
from netmiko import ConnectHandler
import requests

# Load environment variables
load_dotenv()

USERNAME = os.getenv("SSH_USERNAME")
PASSWORD = os.getenv("SSH_PASSWORD")
SECRET = os.getenv("SSH_SECRET", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 10))

WEBHOOK_PROVIDER = os.getenv("WEBHOOK_PROVIDER", "discord").lower()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

# Target devices parsing
targets_raw = os.getenv("TARGET_DEVICES", "").split(",")
TARGETS = []
for t in targets_raw:
    if ":" in t:
        host, dev_type = t.strip().split(":", 1)
        TARGETS.append({"host": host.strip(), "device_type": dev_type.strip()})

# Vendor to CLI command mapping
VENDOR_COMMANDS = {
    "cisco_ios": "show ip interface brief",
    "cisco_nxos": "show interface status",
    "cisco_xr": "show ip interface brief",
    "arista_eos": "show ip interface brief",
    "juniper_junos": "show interfaces terse",
    "vyos": "show interfaces",
}


def send_webhook_alert(host: str, interface: str, old_state: str, new_state: str):
    """Sends a formatted notification to Google Chat, Discord, or Slack."""
    if not WEBHOOK_URL:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_down = "down" in new_state.lower() or "disable" in new_state.lower()
    status_icon = "🔴" if is_down else "🟢"
    title = f"{status_icon} Interface State Change on {host}"

    payload = {}

    # 1. Google Workspace / Google Chat Webhook Format
    if WEBHOOK_PROVIDER == "google_chat":
        payload = {
            "cardsV2": [
                {
                    "cardId": "interface_alert",
                    "card": {
                        "header": {
                            "title": title,
                            "subtitle": f"Time: {timestamp}",
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {"textParagraph": {"text": f"<b>Device:</b> {host}"}},
                                    {"textParagraph": {"text": f"<b>Interface:</b> {interface}"}},
                                    {
                                        "textParagraph": {
                                            "text": f"<b>Transition:</b> <code>{old_state.upper()}</code> ➔ <code>{new_state.upper()}</code>"
                                        }
                                    },
                                ]
                            }
                        ],
                    },
                }
            ]
        }

    # 2. Discord Webhook Format (Rich Embed)
    elif WEBHOOK_PROVIDER == "discord":
        color_code = 15158332 if is_down else 3066993  # Red or Green
        payload = {
            "embeds": [
                {
                    "title": title,
                    "color": color_code,
                    "fields": [
                        {"name": "Device Host", "value": f"`{host}`", "inline": True},
                        {"name": "Interface", "value": f"`{interface}`", "inline": True},
                        {
                            "name": "State Transition",
                            "value": f"`{old_state.upper()}` ➡️ `{new_state.upper()}`",
                            "inline": False,
                        },
                    ],
                    "footer": {"text": f"Timestamp: {timestamp}"},
                }
            ]
        }

    # 3. Slack Webhook Format (Block Kit)
    elif WEBHOOK_PROVIDER == "slack":
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": title, "emoji": True},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Device:*\n{host}"},
                        {"type": "mrkdwn", "text": f"*Interface:*\n{interface}"},
                        {
                            "type": "mrkdwn",
                            "text": f"*State Change:*\n`{old_state.upper()}` ➔ `{new_state.upper()}`",
                        },
                        {"type": "mrkdwn", "text": f"*Time:*\n{timestamp}"},
                    ],
                },
            ]
        }

    # Dispatch HTTP POST request to the Webhook URL
    try:
        res = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        res.raise_for_status()
    except Exception as err:
        print(f"❌ [{host}] Webhook dispatch failed: {err}")


def get_vendor_command(device_type: str) -> str:
    return VENDOR_COMMANDS.get(device_type, "show ip interface brief")


def parse_raw_interfaces(output: str) -> dict:
    states = {}
    for line in output.splitlines():
        match = re.search(
            r"^([\w\/\.\-]+)\s+.*?\b(up|down|administratively down|disable)\b",
            line,
            re.IGNORECASE,
        )
        if match:
            intf, status = match.groups()
            states[intf] = status.lower()
    return states


def fetch_interface_states(net_connect, device_type: str) -> dict:
    command = get_vendor_command(device_type)
    try:
        output = net_connect.send_command(command, use_textfsm=True)
    except Exception:
        output = net_connect.send_command(command)

    states = {}

    if isinstance(output, list):
        for row in output:
            intf = row.get("interface") or row.get("intf") or row.get("port")
            status = row.get("status") or row.get("admin_status") or row.get("proto")
            if intf and status:
                states[intf] = str(status).lower()
    else:
        states = parse_raw_interfaces(output)

    return states


def monitor_single_device(target: dict):
    host = target["host"]
    device_type = target["device_type"]

    device_params = {
        "device_type": device_type,
        "host": host,
        "username": USERNAME,
        "password": PASSWORD,
        "secret": SECRET,
        "fast_cli": False,
    }

    print(f"[{host}] Connecting as platform '{device_type}'...")

    try:
        with ConnectHandler(**device_params) as net_connect:
            if SECRET:
                net_connect.enable()

            print(f"[{host}] Connected. Initializing baseline...")
            previous_states = fetch_interface_states(net_connect, device_type)

            print(f"[{host}] Monitoring active ({len(previous_states)} interface(s) loaded)...\n")

            while True:
                time.sleep(POLL_INTERVAL)
                current_states = fetch_interface_states(net_connect, device_type)

                for intf, new_state in current_states.items():
                    old_state = previous_states.get(intf)

                    if old_state and old_state != new_state:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(
                            f"🚨 [{timestamp}] [{host}] ALERT: {intf} "
                            f"changed state: {old_state.upper()} ➡️  {new_state.upper()}"
                        )
                        # Dispatch Webhook Notice
                        send_webhook_alert(host, intf, old_state, new_state)

                    previous_states[intf] = new_state

    except Exception as e:
        print(f"❌ [{host}] Error: {e}")


def main():
    if not TARGETS:
        print("No targets configured in .env under TARGET_DEVICES.")
        return

    print(f"Starting monitor for {len(TARGETS)} device(s) [Webhook: {WEBHOOK_PROVIDER}]...")

    with ThreadPoolExecutor(max_workers=len(TARGETS)) as executor:
        executor.map(monitor_single_device, TARGETS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGlobal monitoring stopped by user.")