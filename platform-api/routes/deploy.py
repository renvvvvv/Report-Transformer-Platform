# -*- coding: utf-8 -*-
"""
部署管理路由
处理服务的部署、启动、停止和删除
"""

import os
import json
from flask import Blueprint, request, jsonify

from core.docker_generator import DockerGenerator
from core.nginx_manager import NginxManager

deploy_bp = Blueprint('deploy', __name__)

SERVICES_DIR = os.environ.get('SERVICES_DIR', '/app/services')
UPLOAD_FOLDER = os.environ.get('UPLOADS_DIR', '/app/uploads')


def get_docker_generator():
    return DockerGenerator(SERVICES_DIR)


def get_nginx_manager():
    return NginxManager()


@deploy_bp.route('/deploy', methods=['POST'])
def deploy_service():
    """部署服务"""
    data = request.get_json()
    upload_id = data.get('upload_id')
    service_config = data.get('service_config', {})
    
    if not upload_id:
        return jsonify({'success': False, 'message': '缺少upload_id'}), 400
    
    try:
        # 获取生成的文件
        bundle_dir = os.path.join(UPLOAD_FOLDER, f"bundle_{upload_id}")
        generated_dir = os.path.join(bundle_dir, 'generated')
        
        if not os.path.exists(generated_dir):
            return jsonify({'success': False, 'message': '未找到生成的文件，请先执行转化'}), 400
        
        # 读取生成的文件
        generated_files = {}
        for root, dirs, files in os.walk(generated_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, generated_dir).replace(os.sep, '/')
                with open(fpath, 'r', encoding='utf-8') as f:
                    generated_files[rel_path] = f.read()
        
        # 服务名称
        service_name = service_config.get('name', f'report-{upload_id}')
        
        # 生成Docker配置
        docker_gen = get_docker_generator()
        port = docker_gen.get_next_available_port()
        
        # 添加Dockerfile和docker-compose（如果模板中没有）
        if 'Dockerfile' not in generated_files:
            generated_files['Dockerfile'] = docker_gen.generate_service_dockerfile()
        
        if 'docker-compose.yml' not in generated_files:
            service_path = service_config.get('path', f'/reports/{service_name}')
            generated_files['docker-compose.yml'] = docker_gen.generate_service_compose(
                service_name, port
            )
        
        # 写入服务目录
        service_dir = docker_gen.generate_service_files(service_name, generated_files)
        
        # 注册Nginx路由
        nginx_mgr = get_nginx_manager()
        service_path = service_config.get('path', f'/reports/{service_name}')
        nginx_mgr.add_service_route(service_name, service_path, service_name, 5000)
        nginx_mgr.reload_nginx()
        
        return jsonify({
            'success': True,
            'service_name': service_name,
            'service_dir': service_dir,
            'port': port,
            'path': service_path,
            'access_url': f"http://localhost{service_path}"
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'部署失败: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500


@deploy_bp.route('/deploy/build/<service_name>', methods=['POST'])
def build_service(service_name):
    """构建服务镜像"""
    docker_gen = get_docker_generator()
    success = docker_gen.build_service(service_name)
    
    return jsonify({
        'success': success,
        'service_name': service_name,
        'message': '构建成功' if success else '构建失败'
    })


@deploy_bp.route('/deploy/start/<service_name>', methods=['POST'])
def start_service(service_name):
    """启动服务"""
    docker_gen = get_docker_generator()
    success = docker_gen.start_service(service_name)
    
    return jsonify({
        'success': success,
        'service_name': service_name,
        'message': '启动成功' if success else '启动失败'
    })


@deploy_bp.route('/deploy/stop/<service_name>', methods=['POST'])
def stop_service(service_name):
    """停止服务"""
    docker_gen = get_docker_generator()
    success = docker_gen.stop_service(service_name)
    
    return jsonify({
        'success': success,
        'service_name': service_name,
        'message': '停止成功' if success else '停止失败'
    })


@deploy_bp.route('/deploy/restart/<service_name>', methods=['POST'])
def restart_service(service_name):
    """重启服务"""
    docker_gen = get_docker_generator()
    
    # 先停止
    docker_gen.stop_service(service_name)
    # 再启动
    success = docker_gen.start_service(service_name)
    
    return jsonify({
        'success': success,
        'service_name': service_name,
        'message': '重启成功' if success else '重启失败'
    })


@deploy_bp.route('/deploy/delete/<service_name>', methods=['DELETE'])
def delete_service(service_name):
    """删除服务"""
    try:
        # 停止服务
        docker_gen = get_docker_generator()
        docker_gen.stop_service(service_name)
        
        # 移除Nginx路由
        nginx_mgr = get_nginx_manager()
        nginx_mgr.remove_service_route(service_name)
        nginx_mgr.reload_nginx()
        
        # 删除服务目录
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
    """一键完整部署（解析+生成+部署+启动）"""
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
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            if fname.endswith('.py'):
                py_content = content
            elif fname.endswith('.md'):
                md_content = content
        
        # 2. 解析
        from core.html_parser import HTMLParser
        from core.skill_parser import SkillParser
        from core.transformer import Transformer
        
        html_parser = HTMLParser(html_content)
        html_info = html_parser.parse()
        
        skill_parser = SkillParser(py_content, md_content)
        skill_info = skill_parser.parse()
        
        # 3. 配置
        default_config = {
            'name': service_config.get('name', f'report-{upload_id}'),
            'title': service_config.get('title', html_info['title']),
            'datacenter': service_config.get('datacenter', 'default'),
            'refresh_strategy': service_config.get('refresh_strategy', 'cron'),
            'refresh_cron': service_config.get('refresh_cron', '0 */6 * * *'),
            'path': service_config.get('path', f"/reports/report-{upload_id}"),
        }
        
        # 4. 转化
        transformer = Transformer()
        generated_files = transformer.transform(html_info, skill_info, default_config)
        
        # 5. 部署
        docker_gen = get_docker_generator()
        port = docker_gen.get_next_available_port()
        
        if 'Dockerfile' not in generated_files:
            generated_files['Dockerfile'] = docker_gen.generate_service_dockerfile()
        
        if 'docker-compose.yml' not in generated_files:
            generated_files['docker-compose.yml'] = docker_gen.generate_service_compose(
                default_config['name'], port
            )
        
        service_dir = docker_gen.generate_service_files(default_config['name'], generated_files)
        
        # 6. 注册Nginx
        nginx_mgr = get_nginx_manager()
        nginx_mgr.add_service_route(
            default_config['name'],
            default_config['path'],
            default_config['name'],
            5000
        )
        nginx_mgr.reload_nginx()
        
        return jsonify({
            'success': True,
            'service_name': default_config['name'],
            'service_dir': service_dir,
            'port': port,
            'path': default_config['path'],
            'access_url': f"http://localhost{default_config['path']}",
            'message': '服务已生成并部署，请手动启动容器'
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'部署失败: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500
