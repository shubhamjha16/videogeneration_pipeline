import sys
from unittest.mock import MagicMock

# Gracefully mock binary/onnx/heavy dependencies that are missing in host Python 3.14 environment
sys.modules["lancedb"] = MagicMock()
sys.modules["fastembed"] = MagicMock()
sys.modules["pandas"] = MagicMock()

# Mock moviepy to avoid import errors in ledger tests
sys.modules["moviepy"] = MagicMock()
sys.modules["moviepy.editor"] = MagicMock()
