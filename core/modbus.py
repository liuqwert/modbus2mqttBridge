# -*- coding: utf-8 -*-
"""
github: https://github.com/liuqwert/modbus2mqttBridge.git
author: liuqwert
email: 15251908@qq.com
"""


import time
from typing import Dict, Any
from loguru import logger
import threading

from pymodbus import ModbusException
from pymodbus.client import ModbusTcpClient

from core.mqtt import MQTTClient


mapping = {
    "0": ("0x", 0x01, 0x05), # coils
    "1": ("1x", 0x02, None), # discrete_inputs
    "3": ("3x", 0x04, None), # input_registers
    "4": ("4x", 0x03, 0x06), # holding_registers
}

def plc_to_modbus(plc_address: int) -> Dict:
    address_str = f"{int(plc_address):06d}"
    prefix = address_str[0]
    address = int(address_str[1:]) - 1

    if prefix not in mapping:
        raise ValueError(f"Invalid PLC address prefix: {prefix}")

    name, read_code, write_code = mapping[prefix]
    return {"type": name, "plc_address": plc_address, "address": address, "read_code": read_code, "write_code": write_code}


class ModbusSlave:
    def __init__(self, slave_config, master_name):
        self.slave_id = slave_config['slave_id']
        self.registers = slave_config['registers']
        self.master_name = master_name
        self.data_cache: Dict[int, Any] = {}

        self.parsed_registers = {}
        for reg_conf in self.registers:
            reg = plc_to_modbus(reg_conf['start'])
            reg['count'] = reg_conf['count']
            self.parsed_registers[reg_conf['start']] = reg


class ModbusMaster:
    """Modbus主站管理器"""

    def __init__(self, config: dict, mqtt_client: MQTTClient):
        self.name = config['name']
        self.host = config['host']
        self.port = config['port']
        self.poll_interval = config['poll_interval']
        self.reconnect_interval = config.get('reconnect_interval', 5)
        self.mqtt_client = mqtt_client

        self.client = ModbusTcpClient(config['host'], port=config['port'])
        self.client.connect()

        self.lock = threading.Lock()

        self.slaves: Dict[int, ModbusSlave] = {}
        self._running = False
        self._init_slaves(config['slaves'])

    def _init_slaves(self, slaves_config: list):
        """初始化从站"""
        for slave_cfg in slaves_config:
            slave = ModbusSlave(
                slave_config=slave_cfg,
                master_name=self.name,
            )
            self.slaves[slave.slave_id] = slave
        logger.info(f"Initialized {len(self.slaves)} slaves for master {self.name}")

    def start(self):
        """启动轮询线程"""
        self._running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def _poll_loop(self):
        """持续轮询数据"""
        while self._running:
            try:
                if not self.client.connected:
                    self.client.connect()

                data = {}
                with self.lock:
                    for slave in self.slaves.values():
                        for reg in slave.parsed_registers.values():
                            # key = f"{reg['plc_address']}-{reg['plc_address'] + reg['count'] -1}"
                            val = None
                            if reg['type'] == "4x":
                                response = self.client.read_holding_registers(
                                    reg['address'],
                                    count=reg['count'],
                                    slave=slave.slave_id
                                )
                                val = response.registers
                            elif reg['type'] == "3x":
                                response = self.client.read_input_registers(
                                    reg['address'],
                                    count=reg['count'],
                                    slave=slave.slave_id
                                )
                                val = response.registers
                            elif reg['type'] == "1x":
                                response = self.client.read_discrete_inputs(
                                    reg['address'],
                                    count=reg['count'],
                                    slave=slave.slave_id
                                )
                                val = response.bits
                            elif reg['type'] == "0x":
                                response = self.client.read_coils(
                                    reg['address'],
                                    count=reg['count'],
                                    slave=slave.slave_id
                                )
                                val = response.bits
                            if response.isError() or not val:
                                logger.opt(exception=True).error(f"Read error: {response}")
                                continue

                            time.sleep(0.5) # modbus指令之间的延时
                            # slave.data_cache = data
                            if reg['count'] == len(val):
                                for i in range(reg['count']):
                                    slave.data_cache[reg['plc_address'] + i] = val[i]

                        self.mqtt_client.publish_status(self.name, slave.slave_id, slave.data_cache)
            except ModbusException as e:
                logger.opt(exception=True).error(f"Modbus error: {e}")
            except Exception as e:
                logger.opt(exception=True).error(f"Unexpected error: {e}")

            time.sleep(self.poll_interval)

    def write_register(self, slave_id: int, plc_address: int, value: int):
        """处理PLC地址格式的写入请求"""
        try:
            plc_address = int(plc_address)
            parsed = plc_to_modbus(plc_address)
            if not parsed['write_code']:
                raise ValueError("Write not supported for this address type")

            with self.lock:
                if parsed['type'] == "4x":
                    result = self.client.write_register(
                        address=parsed['address'],
                        value=value,
                        slave=slave_id
                    )
                elif parsed['type'] == "0x":
                    result = self.client.write_coil(
                        address=parsed['address'],
                        value=bool(value),
                        slave=slave_id
                    )
                    value = bool(value)
                else:
                    raise ValueError("Unsupported write operation:{}", [slave_id, plc_address, value, parsed])

                if result.isError():
                    return False

                # 立即读取验证
                time.sleep(0.5)
                if parsed['type'] == "4x":
                    response = self.client.read_holding_registers(parsed['address'], count=1, slave=slave_id)
                    current_value = response.registers[0] if not response.isError() else None
                elif parsed['type'] == "0x":
                    response = self.client.read_coils(parsed['address'], count=1, slave=slave_id)
                    current_value = response.bits[0] if not response.isError() else None

                if current_value == value:
                    self.mqtt_client.publish_status(
                        self.name, slave_id,
                        {f"{plc_address}": current_value}
                    )
                    self.slaves[slave_id].data_cache[plc_address] = value
                    return True
                return False
        except Exception as e:
            logger.opt(exception=True).error(f"Address conversion failed: {e}")
            return None

    def stop(self):
        """停止主站服务"""
        self._running = False
        self.client.close()
        logger.info(f"Master {self.name} service stopped")