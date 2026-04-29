# -*- coding: utf-8 -*-
"""
服务运行器
在平台容器内直接以子进程方式运行生成的服务（不依赖Docker）
"""

import os
import sys
import json
import signal
import subprocess
import time
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime


class ServiceRunner:
    """管理子进程服务的生命周期"""
    
    # 全局进程注册表（内存中）
    _processes: Dict[str, Dict[str, Any]] = {}
    
    # 端口范围
    BASE_PORT = 15001
    MAX_PORT = 16000
    
    def __init__(self, services_base_dir: str = None):
        if services_base_dir is None:
            services_base_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'services')
        self.services_base_dir = services_base_dir
        self._load_running_processes()
    
    def _load_running_processes(self):
        """从系统进程列表恢复已运行的服务"""
        for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and len(cmdline) >= 2:
                    # 查找运行中的服务进程
                    # 模式: python /app/services/{name}/app/app.py
                    for i, arg in enumerate(cmdline):
                        if arg.endswith('/app/app.py') and 'services' in arg:
                            parts = arg.split('/')
                            if 'services' in parts:
                                idx = parts.index('services')
                                if idx + 1 < len(parts):
                                    service_name = parts[idx + 1]
                                    port = self._extract_port_from_cmdline(cmdline)
                                    self._processes[service_name] = {
                                        'pid': proc.info['pid'],
                                        'port': port,
                                        'started_at': datetime.fromtimestamp(proc.info['create_time']).isoformat(),
                                        'status': 'running'
                                    }
                                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    def _extract_port_from_cmdline(self, cmdline: List[str]) -> int:
        """从命令行参数提取端口"""
        for i, arg in enumerate(cmdline):
            if arg == '--port' and i + 1 < len(cmdline):
                return int(cmdline[i + 1])
        return 5000
    
    def _find_available_port(self) -> int:
        """查找可用端口"""
        used_ports = set()
        
        # 从注册表获取已用端口
        for info in self._processes.values():
            used_ports.add(info.get('port', 0))
        
        # 从系统获取已用端口
        for conn in psutil.net_connections():
            if conn.laddr:
                used_ports.add(conn.laddr.port)
        
        for port in range(self.BASE_PORT, self.MAX_PORT):
            if port not in used_ports:
                return port
        
        raise RuntimeError("没有可用端口")
    
    def start_service(self, service_name: str) -> Dict[str, Any]:
        """
        启动服务子进程
        
        Returns:
            {'success': bool, 'port': int, 'pid': int, 'message': str}
        """
        service_dir = os.path.join(self.services_base_dir, service_name)
        app_file = os.path.join(service_dir, 'app', 'app.py')
        
        if not os.path.exists(app_file):
            return {
                'success': False,
                'message': f'找不到服务入口文件: {app_file}'
            }
        
        # 如果已在运行，先停止
        if service_name in self._processes:
            self.stop_service(service_name)
        
        try:
            port = self._find_available_port()
            
            # 设置环境变量
            env = os.environ.copy()
            env['SERVICE_PORT'] = str(port)
            env['SERVICE_NAME'] = service_name
            env['PYTHONPATH'] = os.path.join(service_dir, 'app')
            
            # 启动子进程 - 输出重定向到日志文件，避免PIPE缓冲区满导致阻塞
            log_file = os.path.join(service_dir, 'app.log')
            log_fp = open(log_file, 'a', encoding='utf-8')
            log_fp.write(f"\n{'='*60}\n")
            log_fp.write(f"[START] Service {service_name} started at {datetime.now().isoformat()}\n")
            log_fp.write(f"[START] Port: {port}, PID: will be assigned\n")
            log_fp.flush()
            
            process = subprocess.Popen(
                [sys.executable, app_file, '--port', str(port)],
                cwd=os.path.join(service_dir, 'app'),
                env=env,
                stdout=log_fp,
                stderr=subprocess.STDOUT,  # 合并stderr到stdout
                start_new_session=True  # 创建新进程组，避免被父进程信号影响
            )
            
            # 等待服务启动
            time.sleep(2)
            
            # 检查进程是否存活
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=5)
                return {
                    'success': False,
                    'message': f'服务启动失败，进程已退出',
                    'stdout': stdout.decode('utf-8', errors='replace')[:500],
                    'stderr': stderr.decode('utf-8', errors='replace')[:1000]
                }
            
            # 注册进程
            self._processes[service_name] = {
                'pid': process.pid,
                'port': port,
                'started_at': datetime.now().isoformat(),
                'status': 'running'
            }
            
            return {
                'success': True,
                'port': port,
                'pid': process.pid,
                'message': f'服务已启动，监听端口 {port}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'启动异常: {str(e)}'
            }
    
    def stop_service(self, service_name: str) -> bool:
        """停止服务子进程"""
        if service_name not in self._processes:
            # 尝试从系统查找
            self._load_running_processes()
        
        if service_name not in self._processes:
            return False
        
        info = self._processes[service_name]
        pid = info.get('pid')
        
        if pid:
            try:
                # 发送SIGTERM信号给进程组
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                
                # 等待进程退出
                for _ in range(10):
                    if not psutil.pid_exists(pid):
                        break
                    time.sleep(0.5)
                
                # 如果还在，强制终止
                if psutil.pid_exists(pid):
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                    
            except (ProcessLookupError, OSError):
                pass
        
        del self._processes[service_name]
        return True
    
    def restart_service(self, service_name: str) -> Dict[str, Any]:
        """重启服务"""
        self.stop_service(service_name)
        time.sleep(1)
        return self.start_service(service_name)
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """获取服务状态"""
        if service_name not in self._processes:
            self._load_running_processes()
        
        if service_name not in self._processes:
            return {
                'name': service_name,
                'status': 'not_deployed',
                'pid': None,
                'port': None
            }
        
        info = self._processes[service_name]
        pid = info.get('pid')
        
        # 检查进程是否还活着
        is_running = pid and psutil.pid_exists(pid)
        
        if not is_running and service_name in self._processes:
            info['status'] = 'crashed'
        
        return {
            'name': service_name,
            'status': 'running' if is_running else info.get('status', 'unknown'),
            'pid': pid,
            'port': info.get('port'),
            'started_at': info.get('started_at')
        }
    
    def get_service_logs(self, service_name: str, tail: int = 50) -> str:
        """获取服务日志（从日志文件读取）"""
        log_file = os.path.join(self.services_base_dir, service_name, 'app.log')
        
        if not os.path.exists(log_file):
            return ''
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                return ''.join(lines[-tail:])
        except:
            return ''
    
    def list_services(self) -> List[Dict[str, Any]]:
        """列出所有服务及其状态"""
        self._load_running_processes()
        
        services = []
        if not os.path.exists(self.services_base_dir):
            return services
        
        for service_name in os.listdir(self.services_base_dir):
            service_dir = os.path.join(self.services_base_dir, service_name)
            if os.path.isdir(service_dir):
                status = self.get_service_status(service_name)
                
                # 读取配置
                import yaml
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
                    'pid': status.get('pid'),
                    'port': status.get('port'),
                    'created_at': config.get('created_at', ''),
                    'refresh_strategy': config.get('refresh', {}).get('strategy', 'unknown')
                })
        
        return services
    
    def get_all_running_ports(self) -> Dict[str, int]:
        """获取所有运行中服务的端口映射"""
        return {
            name: info['port']
            for name, info in self._processes.items()
            if info.get('status') == 'running'
        }
