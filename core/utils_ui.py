import os
import json
import threading
import time

# Global lock to prevent concurrent file access within the same process
_config_lock = threading.Lock()

def get_config_path():
    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    # Template path for fallback if config doesn't exist
    template_path = os.path.join(os.path.dirname(__file__), "config.template.json")
    if not os.path.exists(cfg_path) and os.path.exists(template_path):
        import shutil
        shutil.copy(template_path, cfg_path)
    return cfg_path

def load_full_config():
    cfg_path = get_config_path()
    with _config_lock:
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[utils_ui Load Error] {e}")
    return {}

def save_full_config(config):
    cfg_path = get_config_path()
    temp_path = cfg_path + ".tmp"
    
    with _config_lock:
        try:
            with open(temp_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            # Retry loop for Windows file contention
            for i in range(5):
                try:
                    if os.path.exists(cfg_path):
                        os.replace(temp_path, cfg_path)
                    else:
                        os.rename(temp_path, cfg_path)
                    return True
                except PermissionError:
                    time.sleep(0.1)
            raise PermissionError(f"Could not replace {cfg_path} after 5 attempts")
            
        except Exception as e:
            print(f"[Config Save Error] {e}")
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            return False