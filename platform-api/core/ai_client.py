# -*- coding: utf-8 -*-
"""
AI 客户端
支持 Minimax / OpenAI 兼容接口进行智能代码生成
"""

import os
import json
import re
from typing import Dict, List, Any, Optional
import requests


class AIClient:
    """AI 大模型客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv('AI_API_KEY', '')
        self.base_url = base_url or os.getenv('AI_BASE_URL', 'https://api.minimax.chat/v1')
        self.model = model or os.getenv('AI_MODEL', 'MiniMax-Text-01')
        
    def generate_code(self, prompt: str, system_prompt: str = None, temperature: float = 0.3) -> str:
        """
        调用 AI 生成代码
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数
        
        Returns:
            生成的代码文本
        """
        if not self.api_key:
            raise ValueError("AI API Key 未配置")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 8000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            
            # 提取生成的内容
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            return content
            
        except Exception as e:
            print(f"[ERROR] AI 调用失败: {e}")
            raise
    
    def generate_service_code(self, html_info: Dict[str, Any], skill_info: Dict[str, Any], 
                              service_config: Dict[str, Any]) -> Dict[str, str]:
        """
        智能生成服务代码
        
        根据 HTML 结构和技能包信息，调用 AI 生成高质量的动态服务代码
        """
        system_prompt = """你是一位专业的 Python 后端开发工程师和前端开发专家。
你的任务是根据用户提供的 HTML 报表页面结构和数据技能包，生成完整的 Flask 动态服务代码。

要求：
1. 生成的代码必须可直接运行
2. 保留原 HTML 的所有样式和交互
3. 将静态数据替换为动态数据接口
4. 添加自动刷新功能
5. 代码注释使用中文
6. 遵循 RESTful API 设计规范

输出格式：
- 只输出代码，不要解释
- 使用 ```python 和 ```html 标记代码块
- 文件之间用 ### filename ### 分隔
"""
        
        prompt = self._build_generation_prompt(html_info, skill_info, service_config)
        
        try:
            content = self.generate_code(prompt, system_prompt, temperature=0.2)
            return self._parse_generated_code(content)
        except Exception as e:
            print(f"[WARN] AI 生成失败，回退到模板生成: {e}")
            # 回退到模板生成
            from core.transformer import Transformer
            transformer = Transformer()
            return transformer.transform(html_info, skill_info, service_config)
    
    def _build_generation_prompt(self, html_info: Dict[str, Any], skill_info: Dict[str, Any],
                                  service_config: Dict[str, Any]) -> str:
        """构建生成提示词"""
        
        # HTML 结构摘要
        html_summary = f"""
【HTML 报表页面】
- 标题: {html_info.get('title', '未命名')}
- 主题: {html_info.get('style', {}).get('theme', 'default')}
- 数据区域: {len(html_info.get('data_regions', []))} 个
"""
        
        # 数据区域详情
        for region in html_info.get('data_regions', []):
            if region['type'] == 'stat_cards':
                html_summary += f"- 统计卡片: {len(region.get('items', []))} 个指标\n"
            elif region['type'] == 'data_table':
                html_summary += f"- 数据表格: {len(region.get('columns', []))} 列\n"
            elif region['type'] == 'conclusion_box':
                html_summary += f"- 结论区域: {len(region.get('items', []))} 项\n"
        
        # 技能包摘要
        skill_summary = f"""
【技能包配置】
- 名称: {skill_info.get('name', '未命名')}
- 数据源: {skill_info.get('data_source', {}).get('type', 'unknown')}
- 数据源地址: {skill_info.get('data_source', {}).get('base_url', '')}
- 计算公式: {skill_info.get('calculation', {}).get('formula', '无')}
- 过滤条件: {skill_info.get('calculation', {}).get('filters', [])}
- 阈值: {skill_info.get('calculation', {}).get('thresholds', {})}
"""
        
        # 服务配置
        config_summary = f"""
【服务配置】
- 名称: {service_config.get('name', 'dynamic-report')}
- 标题: {service_config.get('title', '动态报表')}
- 刷新策略: {service_config.get('refresh_strategy', 'cron')}
- Cron: {service_config.get('refresh_cron', '0 */6 * * *')}
"""
        
        prompt = f"""请根据以下信息生成完整的 Flask 动态服务代码：

{html_summary}
{skill_summary}
{config_summary}

请生成以下文件：

1. **app.py** - Flask 主应用，包含：
   - / 路由渲染动态页面
   - /api/data 路由返回 JSON 数据
   - /api/refresh 路由手动刷新
   - APScheduler 定时任务
   - 数据缓存机制

2. **data_fetcher.py** - 数据拉取模块，包含：
   - 从智航 CMDB 获取设备列表
   - 获取实时数据
   - 错误处理和重试机制

3. **calculator.py** - 计算模块，包含：
   - 业务计算逻辑
   - 数据过滤
   - 汇总统计

4. **templates/index.html** - 动态前端页面：
   - 保留原 HTML 样式
   - 使用 Jinja2 模板变量
   - 添加前端自动刷新 JS
   - 保留 Excel 导出功能

请确保代码完整、可直接运行。
"""
        return prompt
    
    def _parse_generated_code(self, content: str) -> Dict[str, str]:
        """解析 AI 生成的代码"""
        files = {}
        
        # 按文件分隔符分割
        file_pattern = r'###\s*(.+?)\s*###\s*```(?:\w+)?\s*\n(.*?)```'
        matches = re.findall(file_pattern, content, re.DOTALL)
        
        for filename, code in matches:
            files[filename.strip()] = code.strip()
        
        # 如果没有匹配到分隔符格式，尝试直接提取代码块
        if not files:
            code_blocks = re.findall(r'```(?:\w+)?\s*\n(.*?)```', content, re.DOTALL)
            if len(code_blocks) >= 4:
                files['app.py'] = code_blocks[0]
                files['data_fetcher.py'] = code_blocks[1]
                files['calculator.py'] = code_blocks[2]
                files['templates/index.html'] = code_blocks[3]
        
        return files
    
    def analyze_html(self, html_content: str) -> Dict[str, Any]:
        """
        使用 AI 分析 HTML 结构
        """
        system_prompt = "你是一位前端分析专家，擅长分析 HTML 页面结构。"
        
        prompt = f"""请分析以下 HTML 页面的结构，提取关键信息：

```html
{html_content[:5000]}
```

请输出 JSON 格式：
{{
  "title": "页面标题",
  "theme": "主题风格(dark/light)",
  "data_regions": [
    {{"type": "stat_cards/table/chart", "description": "描述"}}
  ],
  "interactions": ["export", "refresh", "search"],
  "key_data_fields": ["字段名"]
}}
"""
        
        try:
            content = self.generate_code(prompt, system_prompt, temperature=0.1)
            # 提取 JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"[WARN] AI HTML 分析失败: {e}")
        
        return {}
    
    def analyze_skill(self, skill_py: str, skill_md: str = '') -> Dict[str, Any]:
        """
        使用 AI 分析技能包
        """
        system_prompt = "你是一位 Python 代码分析专家，擅长提取代码中的配置和逻辑。"
        
        prompt = f"""请分析以下技能包代码，提取关键配置：

【Python 代码】
```python
{skill_py[:8000]}
```

【Markdown 文档】
```markdown
{skill_md[:3000]}
```

请输出 JSON 格式：
{{
  "name": "技能名称",
  "data_source": {{"type": "", "base_url": ""}},
  "fetch_steps": ["步骤1", "步骤2"],
  "calculation": {{"formula": "", "filters": [], "thresholds": {{}}}},
  "datacenters": {{"名称": "domainCode"}}
}}
"""
        
        try:
            content = self.generate_code(prompt, system_prompt, temperature=0.1)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"[WARN] AI Skill 分析失败: {e}")
        
        return {}


# 全局 AI 客户端实例
_ai_client = None

def get_ai_client() -> AIClient:
    """获取全局 AI 客户端实例"""
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client

def configure_ai(api_key: str, base_url: str = None, model: str = None):
    """配置 AI 客户端"""
    global _ai_client
    _ai_client = AIClient(api_key=api_key, base_url=base_url, model=model)
    return _ai_client
