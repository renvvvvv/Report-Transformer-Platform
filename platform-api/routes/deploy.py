# -*- coding: utf-8 -*-
"""
部署管理路由
处理服务的部署、启动、停止和删除 - 在平台容器内直接运行子进程
"""

import os
import json
import re
from flask import Blueprint, request, jsonify

from core.service_runner import ServiceRunner
from core.nginx_manager import NginxManager

deploy_bp = Blueprint('deploy', __name__)

SERVICES_DIR = os.environ.get('SERVICES_DIR', '/app/services')
UPLOAD_FOLDER = os.environ.get('UPLOADS_DIR', '/app/uploads')


def get_service_runner():
    return ServiceRunner(SERVICES_DIR)


def get_nginx_manager():
    return NginxManager()


@deploy_bp.route('/deploy', methods=['POST'])
def deploy_service():
    """部署服务（生成代码+配置Nginx）"""
    data = request.get_json()
    upload_id = data.get('upload_id')
    service_config = data.get('service_config', {})
    
    if not upload_id:
        return jsonify({'success': False, 'message': '缺少upload_id'}), 400
    
    try:
        bundle_dir = os.path.join(UPLOAD_FOLDER, f"bundle_{upload_id}")
        generated_dir = os.path.join(bundle_dir, 'generated')
        
        if not os.path.exists(generated_dir):
            return jsonify({'success': False, 'message': '未找到生成的文件，请先执行转化'}), 400
        
        generated_files = {}
        for root, dirs, files in os.walk(generated_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, generated_dir).replace(os.sep, '/')
                with open(fpath, 'r', encoding='utf-8') as f:
                    generated_files[rel_path] = f.read()
        
        service_name = service_config.get('name', f'report-{upload_id}')
        safe_name = re.sub(r'[^a-z0-9]+', '-', service_name.lower()).strip('-')
        if not safe_name:
            safe_name = f'report-{upload_id}'
        
        # 生成Docker配置（保留用于参考）
        from core.docker_generator import DockerGenerator
        docker_gen = DockerGenerator(SERVICES_DIR)
        port = docker_gen.get_next_available_port()
        
        if 'Dockerfile' not in generated_files:
            generated_files['Dockerfile'] = docker_gen.generate_service_dockerfile()
        
        if 'docker-compose.yml' not in generated_files:
            generated_files['docker-compose.yml'] = docker_gen.generate_service_compose(safe_name, port)
        
        service_dir = docker_gen.generate_service_files(safe_name, generated_files)
        
        # 注册Nginx路由
        nginx_mgr = get_nginx_manager()
        service_path = service_config.get('path', f'/reports/{safe_name}')
        nginx_mgr.add_service_route(safe_name, service_path, safe_name, 5000)
        nginx_mgr.reload_nginx()
        
        return jsonify({
            'success': True,
            'service_name': safe_name,
            'service_dir': service_dir,
            'path': service_path,
            'access_url': f"http://localhost{service_path}",
            'message': '服务代码已生成，请调用 /api/deploy/start/{service_name} 启动服务'
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'部署失败: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500


@deploy_bp.route('/deploy/start/<service_name>', methods=['POST'])
def start_service(service_name):
    """启动服务子进程（真正的运行）"""
    runner = get_service_runner()
    
    # 检查服务目录是否存在
    service_dir = os.path.join(SERVICES_DIR, service_name)
    if not os.path.exists(service_dir):
        return jsonify({
            'success': False,
            'message': f'服务目录不存在: {service_name}'
        }), 404
    
    result = runner.start_service(service_name)
    
    if result['success']:
        port = result['port']
        
        # 更新Nginx路由指向实际端口
        nginx_mgr = get_nginx_manager()
        
        # 读取配置获取path
        import yaml
        config_path = os.path.join(service_dir, 'config.yml')
        service_path = f'/reports/{service_name}'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
                service_path = config.get('path', service_path)
            except:
                pass
        
        nginx_mgr.add_service_route(service_name, service_path, service_name, port)
        nginx_mgr.reload_nginx()
        
        return jsonify({
            'success': True,
            'service_name': service_name,
            'message': '服务已启动',
            'pid': result['pid'],
            'port': port,
            'access_url': f'http://localhost{service_path}'
        })
    else:
        return jsonify({
            'success': False,
            'service_name': service_name,
            'message': result.get('message', '启动失败'),
            'details': result.get('stderr', '')
        }), 500


@deploy_bp.route('/deploy/stop/<service_name>', methods=['POST'])
def stop_service(service_name):
    """停止服务"""
    runner = get_service_runner()
    success = runner.stop_service(service_name)
    
    return jsonify({
        'success': success,
        'service_name': service_name,
        'message': '服务已停止' if success else '服务未运行'
    })


@deploy_bp.route('/deploy/restart/<service_name>', methods=['POST'])
def restart_service(service_name):
    """重启服务"""
    runner = get_service_runner()
    result = runner.restart_service(service_name)
    
    if result['success']:
        port = result['port']
        
        # 更新Nginx路由
        nginx_mgr = get_nginx_manager()
        service_dir = os.path.join(SERVICES_DIR, service_name)
        import yaml
        config_path = os.path.join(service_dir, 'config.yml')
        service_path = f'/reports/{service_name}'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
                service_path = config.get('path', service_path)
            except:
                pass
        
        nginx_mgr.add_service_route(service_name, service_path, service_name, port)
        nginx_mgr.reload_nginx()
        
        return jsonify({
            'success': True,
            'service_name': service_name,
            'pid': result['pid'],
            'port': port,
            'message': '服务已重启'
        })
    else:
        return jsonify({
            'success': False,
            'service_name': service_name,
            'message': result.get('message', '重启失败')
        }), 500


@deploy_bp.route('/deploy/status/<service_name>', methods=['GET'])
def service_status(service_name):
    """获取服务状态"""
    runner = get_service_runner()
    status = runner.get_service_status(service_name)
    logs = runner.get_service_logs(service_name, tail=20)
    
    return jsonify({
        'success': True,
        'service_name': service_name,
        'status': status.get('status', 'unknown'),
        'pid': status.get('pid'),
        'port': status.get('port'),
        'started_at': status.get('started_at'),
        'logs': logs
    })


@deploy_bp.route('/deploy/logs/<service_name>', methods=['GET'])
def service_logs(service_name):
    """获取服务日志"""
    tail = request.args.get('tail', 50, type=int)
    runner = get_service_runner()
    logs = runner.get_service_logs(service_name, tail=tail)
    
    return jsonify({
        'success': True,
        'service_name': service_name,
        'logs': logs
    })


@deploy_bp.route('/deploy/delete/<service_name>', methods=['DELETE'])
def delete_service(service_name):
    """删除服务"""
    try:
        runner = get_service_runner()
        runner.stop_service(service_name)
        
        nginx_mgr = get_nginx_manager()
        nginx_mgr.remove_service_route(service_name)
        nginx_mgr.reload_nginx()
        
        import shutil
        service_dir = os.path.join(SERVICES_DIR, service_name)
        if os.path.exists(service_dir):
            shutil.rmtree(service_dir)
        
        return jsonify({
            'success': True,
            'service_name': service_name,
            'message': '服务已删除'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500


@deploy_bp.route('/deploy/full', methods=['POST'])
def full_deploy():
    """
    一键完整部署：解析 + 生成 + 部署 + 启动子进程
    真正的端到端部署，服务会在平台容器内以子进程运行
    """
    data = request.get_json()
    upload_id = data.get('upload_id')
    service_config = data.get('service_config', {})
    
    if not upload_id:
        return jsonify({'success': False, 'message': '缺少upload_id'}), 400
    
    try:
        # 1. 读取原始文件
        bundle_dir = os.path.join(UPLOAD_FOLDER, f"bundle_{upload_id}")
        
        html_path = os.path.join(bundle_dir, 'report.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        skill_dir = os.path.join(bundle_dir, 'skill')
        py_content = ''
        md_content = ''
        
        for fname in os.listdir(skill_dir):
            fpath = os.path.join(skill_dir, fname)
            if fname.startswith('.') or fname.endswith('.pyc') or fname.endswith('.DS_Store'):
                continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, IOError):
                continue
            if fname.endswith('.py'):
                py_content = content
            elif fname.endswith('.md'):
                md_content = content
        
        # 2. 深度解析
        from core.html_parser import HTMLParser
        from core.skill_parser import SkillParser
        from core.transformer import Transformer
        
        html_parser = HTMLParser(html_content)
        html_info = html_parser.parse()
        
        skill_parser = SkillParser(py_content, md_content)
        skill_info = skill_parser.parse()
        
        # 3. 服务名称处理
        raw_name = service_config.get('name', f'report-{upload_id}')
        safe_name = re.sub(r'[^a-z0-9]+', '-', raw_name.lower()).strip('-')
        if not safe_name:
            safe_name = f'report-{upload_id}'
        
        default_config = {
            'name': safe_name,
            'title': service_config.get('title', html_info['title']),
            'datacenter': service_config.get('datacenter', 'default'),
            'refresh_strategy': service_config.get('refresh_strategy', 'cron'),
            'refresh_cron': service_config.get('refresh_cron', '0 */6 * * *'),
            'path': service_config.get('path', f"/reports/{safe_name}"),
        }
        
        # 4. 智能转化生成代码
        transformer = Transformer()
        generated_files = transformer.transform(html_info, skill_info, default_config)
        
        # 5. 生成Docker配置（保留参考）
        from core.docker_generator import DockerGenerator
        docker_gen = DockerGenerator(SERVICES_DIR)
        port = docker_gen.get_next_available_port()
        
        if 'Dockerfile' not in generated_files:
            generated_files['Dockerfile'] = docker_gen.generate_service_dockerfile()
        
        if 'docker-compose.yml' not in generated_files:
            generated_files['docker-compose.yml'] = docker_gen.generate_service_compose(safe_name, port)
        
        service_dir = docker_gen.generate_service_files(safe_name, generated_files)
        
        # 6. 注册Nginx（先占位，端口后面更新）
        nginx_mgr = get_nginx_manager()
        nginx_mgr.add_service_route(safe_name, default_config['path'], safe_name, 5000)
        nginx_mgr.reload_nginx()
        
        # 7. 启动子进程服务！
        runner = get_service_runner()
        start_result = runner.start_service(safe_name)
        
        if start_result['success']:
            actual_port = start_result['port']
            
            # 更新Nginx路由指向实际端口
            nginx_mgr.add_service_route(safe_name, default_config['path'], safe_name, actual_port)
            nginx_mgr.reload_nginx()
            
            return jsonify({
                'success': True,
                'service_name': safe_name,
                'service_dir': service_dir,
                'port': actual_port,
                'path': default_config['path'],
                'access_url': f"http://localhost{default_config['path']}",
                'pid': start_result['pid'],
                'message': '服务已成功部署并启动',
                'status': 'running'
            })
        else:
            # 代码已生成但启动失败
            return jsonify({
                'success': True,
                'service_name': safe_name,
                'service_dir': service_dir,
                'path': default_config['path'],
                'access_url': f"http://localhost{default_config['path']}",
                'status': 'code_generated',
                'message': '服务代码已生成，但启动失败',
                'error': start_result.get('message', '未知错误'),
                'details': start_result.get('stderr', '')
            })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'部署失败: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500
