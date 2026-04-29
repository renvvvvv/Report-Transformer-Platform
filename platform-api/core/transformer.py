# -*- coding: utf-8 -*-
"""
转化引擎
将HTML解析结果和技能包解析结果进行智能匹配，生成动态服务代码
"""

import os
import re
import json
from typing import Dict, List, Any, Optional
from jinja2 import Environment, FileSystemLoader


class Transformer:
    """HTML静态页面 → 动态服务 转化引擎"""
    
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'service_template')
        
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.template_dir = template_dir
    
    def transform(self, html_info: Dict[str, Any], skill_info: Dict[str, Any], 
                  service_config: Dict[str, Any] = None) -> Dict[str, str]:
        """
        执行转化，生成完整的动态服务代码
        
        Args:
            html_info: HTMLParser.parse() 的输出
            skill_info: SkillParser.parse() 的输出
            service_config: 服务配置（名称、刷新策略等）
        
        Returns:
            生成的文件内容字典
        """
        if service_config is None:
            service_config = {}
        
        # 1. 智能匹配：HTML数据区域 ↔ 技能包数据输出
        mapping = self._match_html_to_skill(html_info, skill_info)
        
        # 2. 生成数据拉取模块
        data_fetcher = self._generate_data_fetcher(skill_info)
        
        # 3. 生成计算模块
        calculator = self._generate_calculator(skill_info)
        
        # 4. 生成动态HTML（使用Jinja2模板）
        dynamic_html = self._generate_dynamic_html(html_info, mapping, service_config)
        
        # 5. 生成Flask主应用
        flask_app = self._generate_flask_app(html_info, skill_info, mapping, service_config)
        
        # 6. 生成Docker配置
        dockerfile = self._generate_dockerfile()
        docker_compose = self._generate_docker_compose(service_config)
        
        # 7. 生成requirements.txt
        requirements = self._generate_requirements(skill_info)
        
        # 8. 生成服务配置
        config_yaml = self._generate_service_config(service_config, skill_info)
        
        return {
            'app.py': flask_app,
            'data_fetcher.py': data_fetcher,
            'calculator.py': calculator,
            'templates/index.html': dynamic_html,
            'Dockerfile': dockerfile,
            'docker-compose.yml': docker_compose,
            'requirements.txt': requirements,
            'config.yml': config_yaml,
            '_mapping.json': json.dumps(mapping, ensure_ascii=False, indent=2),
        }
    
    def _match_html_to_skill(self, html_info: Dict[str, Any], skill_info: Dict[str, Any]) -> Dict[str, Any]:
        """智能匹配HTML数据区域与技能包数据输出"""
        mapping = {
            'stat_cards': {},
            'tables': {},
            'conclusions': {},
            'refresh_strategy': 'cron'
        }
        
        # 匹配统计卡片
        for region in html_info.get('data_regions', []):
            if region['type'] == 'stat_cards':
                for card in region.get('items', []):
                    data_key = card.get('data_key', '')
                    label = card.get('label', '')
                    
                    # 根据标签推断对应的数据源
                    if '设备' in label or '台' in label or 'count' in data_key:
                        mapping['stat_cards'][data_key] = {
                            'source': 'len(results)',
                            'label': label,
                            'type': 'count'
                        }
                    elif '平均' in label or 'avg' in data_key:
                        mapping['stat_cards'][data_key] = {
                            'source': 'avg_unbalance',
                            'label': label,
                            'type': 'average'
                        }
                    elif '最大' in label or 'max' in data_key:
                        mapping['stat_cards'][data_key] = {
                            'source': 'max_unbalance',
                            'label': label,
                            'type': 'maximum'
                        }
                    elif '异常' in label or 'abnormal' in data_key:
                        mapping['stat_cards'][data_key] = {
                            'source': 'abnormal_count',
                            'label': label,
                            'type': 'count'
                        }
            
            elif region['type'] == 'data_table':
                mapping['tables']['main'] = {
                    'columns': region.get('columns', []),
                    'data_source': 'abnormal_data',
                    'sort_by': 'unbalance DESC'
                }
            
            elif region['type'] == 'conclusion_box':
                mapping['conclusions'] = {
                    'items': region.get('items', []),
                    'data_source': 'summary_stats'
                }
        
        # 从技能包推断刷新策略
        calc = skill_info.get('calculation', {})
        if calc.get('thresholds', {}).get('abnormal'):
            mapping['thresholds'] = calc['thresholds']
        
        return mapping
    
    def _generate_data_fetcher(self, skill_info: Dict[str, Any]) -> str:
        """生成数据拉取模块"""
        template = self.env.get_template('data_fetcher.py.j2')
        
        context = {
            'data_source': skill_info.get('data_source', {}),
            'fetch_steps': skill_info.get('fetch_steps', []),
            'config': skill_info.get('config', {}),
        }
        
        return template.render(**context)
    
    def _generate_calculator(self, skill_info: Dict[str, Any]) -> str:
        """生成计算模块"""
        template = self.env.get_template('calculator.py.j2')
        
        calc = skill_info.get('calculation', {})
        config = skill_info.get('config', {})
        
        context = {
            'formula': calc.get('formula', ''),
            'formula_description': calc.get('formula_description', ''),
            'filters': calc.get('filters', []),
            'thresholds': calc.get('thresholds', {}),
            'point_mapping': config.get('point_mapping', {}),
        }
        
        return template.render(**context)
    
    def _generate_dynamic_html(self, html_info: Dict[str, Any], mapping: Dict[str, Any], 
                                 service_config: Dict[str, Any] = None) -> str:
        """生成动态HTML模板 - 直接返回Jinja2模板源码，由Flask在请求时渲染"""
        if service_config is None:
            service_config = {}
        
        template = self.env.get_template('index.html.j2')
        
        # 直接读取模板源码，不做渲染（保留Jinja2语法）
        template_path = os.path.join(self.template_dir, 'index.html.j2')
        with open(template_path, 'r', encoding='utf-8') as f:
            template_source = f.read()
        
        # 只替换模板中的静态配置项（标题、数据中心等）
        # 使用占位符标记，后续用字符串替换
        template_source = template_source.replace(
            '{{ title }}',
            html_info.get('title', '动态报表')
        )
        template_source = template_source.replace(
            '{{ datacenter }}',
            service_config.get('datacenter', 'default')
        )
        
        return template_source
    
    def _replace_stat_value(self, html: str, label_pattern: str, template_var: str) -> str:
        """替换统计卡片的数值"""
        # 查找包含特定标签的统计卡片，替换其中的数值
        pattern = rf'(<[^>]*>[^<]*{label_pattern}[^<]*</[^>]*>\s*</div>\s*<div[^>]*class="[^"]*(?:stat-value|text-3xl)[^"]*"[^>]*>)([^<]+)(</div>)'
        
        def replacer(match):
            return match.group(1) + template_var + match.group(3)
        
        return re.sub(pattern, replacer, html, flags=re.DOTALL | re.I)
    
    def _replace_conclusions(self, html: str, mapping: Dict[str, Any]) -> str:
        """替换结论区域的内容"""
        # 简化处理：保留结构，将具体数值替换为模板变量
        # 紧急处理数量
        html = re.sub(
            r'(紧急处理\s*\()(\d+)(台\))',
            r'\1{{ summary.urgent_count }}\3',
            html
        )
        # 重点关注数量
        html = re.sub(
            r'(重点关注\s*\()(\d+)(台\))',
            r'\1{{ summary.focus_count }}\3',
            html
        )
        # 整体评估数量
        html = re.sub(
            r'(整体评估\s*\()(\d+)(台\))',
            r'\1{{ summary.valid_count }}\3',
            html
        )
        
        return html
    
    def _generate_refresh_script(self, mapping: Dict[str, Any]) -> str:
        """生成前端动态刷新脚本"""
        return '''
    <script>
        // 动态数据刷新功能
        const REFRESH_INTERVAL = 300000; // 5分钟默认刷新
        
        async function refreshData() {
            try {
                const response = await fetch('./api/data');
                const result = await response.json();
                
                if (result.success) {
                    const data = result.data;
                    
                    // 更新统计卡片
                    if (data.summary) {
                        updateStatCards(data.summary);
                    }
                    
                    // 更新表格
                    if (data.devices) {
                        updateTable(data.devices);
                    }
                    
                    // 更新刷新时间
                    document.getElementById('refreshTime').textContent = data.refresh_time;
                }
            } catch (error) {
                console.error('数据刷新失败:', error);
            }
        }
        
        function updateStatCards(summary) {
            // 根据summary更新页面上的统计值
            const statElements = document.querySelectorAll('.stat-value, [class*="text-3xl"]');
            statElements.forEach(el => {
                // 根据上下文更新对应值
            });
        }
        
        function updateTable(devices) {
            // 重新渲染表格
            if (typeof renderTable === 'function') {
                // 更新数据源并重新渲染
                window.abnormalData = devices;
                renderTable();
            }
        }
        
        // 定时刷新
        setInterval(refreshData, REFRESH_INTERVAL);
        
        // 页面可见性变化时刷新
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                refreshData();
            }
        });
    </script>
'''
    
    def _generate_flask_app(self, html_info: Dict[str, Any], skill_info: Dict[str, Any],
                           mapping: Dict[str, Any], service_config: Dict[str, Any]) -> str:
        """生成Flask主应用"""
        template = self.env.get_template('app.py.j2')
        
        context = {
            'service_name': service_config.get('name', 'dynamic-report'),
            'service_title': html_info.get('title', '动态报表'),
            'html_theme': html_info.get('style', {}).get('theme', 'default'),
            'data_source': skill_info.get('data_source', {}),
            'fetch_steps': skill_info.get('fetch_steps', []),
            'calculation': skill_info.get('calculation', {}),
            'config': skill_info.get('config', {}),
            'mapping': mapping,
            'refresh_cron': service_config.get('refresh_cron', '0 */6 * * *'),
            'datacenter': service_config.get('datacenter', 'default'),
        }
        
        return template.render(**context)
    
    def _generate_dockerfile(self) -> str:
        """生成Dockerfile"""
        template = self.env.get_template('Dockerfile')
        return template.render()
    
    def _generate_docker_compose(self, service_config: Dict[str, Any]) -> str:
        """生成docker-compose.yml"""
        template = self.env.get_template('docker-compose.yml.j2')
        
        context = {
            'service_name': service_config.get('name', 'dynamic-report'),
            'port': service_config.get('port', 5000),
            'service_path': service_config.get('path', '/reports/dynamic-report'),
        }
        
        return template.render(**context)
    
    def _generate_requirements(self, skill_info: Dict[str, Any]) -> str:
        """生成requirements.txt"""
        base_requirements = [
            'flask==3.0.0',
            'flask-cors==4.0.0',
            'requests==2.31.0',
            'apscheduler==3.10.4',
            'pyyaml==6.0.1',
            'python-dateutil==2.8.2',
        ]
        
        # 根据数据源添加额外依赖
        data_source = skill_info.get('data_source', {})
        if data_source.get('type') == 'zhihang-cmdb':
            # 智航CMDB使用标准HTTP
            pass
        
        return '\n'.join(base_requirements)
    
    def _generate_service_config(self, service_config: Dict[str, Any], skill_info: Dict[str, Any]) -> str:
        """生成服务配置文件"""
        config = {
            'name': service_config.get('name', 'dynamic-report'),
            'title': service_config.get('title', '动态报表'),
            'version': '1.0.0',
            'refresh': {
                'strategy': service_config.get('refresh_strategy', 'cron'),
                'cron': service_config.get('refresh_cron', '0 */6 * * *'),
                'interval_seconds': service_config.get('refresh_interval', 300),
            },
            'datacenter': service_config.get('datacenter', 'default'),
            'data_source': skill_info.get('data_source', {}),
            'thresholds': skill_info.get('calculation', {}).get('thresholds', {}),
        }
        
        import yaml
        return yaml.dump(config, allow_unicode=True, sort_keys=False)
