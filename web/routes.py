# -*- coding: utf-8 -*-
"""
github: https://github.com/liuqwert/modbus2mqttBridge.git
author: liuqwert
email: 15251908@qq.com
"""


from flask import Blueprint, jsonify, request, render_template, Flask
from core.bridge import ModbusBridge

bp = Blueprint('main', __name__)

def start_web(bridge: ModbusBridge, config):
    @bp.route('/')
    def index():
        return render_template('index.html')

    @bp.route('/api/status')
    def get_status():
        status = []
        for master in bridge.masters.values():
            master_data = {
                'name': master.name,
                'slaves': []
            }
            for slave in master.slaves.values():
                for reg in slave.parsed_registers.values():
                    master_data['slaves'].append({
                        'id': slave.slave_id,
                        'data': reg['data_cache']
                    })
            status.append(master_data)
        return jsonify(status)

    @bp.route('/api/write', methods=['POST'])
    def handle_write():
        data = request.json
        success = bridge.write_register(
            data['master'],
            data['slave_id'],
            data['address'],
            data['value']
        )
        return jsonify({'success': success})

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.run(
        host=config['web']['host'],
        port=config['web']['port'],
        debug=config['web']['debug']
    )