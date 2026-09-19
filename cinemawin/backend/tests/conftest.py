import sys
from pathlib import Path

# Make `import config`, `from services import ...` work when pytest runs from
# the backend directory or the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
