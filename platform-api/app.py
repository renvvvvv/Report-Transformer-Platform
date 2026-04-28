# -*- coding: utf-8 -*-
"""
Report Transformer Platform - 主应用
HTML静态报表 → Docker动态服务 自动化转化平台
"""

import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, jsonify
from flask_cors import CORS

# 导入路由
from routes.upload import upload_bp
from routes.transform import transform_bp
from routes.deploy import deploy_bp
from routes.services import services_bp

app = Flask(__name__)
CORS(app)

# 注册蓝图
app.register_blueprint(upload_bp, url_prefix='/api')
app.register_blueprint(transform_bp, url_prefix='/api')
app.register_blueprint(deploy_bp, url_prefix='/api')
app.register_blueprint(services_bp, url_prefix='/api')

# ========== 管理界面HTML模板 ==========
ADMIN_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Transformer Platform - 报表自动化转化平台</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Noto Sans SC', sans-serif; background: #0f172a; color: #e2e8f0; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(56, 189, 248, 0.15); }
        .gradient-text { background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .step-active { border-color: #38bdf8; background: rgba(56, 189, 248, 0.1); }
        .step-done { border-color: #10b981; background: rgba(16, 185, 129, 0.1); }
        .btn-primary { background: linear-gradient(135deg, #3b82f6, #2563eb); }
        .btn-primary:hover { background: linear-gradient(135deg, #2563eb, #1d4ed8); }
        .btn-success { background: linear-gradient(135deg, #10b981, #059669); }
        .btn-success:hover { background: linear-gradient(135deg, #059669, #047857); }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #dc2626); }
        .service-card { transition: all 0.3s ease; }
        .service-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(56, 189, 248, 0.15); }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
        .status-running { background: #10b981; box-shadow: 0 0 8px #10b981; }
        .status-stopped { background: #ef4444; }
        .status-deploying { background: #f59e0b; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .log-container { font-family: 'Consolas', monospace; font-size: 12px; line-height: 1.6; }
        .tab-active { border-bottom: 2px solid #38bdf8; color: #38bdf8; }
        .drop-zone { border: 2px dashed rgba(56, 189, 248, 0.3); transition: all 0.3s; }
        .drop-zone.dragover { border-color: #38bdf8; background: rgba(56, 189, 248, 0.1); }
    </style>
</head>
<body class="min-h-screen">
    <!-- Header -->
    <header class="glass sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div class="flex items-center gap-4">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/>
                    </svg>
                </div>
                <div>
                    <h1 class="text-xl font-bold gradient-text">Report Transformer</h1>
                    <p class="text-xs text-gray-400">HTML静态报表 → Docker动态服务</p>
                </div>
            </div>
            <div class="flex items-center gap-4">
                <span class="text-sm text-gray-400" id="platformStatus">
                    <span class="status-dot status-running mr-2"></span>平台运行中
                </span>
                <a href="/api/services" target="_blank" class="text-sm text-cyan-400 hover:text-cyan-300">API文档</a>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-8">
        <!-- 标签页 -->
        <div class="flex gap-6 mb-8 border-b border-gray-700">
            <button onclick="switchTab('create')" id="tab-create" class="tab-active pb-3 px-2 font-medium">🚀 创建服务</button>
            <button onclick="switchTab('services')" id="tab-services" class="pb-3 px-2 font-medium text-gray-400 hover:text-gray-200">📊 服务管理</button>
            <button onclick="switchTab('routes')" id="tab-routes" class="pb-3 px-2 font-medium text-gray-400 hover:text-gray-200">🌐 路由配置</button>
        </div>

        <!-- 创建服务页 -->
        <div id="page-create" class="space-y-6">
            <!-- 步骤指示器 -->
            <div class="flex gap-4 mb-8">
                <div id="step1-indicator" class="flex-1 glass rounded-xl p-4 step-active">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold">1</div>
                        <div>
                            <div class="font-medium">上传文件</div>
                            <div class="text-xs text-gray-400">HTML + 技能包</div>
                        </div>
                    </div>
                </div>
                <div id="step2-indicator" class="flex-1 glass rounded-xl p-4">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white font-bold">2</div>
                        <div>
                            <div class="font-medium">解析配置</div>
                            <div class="text-xs text-gray-400">自动分析结构</div>
                        </div>
                    </div>
                </div>
                <div id="step3-indicator" class="flex-1 glass rounded-xl p-4">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white font-bold">3</div>
                        <div>
                            <div class="font-medium">生成部署</div>
                            <div class="text-xs text-gray-400">Docker服务</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Step 1: 上传 -->
            <div id="step1" class="glass rounded-xl p-6">
                <h2 class="text-lg font-semibold mb-4">📁 上传报表文件</h2>
                
                <div class="grid md:grid-cols-2 gap-6">
                    <!-- HTML上传 -->
                    <div>
                        <label class="block text-sm text-gray-400 mb-2">HTML报表文件</label>
                        <div id="htmlDropZone" class="drop-zone rounded-xl p-8 text-center cursor-pointer">
                            <svg class="w-12 h-12 mx-auto text-gray-500 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                            </svg>
                            <p class="text-gray-400">拖拽HTML文件到此处</p>
                            <p class="text-xs text-gray-500 mt-1">或点击选择文件</p>
                            <input type="file" id="htmlFile" accept=".html,.htm" class="hidden" onchange="handleHtmlSelect(event)">
                        </div>
                        <div id="htmlFileInfo" class="mt-2 text-sm text-cyan-400 hidden"></div>
                    </div>

                    <!-- 技能包上传 -->
                    <div>
                        <label class="block text-sm text-gray-400 mb-2">技能包文件 (Python + Markdown)</label>
                        <div id="skillDropZone" class="drop-zone rounded-xl p-8 text-center cursor-pointer">
                            <svg class="w-12 h-12 mx-auto text-gray-500 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
                            </svg>
                            <p class="text-gray-400">拖拽技能包文件到此处</p>
                            <p class="text-xs text-gray-500 mt-1">支持 .py, .md, .yaml</p>
                            <input type="file" id="skillFiles" accept=".py,.md,.yaml,.yml,.json" multiple class="hidden" onchange="handleSkillSelect(event)">
                        </div>
                        <div id="skillFilesInfo" class="mt-2 text-sm text-cyan-400 hidden"></div>
                    </div>
                </div>

                <div class="mt-6 flex justify-end">
                    <button onclick="uploadBundle()" id="uploadBtn" class="btn-primary px-6 py-2 rounded-lg text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed" disabled>
                        上传并解析
                    </button>
                </div>
            </div>

            <!-- Step 2: 解析结果 -->
            <div id="step2" class="glass rounded-xl p-6 hidden">
                <h2 class="text-lg font-semibold mb-4">🔍 解析结果</h2>
                
                <div class="grid md:grid-cols-2 gap-6">
                    <!-- HTML解析 -->
                    <div class="bg-gray-800/50 rounded-lg p-4">
                        <h3 class="font-medium text-cyan-400 mb-3">📄 HTML结构</h3>
                        <div id="htmlParseResult" class="space-y-2 text-sm"></div>
                    </div>

                    <!-- 技能包解析 -->
                    <div class="bg-gray-800/50 rounded-lg p-4">
                        <h3 class="font-medium text-purple-400 mb-3">⚙️ 技能包配置</h3>
                        <div id="skillParseResult" class="space-y-2 text-sm"></div>
                    </div>
                </div>

                <!-- 服务配置 -->
                <div class="mt-6 bg-gray-800/50 rounded-lg p-4">
                    <h3 class="font-medium text-green-400 mb-3">🔧 服务配置</h3>
                    <div class="grid md:grid-cols-3 gap-4">
                        <div>
                            <label class="block text-xs text-gray-400 mb-1">服务名称</label>
                            <input type="text" id="serviceName" class="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm" placeholder="pdu-unbalance">
                        </div>
                        <div>
                            <label class="block text-xs text-gray-400 mb-1">数据中心</label>
                            <select id="datacenterSelect" class="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm">
                                <option value="default">默认</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs text-gray-400 mb-1">刷新策略</label>
                            <select id="refreshStrategy" class="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm">
                                <option value="cron">定时Cron</option>
                                <option value="interval">固定间隔</option>
                                <option value="manual">手动刷新</option>
                            </select>
                        </div>
                    </div>
                    <div class="mt-4">
                        <label class="block text-xs text-gray-400 mb-1">Cron表达式</label>
                        <input type="text" id="cronExpression" class="w-full md:w-1/3 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm" value="0 */6 * * *" placeholder="0 */6 * * *">
                        <p class="text-xs text-gray-500 mt-1">默认每6小时刷新一次</p>
                    </div>
                </div>

                <div class="mt-6 flex justify-end gap-3">
                    <button onclick="generateService()" id="generateBtn" class="btn-primary px-6 py-2 rounded-lg text-white font-medium">
                        生成服务代码
                    </button>
                </div>
            </div>

            <!-- Step 3: 部署 -->
            <div id="step3" class="glass rounded-xl p-6 hidden">
                <h2 class="text-lg font-semibold mb-4">🚀 部署服务</h2>
                
                <div id="generatedFiles" class="bg-gray-800/50 rounded-lg p-4 mb-4">
                    <h3 class="font-medium text-cyan-400 mb-2">📦 生成的文件</h3>
                    <div id="filesList" class="space-y-1 text-sm"></div>
                </div>

                <div id="deployPreview" class="bg-gray-800/50 rounded-lg p-4 mb-4 hidden">
                    <h3 class="font-medium text-green-400 mb-2">✅ 部署预览</h3>
                    <div class="text-sm space-y-1">
                        <p>服务名称: <span id="previewName" class="text-cyan-400"></span></p>
                        <p>访问路径: <span id="previewPath" class="text-cyan-400"></span></p>
                        <p>容器端口: <span id="previewPort" class="text-cyan-400"></span></p>
                    </div>
                </div>

                <div class="flex justify-end gap-3">
                    <button onclick="deployService()" id="deployBtn" class="btn-success px-6 py-2 rounded-lg text-white font-medium">
                        一键部署
                    </button>
                </div>

                <!-- 部署日志 -->
                <div id="deployLogs" class="mt-4 hidden">
                    <h3 class="font-medium text-gray-400 mb-2">📋 部署日志</h3>
                    <div class="log-container bg-black rounded-lg p-4 max-h-64 overflow-y-auto" id="logContent"></div>
                </div>
            </div>
        </div>

        <!-- 服务管理页 -->
        <div id="page-services" class="hidden space-y-6">
            <div class="flex items-center justify-between">
                <h2 class="text-lg font-semibold">📊 已部署服务</h2>
                <button onclick="loadServices()" class="text-sm text-cyan-400 hover:text-cyan-300">
                    <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    刷新
                </button>
            </div>
            <div id="servicesList" class="grid md:grid-cols-2 lg:grid-cols-3 gap-4"></div>
        </div>

        <!-- 路由配置页 -->
        <div id="page-routes" class="hidden space-y-6">
            <h2 class="text-lg font-semibold">🌐 Nginx路由配置</h2>
            <div class="glass rounded-xl p-4">
                <div id="routesList" class="space-y-2"></div>
            </div>
        </div>
    </main>

    <script>
        // 全局状态
        let currentUploadId = null;
        let currentServiceName = null;
        let htmlFileSelected = null;
        let skillFilesSelected = [];

        // 标签切换
        function switchTab(tab) {
            ['create', 'services', 'routes'].forEach(t => {
                document.getElementById(`page-${t}`).classList.add('hidden');
                document.getElementById(`tab-${t}`).classList.remove('tab-active');
                document.getElementById(`tab-${t}`).classList.add('text-gray-400');
            });
            document.getElementById(`page-${tab}`).classList.remove('hidden');
            document.getElementById(`tab-${tab}`).classList.add('tab-active');
            document.getElementById(`tab-${tab}`).classList.remove('text-gray-400');

            if (tab === 'services') loadServices();
            if (tab === 'routes') loadRoutes();
        }

        // 拖拽上传
        function setupDropZone(zoneId, inputId, handler) {
            const zone = document.getElementById(zoneId);
            const input = document.getElementById(inputId);

            zone.addEventListener('click', () => input.click());
            zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
            zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('dragover');
                handler(e.dataTransfer.files);
            });
        }

        setupDropZone('htmlDropZone', 'htmlFile', (files) => {
            if (files.length > 0) {
                htmlFileSelected = files[0];
                document.getElementById('htmlFileInfo').textContent = `✓ ${files[0].name} (${(files[0].size/1024).toFixed(1)}KB)`;
                document.getElementById('htmlFileInfo').classList.remove('hidden');
                checkUploadReady();
            }
        });

        setupDropZone('skillDropZone', 'skillFiles', (files) => {
            skillFilesSelected = Array.from(files);
            const names = skillFilesSelected.map(f => f.name).join(', ');
            document.getElementById('skillFilesInfo').textContent = `✓ ${skillFilesSelected.length} 个文件: ${names}`;
            document.getElementById('skillFilesInfo').classList.remove('hidden');
            checkUploadReady();
        });

        function handleHtmlSelect(e) {
            if (e.target.files.length > 0) {
                htmlFileSelected = e.target.files[0];
                document.getElementById('htmlFileInfo').textContent = `✓ ${htmlFileSelected.name} (${(htmlFileSelected.size/1024).toFixed(1)}KB)`;
                document.getElementById('htmlFileInfo').classList.remove('hidden');
                checkUploadReady();
            }
        }

        function handleSkillSelect(e) {
            skillFilesSelected = Array.from(e.target.files);
            const names = skillFilesSelected.map(f => f.name).join(', ');
            document.getElementById('skillFilesInfo').textContent = `✓ ${skillFilesSelected.length} 个文件: ${names}`;
            document.getElementById('skillFilesInfo').classList.remove('hidden');
            checkUploadReady();
        }

        function checkUploadReady() {
            const btn = document.getElementById('uploadBtn');
            btn.disabled = !(htmlFileSelected && skillFilesSelected.length > 0);
        }

        // 上传文件包
        async function uploadBundle() {
            const btn = document.getElementById('uploadBtn');
            btn.disabled = true;
            btn.textContent = '上传中...';

            const formData = new FormData();
            formData.append('html', htmlFileSelected);
            skillFilesSelected.forEach(f => formData.append('skill_files', f));

            try {
                const res = await fetch('/api/upload/bundle', { method: 'POST', body: formData });
                const data = await res.json();

                if (data.success) {
                    currentUploadId = data.upload_id;
                    showToast('上传成功', 'success');
                    
                    // 进入步骤2
                    document.getElementById('step1').classList.add('hidden');
                    document.getElementById('step2').classList.remove('hidden');
                    document.getElementById('step1-indicator').classList.add('step-done');
                    document.getElementById('step1-indicator').classList.remove('step-active');
                    document.getElementById('step2-indicator').classList.add('step-active');
                    
                    // 自动解析
                    parseUpload();
                } else {
                    showToast(data.message, 'error');
                }
            } catch (e) {
                showToast('上传失败: ' + e.message, 'error');
            } finally {
                btn.textContent = '上传并解析';
                btn.disabled = false;
            }
        }

        // 解析上传
        async function parseUpload() {
            try {
                const res = await fetch('/api/transform/parse', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ upload_id: currentUploadId })
                });
                const data = await res.json();

                if (data.success) {
                    const result = data.parse_result;
                    
                    // 显示HTML解析结果
                    document.getElementById('htmlParseResult').innerHTML = `
                        <p>📌 标题: ${result.html.title}</p>
                        <p>🎨 主题: ${result.html.theme}</p>
                        <p>📊 数据区域: ${result.html.data_regions_count} 个</p>
                        <p>🖱️ 交互: ${result.html.interactions.map(i => i.type).join(', ') || '无'}</p>
                    `;
                    
                    // 显示技能包解析结果
                    document.getElementById('skillParseResult').innerHTML = `
                        <p>📛 名称: ${result.skill.name}</p>
                        <p>🔌 数据源: ${result.skill.data_source_type}</p>
                        <p>📡 拉取步骤: ${result.skill.fetch_steps_count} 步</p>
                        <p>🧮 计算公式: ${result.skill.calculation_formula || '无'}</p>
                        <p>🏢 数据中心: ${result.skill.datacenters.join(', ') || '默认'}</p>
                    `;
                    
                    // 填充数据中心选项
                    const dcSelect = document.getElementById('datacenterSelect');
                    dcSelect.innerHTML = result.skill.datacenters.map(dc => 
                        `<option value="${dc}">${dc}</option>`
                    ).join('') || '<option value="default">默认</option>';
                    
                    // 设置默认服务名
                    document.getElementById('serviceName').value = result.skill.name 
                        ? result.skill.name.toLowerCase().replace(/\\s+/g, '-').replace(/[^a-z0-9-]/g, '')
                        : `report-${currentUploadId}`;
                }
            } catch (e) {
                showToast('解析失败: ' + e.message, 'error');
            }
        }

        // 生成服务
        async function generateService() {
            const btn = document.getElementById('generateBtn');
            btn.disabled = true;
            btn.textContent = '生成中...';

            const config = {
                name: document.getElementById('serviceName').value,
                datacenter: document.getElementById('datacenterSelect').value,
                refresh_strategy: document.getElementById('refreshStrategy').value,
                refresh_cron: document.getElementById('cronExpression').value,
                path: `/reports/${document.getElementById('serviceName').value}`
            };

            try {
                const res = await fetch('/api/transform/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ upload_id: currentUploadId, service_config: config })
                });
                const data = await res.json();

                if (data.success) {
                    currentServiceName = data.service_name;
                    showToast('服务代码生成成功', 'success');
                    
                    // 进入步骤3
                    document.getElementById('step2').classList.add('hidden');
                    document.getElementById('step3').classList.remove('hidden');
                    document.getElementById('step2-indicator').classList.add('step-done');
                    document.getElementById('step2-indicator').classList.remove('step-active');
                    document.getElementById('step3-indicator').classList.add('step-active');
                    
                    // 显示文件列表
                    document.getElementById('filesList').innerHTML = data.generated_files.map(f => 
                        `<div class="flex items-center gap-2"><span class="text-green-400">✓</span> ${f}</div>`
                    ).join('');
                    
                    // 显示部署预览
                    document.getElementById('deployPreview').classList.remove('hidden');
                    document.getElementById('previewName').textContent = data.service_name;
                    document.getElementById('previewPath').textContent = data.service_config.path;
                    document.getElementById('previewPort').textContent = '自动分配';
                } else {
                    showToast(data.message, 'error');
                }
            } catch (e) {
                showToast('生成失败: ' + e.message, 'error');
            } finally {
                btn.textContent = '生成服务代码';
                btn.disabled = false;
            }
        }

        // 部署服务
        async function deployService() {
            const btn = document.getElementById('deployBtn');
            btn.disabled = true;
            btn.textContent = '部署中...';

            const config = {
                name: document.getElementById('serviceName').value,
                path: `/reports/${document.getElementById('serviceName').value}`
            };

            try {
                const res = await fetch('/api/deploy/full', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ upload_id: currentUploadId, service_config: config })
                });
                const data = await res.json();

                document.getElementById('deployLogs').classList.remove('hidden');
                const logContent = document.getElementById('logContent');

                if (data.success) {
                    logContent.innerHTML += `<div class="text-green-400">✅ ${data.message}</div>`;
                    logContent.innerHTML += `<div class="text-cyan-400">📍 访问地址: <a href="${data.access_url}" target="_blank" class="underline">${data.access_url}</a></div>`;
                    showToast('部署成功', 'success');
                    
                    // 显示启动按钮
                    btn.textContent = '已部署';
                    btn.classList.remove('btn-success');
                    btn.classList.add('bg-gray-600');
                } else {
                    logContent.innerHTML += `<div class="text-red-400">❌ ${data.message}</div>`;
                    if (data.traceback) {
                        logContent.innerHTML += `<div class="text-gray-500 mt-2">${data.traceback.replace(/\\n/g, '<br>')}</div>`;
                    }
                    showToast(data.message, 'error');
                    btn.disabled = false;
                    btn.textContent = '重新部署';
                }
            } catch (e) {
                showToast('部署失败: ' + e.message, 'error');
                btn.disabled = false;
                btn.textContent = '重新部署';
            }
        }

        // 加载服务列表
        async function loadServices() {
            try {
                const res = await fetch('/api/services');
                const data = await res.json();

                const container = document.getElementById('servicesList');
                if (data.services && data.services.length > 0) {
                    container.innerHTML = data.services.map(s => `
                        <div class="service-card glass rounded-xl p-4">
                            <div class="flex items-center justify-between mb-3">
                                <h3 class="font-semibold">${s.title}</h3>
                                <span class="status-dot ${s.status === 'running' ? 'status-running' : s.status === 'deploying' ? 'status-deploying' : 'status-stopped'}"></span>
                            </div>
                            <div class="text-sm text-gray-400 space-y-1">
                                <p>名称: ${s.name}</p>
                                <p>状态: ${s.status}</p>
                                <p>刷新: ${s.refresh_strategy}</p>
                            </div>
                            <div class="mt-3 flex gap-2">
                                <button onclick="controlService('${s.name}', 'start')" class="text-xs bg-green-600 hover:bg-green-700 px-3 py-1 rounded">启动</button>
                                <button onclick="controlService('${s.name}', 'stop')" class="text-xs bg-red-600 hover:bg-red-700 px-3 py-1 rounded">停止</button>
                                <button onclick="controlService('${s.name}', 'restart')" class="text-xs bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded">重启</button>
                                <button onclick="deleteService('${s.name}')" class="text-xs bg-gray-600 hover:bg-gray-700 px-3 py-1 rounded">删除</button>
                            </div>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<div class="text-gray-500 text-center py-8">暂无部署的服务</div>';
                }
            } catch (e) {
                document.getElementById('servicesList').innerHTML = '<div class="text-red-400 text-center py-8">加载失败</div>';
            }
        }

        // 控制服务
        async function controlService(name, action) {
            try {
                const res = await fetch(`/api/deploy/${action}/${name}`, { method: 'POST' });
                const data = await res.json();
                showToast(data.message, data.success ? 'success' : 'error');
                if (data.success) loadServices();
            } catch (e) {
                showToast('操作失败', 'error');
            }
        }

        // 删除服务
        async function deleteService(name) {
            if (!confirm(`确定要删除服务 ${name} 吗？`)) return;
            try {
                const res = await fetch(`/api/deploy/delete/${name}`, { method: 'DELETE' });
                const data = await res.json();
                showToast(data.message, data.success ? 'success' : 'error');
                if (data.success) loadServices();
            } catch (e) {
                showToast('删除失败', 'error');
            }
        }

        // 加载路由
        async function loadRoutes() {
            try {
                const res = await fetch('/api/routes');
                const data = await res.json();

                const container = document.getElementById('routesList');
                if (data.routes && data.routes.length > 0) {
                    container.innerHTML = data.routes.map(r => `
                        <div class="flex items-center justify-between bg-gray-800/50 rounded-lg p-3">
                            <div>
                                <span class="text-cyan-400 font-mono">${r.path}</span>
                                <span class="text-gray-500 mx-2">→</span>
                                <span class="text-green-400">${r.upstream}</span>
                            </div>
                            <span class="text-xs text-gray-500">${r.service_name}</span>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<div class="text-gray-500 text-center py-4">暂无路由配置</div>';
                }
            } catch (e) {
                document.getElementById('routesList').innerHTML = '<div class="text-red-400 text-center py-4">加载失败</div>';
            }
        }

        // Toast通知
        function showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `fixed top-4 right-4 px-4 py-2 rounded-lg text-white font-medium z-50 transition-all duration-300 ${
                type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-blue-600'
            }`;
            toast.textContent = message;
            document.body.appendChild(toast);
            setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
        }

        // 初始化
        document.addEventListener('DOMContentLoaded', () => {
            loadServices();
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    """平台管理首页"""
    return render_template_string(ADMIN_HTML)


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'platform': 'report-transformer-platform',
        'version': '1.0.0'
    })


if __name__ == '__main__':
    # 确保目录存在
    os.makedirs(os.environ.get('UPLOADS_DIR', '/app/uploads'), exist_ok=True)
    os.makedirs(os.environ.get('SERVICES_DIR', '/app/services'), exist_ok=True)
    os.makedirs(os.environ.get('NGINX_CONF_DIR', '/app/nginx_conf'), exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
