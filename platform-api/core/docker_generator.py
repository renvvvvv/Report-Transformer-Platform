# -*- coding: utf-8 -*-
"""
Docker配置生成器
生成服务所需的Dockerfile和docker-compose配置
"""

import os
import yaml
from typing import Dict, List, Any


class DockerGenerator:
    """生成Docker相关配置文件"""
    
    def __init__(self, services_base_dir: str = None):
        if services_base_dir is None:
            services_base_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'services')
        self.services_base_dir = services_base_dir
    
    def generate_service_files(self, service_name: str, generated_files: Dict[str, str]) -> str:
        """
        将生成的文件写入服务目录
        
        Args:
            service_name: 服务名称
            generated_files: Transformer生成的文件字典
        
        Returns:
            服务目录路径
        """
        service_dir = os.path.join(self.services_base_dir, service_name)
        app_dir = os.path.join(service_dir, 'app')
        templates_dir = os.path.join(app_dir, 'templates')
        static_dir = os.path.join(app_dir, 'static')
        
        # 创建目录
        os.makedirs(service_dir, exist_ok=True)
        os.makedirs(app_dir, exist_ok=True)
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(static_dir, exist_ok=True)
        
        # 写入文件
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
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(generated_files[file_key])
        
        # 写入映射信息（调试用）
        if '_mapping.json' in generated_files:
            mapping_path = os.path.join(service_dir, '_mapping.json')
            with open(mapping_path, 'w', encoding='utf-8') as f:
                f.write(generated_files['_mapping.json'])
        
        return service_dir
    
    def generate_service_dockerfile(self) -> str:
        """生成服务专用的Dockerfile"""
        return '''FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据缓存目录
RUN mkdir -p /app/cache

EXPOSE 5000

# 使用gunicorn运行
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]
'''
    
    def generate_service_compose(self, service_name: str, port: int = None) -> str:
        """生成服务的docker-compose配置"""
        if port is None:
            # 自动分配端口（基于服务名哈希）
            port = 5000 + (hash(service_name) % 1000)
        
        compose = {
            'version': '3.8',
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
                        'SERVICE_PATH=/reports/' + service_name,
                    ],
                    'networks': ['report-platform'],
                    'restart': 'unless-stopped',
                    'healthcheck': {
                        'test': ['CMD', 'curl', '-f', 'http://localhost:5000/health'],
                        'interval': '30s',
                        'timeout': '10s',
                        'retries': 3,
                        'start_period': '40s'
                    }
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
        
        # 扫描已部署的服务
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
        
        # 找到第一个可用端口
        port = base_port
        while port in used_ports:
            port += 1
        
        return port
    
    def build_service(self, service_name: str) -> bool:
        """构建服务Docker镜像"""
        service_dir = os.path.join(self.services_base_dir, service_name)
        app_dir = os.path.join(service_dir, 'app')
        
        if not os.path.exists(service_dir) or not os.path.exists(app_dir):
            return False
        
        import subprocess
        try:
            # Use docker build directly (no docker-compose available)
            image_name = f"report-service-{service_name.lower().replace(' ', '-').replace('_', '-')}"
            result = subprocess.run(
                ['docker', 'build', '-t', image_name, '.'],
                cwd=app_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                print(f"构建输出: {result.stdout}")
                print(f"构建错误: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            print(f"构建服务失败: {e}")
            return False
    
    def start_service(self, service_name: str) -> bool:
        """启动服务"""
        service_dir = os.path.join(self.services_base_dir, service_name)
        
        if not os.path.exists(service_dir):
            return False
        
        import subprocess
        import yaml
        
        try:
            # Read compose config to get port
            compose_path = os.path.join(service_dir, 'docker-compose.yml')
            port = 5000
            if os.path.exists(compose_path):
                with open(compose_path, 'r') as f:
                    compose = yaml.safe_load(f)
                for svc in compose.get('services', {}).values():
                    for port_mapping in svc.get('ports', []):
                        if isinstance(port_mapping, str):
                            port = int(port_mapping.split(':')[0])
                            break
            
            image_name = f"report-service-{service_name.lower().replace(' ', '-').replace('_', '-')}"
            container_name = f"report-svc-{service_name.lower().replace(' ', '-').replace('_', '-')}"
            
            # Run container directly with docker run
            result = subprocess.run(
                [
                    'docker', 'run', '-d',
                    '--name', container_name,
                    '--network', 'report-transformer-platform_report-platform',
                    '-p', f'{port}:5000',
                    '-v', f'{service_dir}/config.yml:/app/config.yml:ro',
                    '-e', f'SERVICE_NAME={service_name}',
                    '-e', 'FLASK_ENV=production',
                    '--restart', 'unless-stopped',
                    image_name
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                print(f"启动输出: {result.stdout}")
                print(f"启动错误: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            print(f"启动服务失败: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """停止服务"""
        import subprocess
        
        container_name = f"report-svc-{service_name.lower().replace(' ', '-').replace('_', '-')}"
        
        try:
            result = subprocess.run(
                ['docker', 'rm', '-f', container_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            print(f"停止服务失败: {e}")
            return False
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """获取服务状态"""
        import subprocess
        
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={service_name}', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout.strip():
                import json
                container_info = json.loads(result.stdout.strip())
                return {
                    'name': service_name,
                    'status': 'running' if 'Up' in container_info.get('Status', '') else 'stopped',
                    'container_id': container_info.get('ID', ''),
                    'ports': container_info.get('Ports', ''),
                    'uptime': container_info.get('Status', '')
                }
            else:
                return {
                    'name': service_name,
                    'status': 'not_deployed',
                    'container_id': '',
                    'ports': '',
                    'uptime': ''
                }
        except Exception as e:
            return {
                'name': service_name,
                'status': 'error',
                'error': str(e)
            }
    
    def list_services(self) -> List[Dict[str, Any]]:
        """列出所有服务及其状态"""
        services = []
        
        if not os.path.exists(self.services_base_dir):
            return services
        
        for service_name in os.listdir(self.services_base_dir):
            service_dir = os.path.join(self.services_base_dir, service_name)
            if os.path.isdir(service_dir):
                status = self.get_service_status(service_name)
                
                # 读取配置
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
