# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "folium", "branca"]
# ///

"""Run the tornado map generator."""

from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).parent
SCRIPT = HERE / "tornado_map.py"


def main():
    print(f"Running {SCRIPT.name}...")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)


if __name__ == "__main__":
    main()
