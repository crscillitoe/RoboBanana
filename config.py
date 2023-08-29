import configparser
import yaml
import os.path
import logging
import sys

LOG = logging.getLogger(__name__)


class Config:
    CONFIG = configparser.ConfigParser()
    CONFIG.read(os.path.join(os.path.dirname(__file__), "config.ini"))


class YAMLConfig:
    CONFIG = dict()
    try:
        with open(
            os.path.join(os.path.dirname(__file__), "config.yaml")
        ) as config_file:
            CONFIG = yaml.safe_load(config_file)

        if CONFIG is not None:
            with open(
                os.path.join(os.path.dirname(__file__), "secrets.yaml")
            ) as secrets_file:
                CONFIG["Secrets"] = yaml.safe_load(secrets_file)
    except FileNotFoundError:
        LOG.error(
            "Failed to load YAML config. "
            "Please make sure you've used config_converter.py "
            "to convert your config file to the new format "
            "or filled in config.yaml + secrets.yaml."
        )
        sys.exit(-1)
