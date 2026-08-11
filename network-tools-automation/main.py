import yaml
from vendors import get_vendor_driver

def deploy_to_node(node_name: str, commands: list):
    with open("inventory.yaml") as f:
        inventory = yaml.safe_load(f)["nodes"]

    node = inventory[node_name]
    driver = get_vendor_driver(vendor=node["vendor"], node_name=node_name, ip=node["ip"])

    try:
        driver.connect()
        result = driver.safe_deploy_config(config_commands=commands, rollback_mins=5)
        print(f"\n[Result]: {result}")
        driver.disconnect()
    except Exception as err:
        print(f"\n❌ Deployment failed safely: {err}")

if __name__ == "__main__":
    # Example: BGP Neighbor Config
    proposed_changes = [
        "router bgp 65001",
        "neighbor 10.255.255.2 remote-as 65002",
        "neighbor 10.255.255.2 description Peer_To_Border_Rtr",
    ]
    
    deploy_to_node("dist-sw02", proposed_changes)