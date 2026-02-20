import os
import yaml
import logging

logger = logging.getLogger(__name__)

# Path to the state file
STATE_FILE = os.path.join(os.path.expanduser("~"), ".red_pill_state.yaml")

DEFAULT_STATE = {
    "skin": "matrix"
}

def load_state():
    """Load the current state from the state file."""
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    
    try:
        with open(STATE_FILE, "r") as f:
            state = yaml.safe_load(f)
            if not state:
                return DEFAULT_STATE.copy()
            return {**DEFAULT_STATE, **state}
    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return DEFAULT_STATE.copy()

def save_state(state):
    """Save the state to the state file."""
    try:
        with open(STATE_FILE, "w") as f:
            yaml.dump(state, f)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")

def get_skin():
    """Get the currently active skin."""
    return load_state().get("skin", "matrix")

def set_skin(skin_name):
    """Set the active skin."""
    state = load_state()
    state["skin"] = skin_name
    save_state(state)
