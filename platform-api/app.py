# -*- coding: utf-8 -*-
"""
Report Transformer Platform - 主应用
HTML静态报表 → Docker动态服务 自动化转化平台
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS

from routes.upload import upload_bp
from routes.transform import transform_bp
from routes.deploy import deploy_bp
from routes.services import services_bp
from routes.ai_config import ai_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(upload_bp, url_prefix='/api')
app.register_blueprint(transform_bp, url_prefix='/api')
app.register_blueprint(deploy_bp, url_prefix='/api')
app.register_blueprint(services_bp, url_prefix='/api')
app.register_blueprint(ai_bp, url_prefix='/api')

ADMIN_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Report Transformer Platform</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<script>
tailwind.config = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: { 50:'#eff6ff',100:'#dbeafe',200:'#bfdbfe',300:'#93c5fd',400:'#60a5fa',500:'#3b82f6',600:'#2563eb',700:'#1d4ed8',800:'#1e40af',900:'#1e3a8a' },
        dark: { 50:'#f8fafc',100:'#f1f5f9',200:'#e2e8f0',300:'#cbd5e1',400:'#94a3b8',500:'#64748b',600:'#475569',700:'#334155',800:'#1e293b',900:'#0f172a',950:'#020617' },
        accent: { 50:'#fdf4ff',100:'#fae8ff',200:'#f0abfc',300:'#e879f9',400:'#d946ef',500:'#c026d3',600:'#a21caf' },
        success: { 50:'#f0fdf4',100:'#dcfce7',200:'#bbf7d0',300:'#86efac',400:'#4ade80',500:'#22c55e',600:'#16a34a' },
        warning: { 50:'#fffbeb',100:'#fef3c7',200:'#fde68a',300:'#fcd34d',400:'#fbbf24',500:'#f59e0b' },
        danger: { 50:'#fef2f2',100:'#fee2e2',200:'#fecaca',300:'#fca5a5',400:'#f87171',500:'#ef4444' },
      }
    }
  }
}
</script>
<style>
*{box-sizing:border-box}
body{font-family:'Inter','Noto Sans SC',system-ui,sans-serif;background:#020617;color:#e2e8f0;min-height:100vh;margin:0}
.glass{background:rgba(30,41,59,0.6);backdrop-filter:blur(20px);border:1px solid rgba(148,163,184,0.08)}
.glass-hover:hover{background:rgba(51,65,85,0.5);border-color:rgba(148,163,184,0.15)}
.card{background:linear-gradient(145deg,rgba(30,41,59,0.8),rgba(15,23,42,0.9));border:1px solid rgba(148,163,184,0.08);border-radius:16px;transition:all .3s ease}
.card:hover{transform:translateY(-2px);border-color:rgba(148,163,184,0.15);box-shadow:0 20px 60px rgba(0,0,0,0.4)}
.btn-primary{background:linear-gradient(135deg,#3b82f6,#2563eb);border:none;color:#fff;padding:10px 24px;border-radius:10px;font-weight:500;cursor:pointer;transition:all .2s}
.btn-primary:hover{transform:translateY(-1px);box-shadow:0 8px 30px rgba(59,130,246,0.35)}
.btn-primary:disabled{opacity:.5;cursor:not-allowed;transform:none}
.btn-success{background:linear-gradient(135deg,#22c55e,#16a34a);border:none;color:#fff;padding:10px 24px;border-radius:10px;font-weight:500;cursor:pointer;transition:all .2s}
.btn-success:hover{transform:translateY(-1px);box-shadow:0 8px 30px rgba(34,197,94,0.35)}
.btn-ghost{background:transparent;border:1px solid rgba(148,163,184,0.2);color:#94a3b8;padding:8px 16px;border-radius:10px;cursor:pointer;transition:all .2s}
.btn-ghost:hover{border-color:#3b82f6;color:#3b82f6;background:rgba(59,130,246,0.08)}
.input-dark{background:rgba(15,23,42,0.8);border:1px solid rgba(148,163,184,0.15);color:#e2e8f0;padding:10px 14px;border-radius:10px;font-size:14px;transition:all .2s;width:100%}
.input-dark:focus{outline:none;border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,0.1)}
.input-dark::placeholder{color:#475569}
.select-dark{background:rgba(15,23,42,0.8);border:1px solid rgba(148,163,184,0.15);color:#e2e8f0;padding:10px 14px;border-radius:10px;font-size:14px;width:100%;cursor:pointer}
.tab-btn{padding:12px 20px;border:none;background:transparent;color:#64748b;font-size:14px;font-weight:500;cursor:pointer;border-bottom:2px solid transparent;transition:all .2s}
.tab-btn.active{color:#60a5fa;border-bottom-color:#3b82f6}
.tab-btn:hover:not(.active){color:#94a3b8}
.step-dot{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:14px;transition:all .3s}
.step-dot.active{background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;box-shadow:0 0 20px rgba(59,130,246,0.4)}
.step-dot.done{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff}
.step-dot.pending{background:rgba(51,65,85,0.5);color:#64748b;border:1px solid rgba(148,163,184,0.1)}
.dropzone{border:2px dashed rgba(148,163,184,0.15);border-radius:16px;padding:40px;text-align:center;cursor:pointer;transition:all .3s;background:rgba(15,23,42,0.4)}
.dropzone:hover,.dropzone.dragover{border-color:#3b82f6;background:rgba(59,130,246,0.05)}
.status-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:500}
.status-running{background:rgba(34,197,94,0.12);color:#4ade80}
.status-stopped{background:rgba(239,68,68,0.12);color:#f87171}
.status-deploying{background:rgba(245,158,11,0.12);color:#fbbf24}
.pulse-dot{width:6px;height:6px;border-radius:50%;background:#22c55e;box-shadow:0 0 8px #22c55e;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.toast{position:fixed;top:20px;right:20px;padding:14px 22px;border-radius:12px;color:#fff;font-weight:500;z-index:9999;opacity:0;transform:translateY(-20px);transition:all .3s ease;box-shadow:0 10px 40px rgba(0,0,0,0.3)}
.toast.show{opacity:1;transform:translateY(0)}
.toast.success{background:linear-gradient(135deg,#22c55e,#16a34a)}
.toast.error{background:linear-gradient(135deg,#ef4444,#dc2626)}
.toast.info{background:linear-gradient(135deg,#3b82f6,#2563eb)}
.code-block{background:#0f172a;border:1px solid rgba(148,163,184,0.1);border-radius:12px;padding:16px;font-family:'JetBrains Mono','Fira Code',monospace;font-size:13px;line-height:1.7;overflow-x:auto;color:#94a3b8}
.preview-frame{width:100%;height:500px;border:1px solid rgba(148,163,184,0.1);border-radius:12px;background:#0f172a}
.metric-card{padding:24px;border-radius:16px;background:linear-gradient(145deg,rgba(30,41,59,0.8),rgba(15,23,42,0.9));border:1px solid rgba(148,163,184,0.08)}
.metric-value{font-size:32px;font-weight:700;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(148,163,184,0.2);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:rgba(148,163,184,0.3)}
</style>
</head>
<body>

<!-- Header -->
<header style="position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(2,6,23,0.8);backdrop-filter:blur(20px);border-bottom:1px solid rgba(148,163,184,0.08)">
  <div style="max-width:1400px;margin:0 auto;padding:0 24px;height:64px;display:flex;align-items:center;justify-content:space-between">
    <div style="display:flex;align-items:center;gap:12px">
      <div style="width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center">
        <i class="fas fa-cube" style="color:#fff;font-size:16px"></i>
      </div>
      <div>
        <div style="font-size:16px;font-weight:700;color:#f8fafc;letter-spacing:-0.3px">Report Transformer</div>
        <div style="font-size:11px;color:#64748b;margin-top:-2px">静态报表 → 动态服务</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:16px">
      <div style="display:flex;align-items:center;gap:8px;padding:6px 14px;border-radius:20px;background:rgba(34,197,94,0.08)">
        <div class="pulse-dot"></div>
        <span style="font-size:13px;color:#4ade80;font-weight:500">运行中</span>
      </div>
      <a href="https://github.com/renvvvvv/Report-Transformer-Platform" target="_blank" style="color:#64748b;font-size:18px;transition:color .2s" onmouseover="this.style.color='#94a3b8'" onmouseout="this.style.color='#64748b'"><i class="fab fa-github"></i></a>
    </div>
  </div>
</header>

<!-- Main Content -->
<main style="max-width:1400px;margin:0 auto;padding:88px 24px 40px">

  <!-- Hero Section -->
  <div style="text-align:center;padding:48px 0 40px">
    <div style="display:inline-block;padding:6px 16px;border-radius:20px;background:linear-gradient(135deg,rgba(59,130,246,0.1),rgba(139,92,246,0.1));border:1px solid rgba(139,92,246,0.2);margin-bottom:20px">
      <span style="font-size:13px;color:#a78bfa;font-weight:500"><i class="fas fa-sparkles" style="margin-right:6px"></i>v1.0.0 自动化部署平台</span>
    </div>
    <h1 style="font-size:42px;font-weight:800;color:#f8fafc;margin:0 0 16px;letter-spacing:-1px;line-height:1.2">
      将静态 HTML 报表<br><span style="background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent">转化为动态 Docker 服务</span>
    </h1>
    <p style="font-size:17px;color:#64748b;max-width:560px;margin:0 auto 32px;line-height:1.7">
      上传 HTML 报表与技能包，自动解析、生成代码、部署为可定时刷新的动态服务，通过 Nginx 子路径统一管理
    </p>
    <div style="display:flex;gap:12px;justify-content:center">
      <button onclick="switchTab('create')" class="btn-primary" style="font-size:15px;padding:12px 28px">
        <i class="fas fa-rocket" style="margin-right:8px"></i>开始创建
      </button>
      <button onclick="switchTab('showcase')" class="btn-ghost" style="font-size:15px;padding:12px 28px">
        <i class="fas fa-images" style="margin-right:8px"></i>产品展示
      </button>
    </div>
  </div>

  <!-- Metrics Dashboard -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px">
    <div class="metric-card">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <div style="width:32px;height:32px;border-radius:8px;background:rgba(59,130,246,0.1);display:flex;align-items:center;justify-content:center"><i class="fas fa-server" style="color:#60a5fa;font-size:14px"></i></div>
        <span style="font-size:13px;color:#64748b">运行服务</span>
      </div>
      <div class="metric-value" id="metricServices">0</div>
    </div>
    <div class="metric-card">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <div style="width:32px;height:32px;border-radius:8px;background:rgba(139,92,246,0.1);display:flex;align-items:center;justify-content:center"><i class="fas fa-code" style="color:#a78bfa;font-size:14px"></i></div>
        <span style="font-size:13px;color:#64748b">生成文件</span>
      </div>
      <div class="metric-value" id="metricFiles">0</div>
    </div>
    <div class="metric-card">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <div style="width:32px;height:32px;border-radius:8px;background:rgba(34,197,94,0.1);display:flex;align-items:center;justify-content:center"><i class="fas fa-check-circle" style="color:#4ade80;font-size:14px"></i></div>
        <span style="font-size:13px;color:#64748b">部署成功</span>
      </div>
      <div class="metric-value" id="metricSuccess">0</div>
    </div>
    <div class="metric-card">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <div style="width:32px;height:32px;border-radius:8px;background:rgba(245,158,11,0.1);display:flex;align-items:center;justify-content:center"><i class="fas fa-clock" style="color:#fbbf24;font-size:14px"></i></div>
        <span style="font-size:13px;color:#64748b">最后更新</span>
      </div>
      <div style="font-size:28px;font-weight:700;color:#fbbf24" id="metricLastUpdate">--</div>
    </div>
  </div>

  <!-- Tabs -->
  <div style="display:flex;gap:4px;margin-bottom:24px;border-bottom:1px solid rgba(148,163,184,0.08)">
    <button class="tab-btn active" onclick="switchTab('create')" id="tab-create"><i class="fas fa-rocket" style="margin-right:8px"></i>创建服务</button>
    <button class="tab-btn" onclick="switchTab('showcase')" id="tab-showcase"><i class="fas fa-images" style="margin-right:8px"></i>产品展示</button>
    <button class="tab-btn" onclick="switchTab('services')" id="tab-services"><i class="fas fa-server" style="margin-right:8px"></i>服务管理</button>
    <button class="tab-btn" onclick="switchTab('routes')" id="tab-routes"><i class="fas fa-network-wired" style="margin-right:8px"></i>路由配置</button>
  </div>

  <!-- ========== PAGE: CREATE ========== -->
  <div id="page-create">

    <!-- Steps -->
    <div style="display:flex;gap:16px;margin-bottom:32px">
      <div id="step1-indicator" style="flex:1;padding:20px;border-radius:16px;background:linear-gradient(145deg,rgba(30,41,59,0.8),rgba(15,23,42,0.9));border:1px solid rgba(59,130,246,0.3);transition:all .3s">
        <div style="display:flex;align-items:center;gap:14px">
          <div class="step-dot active" id="dot1">1</div>
          <div>
            <div style="font-weight:600;color:#f8fafc">上传文件</div>
            <div style="font-size:12px;color:#64748b;margin-top:2px">HTML + 技能包</div>
          </div>
        </div>
      </div>
      <div id="step2-indicator" style="flex:1;padding:20px;border-radius:16px;background:linear-gradient(145deg,rgba(30,41,59,0.4),rgba(15,23,42,0.5));border:1px solid rgba(148,163,184,0.08);transition:all .3s">
        <div style="display:flex;align-items:center;gap:14px">
          <div class="step-dot pending" id="dot2">2</div>
          <div>
            <div style="font-weight:600;color:#94a3b8">解析配置</div>
            <div style="font-size:12px;color:#475569;margin-top:2px">自动分析结构</div>
          </div>
        </div>
      </div>
      <div id="step3-indicator" style="flex:1;padding:20px;border-radius:16px;background:linear-gradient(145deg,rgba(30,41,59,0.4),rgba(15,23,42,0.5));border:1px solid rgba(148,163,184,0.08);transition:all .3s">
        <div style="display:flex;align-items:center;gap:14px">
          <div class="step-dot pending" id="dot3">3</div>
          <div>
            <div style="font-weight:600;color:#94a3b8">生成部署</div>
            <div style="font-size:12px;color:#475569;margin-top:2px">Docker 服务</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 1: Upload -->
    <div id="step1-content">
      <div class="card" style="padding:32px">
        <h2 style="font-size:20px;font-weight:700;color:#f8fafc;margin:0 0 24px"><i class="fas fa-cloud-upload-alt" style="margin-right:10px;color:#60a5fa"></i>上传报表文件</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div>
            <label style="display:block;font-size:13px;color:#94a3b8;margin-bottom:8px;font-weight:500">HTML 报表文件 <span style="color:#ef4444">*</span></label>
            <div id="htmlDropZone" class="dropzone" onclick="document.getElementById('htmlFile').click()">
              <i class="fas fa-file-code" style="font-size:36px;color:#475569;margin-bottom:12px"></i>
              <div style="font-size:15px;color:#94a3b8;margin-bottom:4px">点击或拖拽 HTML 文件到此处</div>
              <div style="font-size:12px;color:#475569">支持 .html, .htm</div>
            </div>
            <input type="file" id="htmlFile" accept=".html,.htm" style="display:none" onchange="handleHtmlSelect(this)">
            <div id="htmlFileInfo" style="margin-top:10px;font-size:13px;color:#4ade80;display:none"></div>
          </div>
          <div>
            <label style="display:block;font-size:13px;color:#94a3b8;margin-bottom:8px;font-weight:500">技能包文件 <span style="color:#ef4444">*</span></label>
            <div id="skillDropZone" class="dropzone" onclick="document.getElementById('skillFiles').click()">
              <i class="fas fa-file-archive" style="font-size:36px;color:#475569;margin-bottom:12px"></i>
              <div style="font-size:15px;color:#94a3b8;margin-bottom:4px">点击或拖拽技能包文件到此处</div>
              <div style="font-size:12px;color:#475569">支持 .py, .md, .yaml, .yml, .json, .zip</div>
            </div>
            <input type="file" id="skillFiles" accept=".py,.md,.yaml,.yml,.json,.zip" multiple style="display:none" onchange="handleSkillSelect(this)">
            <div id="skillFilesInfo" style="margin-top:10px;font-size:13px;color:#4ade80;display:none"></div>
          </div>
        </div>
        <div style="display:flex;justify-content:flex-end;margin-top:24px">
          <button onclick="uploadBundle()" id="uploadBtn" class="btn-primary" disabled>
            <i class="fas fa-arrow-right" style="margin-right:8px"></i>上传并解析
          </button>
        </div>
      </div>
    </div>

    <!-- Step 2: Parse Result -->
    <div id="step2-content" style="display:none">
      <div class="card" style="padding:32px;margin-bottom:20px">
        <h2 style="font-size:20px;font-weight:700;color:#f8fafc;margin:0 0 24px"><i class="fas fa-search" style="margin-right:10px;color:#a78bfa"></i>解析结果</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px">
          <div style="padding:20px;border-radius:12px;background:rgba(15,23,42,0.6);border:1px solid rgba(148,163,184,0.08)">
            <h3 style="font-size:14px;font-weight:600;color:#60a5fa;margin:0 0 14px"><i class="fas fa-file-code" style="margin-right:8px"></i>HTML 结构</h3>
            <div id="htmlParseResult" style="font-size:13px;color:#94a3b8;line-height:1.8"></div>
          </div>
          <div style="padding:20px;border-radius:12px;background:rgba(15,23,42,0.6);border:1px solid rgba(148,163,184,0.08)">
            <h3 style="font-size:14px;font-weight:600;color:#a78bfa;margin:0 0 14px"><i class="fas fa-cogs" style="margin-right:8px"></i>技能包配置</h3>
            <div id="skillParseResult" style="font-size:13px;color:#94a3b8;line-height:1.8"></div>
          </div>
        </div>
      </div>

      <div class="card" style="padding:32px;margin-bottom:20px">
        <h2 style="font-size:20px;font-weight:700;color:#f8fafc;margin:0 0 24px"><i class="fas fa-sliders-h" style="margin-right:10px;color:#4ade80"></i>服务配置</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px">
          <div>
            <label style="display:block;font-size:12px;color:#64748b;margin-bottom:6px">服务名称</label>
            <input type="text" id="serviceName" class="input-dark" placeholder="pdu-unbalance">
          </div>
          <div>
            <label style="display:block;font-size:12px;color:#64748b;margin-bottom:6px">数据中心</label>
            <select id="datacenterSelect" class="select-dark"><option value="default">默认</option></select>
          </div>
          <div>
            <label style="display:block;font-size:12px;color:#64748b;margin-bottom:6px">刷新策略</label>
            <select id="refreshStrategy" class="select-dark">
              <option value="cron">定时 Cron</option>
              <option value="interval">固定间隔</option>
              <option value="manual">手动刷新</option>
            </select>
          </div>
        </div>
        <div>
          <label style="display:block;font-size:12px;color:#64748b;margin-bottom:6px">Cron 表达式</label>
          <input type="text" id="cronExpression" class="input-dark" value="0 */6 * * *" style="max-width:300px">
          <div style="font-size:12px;color:#475569;margin-top:6px">默认每 6 小时刷新一次</div>
        </div>
        <div style="display:flex;justify-content:flex-end;margin-top:24px">
          <button onclick="generateService()" id="generateBtn" class="btn-primary">
            <i class="fas fa-magic" style="margin-right:8px"></i>生成服务代码
          </button>
        </div>
      </div>
    </div>

    <!-- Step 3: Deploy -->
    <div id="step3-content" style="display:none">
      <div class="card" style="padding:32px;margin-bottom:20px">
        <h2 style="font-size:20px;font-weight:700;color:#f8fafc;margin:0 0 24px"><i class="fas fa-rocket" style="margin-right:10px;color:#fbbf24"></i>部署服务</h2>
        <div style="padding:20px;border-radius:12px;background:rgba(15,23,42,0.6);border:1px solid rgba(148,163,184,0.08);margin-bottom:20px">
          <h3 style="font-size:14px;font-weight:600;color:#60a5fa;margin:0 0 12px"><i class="fas fa-box-open" style="margin-right:8px"></i>生成的文件</h3>
          <div id="filesList" style="font-size:13px;color:#94a3b8"></div>
        </div>
        <div id="deployPreview" style="padding:20px;border-radius:12px;background:rgba(34,197,94,0.05);border:1px solid rgba(34,197,94,0.15);margin-bottom:20px;display:none">
          <h3 style="font-size:14px;font-weight:600;color:#4ade80;margin:0 0 12px"><i class="fas fa-check-circle" style="margin-right:8px"></i>部署预览</h3>
          <div style="font-size:13px;color:#94a3b8;line-height:2">
            <div>服务名称: <span id="previewName" style="color:#60a5fa;font-weight:600"></span></div>
            <div>访问路径: <span id="previewPath" style="color:#60a5fa;font-weight:600"></span></div>
            <div>容器端口: <span id="previewPort" style="color:#60a5fa;font-weight:600"></span></div>
          </div>
        </div>
        <div style="display:flex;justify-content:flex-end">
          <button onclick="deployService()" id="deployBtn" class="btn-success">
            <i class="fas fa-rocket" style="margin-right:8px"></i>一键部署
          </button>
        </div>
      </div>
      <div id="deployLogs" style="display:none">
        <div class="card" style="padding:24px">
          <h3 style="font-size:14px;font-weight:600;color:#94a3b8;margin:0 0 12px"><i class="fas fa-terminal" style="margin-right:8px"></i>部署日志</h3>
          <div id="logContent" class="code-block" style="max-height:300px;overflow-y:auto"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- ========== PAGE: SHOWCASE ========== -->
  <div id="page-showcase" style="display:none">
    <div style="text-align:center;padding:20px 0 32px">
      <h2 style="font-size:28px;font-weight:800;color:#f8fafc;margin:0 0 8px">产品展示</h2>
      <p style="font-size:15px;color:#64748b;margin:0">已转化的动态服务展示，点击卡片预览效果</p>
    </div>

    <!-- Showcase Grid -->
    <div id="showcaseGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:20px">
      <!-- Demo Card: PDU Unbalance -->
      <div class="card" style="overflow:hidden;cursor:pointer" onclick="previewShowcase('pdu-unbalance-demo')">
        <div style="height:200px;background:linear-gradient(135deg,#0f172a,#1e3a5f);display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden">
          <div style="position:absolute;inset:0;opacity:0.3">
            <div style="position:absolute;top:20px;left:20px;width:60px;height:60px;border-radius:12px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center">
              <i class="fas fa-bolt" style="color:#fff;font-size:24px"></i>
            </div>
            <div style="position:absolute;top:30px;right:30px;padding:6px 14px;border-radius:20px;background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3)">
              <span style="font-size:11px;color:#4ade80;font-weight:600"><i class="fas fa-circle" style="font-size:6px;margin-right:4px;vertical-align:middle"></i>运行中</span>
            </div>
            <div style="position:absolute;bottom:20px;left:20px;right:20px">
              <div style="display:flex;gap:12px">
                <div style="flex:1;padding:12px;border-radius:10px;background:rgba(30,41,59,0.8);border:1px solid rgba(148,163,184,0.1)">
                  <div style="font-size:11px;color:#64748b">有效设备</div>
                  <div style="font-size:20px;font-weight:700;color:#60a5fa">170</div>
                </div>
                <div style="flex:1;padding:12px;border-radius:10px;background:rgba(30,41,59,0.8);border:1px solid rgba(148,163,184,0.1)">
                  <div style="font-size:11px;color:#64748b">平均不平衡度</div>
                  <div style="font-size:20px;font-weight:700;color:#fbbf24">14.32%</div>
                </div>
                <div style="flex:1;padding:12px;border-radius:10px;background:rgba(30,41,59,0.8);border:1px solid rgba(148,163,184,0.1)">
                  <div style="font-size:11px;color:#64748b">异常设备</div>
                  <div style="font-size:20px;font-weight:700;color:#f87171">30</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div style="padding:20px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
            <h3 style="font-size:16px;font-weight:700;color:#f8fafc;margin:0">PDU 三相不平衡度监控</h3>
            <span class="status-badge status-running"><i class="fas fa-circle" style="font-size:5px"></i>运行中</span>
          </div>
          <p style="font-size:13px;color:#64748b;margin:0 0 14px;line-height:1.6">太仓基地F楼交流列头柜三相电流不平衡度实时监测，支持Excel导出与定时刷新</p>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <span style="padding:4px 10px;border-radius:6px;background:rgba(59,130,246,0.1);color:#60a5fa;font-size:11px">智航CMDB</span>
            <span style="padding:4px 10px;border-radius:6px;background:rgba(139,92,246,0.1);color:#a78bfa;font-size:11px">定时刷新</span>
            <span style="padding:4px 10px;border-radius:6px;background:rgba(34,197,94,0.1);color:#4ade80;font-size:11px">Excel导出</span>
          </div>
          <div style="display:flex;gap:8px;margin-top:16px">
            <button class="btn-primary" style="flex:1;font-size:13px;padding:8px 16px" onclick="event.stopPropagation();window.open('/reports/pdu-unbalance-v1/','_blank')">
              <i class="fas fa-external-link-alt" style="margin-right:6px"></i>访问服务
            </button>
            <button class="btn-ghost" style="font-size:13px;padding:8px 16px" onclick="event.stopPropagation();previewShowcase('pdu-unbalance-demo')">
              <i class="fas fa-eye" style="margin-right:6px"></i>预览
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div id="showcaseEmpty" style="display:none;grid-column:1/-1;text-align:center;padding:60px 20px">
        <div style="width:80px;height:80px;border-radius:20px;background:linear-gradient(135deg,rgba(59,130,246,0.1),rgba(139,92,246,0.1));display:flex;align-items:center;justify-content:center;margin:0 auto 20px">
          <i class="fas fa-images" style="font-size:32px;color:#475569"></i>
        </div>
        <h3 style="font-size:18px;font-weight:600;color:#94a3b8;margin:0 0 8px">暂无展示服务</h3>
        <p style="font-size:14px;color:#475569;margin:0 0 20px">在"创建服务"页面转化并部署你的第一个动态服务</p>
        <button onclick="switchTab('create')" class="btn-primary" style="font-size:14px">
          <i class="fas fa-plus" style="margin-right:8px"></i>创建服务
        </button>
      </div>
    </div>

    <!-- Preview Modal -->
    <div id="previewModal" style="display:none;position:fixed;inset:0;z-index:200;background:rgba(2,6,23,0.9);backdrop-filter:blur(10px)">
      <div style="position:absolute;top:16px;right:16px;display:flex;gap:8px">
        <button onclick="openPreviewFull()" class="btn-ghost" style="font-size:13px"><i class="fas fa-external-link-alt" style="margin-right:6px"></i>全屏打开</button>
        <button onclick="closePreview()" class="btn-ghost" style="font-size:13px"><i class="fas fa-times" style="margin-right:6px"></i>关闭</button>
      </div>
      <div style="max-width:1200px;margin:60px auto 20px;padding:0 24px">
        <h3 id="previewTitle" style="font-size:18px;font-weight:700;color:#f8fafc;margin:0 0 16px">服务预览</h3>
        <iframe id="previewFrame" class="preview-frame"></iframe>
      </div>
    </div>
  </div>

  <!-- ========== PAGE: SERVICES ========== -->
  <div id="page-services" style="display:none">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px">
      <div>
        <h2 style="font-size:24px;font-weight:700;color:#f8fafc;margin:0 0 4px">服务管理</h2>
        <p style="font-size:14px;color:#64748b;margin:0">管理已部署的所有动态服务</p>
      </div>
      <button onclick="loadServices()" class="btn-ghost">
        <i class="fas fa-sync-alt" style="margin-right:8px"></i>刷新
      </button>
    </div>
    <div id="servicesList" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px"></div>
  </div>

  <!-- ========== PAGE: ROUTES ========== -->
  <div id="page-routes" style="display:none">
    <div style="margin-bottom:24px">
      <h2 style="font-size:24px;font-weight:700;color:#f8fafc;margin:0 0 4px">路由配置</h2>
      <p style="font-size:14px;color:#64748b;margin:0">Nginx 反向代理路由表</p>
    </div>
    <div class="card" style="padding:24px">
      <div id="routesList"></div>
    </div>
  </div>

</main>

<!-- Toast -->
<div id="toast" class="toast"></div>

<!-- Process Modal -->
<div id="processModal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:1000;justify-content:center;align-items:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
  <div style="background:linear-gradient(145deg,#0f172a,#1e293b);border-radius:20px;padding:36px;max-width:640px;width:92%;border:1px solid rgba(148,163,184,0.12);box-shadow:0 25px 50px -12px rgba(0,0,0,0.5)">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px">
      <h3 id="processTitle" style="margin:0;font-size:18px;font-weight:700;color:#f8fafc">正在处理...</h3>
      <div id="processSpinner" style="width:20px;height:20px;border:2px solid rgba(96,165,250,0.2);border-top-color:#60a5fa;border-radius:50%;animation:spin 1s linear infinite"></div>
    </div>
    <div id="processSteps" style="margin-bottom:20px"></div>
    <div id="processLog" style="max-height:280px;overflow-y:auto;font-family:'SF Mono',Monaco,monospace;font-size:12px;line-height:1.6;color:#94a3b8;padding:16px;background:rgba(15,23,42,0.8);border-radius:12px;border:1px solid rgba(148,163,184,0.08)"></div>
    <div id="processActions" style="margin-top:20px;display:none;gap:12px;justify-content:flex-end">
      <button onclick="closeProcessModal()" class="btn-ghost" style="font-size:13px;padding:8px 20px">关闭</button>
      <button onclick="retryProcess()" class="btn-primary" style="font-size:13px;padding:8px 20px"><i class="fas fa-redo" style="margin-right:6px"></i>重试</button>
    </div>
  </div>
</div>
<style>@keyframes spin{to{transform:rotate(360deg)}}</style>

<script>
let currentUploadId=null,currentServiceName=null;
let htmlFileSelected=null,skillFilesSelected=[];
let previewUrl='';
let processRetryFn=null;

// Process Modal Functions
function showProcessModal(title){
  document.getElementById('processModal').style.display='flex';
  document.getElementById('processTitle').textContent=title||'正在处理...';
  document.getElementById('processSpinner').style.display='block';
  document.getElementById('processActions').style.display='none';
  document.getElementById('processSteps').innerHTML='';
  document.getElementById('processLog').innerHTML='';
}
function closeProcessModal(){
  document.getElementById('processModal').style.display='none';
}
function updateProcessStep(stepNum,status,label){
  const steps=['上传文件','解析结构','生成代码','部署服务'];
  const colors={pending:'#475569',active:'#60a5fa',done:'#4ade80',error:'#ef4444'};
  const icons={pending:'○',active:'◐',done:'✓',error:'✗'};
  let html='';
  for(let i=0;i<steps.length;i++){
    const s=i<stepNum?'done':i===stepNum?status:'pending';
    const c=colors[s];
    const icon=icons[s];
    html+='<div style="display:flex;align-items:center;gap:10px;padding:8px 0;font-size:13px;color:'+c+'">'+icon+' '+steps[i]+(i===stepNum&&label?': '+label:'')+'</div>';
  }
  document.getElementById('processSteps').innerHTML=html;
}
function appendProcessLog(msg,type){
  const log=document.getElementById('processLog');
  const color=type==='error'?'#f87171':type==='success'?'#4ade80':type==='warn'?'#fbbf24':'#94a3b8';
  const time=new Date().toLocaleTimeString('zh-CN',{hour12:false});
  log.innerHTML+='<div style="color:'+color+'">['+time+'] '+msg+'</div>';
  log.scrollTop=log.scrollHeight;
}
function showProcessError(title,message){
  document.getElementById('processTitle').textContent=title;
  document.getElementById('processSpinner').style.display='none';
  document.getElementById('processActions').style.display='flex';
  appendProcessLog(message,'error');
}
function showProcessSuccess(title){
  document.getElementById('processTitle').textContent=title;
  document.getElementById('processSpinner').style.display='none';
  document.getElementById('processActions').style.display='flex';
}
function retryProcess(){
  if(processRetryFn)processRetryFn();
}

function switchTab(tab){
  document.querySelectorAll('.tab-btn').forEach(b=>{b.classList.remove('active');});
  document.getElementById('tab-'+tab).classList.add('active');
  ['create','showcase','services','routes'].forEach(t=>{
    document.getElementById('page-'+t).style.display='none';
  });
  document.getElementById('page-'+tab).style.display='block';
  if(tab==='services')loadServices();
  if(tab==='routes')loadRoutes();
  if(tab==='showcase')loadShowcase();
}

// Drop zones
function setupDropZone(zoneId,inputId,handler){
  const zone=document.getElementById(zoneId),input=document.getElementById(inputId);
  zone.addEventListener('click',()=>input.click());
  zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('dragover');});
  zone.addEventListener('dragleave',()=>zone.classList.remove('dragover'));
  zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('dragover');handler(e.dataTransfer.files);});
}
setupDropZone('htmlDropZone','htmlFile',files=>{
  if(files.length>0){htmlFileSelected=files[0];document.getElementById('htmlFileInfo').textContent='✓ '+files[0].name+' ('+(files[0].size/1024).toFixed(1)+'KB)';document.getElementById('htmlFileInfo').style.display='block';checkUploadReady();}
});
setupDropZone('skillDropZone','skillFiles',files=>{
  skillFilesSelected=Array.from(files);const names=skillFilesSelected.map(f=>f.name).join(', ');
  document.getElementById('skillFilesInfo').textContent='✓ '+skillFilesSelected.length+' 个文件: '+names;document.getElementById('skillFilesInfo').style.display='block';checkUploadReady();
});
function handleHtmlSelect(input){console.log('HTML file selected:',input.files);if(input.files&&input.files.length>0){htmlFileSelected=input.files[0];document.getElementById('htmlFileInfo').textContent='✓ '+htmlFileSelected.name+' ('+(htmlFileSelected.size/1024).toFixed(1)+'KB)';document.getElementById('htmlFileInfo').style.display='block';checkUploadReady();}}
function handleSkillSelect(input){console.log('Skill files selected:',input.files);if(input.files&&input.files.length>0){skillFilesSelected=Array.from(input.files);const names=skillFilesSelected.map(f=>f.name).join(', ');document.getElementById('skillFilesInfo').textContent='✓ '+skillFilesSelected.length+' 个文件: '+names;document.getElementById('skillFilesInfo').style.display='block';checkUploadReady();}}
function checkUploadReady(){const ready=htmlFileSelected&&skillFilesSelected.length>0;document.getElementById('uploadBtn').disabled=!ready;console.log('Upload ready:',ready,'HTML:',htmlFileSelected,'Skills:',skillFilesSelected.length);}

function setStep(step){
  for(let i=1;i<=3;i++){
    const dot=document.getElementById('dot'+i),ind=document.getElementById('step'+i+'-indicator');
    if(i<step){dot.className='step-dot done';dot.innerHTML='<i class="fas fa-check"></i>';ind.style.borderColor='rgba(34,197,94,0.3)';ind.style.background='linear-gradient(145deg,rgba(34,197,94,0.08),rgba(15,23,42,0.5))';}
    else if(i===step){dot.className='step-dot active';dot.innerHTML=i;ind.style.borderColor='rgba(59,130,246,0.3)';ind.style.background='linear-gradient(145deg,rgba(30,41,59,0.8),rgba(15,23,42,0.9))';}
    else{dot.className='step-dot pending';dot.innerHTML=i;ind.style.borderColor='rgba(148,163,184,0.08)';ind.style.background='linear-gradient(145deg,rgba(30,41,59,0.4),rgba(15,23,42,0.5))';}
  }
  document.getElementById('step1-content').style.display=step===1?'block':'none';
  document.getElementById('step2-content').style.display=step===2?'block':'none';
  document.getElementById('step3-content').style.display=step===3?'block':'none';
}

async function uploadBundle(){
  const btn=document.getElementById('uploadBtn');btn.disabled=true;
  processRetryFn=uploadBundle;
  showProcessModal('上传并解析文件');
  updateProcessStep(0,'active','准备上传');
  appendProcessLog('开始上传文件...','info');
  
  const formData=new FormData();formData.append('html',htmlFileSelected);skillFilesSelected.forEach(f=>formData.append('skill_files',f));
  try{
    updateProcessStep(0,'active','上传中');
    appendProcessLog('上传 HTML: '+htmlFileSelected.name,'info');
    appendProcessLog('上传技能包: '+skillFilesSelected.map(f=>f.name).join(', '),'info');
    
    const res=await fetch('/api/upload/bundle',{method:'POST',body:formData});
    const data=await res.json();
    
    if(data.success){
      currentUploadId=data.upload_id;
      updateProcessStep(0,'done','上传成功');
      appendProcessLog('上传完成，ID: '+currentUploadId,'success');
      setStep(2);
      await parseUpload();
    }else{
      updateProcessStep(0,'error','上传失败');
      showProcessError('上传失败',data.message);
      showToast(data.message,'error');
    }
  }catch(e){
    updateProcessStep(0,'error','上传异常');
    showProcessError('上传失败','网络错误: '+e.message);
    showToast('上传失败: '+e.message,'error');
  }finally{btn.disabled=false;}
}

async function parseUpload(){
  processRetryFn=()=>{uploadBundle();};
  updateProcessStep(1,'active','解析中');
  appendProcessLog('开始解析文件结构...','info');
  
  try{
    const res=await fetch('/api/transform/parse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({upload_id:currentUploadId})});
    const data=await res.json();
    
    if(data.success){
      const r=data.parse_result;
      appendProcessLog('HTML 标题: '+r.html.title,'success');
      appendProcessLog('数据区域: '+r.html.data_regions_count+' 个','info');
      appendProcessLog('技能名称: '+r.skill.name,'success');
      appendProcessLog('数据源: '+r.skill.data_source_type,'info');
      
      document.getElementById('htmlParseResult').innerHTML='<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.08)"><span>📌 标题</span><span style="color:#e2e8f0">'+r.html.title+'</span></div><div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.08)"><span>🎨 主题</span><span style="color:#e2e8f0">'+r.html.theme+'</span></div><div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.08)"><span>📊 数据区域</span><span style="color:#e2e8f0">'+r.html.data_regions_count+' 个</span></div><div style="display:flex;justify-content:space-between;padding:6px 0"><span>🖱️ 交互</span><span style="color:#e2e8f0">'+(r.html.interactions.map(i=>i.type).join(', ')||'无')+'</span></div>';
      document.getElementById('skillParseResult').innerHTML='<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.08)"><span>📛 名称</span><span style="color:#e2e8f0">'+r.skill.name+'</span></div><div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.08)"><span>🔌 数据源</span><span style="color:#e2e8f0">'+r.skill.data_source_type+'</span></div><div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.08)"><span>📡 拉取步骤</span><span style="color:#e2e8f0">'+r.skill.fetch_steps_count+' 步</span></div><div style="display:flex;justify-content:space-between;padding:6px 0"><span>🧮 计算公式</span><span style="color:#e2e8f0">'+(r.skill.calculation_formula||'无')+'</span></div>';
      const dcSelect=document.getElementById('datacenterSelect');
      dcSelect.innerHTML=r.skill.datacenters.map(dc=>'<option value="'+dc+'">'+dc+'</option>').join('')||'<option value="default">默认</option>';
      const rawName=r.skill.name||'report-'+currentUploadId;const safeName=rawName.toLowerCase().replace(/\s+/g,'-').replace(/^-+|-+$/g,'')||'report-'+currentUploadId;document.getElementById('serviceName').value=safeName;
      
      updateProcessStep(1,'done','解析成功');
      appendProcessLog('解析完成，请配置服务参数','success');
      showProcessSuccess('解析完成');
      showToast('解析成功','success');
    }else{
      updateProcessStep(1,'error','解析失败');
      showProcessError('解析失败',data.message);
      showToast(data.message,'error');
    }
  }catch(e){
    updateProcessStep(1,'error','解析异常');
    showProcessError('解析失败','错误: '+e.message);
    showToast('解析失败: '+e.message,'error');
  }
}

async function generateService(){
  const btn=document.getElementById('generateBtn');btn.disabled=true;
  processRetryFn=generateService;
  showProcessModal('生成服务代码');
  updateProcessStep(2,'active','生成中');
  appendProcessLog('开始生成服务代码...','info');
  appendProcessLog('服务名称: '+document.getElementById('serviceName').value,'info');
  
  const config={name:document.getElementById('serviceName').value,datacenter:document.getElementById('datacenterSelect').value,refresh_strategy:document.getElementById('refreshStrategy').value,refresh_cron:document.getElementById('cronExpression').value,path:'/reports/'+document.getElementById('serviceName').value};
  try{
    const res=await fetch('/api/transform/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({upload_id:currentUploadId,service_config:config})});
    const data=await res.json();
    
    if(data.success){
      currentServiceName=data.service_name;
      updateProcessStep(2,'done','生成成功');
      appendProcessLog('生成完成，共 '+data.generated_files.length+' 个文件','success');
      data.generated_files.forEach(f=>appendProcessLog('  ✓ '+f,'info'));
      
      setStep(3);
      document.getElementById('filesList').innerHTML=data.generated_files.map(f=>'<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.06)"><i class="fas fa-file-code" style="color:#60a5fa;font-size:12px"></i><span>'+f+'</span></div>').join('');
      document.getElementById('deployPreview').style.display='block';
      document.getElementById('previewName').textContent=data.service_name;
      document.getElementById('previewPath').textContent=data.service_config.path;
      document.getElementById('previewPort').textContent='自动分配';
      
      showProcessSuccess('生成完成');
      showToast('服务代码生成成功','success');
    }else{
      updateProcessStep(2,'error','生成失败');
      if(data.traceback)appendProcessLog(data.traceback,'error');
      showProcessError('生成失败',data.message);
      showToast(data.message,'error');
    }
  }catch(e){
    updateProcessStep(2,'error','生成异常');
    showProcessError('生成失败','错误: '+e.message);
    showToast('生成失败: '+e.message,'error');
  }finally{btn.disabled=false;}
}

async function deployService(){
  const btn=document.getElementById('deployBtn');btn.disabled=true;
  processRetryFn=deployService;
  showProcessModal('部署服务');
  updateProcessStep(3,'active','部署中');
  appendProcessLog('开始部署服务...','info');
  appendProcessLog('服务: '+document.getElementById('serviceName').value,'info');
  
  const config={name:document.getElementById('serviceName').value,path:'/reports/'+document.getElementById('serviceName').value};
  try{
    const res=await fetch('/api/deploy/full',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({upload_id:currentUploadId,service_config:config})});
    const data=await res.json();
    document.getElementById('deployLogs').style.display='block';
    const logContent=document.getElementById('logContent');
    
    if(data.success){
      logContent.innerHTML+='<div style="color:#4ade80">✓ '+data.message+'</div>';
      logContent.innerHTML+='<div style="color:#60a5fa;margin-top:4px">→ 访问地址: <a href="'+data.access_url+'" target="_blank" style="color:#60a5fa;text-decoration:underline">'+data.access_url+'</a></div>';
      
      updateProcessStep(3,'done','部署成功');
      appendProcessLog('部署成功!','success');
      appendProcessLog('访问地址: '+data.access_url,'success');
      
      showProcessSuccess('部署完成');
      showToast('部署成功','success');
      btn.innerHTML='<i class="fas fa-check" style="margin-right:8px"></i>已部署';
      btn.classList.remove('btn-success');
      btn.style.background='linear-gradient(135deg,#475569,#334155)';
      updateMetrics();
    }else{
      logContent.innerHTML+='<div style="color:#f87171">✗ '+data.message+'</div>';
      if(data.traceback)logContent.innerHTML+='<div style="color:#475569;margin-top:8px;font-size:12px">'+data.traceback.replace(/\\\\n/g,'<br>')+'</div>';
      
      updateProcessStep(3,'error','部署失败');
      if(data.traceback)appendProcessLog(data.traceback,'error');
      showProcessError('部署失败',data.message);
      showToast(data.message,'error');
      btn.disabled=false;
      btn.innerHTML='<i class="fas fa-redo" style="margin-right:8px"></i>重新部署';
    }
  }catch(e){
    updateProcessStep(3,'error','部署异常');
    showProcessError('部署失败','错误: '+e.message);
    showToast('部署失败: '+e.message,'error');
    btn.disabled=false;
    btn.innerHTML='<i class="fas fa-redo" style="margin-right:8px"></i>重新部署';
  }
}

async function loadServices(){
  try{
    const res=await fetch('/api/services');const data=await res.json();
    const container=document.getElementById('servicesList');
    if(data.services&&data.services.length>0){
      container.innerHTML=data.services.map(s=>`
        <div class="card" style="padding:24px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
            <h3 style="font-size:16px;font-weight:700;color:#f8fafc;margin:0">${s.title}</h3>
            <span class="status-badge status-${s.status}"><i class="fas fa-circle" style="font-size:5px"></i>${s.status==='running'?'运行中':s.status==='deploying'?'部署中':'已停止'}</span>
          </div>
          <div style="font-size:13px;color:#64748b;line-height:1.8">
            <div><i class="fas fa-tag" style="width:16px;margin-right:6px;color:#475569"></i>${s.name}</div>
            <div><i class="fas fa-clock" style="width:16px;margin-right:6px;color:#475569"></i>${s.refresh_strategy}</div>
          </div>
          <div style="display:flex;gap:8px;margin-top:16px">
            <button onclick="controlService('${s.name}','start')" class="btn-ghost" style="flex:1;font-size:12px;padding:6px 12px"><i class="fas fa-play" style="margin-right:4px;color:#4ade80"></i>启动</button>
            <button onclick="controlService('${s.name}','stop')" class="btn-ghost" style="flex:1;font-size:12px;padding:6px 12px"><i class="fas fa-stop" style="margin-right:4px;color:#f87171"></i>停止</button>
            <button onclick="controlService('${s.name}','restart')" class="btn-ghost" style="flex:1;font-size:12px;padding:6px 12px"><i class="fas fa-sync-alt" style="margin-right:4px;color:#60a5fa"></i>重启</button>
            <button onclick="deleteService('${s.name}')" class="btn-ghost" style="font-size:12px;padding:6px 12px"><i class="fas fa-trash" style="margin-right:4px;color:#f87171"></i></button>
          </div>
        </div>
      `).join('');
      document.getElementById('metricServices').textContent=data.services.filter(s=>s.status==='running').length;
    }else{
      container.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:60px 20px"><div style="width:64px;height:64px;border-radius:16px;background:linear-gradient(135deg,rgba(59,130,246,0.1),rgba(139,92,246,0.1));display:flex;align-items:center;justify-content:center;margin:0 auto 16px"><i class="fas fa-server" style="font-size:24px;color:#475569"></i></div><h3 style="font-size:16px;font-weight:600;color:#94a3b8;margin:0 0 8px">暂无部署的服务</h3><p style="font-size:13px;color:#475569;margin:0">在创建服务页面部署你的第一个动态服务</p></div>';
      document.getElementById('metricServices').textContent='0';
    }
  }catch(e){document.getElementById('servicesList').innerHTML='<div style="grid-column:1/-1;text-align:center;padding:40px;color:#f87171">加载失败</div>';}
}

async function controlService(name,action){
  try{const res=await fetch('/api/deploy/'+action+'/'+name,{method:'POST'});const data=await res.json();showToast(data.message,data.success?'success':'error');if(data.success)loadServices();}catch(e){showToast('操作失败','error');}
}
async function deleteService(name){
  if(!confirm('确定要删除服务 '+name+' 吗？'))return;
  try{const res=await fetch('/api/deploy/delete/'+name,{method:'DELETE'});const data=await res.json();showToast(data.message,data.success?'success':'error');if(data.success)loadServices();}catch(e){showToast('删除失败','error');}
}

async function loadRoutes(){
  try{
    const res=await fetch('/api/routes');const data=await res.json();
    const container=document.getElementById('routesList');
    if(data.routes&&data.routes.length>0){
      container.innerHTML=data.routes.map(r=>`
        <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-radius:10px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.08);margin-bottom:8px">
          <div style="display:flex;align-items:center;gap:12px">
            <div style="padding:6px 10px;border-radius:6px;background:rgba(59,130,246,0.1);color:#60a5fa;font-size:12px;font-weight:600">${r.path}</div>
            <i class="fas fa-arrow-right" style="color:#475569;font-size:11px"></i>
            <div style="padding:6px 10px;border-radius:6px;background:rgba(34,197,94,0.1);color:#4ade80;font-size:12px;font-weight:600">${r.upstream}</div>
          </div>
          <span style="font-size:12px;color:#475569">${r.service_name}</span>
        </div>
      `).join('');
    }else{
      container.innerHTML='<div style="text-align:center;padding:40px;color:#475569">暂无路由配置</div>';
    }
  }catch(e){document.getElementById('routesList').innerHTML='<div style="text-align:center;padding:40px;color:#f87171">加载失败</div>';}
}

// Showcase functions
function loadShowcase(){
  // Update metrics from services
  loadServices();
}

function previewShowcase(id){
  if(id==='pdu-unbalance-demo'){
    previewUrl='/reports/pdu-unbalance-v1/';
    document.getElementById('previewTitle').textContent='PDU 三相不平衡度监控 - 预览';
  }
  document.getElementById('previewFrame').src=previewUrl;
  document.getElementById('previewModal').style.display='block';
}

function closePreview(){
  document.getElementById('previewModal').style.display='none';
  document.getElementById('previewFrame').src='';
}

function openPreviewFull(){
  window.open(previewUrl,'_blank');
}

function updateMetrics(){
  document.getElementById('metricSuccess').textContent=parseInt(document.getElementById('metricSuccess').textContent)+1;
  document.getElementById('metricLastUpdate').textContent=new Date().toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'});
}

function showToast(message,type){
  const toast=document.getElementById('toast');
  toast.textContent=message;toast.className='toast '+type;toast.classList.add('show');
  setTimeout(()=>{toast.classList.remove('show');},3000);
}

document.addEventListener('DOMContentLoaded',()=>{
  loadServices();
  document.getElementById('metricLastUpdate').textContent=new Date().toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'});
});
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(ADMIN_HTML)

@app.route('/health')
def health():
    return jsonify({'status':'healthy','platform':'report-transformer-platform','version':'1.0.0'})

if __name__ == '__main__':
    os.makedirs(os.environ.get('UPLOADS_DIR','/app/uploads'), exist_ok=True)
    os.makedirs(os.environ.get('SERVICES_DIR','/app/services'), exist_ok=True)
    os.makedirs(os.environ.get('NGINX_CONF_DIR','/app/nginx_conf'), exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
