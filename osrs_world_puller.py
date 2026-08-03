#!/usr/bin/env python3
import json
import re
import sys
import urllib.request

WORLD_LIST_URL = "https://oldschool.runescape.com/g=oldscape/slu"

# Static custom targets you always want at the top of your list
STATIC_TARGETS = [
    "1.1.1.1",
    "1.0.0.1",
    "8.8.8.8",
    "account.jagex.com",
    "secure.jagex.com",
    "secure.runescape.com",
    "cdn.runescape.com",
    "auth.jagex.com"
]

def fetch_osrs_hosts():
    """
    Fetches active OSRS world hostnames directly from Jagex's web world list.
    """
    req = urllib.request.Request(
        WORLD_LIST_URL, 
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    
    hosts = []
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
            # Find all instances of world numbers in the HTML (e.g. Old School 302 -> oldschool2.runescape.com or oldschool302.runescape.com)
            matches = re.findall(r'Old\s*School\s*(\d+)', html, re.IGNORECASE)
            
            world_ids = sorted(list(set(int(m) for m in matches)))
            for world_id in world_ids:
                hosts.append(f"oldschool{world_id}.runescape.com")
                
    except Exception as e:
        print(f"Warning: Could not fetch live worlds ({e}). Falling back to static targets.", file=sys.stderr)

    return hosts

def generate_yaml_targets(output_file="blackbox_targets.yml"):
    # 1. Fetch live hostnames
    osrs_hosts = fetch_osrs_hosts()
    
    # 2. Combine static targets with OSRS hosts
    all_targets = STATIC_TARGETS + osrs_hosts

    # 3. Write output matching your exact YAML structure
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("targets:\n")
        for target in all_targets:
            f.write(f"  - {target}\n")

    print(f"Successfully generated '{output_file}' with {len(all_targets)} total targets.")

if __name__ == "__main__":
    generate_yaml_targets()