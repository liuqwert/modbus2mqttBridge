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
        for master in self.bridge.masters.values():

            for slave in master.slaves.values():
                topic = self.config['command_topic'].format(
                    master=master.name,
                    slave_id=slave.slave_id
                )
                self.client.subscribe(topic)
                logger.info(f"Subscribed to {topic}")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload)

            # 解析主题
            master_name = topic.split('/')[2]
            slave_id = int(topic.split('/')[3])

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

    def publish_status(self, master_name, slave_id, data):
        topic = self.config['status_topic'].format(
            master=master_name,
            slave_id=slave_id
        )
        print("pub:", topic, data)
        self.client.publish(
            topic,
            payload=json.dumps(data),
            qos=self.config['qos'],
            retain=self.config['retain']
        )