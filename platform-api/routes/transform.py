# -*- coding: utf-8 -*-
"""
转化任务路由
处理HTML+技能包的解析和转化
"""

import os
import json
from flask import Blueprint, request, jsonify

from core.html_parser import HTMLParser
from core.skill_parser import SkillParser
from core.transformer import Transformer

transform_bp = Blueprint('transform', __name__)

UPLOAD_FOLDER = os.environ.get('UPLOADS_DIR', '/app/uploads')


@transform_bp.route('/transform/parse', methods=['POST'])
def parse_upload():
    """解析已上传的文件"""
    data = request.get_json()
    upload_id = data.get('upload_id')
    
    if not upload_id:
        return jsonify({'success': False, 'message': '缺少upload_id'}), 400
    
    try:
        # 查找bundle目录
        bundle_dir = os.path.join(UPLOAD_FOLDER, f"bundle_{upload_id}")
        
        if not os.path.exists(bundle_dir):
            return jsonify({'success': False, 'message': '上传包不存在'}), 404
        
        # 读取HTML
        html_path = os.path.join(bundle_dir, 'report.html')
        html_content = ''
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        # 读取技能包
        skill_dir = os.path.join(bundle_dir, 'skill')
        py_content = ''
        md_content = ''
        yaml_content = ''
        
        if os.path.exists(skill_dir):
            for fname in os.listdir(skill_dir):
                fpath = os.path.join(skill_dir, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if fname.endswith('.py'):
                    py_content = content
                elif fname.endswith('.md'):
                    md_content = content
                elif fname.endswith(('.yaml', '.yml')):
                    yaml_content = content
        
        # 解析HTML
        html_parser = HTMLParser(html_content)
        html_info = html_parser.parse()
        html_schema = html_parser.get_data_schema()
        
        # 解析技能包
        skill_parser = SkillParser(py_content, md_content, yaml_content)
        skill_info = skill_parser.parse()
        
        # 保存解析结果
        parse_result = {
            'upload_id': upload_id,
            'html': {
                'title': html_info['title'],
                'theme': html_info['style'].get('theme', 'default'),
                'data_regions_count': len(html_info['data_regions']),
                'interactions': html_info['interactions'],
                'schema': html_schema
            },
            'skill': {
                'name': skill_info.get('name', '未命名'),
                'data_source_type': skill_info.get('data_source', {}).get('type', 'unknown'),
                'fetch_steps_count': len(skill_info.get('fetch_steps', [])),
                'calculation_formula': skill_info.get('calculation', {}).get('formula', ''),
                'thresholds': skill_info.get('calculation', {}).get('thresholds', {}),
                'datacenters': list(skill_info.get('config', {}).get('datacenters', {}).keys())[:5]
            }
        }
        
        # 保存到文件供后续使用
        result_path = os.path.join(bundle_dir, 'parse_result.json')
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(parse_result, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'parse_result': parse_result
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'解析失败: {str(e)}'}), 500


@transform_bp.route('/transform/generate', methods=['POST'])
def generate_service():
    """生成动态服务代码"""
    data = request.get_json()
    upload_id = data.get('upload_id')
    service_config = data.get('service_config', {})
    
    if not upload_id:
        return jsonify({'success': False, 'message': '缺少upload_id'}), 400
    
    try:
        # 读取原始文件
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
        
        # 解析
        html_parser = HTMLParser(html_content)
        html_info = html_parser.parse()
        
        skill_parser = SkillParser(py_content, md_content)
        skill_info = skill_parser.parse()
        
        # 设置默认服务配置
        default_config = {
            'name': service_config.get('name', f'report-{upload_id}'),
            'title': service_config.get('title', html_info['title']),
            'datacenter': service_config.get('datacenter', 'default'),
            'refresh_strategy': service_config.get('refresh_strategy', 'cron'),
            'refresh_cron': service_config.get('refresh_cron', '0 */6 * * *'),
            'refresh_interval': service_config.get('refresh_interval', 300),
            'path': service_config.get('path', f"/reports/report-{upload_id}"),
        }
        
        # 执行转化
        transformer = Transformer()
        generated_files = transformer.transform(html_info, skill_info, default_config)
        
        # 保存生成的文件
        generated_dir = os.path.join(bundle_dir, 'generated')
        os.makedirs(generated_dir, exist_ok=True)
        
        for file_path, content in generated_files.items():
            full_path = os.path.join(generated_dir, file_path.replace('/', os.sep))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return jsonify({
            'success': True,
            'service_name': default_config['name'],
            'generated_files': list(generated_files.keys()),
            'service_config': default_config
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'生成失败: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500


@transform_bp.route('/transform/preview/<upload_id>', methods=['GET'])
def preview_generated(upload_id):
    """预览生成的文件"""
    file_path = request.args.get('file', 'app.py')
    
    generated_dir = os.path.join(UPLOAD_FOLDER, f"bundle_{upload_id}", 'generated')
    target_path = os.path.join(generated_dir, file_path.replace('/', os.sep))
    
    if not os.path.exists(target_path):
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    
    with open(target_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return jsonify({
        'success': True,
        'file': file_path,
        'content': content
    })
