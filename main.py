# -*- coding: utf-8 -*-
"""
name: modbus2mqttBridge
github: https://github.com/liuqwert/modbus2mqttBridge.git
author: liuqwert
email: 15251908@qq.com
"""


import yaml

from core.bridge import ModbusBridge
from web.routes import start_web


def load_config():
    with open('config/config.yaml') as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    # load config
    config = load_config()

    # init bridge
    bridge = ModbusBridge(config)
    bridge.start()
    # start web
    start_web(bridge, config)
