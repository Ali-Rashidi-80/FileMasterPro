import os, json

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading config:", e)
    return {"font_size": 16, "theme": "light", "main_color": "#3498db"}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        os.system(f'attrib +h "{CONFIG_FILE}"')
    except Exception as e:
        print("Error saving config:", e)
