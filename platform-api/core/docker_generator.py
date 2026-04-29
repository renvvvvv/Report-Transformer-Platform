# -*- coding: utf-8 -*-
"""
Docker配置生成器
生成服务所需的Dockerfile和docker-compose配置，并管理容器生命周期
使用纯docker命令（不依赖docker-compose）
"""

import os
import yaml
import subprocess
import json
import time
from typing import Dict, List, Any


class DockerGenerator:
    """生成Docker相关配置文件并管理容器"""
    
    def __init__(self, services_base_dir: str = None):
        if services_base_dir is None:
            services_base_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'services')
        self.services_base_dir = services_base_dir
    
    def generate_service_files(self, service_name: str, generated_files: Dict[str, str]) -> str:
        """将生成的文件写入服务目录"""
        service_dir = os.path.join(self.services_base_dir, service_name)
        app_dir = os.path.join(service_dir, 'app')
        templates_dir = os.path.join(app_dir, 'templates')
        static_dir = os.path.join(app_dir, 'static')
        cache_dir = os.path.join(service_dir, 'cache')
        
        os.makedirs(service_dir, exist_ok=True)
        os.makedirs(app_dir, exist_ok=True)
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(static_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        file_mapping = {
            'app.py': os.path.join(app_dir, 'app.py'),
            'data_fetcher.py': os.path.join(app_dir, 'data_fetcher.py'),
            'calculator.py': os.path.join(app_dir, 'calculator.py'),
            'templates/index.html': os.path.join(templates_dir, 'index.html'),
            'Dockerfile': os.path.join(app_dir, 'Dockerfile'),
            'docker-compose.yml': os.path.join(service_dir, 'docker-compose.yml'),
            'requirements.txt': os.path.join(app_dir, 'requirements.txt'),
            'config.yml': os.path.join(service_dir, 'config.yml'),
        }
        
        for file_key, file_path in file_mapping.items():
            if file_key in generated_files:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(generated_files[file_key])
        
        if '_mapping.json' in generated_files:
            mapping_path = os.path.join(service_dir, '_mapping.json')
            with open(mapping_path, 'w', encoding='utf-8') as f:
                f.write(generated_files['_mapping.json'])
        
        return service_dir
    
    def generate_service_dockerfile(self) -> str:
        """生成极简Dockerfile - 使用python:3.11-slim，不安装系统包"""
        return '''FROM python:3.11-slim

WORKDIR /app

# 只安装Python依赖（纯Python包不需要gcc）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/cache

EXPOSE 5000

CMD ["python", "app.py"]
'''
    
    def generate_service_compose(self, service_name: str, port: int = None) -> str:
        """生成docker-compose配置（供参考，实际使用docker run）"""
        if port is None:
            port = 5000 + (hash(service_name) % 1000)
        
        compose = {
            'services': {
                service_name: {
                    'build': './app',
                    'container_name': service_name,
                    'ports': [f'{port}:5000'],
                    'volumes': [
                        './config.yml:/app/config.yml:ro',
                        './cache:/app/cache'
                    ],
                    'environment': [
                        'FLASK_ENV=production',
                        'SERVICE_NAME=' + service_name,
                    ],
                    'networks': ['report-platform'],
                    'restart': 'unless-stopped',
                }
            },
            'networks': {
                'report-platform': {
                    'external': True
                }
            }
        }
        
        return yaml.dump(compose, sort_keys=False, allow_unicode=True)
    
    def get_next_available_port(self) -> int:
        """获取下一个可用端口"""
        base_port = 5001
        used_ports = set()
        
        if os.path.exists(self.services_base_dir):
            for service_dir in os.listdir(self.services_base_dir):
                compose_path = os.path.join(self.services_base_dir, service_dir, 'docker-compose.yml')
                if os.path.exists(compose_path):
                    try:
                        with open(compose_path, 'r') as f:
                            compose = yaml.safe_load(f)
                            for svc in compose.get('services', {}).values():
                                for port_mapping in svc.get('ports', []):
                                    if isinstance(port_mapping, str):
                                        host_port = int(port_mapping.split(':')[0])
                                        used_ports.add(host_port)
                    except:
                        pass
        
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Ports}}'],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.strip().split('\n'):
                if '->' in line:
                    for part in line.split(','):
                        part = part.strip()
                        if '->' in part and ':' in part:
                            host_part = part.split(':')[1].split('-')[0] if ':' in part else ''
                            if host_part.isdigit():
                                used_ports.add(int(host_part))
        except:
            pass
        
        port = base_port
        while port in used_ports:
            port += 1
        
        return port
    
    def _ensure_network(self):
        """确保Docker网络存在"""
        try:
            result = subprocess.run(
                ['docker', 'network', 'ls', '--filter', 'name=report-platform', '--format', '{{.Name}}'],
                capture_output=True, text=True, timeout=10
            )
            if 'report-platform' not in result.stdout:
                subprocess.run(
                    ['docker', 'network', 'create', 'report-platform'],
                    capture_output=True, timeout=10
                )
                return True
        except:
            pass
        return False
    
    def build_and_start_service(self, service_name: str, timeout: int = 180) -> Dict[str, Any]:
        """
        使用纯docker命令构建并启动服务（不依赖docker-compose）
        """
        service_dir = os.path.join(self.services_base_dir, service_name)
        app_dir = os.path.join(service_dir, 'app')
        
        if not os.path.exists(app_dir):
            return {'success': False, 'error': f'找不到应用目录: {app_dir}'}
        
        result = {'success': False, 'logs': [], 'container_id': None}
        image_name = f"svc-{service_name.lower().replace(' ', '-').replace('_', '-')}"
        container_name = service_name.lower().replace(' ', '-').replace('_', '-')
        
        # 1. 确保网络
        if self._ensure_network():
            result['logs'].append('[INFO] 创建网络: report-platform')
        
        # 2. 停止并删除旧容器
        try:
            subprocess.run(['docker', 'stop', container_name], capture_output=True, timeout=10)
            subprocess.run(['docker', 'rm', container_name], capture_output=True, timeout=10)
            result['logs'].append('[INFO] 已清理旧容器')
        except:
            pass
        
        # 3. 构建镜像（分步执行，先检查基础镜像）
        try:
            result['logs'].append(f'[INFO] 开始构建镜像: {image_name}...')
            
            # 先检查是否有python:3.11-slim镜像
            check_img = subprocess.run(
                ['docker', 'images', 'python:3.11-slim', '--format', '{{.Repository}}'],
                capture_output=True, text=True, timeout=10
            )
            if 'python' not in check_img.stdout:
                result['logs'].append('[INFO] 正在拉取基础镜像 python:3.11-slim...')
                pull_proc = subprocess.run(
                    ['docker', 'pull', 'python:3.11-slim'],
                    capture_output=True, text=True, timeout=120
                )
                if pull_proc.returncode != 0:
                    result['logs'].append('[WARN] 拉取基础镜像失败，尝试使用本地缓存')
            
            build_proc = subprocess.run(
                ['docker', 'build', '-t', image_name, '.'],
                cwd=app_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if build_proc.returncode != 0:
                result['logs'].append(f'[ERROR] 构建失败')
                result['error'] = build_proc.stderr[-1000:] if build_proc.stderr else '构建失败'
                return result
            
            result['logs'].append('[INFO] 镜像构建成功')
        except subprocess.TimeoutExpired:
            result['logs'].append(f'[ERROR] 构建超时（>{timeout}秒）')
            result['error'] = 'Docker构建超时，可能是网络问题导致基础镜像下载慢'
            return result
        except Exception as e:
            result['logs'].append(f'[ERROR] 构建异常: {str(e)}')
            result['error'] = str(e)
            return result
        
        # 4. 读取端口配置
        port = 5000
        compose_path = os.path.join(service_dir, 'docker-compose.yml')
        if os.path.exists(compose_path):
            try:
                with open(compose_path, 'r') as f:
                    compose = yaml.safe_load(f)
                for svc in compose.get('services', {}).values():
                    for port_mapping in svc.get('ports', []):
                        if isinstance(port_mapping, str):
                            port = int(port_mapping.split(':')[0])
                            break
            except:
                pass
        
        # 5. 启动容器
        try:
            result['logs'].append(f'[INFO] 启动容器: {container_name} (端口 {port})...')
            run_proc = subprocess.run(
                [
                    'docker', 'run', '-d',
                    '--name', container_name,
                    '--network', 'report-platform',
                    '-p', f'{port}:5000',
                    '-v', f'{service_dir}/config.yml:/app/config.yml:ro',
                    '-v', f'{service_dir}/cache:/app/cache',
                    '-e', f'SERVICE_NAME={service_name}',
                    '-e', 'FLASK_ENV=production',
                    '--restart', 'unless-stopped',
                    image_name
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if run_proc.returncode != 0:
                result['logs'].append(f'[ERROR] 启动失败: {run_proc.stderr[:500]}')
                result['error'] = run_proc.stderr[:1000]
                return result
            
            container_id = run_proc.stdout.strip()
            result['container_id'] = container_id[:12]
            result['logs'].append(f'[INFO] 容器启动成功: {container_id[:12]}')
            
            # 6. 等待并检查健康状态
            time.sleep(3)
            health_proc = subprocess.run(
                ['docker', 'ps', '--filter', f'id={container_id}', '--format', '{{.Status}}'],
                capture_output=True, text=True, timeout=10
            )
            status = health_proc.stdout.strip()
            result['logs'].append(f'[INFO] 容器状态: {status}')
            
            result['success'] = True
            result['port'] = port
            
        except Exception as e:
            result['logs'].append(f'[ERROR] 启动异常: {str(e)}')
            result['error'] = str(e)
        
        return result
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """获取服务状态"""
        container_name = service_name.lower().replace(' ', '-').replace('_', '-')
        
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{json .}}'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.stdout.strip():
                info = json.loads(result.stdout.strip())
                return {
                    'name': service_name,
                    'status': 'running' if 'Up' in info.get('Status', '') else 'stopped',
                    'container_id': info.get('ID', '')[:12],
                    'ports': info.get('Ports', ''),
                    'uptime': info.get('Status', '')
                }
            
            # 检查是否已停止
            all_result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', f'name={container_name}', '--format', '{{json .}}'],
                capture_output=True, text=True, timeout=10
            )
            if all_result.stdout.strip():
                info = json.loads(all_result.stdout.strip())
                return {
                    'name': service_name,
                    'status': 'exited',
                    'container_id': info.get('ID', '')[:12],
                    'ports': info.get('Ports', ''),
                }
            
            return {
                'name': service_name,
                'status': 'not_deployed',
                'container_id': '',
                'ports': '',
            }
        except Exception as e:
            return {
                'name': service_name,
                'status': 'error',
                'error': str(e)
            }
    
    def stop_service(self, service_name: str) -> bool:
        """停止并删除服务容器"""
        container_name = service_name.lower().replace(' ', '-').replace('_', '-')
        
        try:
            subprocess.run(['docker', 'stop', container_name], capture_output=True, timeout=15)
            subprocess.run(['docker', 'rm', container_name], capture_output=True, timeout=15)
            return True
        except:
            return False
    
    def restart_service(self, service_name: str) -> bool:
        """重启服务"""
        container_name = service_name.lower().replace(' ', '-').replace('_', '-')
        
        try:
            result = subprocess.run(
                ['docker', 'restart', container_name],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def get_service_logs(self, service_name: str, tail: int = 50) -> str:
        """获取服务日志"""
        container_name = service_name.lower().replace(' ', '-').replace('_', '-')
        
        try:
            result = subprocess.run(
                ['docker', 'logs', '--tail', str(tail), container_name],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout
        except:
            return ''
    
    def list_services(self) -> List[Dict[str, Any]]:
        """列出所有服务及其状态"""
        services = []
        
        if not os.path.exists(self.services_base_dir):
            return services
        
        for service_name in os.listdir(self.services_base_dir):
            service_dir = os.path.join(self.services_base_dir, service_name)
            if os.path.isdir(service_dir):
                status = self.get_service_status(service_name)
                
                config_path = os.path.join(service_dir, 'config.yml')
                config = {}
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r') as f:
                            config = yaml.safe_load(f) or {}
                    except:
                        pass
                
                services.append({
                    'name': service_name,
                    'title': config.get('title', service_name),
                    'status': status['status'],
                    'container_id': status.get('container_id', ''),
                    'created_at': config.get('created_at', ''),
                    'refresh_strategy': config.get('refresh', {}).get('strategy', 'unknown')
                })
        
        return services
