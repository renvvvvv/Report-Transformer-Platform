# -*- coding: utf-8 -*-
"""
服务管理路由
查询和管理已部署的服务
"""

import os
from flask import Blueprint, request, jsonify

from core.docker_generator import DockerGenerator
from core.nginx_manager import NginxManager

services_bp = Blueprint('services', __name__)

SERVICES_DIR = os.environ.get('SERVICES_DIR', '/app/services')


def get_docker_generator():
    return DockerGenerator(SERVICES_DIR)


def get_nginx_manager():
    return NginxManager()


@services_bp.route('/services', methods=['GET'])
def list_services():
    """列出所有服务"""
    docker_gen = get_docker_generator()
    services = docker_gen.list_services()
    
    return jsonify({
        'success': True,
        'count': len(services),
        'services': services
    })


@services_bp.route('/services/<service_name>', methods=['GET'])
def get_service(service_name):
    """获取单个服务详情"""
    docker_gen = get_docker_generator()
    status = docker_gen.get_service_status(service_name)
    
    # 读取配置
    import yaml
    config_path = os.path.join(SERVICES_DIR, service_name, 'config.yml')
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        except:
            pass
    
    # 读取映射信息
    mapping_path = os.path.join(SERVICES_DIR, service_name, '_mapping.json')
    mapping = {}
    if os.path.exists(mapping_path):
        try:
            import json
            with open(mapping_path, 'r') as f:
                mapping = json.load(f)
        except:
            pass
    
    return jsonify({
        'success': True,
        'service': {
            'name': service_name,
            'title': config.get('title', service_name),
            'status': status['status'],
            'container_id': status.get('container_id', ''),
            'uptime': status.get('uptime', ''),
            'config': config,
            'mapping': mapping
        }
    })


@services_bp.route('/services/<service_name>/logs', methods=['GET'])
def get_service_logs(service_name):
    """获取服务日志"""
    tail = request.args.get('tail', '100')
    
    import subprocess
    try:
        result = subprocess.run(
            ['docker', 'logs', '--tail', tail, service_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return jsonify({
            'success': True,
            'service_name': service_name,
            'logs': result.stdout if result.returncode == 0 else result.stderr
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取日志失败: {str(e)}'
        }), 500


@services_bp.route('/services/<service_name>/config', methods=['PUT'])
def update_service_config(service_name):
    """更新服务配置"""
    data = request.get_json()
    
    import yaml
    config_path = os.path.join(SERVICES_DIR, service_name, 'config.yml')
    
    if not os.path.exists(config_path):
        return jsonify({'success': False, 'message': '服务配置不存在'}), 404
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        # 更新配置
        if 'refresh' in data:
            config['refresh'].update(data['refresh'])
        if 'datacenter' in data:
            config['datacenter'] = data['datacenter']
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
        
        return jsonify({
            'success': True,
            'message': '配置已更新',
            'config': config
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@services_bp.route('/routes', methods=['GET'])
def list_routes():
    """列出所有Nginx路由"""
    nginx_mgr = get_nginx_manager()
    routes = nginx_mgr.list_routes()
    
    return jsonify({
        'success': True,
        'count': len(routes),
        'routes': routes
    })


@services_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'platform': 'report-transformer-platform',
        'version': '1.0.0'
    })
