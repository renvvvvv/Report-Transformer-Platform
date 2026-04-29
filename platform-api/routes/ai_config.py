# -*- coding: utf-8 -*-
"""
AI 配置路由
管理 AI API 配置，支持智能代码生成
"""

import os
from flask import Blueprint, request, jsonify

from core.ai_client import configure_ai, get_ai_client

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/ai/config', methods=['GET'])
def get_ai_config():
    """获取当前 AI 配置（隐藏完整 API Key）"""
    api_key = os.getenv('AI_API_KEY', '')
    base_url = os.getenv('AI_BASE_URL', 'https://api.minimax.chat/v1')
    model = os.getenv('AI_MODEL', 'MiniMax-Text-01')
    
    # 隐藏 API Key 中间部分
    masked_key = ''
    if api_key:
        if len(api_key) > 12:
            masked_key = api_key[:6] + '****' + api_key[-6:]
        else:
            masked_key = '****'
    
    return jsonify({
        'success': True,
        'config': {
            'api_key': masked_key,
            'base_url': base_url,
            'model': model,
            'is_configured': bool(api_key)
        }
    })


@ai_bp.route('/ai/config', methods=['POST', 'PUT'])
def update_ai_config():
    """更新 AI 配置"""
    data = request.get_json()
    
    api_key = data.get('api_key', '').strip()
    base_url = data.get('base_url', 'https://api.minimax.chat/v1').strip()
    model = data.get('model', 'MiniMax-Text-01').strip()
    
    if not api_key:
        return jsonify({'success': False, 'message': 'API Key 不能为空'}), 400
    
    try:
        # 更新环境变量
        os.environ['AI_API_KEY'] = api_key
        os.environ['AI_BASE_URL'] = base_url
        os.environ['AI_MODEL'] = model
        
        # 重新配置 AI 客户端
        configure_ai(api_key, base_url, model)
        
        # 可选：测试连接（不阻塞配置保存）
        test_success = False
        test_message = ''
        try:
            client = get_ai_client()
            test_response = client.generate_code(
                prompt="Hello, please respond with 'OK' only.",
                temperature=0.1
            )
            test_success = True
            test_message = test_response[:100]
        except Exception as test_e:
            test_message = str(test_e)
        
        return jsonify({
            'success': True,
            'message': 'AI 配置已保存' + ('，连接验证成功' if test_success else '，连接验证跳过'),
            'config': {
                'base_url': base_url,
                'model': model,
                'is_configured': True
            },
            'test_success': test_success,
            'test_message': test_message
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'配置失败: {str(e)}'
        }), 500


@ai_bp.route('/ai/test', methods=['POST'])
def test_ai_connection():
    """测试 AI 连接"""
    try:
        client = get_ai_client()
        
        # 检查是否已配置
        if not client.api_key:
            return jsonify({
                'success': False,
                'message': 'AI 未配置，请先设置 API Key'
            }), 400
        
        # 发送测试请求
        response = client.generate_code(
            prompt="请用一句话介绍自己。",
            temperature=0.5
        )
        
        return jsonify({
            'success': True,
            'message': 'AI 连接测试成功',
            'response': response
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'连接测试失败: {str(e)}'
        }), 500


@ai_bp.route('/ai/models', methods=['GET'])
def get_supported_models():
    """获取支持的模型列表"""
    models = [
        {
            'id': 'MiniMax-Text-01',
            'name': 'MiniMax-Text-01',
            'provider': 'minimax',
            'description': 'MiniMax 大语言模型，支持长文本',
            'max_tokens': 8000
        },
        {
            'id': 'abab6.5s-chat',
            'name': 'abab6.5s-chat',
            'provider': 'minimax',
            'description': 'MiniMax abab6.5s 对话模型',
            'max_tokens': 8000
        },
        {
            'id': 'gpt-4o',
            'name': 'GPT-4o',
            'provider': 'openai',
            'description': 'OpenAI GPT-4o',
            'max_tokens': 8000
        },
        {
            'id': 'gpt-4o-mini',
            'name': 'GPT-4o Mini',
            'provider': 'openai',
            'description': 'OpenAI GPT-4o Mini（性价比高）',
            'max_tokens': 8000
        },
        {
            'id': 'deepseek-chat',
            'name': 'DeepSeek-V3',
            'provider': 'deepseek',
            'description': 'DeepSeek 对话模型',
            'max_tokens': 8000
        }
    ]
    
    return jsonify({
        'success': True,
        'models': models
    })


@ai_bp.route('/ai/generate', methods=['POST'])
def ai_generate():
    """
    使用 AI 生成代码
    
    请求体：
    {
        "html_info": {...},
        "skill_info": {...},
        "service_config": {...}
    }
    """
    data = request.get_json()
    
    try:
        client = get_ai_client()
        
        if not client.api_key:
            return jsonify({
                'success': False,
                'message': 'AI 未配置，请先设置 API Key',
                'code': 'AI_NOT_CONFIGURED'
            }), 400
        
        html_info = data.get('html_info', {})
        skill_info = data.get('skill_info', {})
        service_config = data.get('service_config', {})
        
        # 调用 AI 生成代码
        generated_files = client.generate_service_code(html_info, skill_info, service_config)
        
        return jsonify({
            'success': True,
            'message': 'AI 代码生成成功',
            'generated_files': list(generated_files.keys()),
            'files': generated_files
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'AI 生成失败: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500
