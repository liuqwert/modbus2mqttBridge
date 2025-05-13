# -*- coding: utf-8 -*-
"""
github: https://github.com/liuqwert/modbus2mqttBridge.git
author: liuqwert
email: 15251908@qq.com
"""


import json
import paho.mqtt.client as mqtt
from loguru import logger


class MQTTClient:
    def __init__(self, config, modbus_bridge):
        self.config = config
        self.bridge = modbus_bridge
        self.client = mqtt.Client()
        self.client.username_pw_set(config['username'], config['passwd'])
        # 设置回调
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message


        # 连接参数
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)  # 最小1秒，最大120秒
        self.client.connect(config['broker'], config['port'])
        # self.client.loop_start()

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.success("Connected to MQTT Broker")
            self._subscribe_all()
        else:
            logger.opt(exception=True).error(f"Connection failed with code {rc}")

    def _subscribe_all(self):
        topic = self.config['command_topic']
        self.client.subscribe(topic)
        logger.info(f"Subscribed to {topic}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)

            # 解析主题
            master_name = payload['master_name']
            slave_id = int(payload['slave_id'])

            # 执行写入
            success = self.bridge.write_register(
                master_name=master_name,
                slave_id=slave_id,
                address=payload['address'],
                value=payload['value']
            )

            logger.info(f"Write {'successful' if success else 'failed'} via MQTT")

        except Exception as e:
            logger.opt(exception=True).error(f"Error processing MQTT message: {e}")

    def publish_status(self, master_name, slave_id, data, reg_conf):
        if reg_conf['topic'] == "attribute":
            topic_addr = self.config['attribute_topic'].format(
                device=reg_conf['device'],
                # master=master_name,
                # slave_id=slave_id,
                # name=reg_conf['name'],
                # gid=reg_conf['gid'],
            )
        elif reg_conf['topic'] == "telemetry":
            topic_addr = self.config['telemetry_topic'].format(
                device=reg_conf['device'],
                # master=master_name,
                # slave_id=slave_id,
                # name=reg_conf['name'],
                # gid=reg_conf['gid'],
            )
        else:
            logger.error("unknown topic:{}", reg_conf['topic'])
            return
        logger.debug("pub:{} : {}", topic_addr, data)
        self.client.publish(
            topic_addr,
            payload=json.dumps(data),
            qos=self.config['qos'],
            retain=self.config['retain']
        )