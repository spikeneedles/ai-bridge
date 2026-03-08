import os
from dotenv import load_dotenv

load_dotenv()

BRIDGE_HOST = os.getenv("BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "8765"))
DB_PATH = os.getenv("DB_PATH", "bridge.db")
