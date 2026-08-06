import argparse
import json
import os
import sys

PROFILES = ["react-web", "flutter-mobile", "backend-api", "vhdl-hardware"]

def install(profile_name):
    config_path = os.path.join(".pipeline", "profile_config.json")
    os.makedirs(".pipeline", exist_ok=True)
    config = {"active_profile": profile_name}
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Successfully configured pipeline for profile: {profile_name}")

def main():
    parser = argparse.ArgumentParser(description="Modular Downstream Installer CLI")
    parser.add_argument("--profile", choices=PROFILES, required=True, help="Target implementation profile")
    args = parser.parse_args()
    install(args.profile)

if __name__ == "__main__":
    main()
