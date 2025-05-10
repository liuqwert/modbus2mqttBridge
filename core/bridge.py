# -*- coding: utf-8 -*-
"""
github: https://github.com/liuqwert/modbus2mqttBridge.git
author: liuqwert
email: 15251908@qq.com
"""


from typing import List, Dict
from loguru import logger

from core.modbus import ModbusMaster
from core.mqtt import MQTTClient


class ModbusBridge:
    def __init__(self, config: dict):
        """初始化Modbus-MQTT桥接核心"""
        self.masters: Dict[str, ModbusMaster] = {}
        self.mqtt_client: MQTTClient = None
        self._init_components(config)

    def _init_components(self, config: dict):
        """初始化所有组件"""
        # 初始化MQTT客户端
        self.mqtt_client = MQTTClient(config['mqtt'], self)

        # 初始化Modbus主站
        for master_cfg in config['modbus']:
            master = ModbusMaster(master_cfg, self.mqtt_client)
            self.masters[master_cfg['name']] = master

        logger.success(f"Initialized {len(self.masters)} Modbus masters")

    def write_register(self, master_name: str, slave_id: int,
                       address: int, value: int) -> bool:
        """
        写入寄存器统一入口
        :param master_name: 主站名称
        :param slave_id: 从站ID
        :param address: PLC地址(如40001)
        :param value: 要写入的值
        :return: 是否成功
        """
        master = self.masters[master_name]
        if master:
            return master.write_register(slave_id, address, value)
        logger.warning(f"Master {master_name} not found")
        return False

    def start(self):
        """启动所有服务"""
        # 启动MQTT
        self.mqtt_client.start()

        # 启动所有Modbus主站
        for master in self.masters.values():
            master.start()

        logger.info("All services started")

    def stop(self):
        """停止所有服务"""
        # 停止Modbus连接
        for master in self.masters.values():
            master.stop()

        # 停止MQTT
        self.mqtt_client.stop()

        logger.info("All services stopped")

