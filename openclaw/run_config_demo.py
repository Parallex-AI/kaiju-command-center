import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import get_config, redacted_config_dict

if __name__ == "__main__":
    config = get_config()
    output = redacted_config_dict(config)
    print(json.dumps(output, indent=2))
