import configparser
import os.path


class Config:
    CONFIG = configparser.ConfigParser()
    CONFIG.read(os.path.join(os.path.dirname(__file__), "config.ini"))
