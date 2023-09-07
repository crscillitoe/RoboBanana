from config import YAMLConfig as Config

HOST = Config.CONFIG["Server"]["Host"]
PORT = Config.CONFIG["Server"]["Port"]


def get_base_url():
    return f"http://{HOST}:{PORT}"
