# -*- coding: utf-8 -*-
"""
技能包解析器
解析技能包（Python脚本 + SKILL.md），提取数据拉取方案、计算逻辑和配置
"""

import re
import ast
import yaml
from typing import Dict, List, Any, Optional


class SkillParser:
    """解析技能包，提取数据拉取和计算方案"""
    
    def __init__(self, skill_py_content: str = '', skill_md_content: str = '', skill_yaml_content: str = ''):
        self.py_content = skill_py_content
        self.md_content = skill_md_content
        self.yaml_content = skill_yaml_content
        
    def parse(self) -> Dict[str, Any]:
        """完整解析技能包"""
        result = {
            'name': '',
            'description': '',
            'version': '1.0.0',
            'data_source': {},
            'fetch_steps': [],
            'calculation': {},
            'output_schema': {},
            'config': {},
            'raw_py': self.py_content,
            'raw_md': self.md_content,
        }
        
        # 解析YAML配置（如果提供）
        if self.yaml_content:
            try:
                yaml_data = yaml.safe_load(self.yaml_content)
                result.update(yaml_data)
            except:
                pass
        
        # 解析Markdown
        if self.md_content:
            md_info = self._parse_markdown()
            result.update(md_info)
        
        # 解析Python脚本（最核心）
        if self.py_content:
            py_info = self._parse_python()
            result['data_source'] = py_info.get('data_source', {})
            result['fetch_steps'] = py_info.get('fetch_steps', [])
            result['calculation'] = py_info.get('calculation', {})
            result['config'] = py_info.get('config', {})
        
        return result
    
    def _parse_markdown(self) -> Dict[str, Any]:
        """从SKILL.md提取信息"""
        info = {
            'name': '',
            'description': '',
            'triggers': [],
            'supported_datacenters': []
        }
        
        # 提取名称
        name_match = re.search(r'##?\s*技能名称\s*\n+([^\n]+)', self.md_content)
        if name_match:
            info['name'] = name_match.group(1).strip()
        
        # 提取触发词
        trigger_section = re.search(r'##?\s*触发词\s*\n+([\s\S]*?)(?=##?\s|$)', self.md_content)
        if trigger_section:
            triggers = re.findall(r'["\']([^"\']+)["\']', trigger_section.group(1))
            info['triggers'] = triggers
        
        # 提取支持的数据中心
        dc_section = re.search(r'##?\s*支持的数据中心\s*\n+([\s\S]*?)(?=##?\s|$)', self.md_content)
        if dc_section:
            dcs = re.findall(r'[\-\*]\s*([^\n]+)', dc_section.group(1))
            info['supported_datacenters'] = [dc.strip() for dc in dcs]
        
        # 提取技术参数
        param_section = re.search(r'##?\s*技术参数\s*\n+([\s\S]*?)(?=##?\s|$)', self.md_content)
        if param_section:
            params = {}
            for line in param_section.group(1).split('\n'):
                match = re.search(r'[\-\*]\s*([^:]+):\s*(.+)', line)
                if match:
                    params[match.group(1).strip()] = match.group(2).strip()
            info['tech_params'] = params
        
        return info
    
    def _parse_python(self) -> Dict[str, Any]:
        """解析Python脚本提取数据拉取和计算逻辑"""
        result = {
            'data_source': {},
            'fetch_steps': [],
            'calculation': {},
            'config': {}
        }
        
        # 1. 提取数据中心配置
        dc_config = self._extract_datacenter_config()
        if dc_config:
            result['config']['datacenters'] = dc_config
        
        # 2. 提取数据拉取步骤
        fetch_steps = self._extract_fetch_steps()
        result['fetch_steps'] = fetch_steps
        
        # 3. 提取API端点和认证信息
        api_info = self._extract_api_info()
        result['data_source'] = api_info
        
        # 4. 提取计算逻辑
        calc_info = self._extract_calculation()
        result['calculation'] = calc_info
        
        # 5. 提取过滤条件
        filters = self._extract_filters()
        result['calculation']['filters'] = filters
        
        # 6. 提取阈值配置
        thresholds = self._extract_thresholds()
        result['calculation']['thresholds'] = thresholds
        
        # 7. 提取点位映射
        point_mapping = self._extract_point_mapping()
        if point_mapping:
            result['config']['point_mapping'] = point_mapping
        
        # 8. 提取设备模型ID
        obj_ids = self._extract_obj_ids()
        if obj_ids:
            result['config']['obj_ids'] = obj_ids
        
        return result
    
    def _extract_datacenter_config(self) -> Dict[str, str]:
        """提取数据中心配置映射"""
        config = {}
        
        # 查找 DATACENTER_CONFIG 字典
        pattern = r"DATACENTER_CONFIG\s*=\s*\{([^}]+)\}"
        match = re.search(pattern, self.py_content, re.DOTALL)
        if match:
            content = match.group(1)
            # 提取键值对
            pairs = re.findall(r"['\"]([^'\"]+)['\"]\s*:\s*\{[^}]*['\"]domain['\"]\s*:\s*['\"]([^'\"]+)['\"]", content)
            for name, domain in pairs:
                config[name] = domain
        
        # 备选：查找domainCode相关配置
        if not config:
            domains = re.findall(r"['\"]domainCode['\"]\s*:\s*['\"](\d+)['\"]", self.py_content)
            for i, domain in enumerate(set(domains)):
                config[f'datacenter_{i}'] = domain
        
        return config
    
    def _extract_fetch_steps(self) -> List[Dict[str, Any]]:
        """提取数据拉取步骤"""
        steps = []
        
        # 查找主要函数调用链
        step_patterns = [
            (r'get_devices_by_domain_and_obj\s*\(', 'get_devices', '获取设备列表'),
            (r'get_point_list_by_instance\s*\(', 'get_points', '获取点位列表'),
            (r'get_realtime_data\s*\(', 'get_realtime', '获取实时数据'),
            (r'build_device_points_map\s*\(', 'build_map', '构建设备点位映射'),
        ]
        
        for pattern, step_id, desc in step_patterns:
            if re.search(pattern, self.py_content):
                steps.append({
                    'id': step_id,
                    'description': desc,
                    'function_pattern': pattern
                })
        
        # 如果没有匹配到标准模式，尝试提取所有函数调用
        if not steps:
            func_calls = re.findall(r'(\w+)\s*\([^)]*\)', self.py_content)
            data_funcs = [f for f in func_calls if any(kw in f.lower() for kw in 
                ['get', 'fetch', 'query', 'load', 'read', 'pull'])]
            for i, func in enumerate(set(data_funcs)[:5]):
                steps.append({
                    'id': f'step_{i}',
                    'description': f'数据操作: {func}',
                    'function': func
                })
        
        return steps
    
    def _extract_api_info(self) -> Dict[str, Any]:
        """提取API端点和认证信息"""
        api_info = {
            'type': 'unknown',
            'base_url': '',
            'auth': {}
        }
        
        # 查找智航CMDB
        if 'zhihang' in self.py_content.lower() or 'cmdb' in self.py_content.lower():
            api_info['type'] = 'zhihang-cmdb'
            
            # 提取base URL
            url_patterns = [
                r"base_url\s*=\s*['\"]([^'\"]+)['\"]",
                r"INTERNAL_BASE_URL\s*=\s*['\"]([^'\"]+)['\"]",
                r"EXTERNAL_BASE_URL\s*=\s*['\"]([^'\"]+)['\"]"
            ]
            for pattern in url_patterns:
                match = re.search(pattern, self.py_content)
                if match:
                    api_info['base_url'] = match.group(1)
                    break
            
            # 提取认证信息
            auth_patterns = [
                (r"username\s*=\s*['\"]([^'\"]+)['\"]", 'username'),
                (r"password\s*=\s*['\"]([^'\"]+)['\"]", 'password'),
            ]
            for pattern, key in auth_patterns:
                match = re.search(pattern, self.py_content)
                if match:
                    api_info['auth'][key] = match.group(1)
        
        # 查找通用HTTP API
        elif 'requests.' in self.py_content:
            api_info['type'] = 'http_api'
            url_match = re.search(r"requests\.(get|post)\s*\(\s*['\"]([^'\"]+)['\"]", self.py_content)
            if url_match:
                api_info['base_url'] = url_match.group(2)
        
        return api_info
    
    def _extract_calculation(self) -> Dict[str, Any]:
        """提取计算逻辑"""
        calc = {
            'formula': '',
            'formula_description': ''
        }
        
        # 查找不平衡度计算函数
        calc_func = re.search(r"def\s+calc_\w+\s*\([^)]*\):\s*\n((?:\s+.+\n)+)", self.py_content)
        if calc_func:
            func_body = calc_func.group(1)
            
            # 提取公式
            if 'max' in func_body and 'min' in func_body:
                if '/ max' in func_body or '/max' in func_body:
                    calc['formula'] = '(max - min) / max * 100'
                    calc['formula_description'] = '基于最大值的三相不平衡度'
                elif '/ avg' in func_body or '/avg' in func_body:
                    calc['formula'] = '(max - min) / avg * 100'
                    calc['formula_description'] = '基于平均值的三相不平衡度'
            
            calc['function_body'] = func_body.strip()
        
        # 备选：查找内联计算
        if not calc['formula']:
            inline_calc = re.search(r'unbalance\s*=\s*(.+)', self.py_content)
            if inline_calc:
                calc['formula'] = inline_calc.group(1).strip()
        
        return calc
    
    def _extract_filters(self) -> List[str]:
        """提取数据过滤条件"""
        filters = []
        
        # 查找常见的过滤模式
        filter_patterns = [
            (r"if\s+total_current\s*<\s*(\d+)", "总电流小于{0}A"),
            (r"if\s+total\s*<\s*(\d+)", "总电流小于{0}A"),
            (r"if\s+\w+\s*<\s*(\d+)", "数值小于{0}"),
            (r"if\s+\w+\s*is\s+None", "空值过滤"),
            (r"if\s+not\s+\w+", "非空过滤"),
        ]
        
        for pattern, desc_template in filter_patterns:
            matches = re.findall(pattern, self.py_content)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                try:
                    filters.append(desc_template.format(match))
                except:
                    filters.append(desc_template)
        
        # 去重
        return list(set(filters))
    
    def _extract_thresholds(self) -> Dict[str, float]:
        """提取阈值配置"""
        thresholds = {}
        
        # 异常阈值
        abnormal_match = re.search(r"abnormal.*?(\d+)(?:%| percent)", self.py_content, re.I)
        if abnormal_match:
            thresholds['abnormal'] = float(abnormal_match.group(1))
        
        # 从比较表达式中提取
        threshold_patterns = [
            (r">\s*(\d+)(?:\s*%)?\s*:", 'abnormal'),
            (r">=\s*(\d+)(?:\s*%)?\s*:", 'critical'),
            (r"<\s*(\d+)(?:\s*A)?", 'min_current'),
        ]
        
        for pattern, key in threshold_patterns:
            matches = re.findall(pattern, self.py_content)
            for match in matches:
                if key not in thresholds:
                    try:
                        thresholds[key] = float(match)
                    except:
                        pass
        
        return thresholds
    
    def _extract_point_mapping(self) -> Dict[str, str]:
        """提取点位ID映射"""
        mapping = {}
        
        # 查找 point_id_map 或类似结构
        pattern = r"point_id_map\s*=\s*\{([^}]+)\}"
        match = re.search(pattern, self.py_content, re.DOTALL)
        if match:
            content = match.group(1)
            pairs = re.findall(r"['\"](\w+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", content)
            for phase, point_id in pairs:
                mapping[phase] = point_id
        
        # 备选：查找 extendsName 映射
        if not mapping:
            extends_patterns = [
                (r"A_\w+_A", 'A'),
                (r"B_\w+_A", 'B'),
                (r"C_\w+_A", 'C'),
            ]
            for pattern, phase in extends_patterns:
                if re.search(pattern, self.py_content):
                    mapping[phase] = pattern
        
        return mapping
    
    def _extract_obj_ids(self) -> List[str]:
        """提取设备模型ID"""
        obj_ids = []
        
        matches = re.findall(r"['\"]objIds['\"]\s*:\s*\[([^\]]+)\]", self.py_content)
        for match in matches:
            ids = re.findall(r"['\"]([^'\"]+)['\"]", match)
            obj_ids.extend(ids)
        
        # 备选
        if not obj_ids:
            ids = re.findall(r"OBJ-\d+", self.py_content)
            obj_ids = list(set(ids))
        
        return obj_ids
    
    def generate_skill_yaml(self) -> str:
        """生成标准化的skill.yaml配置"""
        parsed = self.parse()
        
        skill_yaml = {
            'name': parsed.get('name', '未命名技能'),
            'version': parsed.get('version', '1.0.0'),
            'description': parsed.get('description', ''),
            'data_source': parsed.get('data_source', {}),
            'fetch_steps': parsed.get('fetch_steps', []),
            'calculation': parsed.get('calculation', {}),
            'config': parsed.get('config', {}),
            'output_schema': parsed.get('output_schema', {})
        }
        
        return yaml.dump(skill_yaml, allow_unicode=True, sort_keys=False)
