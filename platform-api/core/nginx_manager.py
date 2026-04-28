# -*- coding: utf-8 -*-
"""
Nginx路由管理器
动态管理Nginx配置，为每个服务添加子路径路由
"""

import os
import re
from typing import Dict, List, Any


class NginxManager:
    """管理Nginx反向代理配置"""
    
    def __init__(self, nginx_conf_dir: str = None):
        if nginx_conf_dir is None:
            # 在Docker环境中，这是挂载的卷
            nginx_conf_dir = os.environ.get('NGINX_CONF_DIR', '/app/nginx_conf')
        self.nginx_conf_dir = nginx_conf_dir
        self.services_conf_path = os.path.join(nginx_conf_dir, 'services.conf')
    
    def add_service_route(self, service_name: str, service_path: str, 
                          container_name: str, port: int = 5000) -> bool:
        """
        为服务添加Nginx路由
        
        Args:
            service_name: 服务名称
            service_path: 子路径（如 /reports/pdu-unbalance）
            container_name: Docker容器名称
            port: 服务内部端口
        
        Returns:
            是否成功
        """
        # 确保路径格式正确
        if not service_path.startswith('/'):
            service_path = '/' + service_path
        if not service_path.endswith('/'):
            service_path = service_path + '/'
        
        # 读取现有配置
        existing_config = self._read_services_conf()
        
        # 检查是否已存在
        if self._route_exists(service_name, existing_config):
            # 更新现有路由
            existing_config = self._remove_route(service_name, existing_config)
        
        # 生成新路由配置
        route_config = self._generate_route_block(
            service_name, service_path, container_name, port
        )
        
        # 追加到配置
        new_config = existing_config + '\n' + route_config + '\n'
        
        # 写入文件
        return self._write_services_conf(new_config)
    
    def remove_service_route(self, service_name: str) -> bool:
        """移除服务的Nginx路由"""
        existing_config = self._read_services_conf()
        
        if not self._route_exists(service_name, existing_config):
            return True
        
        new_config = self._remove_route(service_name, existing_config)
        return self._write_services_conf(new_config)
    
    def reload_nginx(self) -> bool:
        """重新加载Nginx配置"""
        import subprocess
        
        try:
            # 测试配置
            test_result = subprocess.run(
                ['nginx', '-t'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if test_result.returncode != 0:
                print(f"Nginx配置测试失败: {test_result.stderr}")
                return False
            
            # 重新加载
            reload_result = subprocess.run(
                ['nginx', '-s', 'reload'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return reload_result.returncode == 0
        except Exception as e:
            print(f"重载Nginx失败: {e}")
            return False
    
    def list_routes(self) -> List[Dict[str, Any]]:
        """列出所有已配置的路由"""
        config = self._read_services_conf()
        routes = []
        
        # 解析location块
        pattern = r'location\s+(\S+)\s*\{[^}]*proxy_pass\s+http://([^:]+):(\d+)/;[^}]*\}'
        matches = re.findall(pattern, config, re.DOTALL)
        
        for path, host, port in matches:
            # 从注释中提取服务名
            service_name = self._extract_service_name(config, path)
            
            routes.append({
                'service_name': service_name,
                'path': path,
                'upstream': f"{host}:{port}",
                'container': host
            })
        
        return routes
    
    def _generate_route_block(self, service_name: str, service_path: str,
                              container_name: str, port: int) -> str:
        """生成单个路由配置块"""
        return f'''# Service: {service_name}
location {service_path} {{
    proxy_pass http://{container_name}:{port}/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix {service_path.rstrip('/')};
    
    # WebSocket支持
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # 超时设置
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}}'''
    
    def _read_services_conf(self) -> str:
        """读取services.conf内容"""
        if os.path.exists(self.services_conf_path):
            with open(self.services_conf_path, 'r', encoding='utf-8') as f:
                return f.read()
        return '# 此文件由平台API动态生成和管理\n'
    
    def _write_services_conf(self, content: str) -> bool:
        """写入services.conf"""
        try:
            os.makedirs(self.nginx_conf_dir, exist_ok=True)
            with open(self.services_conf_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"写入Nginx配置失败: {e}")
            return False
    
    def _route_exists(self, service_name: str, config: str) -> bool:
        """检查路由是否已存在"""
        return f'# Service: {service_name}' in config
    
    def _remove_route(self, service_name: str, config: str) -> str:
        """从配置中移除指定服务的路由"""
        pattern = rf'# Service: {re.escape(service_name)}\nlocation\s+\S+\s*\{{[^}}]*\}}\n?'
        return re.sub(pattern, '', config, flags=re.DOTALL)
    
    def _extract_service_name(self, config: str, path: str) -> str:
        """从配置中提取服务名"""
        # 查找location前的注释
        pattern = rf'# Service: ([^\n]+)\nlocation\s+{re.escape(path)}'
        match = re.search(pattern, config)
        if match:
            return match.group(1)
        
        # 从路径推断
        return path.strip('/').replace('/', '-')
    
    def generate_full_nginx_conf(self, routes: List[Dict[str, Any]]) -> str:
        """生成完整的Nginx配置（用于初始化）"""
        blocks = ['# 动态生成的服务路由\n']
        
        for route in routes:
            block = self._generate_route_block(
                route['service_name'],
                route['path'],
                route['container'],
                route.get('port', 5000)
            )
            blocks.append(block)
        
        return '\n'.join(blocks)
