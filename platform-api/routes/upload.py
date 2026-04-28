# -*- coding: utf-8 -*-
"""
文件上传路由
处理HTML文件和技能包的上传
"""

import os
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

upload_bp = Blueprint('upload', __name__)

UPLOAD_FOLDER = os.environ.get('UPLOADS_DIR', '/app/uploads')
ALLOWED_HTML_EXTENSIONS = {'html', 'htm'}
ALLOWED_SKILL_EXTENSIONS = {'py', 'md', 'yaml', 'yml', 'json', 'zip'}


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


@upload_bp.route('/upload/html', methods=['POST'])
def upload_html():
    """上传HTML文件"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    
    if not allowed_file(file.filename, ALLOWED_HTML_EXTENSIONS):
        return jsonify({'success': False, 'message': '只允许上传HTML文件'}), 400
    
    try:
        # 生成唯一ID
        upload_id = str(uuid.uuid4())[:8]
        filename = f"{upload_id}_{secure_filename(file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        file.save(filepath)
        
        # 读取内容
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'filename': filename,
            'size': len(content),
            'preview': content[:500] + '...' if len(content) > 500 else content
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500


@upload_bp.route('/upload/skill', methods=['POST'])
def upload_skill():
    """上传技能包"""
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': '没有文件'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': '文件名为空'}), 400
    
    upload_id = str(uuid.uuid4())[:8]
    skill_dir = os.path.join(UPLOAD_FOLDER, f"skill_{upload_id}")
    os.makedirs(skill_dir, exist_ok=True)
    
    saved_files = []
    
    try:
        for file in files:
            if file and allowed_file(file.filename, ALLOWED_SKILL_EXTENSIONS):
                filename = secure_filename(file.filename)
                filepath = os.path.join(skill_dir, filename)
                file.save(filepath)
                saved_files.append(filename)
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'files': saved_files,
            'skill_dir': skill_dir
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500


@upload_bp.route('/upload/bundle', methods=['POST'])
def upload_bundle():
    """上传完整包（HTML + 技能包）"""
    upload_id = str(uuid.uuid4())[:8]
    bundle_dir = os.path.join(UPLOAD_FOLDER, f"bundle_{upload_id}")
    os.makedirs(bundle_dir, exist_ok=True)
    
    try:
        # 保存HTML文件
        html_file = request.files.get('html')
        if html_file and allowed_file(html_file.filename, ALLOWED_HTML_EXTENSIONS):
            html_path = os.path.join(bundle_dir, 'report.html')
            html_file.save(html_path)
        
        # 保存技能包文件
        skill_files = request.files.getlist('skill_files')
        skill_dir = os.path.join(bundle_dir, 'skill')
        os.makedirs(skill_dir, exist_ok=True)
        
        saved_skills = []
        for sf in skill_files:
            if sf and allowed_file(sf.filename, ALLOWED_SKILL_EXTENSIONS):
                sf.save(os.path.join(skill_dir, secure_filename(sf.filename)))
                saved_skills.append(sf.filename)
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'bundle_dir': bundle_dir,
            'html_file': html_file.filename if html_file else None,
            'skill_files': saved_skills
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500


@upload_bp.route('/upload/<upload_id>', methods=['GET'])
def get_upload(upload_id):
    """获取上传文件信息"""
    # 查找上传的文件
    for prefix in ['', 'skill_', 'bundle_']:
        path = os.path.join(UPLOAD_FOLDER, f"{prefix}{upload_id}")
        if os.path.exists(path):
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({
                    'success': True,
                    'upload_id': upload_id,
                    'type': 'file',
                    'content': content
                })
            else:
                files = os.listdir(path)
                return jsonify({
                    'success': True,
                    'upload_id': upload_id,
                    'type': 'directory',
                    'files': files
                })
    
    return jsonify({'success': False, 'message': '文件不存在'}), 404
