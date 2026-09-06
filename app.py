import sys
from pathlib import Path

source_dir = Path(__file__).resolve().parent / "src"
if source_dir.is_dir():
    sys.path.insert(0, str(source_dir))

from keyflip.application import run


if __name__ == "__main__":
    sys.exit(run(sys.argv))
