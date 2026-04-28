# -*- coding: utf-8 -*-
"""
HTML结构解析器
提取静态HTML页面的结构、样式、数据区域和交互元素
"""

import re
import json
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional


class HTMLParser:
    """解析静态HTML报表页面，提取关键信息"""
    
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.html_content = html_content
        
    def parse(self) -> Dict[str, Any]:
        """完整解析HTML，返回结构化信息"""
        return {
            'title': self._extract_title(),
            'style': self._extract_style(),
            'scripts': self._extract_scripts(),
            'data_regions': self._extract_data_regions(),
            'interactions': self._extract_interactions(),
            'raw_html': self.html_content,
        }
    
    def _extract_title(self) -> str:
        """提取页面标题"""
        title_tag = self.soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        h1 = self.soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        return "未命名报表"
    
    def _extract_style(self) -> Dict[str, Any]:
        """提取页面样式信息"""
        style_info = {
            'theme': 'default',
            'colors': [],
            'fonts': [],
            'css_blocks': []
        }
        
        # 提取style标签内容
        style_tags = self.soup.find_all('style')
        for style in style_tags:
            css_text = style.get_text()
            style_info['css_blocks'].append(css_text)
            
            # 识别主题色
            color_matches = re.findall(r'background:\s*([#0-9a-fA-F]+|rgba?\([^)]+\))', css_text)
            style_info['colors'].extend(color_matches[:10])
            
            # 识别字体
            font_matches = re.findall(r'font-family:\s*([^;]+)', css_text)
            style_info['fonts'].extend(font_matches[:5])
        
        # 识别深色/浅色主题
        body = self.soup.find('body')
        if body:
            body_style = body.get('style', '')
            bg_color = self._get_style_value(body_style, 'background') or self._get_style_value(body_style, 'background-color')
            if bg_color and ('0a0e' in bg_color or '0d1b' in bg_color or '000' in bg_color):
                style_info['theme'] = 'dark-tech'
            elif body.get('class') and any('dark' in str(c).lower() for c in body.get('class')):
                style_info['theme'] = 'dark-tech'
        
        # 检查是否有Tailwind
        if 'tailwindcss' in self.html_content or 'tailwind' in self.html_content.lower():
            style_info['framework'] = 'tailwind'
        
        return style_info
    
    def _extract_scripts(self) -> List[Dict[str, Any]]:
        """提取JavaScript脚本"""
        scripts = []
        script_tags = self.soup.find_all('script')
        
        for script in script_tags:
            src = script.get('src', '')
            content = script.get_text(strip=True)
            
            script_info = {
                'src': src,
                'is_external': bool(src),
                'content_length': len(content),
            }
            
            # 识别关键库
            if 'cdn.tailwindcss.com' in src:
                script_info['library'] = 'tailwindcss'
            elif 'sheetjs.com' in src or 'xlsx' in src:
                script_info['library'] = 'sheetjs'
            elif 'cdnjs' in src or 'unpkg' in src or 'jsdelivr' in src:
                script_info['library'] = 'cdn_library'
            
            # 提取内联脚本中的数据
            if content and not src:
                # 查找数据定义
                data_match = re.search(r'const\s+\w+Data\s*=\s*(\[.*?\]);', content, re.DOTALL)
                if data_match:
                    script_info['has_data'] = True
                    script_info['data_var'] = re.search(r'const\s+(\w+Data)', content).group(1)
                
                # 查找函数定义
                functions = re.findall(r'function\s+(\w+)\s*\(', content)
                script_info['functions'] = functions
            
            scripts.append(script_info)
        
        return scripts
    
    def _extract_data_regions(self) -> List[Dict[str, Any]]:
        """提取页面中的数据展示区域"""
        regions = []
        
        # 1. 统计卡片区域
        stat_cards = self._find_stat_cards()
        if stat_cards:
            regions.append({
                'type': 'stat_cards',
                'description': '统计概览卡片',
                'items': stat_cards,
                'selector_hint': '.glass-card, .stat-card, [class*="stat"]'
            })
        
        # 2. 数据表格区域
        tables = self._find_data_tables()
        for i, table in enumerate(tables):
            regions.append({
                'type': 'data_table',
                'description': f'数据表格 #{i+1}',
                'columns': table['columns'],
                'row_count_hint': table.get('row_count', 0),
                'selector_hint': table['selector']
            })
        
        # 3. 结论/摘要区域
        conclusions = self._find_conclusion_boxes()
        if conclusions:
            regions.append({
                'type': 'conclusion_box',
                'description': '核心结论/摘要',
                'items': conclusions,
                'selector_hint': '.conclusion-box, .summary, .alert'
            })
        
        # 4. 图表区域
        charts = self._find_chart_areas()
        if charts:
            regions.append({
                'type': 'chart',
                'description': '图表展示',
                'chart_types': charts,
                'selector_hint': 'canvas, svg, [class*="chart"]'
            })
        
        # 5. 从脚本中提取的硬编码数据
        inline_data = self._extract_inline_data()
        if inline_data:
            regions.append({
                'type': 'inline_data',
                'description': '页面内嵌数据',
                'data_keys': list(inline_data.keys()),
                'sample': inline_data
            })
        
        return regions
    
    def _find_stat_cards(self) -> List[Dict[str, Any]]:
        """查找统计卡片"""
        cards = []
        
        # 常见的统计卡片选择器模式
        selectors = [
            '.glass-card', '.stat-card', '.metric-card',
            '[class*="stat"]', '[class*="metric"]', '[class*="card"]'
        ]
        
        for selector in selectors:
            elements = self.soup.select(selector)
            for elem in elements:
                # 查找数值
                value_elem = elem.select_one('.stat-value, [class*="value"], .text-3xl, .text-4xl')
                label_elem = elem.select_one('.text-sm, [class*="label"], .text-gray')
                
                if value_elem:
                    value_text = value_elem.get_text(strip=True)
                    # 尝试提取数值
                    numeric_match = re.search(r'[\d.]+', value_text)
                    
                    card_info = {
                        'label': label_elem.get_text(strip=True) if label_elem else '未知指标',
                        'value_text': value_text,
                        'value_numeric': float(numeric_match.group()) if numeric_match else None,
                        'unit': re.sub(r'[\d.]+', '', value_text).strip() if numeric_match else '',
                    }
                    
                    # 推断指标类型
                    label_lower = card_info['label'].lower()
                    if '设备' in label_lower or '台' in label_lower:
                        card_info['metric_type'] = 'count'
                        card_info['data_key'] = 'valid_count'
                    elif '平均' in label_lower or 'avg' in label_lower:
                        card_info['metric_type'] = 'average'
                        card_info['data_key'] = 'avg_value'
                    elif '最大' in label_lower or 'max' in label_lower:
                        card_info['metric_type'] = 'maximum'
                        card_info['data_key'] = 'max_value'
                    elif '异常' in label_lower or 'alarm' in label_lower:
                        card_info['metric_type'] = 'abnormal_count'
                        card_info['data_key'] = 'abnormal_count'
                    else:
                        card_info['metric_type'] = 'generic'
                        card_info['data_key'] = f"metric_{len(cards)}"
                    
                    cards.append(card_info)
        
        # 去重
        seen = set()
        unique_cards = []
        for c in cards:
            key = c['label'] + c['value_text']
            if key not in seen:
                seen.add(key)
                unique_cards.append(c)
        
        return unique_cards[:8]  # 最多8个
    
    def _find_data_tables(self) -> List[Dict[str, Any]]:
        """查找数据表格"""
        tables = []
        
        table_elements = self.soup.find_all('table')
        for i, table in enumerate(table_elements):
            # 提取表头
            headers = []
            thead = table.find('thead')
            if thead:
                ths = thead.find_all('th')
                headers = [th.get_text(strip=True) for th in ths]
            else:
                # 尝试第一行
                first_row = table.find('tr')
                if first_row:
                    headers = [td.get_text(strip=True) for td in first_row.find_all(['td', 'th'])]
            
            # 估算行数
            tbody = table.find('tbody')
            row_count = len(tbody.find_all('tr')) if tbody else 0
            
            # 查找tbody id
            tbody_id = tbody.get('id', '') if tbody else ''
            selector = f'#{tbody_id}' if tbody_id else f'table:nth-of-type({i+1})'
            
            tables.append({
                'columns': headers,
                'row_count': row_count,
                'selector': selector,
                'has_pagination': 'page' in self.html_content.lower() or len(self.html_content) > 50000
            })
        
        return tables
    
    def _find_conclusion_boxes(self) -> List[Dict[str, Any]]:
        """查找结论/摘要区域"""
        conclusions = []
        
        selectors = [
            '.conclusion-box', '.summary-box', '.alert',
            '[class*="conclusion"]', '[class*="summary"]'
        ]
        
        for selector in selectors:
            elements = self.soup.select(selector)
            for elem in elements:
                # 查找子项
                items = elem.select('.flex, .grid > div')
                for item in items:
                    title_elem = item.select_one('[class*="font-semibold"], strong, b, h3, h4')
                    desc_elem = item.select_one('[class*="text-sm"], p')
                    
                    if title_elem:
                        conclusions.append({
                            'title': title_elem.get_text(strip=True),
                            'description': desc_elem.get_text(strip=True) if desc_elem else '',
                            'icon': self._extract_icon(item)
                        })
        
        return conclusions
    
    def _find_chart_areas(self) -> List[str]:
        """查找图表区域"""
        charts = []
        
        if self.soup.find_all('canvas'):
            charts.append('canvas')
        if self.soup.find_all('svg'):
            charts.append('svg')
        if 'echarts' in self.html_content.lower():
            charts.append('echarts')
        if 'chart.js' in self.html_content.lower():
            charts.append('chartjs')
        
        return charts
    
    def _extract_inline_data(self) -> Dict[str, Any]:
        """从脚本中提取内嵌数据"""
        data = {}
        
        script_tags = self.soup.find_all('script')
        for script in script_tags:
            content = script.get_text()
            
            # 查找 const/var 定义的数据数组
            patterns = [
                r'const\s+(\w+Data)\s*=\s*(\[.*?\]);',
                r'var\s+(\w+Data)\s*=\s*(\[.*?\]);',
                r'let\s+(\w+Data)\s*=\s*(\[.*?\]);'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for var_name, data_str in matches:
                    try:
                        # 尝试解析JSON
                        parsed = json.loads(data_str)
                        data[var_name] = {
                            'type': 'array',
                            'length': len(parsed) if isinstance(parsed, list) else 'object',
                            'sample': parsed[:2] if isinstance(parsed, list) and len(parsed) > 0 else parsed
                        }
                    except:
                        data[var_name] = {
                            'type': 'raw',
                            'length': len(data_str)
                        }
        
        return data
    
    def _extract_interactions(self) -> List[Dict[str, Any]]:
        """提取页面交互元素"""
        interactions = []
        
        # 导出按钮
        export_btns = self.soup.find_all(['button', 'a'], 
            string=re.compile(r'导出|export|下载|download', re.I))
        for btn in export_btns:
            onclick = btn.get('onclick', '')
            interactions.append({
                'type': 'export',
                'format': 'excel' if 'excel' in onclick.lower() or 'xlsx' in self.html_content.lower() else 'unknown',
                'trigger': onclick or 'click'
            })
        
        # 刷新按钮
        refresh_btns = self.soup.find_all(['button', 'a'],
            string=re.compile(r'刷新|refresh|更新|update', re.I))
        for btn in refresh_btns:
            interactions.append({
                'type': 'refresh',
                'trigger': btn.get('onclick', 'click')
            })
        
        # 搜索/过滤
        inputs = self.soup.find_all('input')
        for inp in inputs:
            placeholder = inp.get('placeholder', '')
            if placeholder:
                interactions.append({
                    'type': 'search',
                    'placeholder': placeholder
                })
        
        return interactions
    
    def _extract_icon(self, element) -> str:
        """提取图标emoji或class"""
        # 查找emoji
        text = element.get_text()
        emoji_match = re.search(r'[\U0001F300-\U0001F9FF]', text)
        if emoji_match:
            return emoji_match.group()
        
        # 查找svg图标
        svg = element.find('svg')
        if svg:
            return 'svg'
        
        return ''
    
    def _get_style_value(self, style_str: str, property_name: str) -> Optional[str]:
        """从style字符串中提取属性值"""
        pattern = rf'{property_name}\s*:\s*([^;]+)'
        match = re.search(pattern, style_str, re.I)
        return match.group(1).strip() if match else None
    
    def get_data_schema(self) -> Dict[str, Any]:
        """从解析结果推断数据Schema"""
        parsed = self.parse()
        schema = {
            'summary_fields': [],
            'table_fields': [],
            'filters': []
        }
        
        # 从统计卡片推断summary字段
        for region in parsed['data_regions']:
            if region['type'] == 'stat_cards':
                for card in region['items']:
                    schema['summary_fields'].append({
                        'key': card.get('data_key', 'unknown'),
                        'label': card['label'],
                        'type': card.get('metric_type', 'generic')
                    })
            
            elif region['type'] == 'data_table':
                schema['table_fields'] = [
                    {'key': self._slugify(col), 'label': col}
                    for col in region['columns']
                ]
        
        return schema
    
    def _slugify(self, text: str) -> str:
        """将中文/混合文本转换为snake_case key"""
        # 简单映射
        mapping = {
            '排名': 'rank', '序号': 'rank',
            '设备名称': 'ins_name', '名称': 'name',
            '楼层': 'floor',
            'A相': 'phase_a', 'A相电流': 'phase_a', 'A': 'phase_a',
            'B相': 'phase_b', 'B相电流': 'phase_b', 'B': 'phase_b',
            'C相': 'phase_c', 'C相电流': 'phase_c', 'C': 'phase_c',
            '总电流': 'total_current', '总': 'total',
            '不平衡度': 'unbalance_rate', '不平衡': 'unbalance',
        }
        
        for cn, en in mapping.items():
            if cn in text:
                return en
        
        # 默认处理
        cleaned = re.sub(r'[^\w\s]', '', text).strip().lower()
        return re.sub(r'\s+', '_', cleaned) or 'field'
