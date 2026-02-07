import json
import os
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Data directory configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
STORE_FILE = os.path.join(DATA_DIR, "transactions_store.json")

# Shared In-Memory Stores
transactions_store: Dict[str, Dict[str, Any]] = {}
ALERTS_QUEUE: List[Dict[str, Any]] = []
approval_queue: Dict[str, Dict[str, Any]] = {}

def save_transactions():
    """Save transactions to disk."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STORE_FILE, "w") as f:
            json.dump(transactions_store, f, default=str, indent=2)
        logger.info(f"Saved {len(transactions_store)} transactions to {STORE_FILE}")
    except Exception as e:
        logger.error(f"Failed to save transactions: {e}")

def load_transactions():
    """Load transactions from disk."""
    global transactions_store
    try:
        if os.path.exists(STORE_FILE):
            with open(STORE_FILE, "r") as f:
                transactions_store = json.load(f)
            logger.info(
                f"Loaded {len(transactions_store)} transactions from {STORE_FILE}"
            )
    except Exception as e:
        logger.error(f"Failed to load transactions: {e}")

# Initialize
# load_transactions() # Can be called by main app startup
