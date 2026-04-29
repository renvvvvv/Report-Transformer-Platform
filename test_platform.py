#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Transformer Platform - 完整功能测试
测试上传 -> 解析 -> 生成 -> 部署 全流程
"""

import os
import sys
import json
import time
import requests

BASE_URL = "http://localhost:8090"
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "uploads", "bundle_e738abf8")


def log(msg, level="INFO"):
    prefix = {"INFO": "[*]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]"}.get(level, "[*]")
    print(f"{prefix} {msg}")


def test_health():
    """测试平台是否可访问"""
    log("测试平台健康状态...")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=10)
        if r.status_code == 200:
            log("平台可访问", "OK")
            return True
        else:
            log(f"平台返回状态码: {r.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"平台无法访问: {e}", "ERROR")
        return False


def test_sample_files():
    """检查样例文件"""
    log("检查样例文件...")
    
    if not os.path.exists(SAMPLE_DIR):
        log(f"样例目录不存在: {SAMPLE_DIR}", "ERROR")
        return None, None
    
    html_path = os.path.join(SAMPLE_DIR, "report.html")
    skill_dir = os.path.join(SAMPLE_DIR, "skill")
    
    if not os.path.exists(html_path):
        log(f"HTML文件不存在", "ERROR")
        return None, None
    
    skill_files = []
    for fname in os.listdir(skill_dir):
        fpath = os.path.join(skill_dir, fname)
        if os.path.isfile(fpath) and not fname.startswith(".") and not fname.endswith(".pyc"):
            skill_files.append(fpath)
    
    if not skill_files:
        log("没有可用的技能文件", "ERROR")
        return None, None
    
    log(f"HTML: {os.path.basename(html_path)} ({os.path.getsize(html_path)} bytes)", "OK")
    log(f"技能文件: {len(skill_files)} 个", "OK")
    for f in skill_files:
        log(f"  - {os.path.basename(f)} ({os.path.getsize(f)} bytes)")
    
    return html_path, skill_files


def test_upload(html_path, skill_files):
    """测试上传"""
    log("测试文件上传...")
    
    url = f"{BASE_URL}/api/upload/bundle"
    files = [("html", ("report.html", open(html_path, "rb"), "text/html"))]
    
    for skill_path in skill_files:
        files.append(("skill_files", (os.path.basename(skill_path), open(skill_path, "rb"), "application/octet-stream")))
    
    try:
        r = requests.post(url, files=files, timeout=30)
        data = r.json()
        
        if data.get("success"):
            upload_id = data["upload_id"]
            log(f"上传成功, ID: {upload_id}", "OK")
            return upload_id
        else:
            log(f"上传失败: {data.get('message', '未知错误')}", "ERROR")
            return None
    except Exception as e:
        log(f"上传异常: {e}", "ERROR")
        return None
    finally:
        for _, (_, fp, _) in files:
            fp.close()


def test_parse(upload_id):
    """测试解析"""
    log("测试解析...")
    
    url = f"{BASE_URL}/api/transform/parse"
    payload = {"upload_id": upload_id}
    
    try:
        r = requests.post(url, json=payload, timeout=30)
        data = r.json()
        
        if data.get("success"):
            result = data["parse_result"]
            log(f"HTML标题: {result['html']['title']}", "OK")
            log(f"数据区域: {result['html']['data_regions_count']} 个")
            log(f"技能名称: {result['skill']['name']}", "OK")
            log(f"数据源: {result['skill']['data_source_type']}")
            log(f"拉取步骤: {result['skill']['fetch_steps_count']} 步")
            return result
        else:
            log(f"解析失败: {data.get('message', '未知错误')}", "ERROR")
            if data.get("traceback"):
                log(f"错误详情: {data['traceback'][:500]}", "ERROR")
            return None
    except Exception as e:
        log(f"解析异常: {e}", "ERROR")
        return None


def test_generate(upload_id, parse_result):
    """测试生成"""
    log("测试生成服务代码...")
    
    url = f"{BASE_URL}/api/transform/generate"
    
    # Use English service name
    skill_name = parse_result["skill"]["name"]
    # Create a safe English name
    safe_name = "pdu-unbalance-test"
    
    payload = {
        "upload_id": upload_id,
        "service_config": {
            "name": safe_name,
            "title": parse_result["html"]["title"],
            "datacenter": parse_result["skill"]["datacenters"][0] if parse_result["skill"]["datacenters"] else "default",
            "refresh_strategy": "cron",
            "refresh_cron": "0 */6 * * *",
            "refresh_interval": 300,
            "path": f"/reports/{safe_name}"
        }
    }
    
    try:
        r = requests.post(url, json=payload, timeout=60)
        data = r.json()
        
        if data.get("success"):
            log(f"生成成功: {data['service_name']}", "OK")
            log(f"生成文件: {len(data['generated_files'])} 个", "OK")
            for fname in data["generated_files"]:
                log(f"  - {fname}")
            return data
        else:
            log(f"生成失败: {data.get('message', '未知错误')}", "ERROR")
            if data.get("traceback"):
                log(f"错误详情: {data['traceback'][:500]}", "ERROR")
            return None
    except Exception as e:
        log(f"生成异常: {e}", "ERROR")
        return None


def test_deploy(upload_id, service_name):
    """测试部署"""
    log("测试部署服务...")
    
    url = f"{BASE_URL}/api/deploy/full"
    payload = {
        "upload_id": upload_id,
        "service_config": {
            "name": service_name,
            "path": f"/reports/{service_name}"
        }
    }
    
    try:
        r = requests.post(url, json=payload, timeout=120)
        data = r.json()
        
        log(f"部署响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if data.get("success"):
            log(f"部署结果: {data.get('message', '成功')}", "OK")
            log(f"访问地址: {data.get('access_url', 'N/A')}", "OK")
            return data
        else:
            log(f"部署失败: {data.get('message', '未知错误')}", "ERROR")
            if data.get("traceback"):
                log(f"错误详情: {data['traceback'][:500]}", "ERROR")
            return None
    except Exception as e:
        log(f"部署异常: {e}", "ERROR")
        return None


def test_services():
    """测试服务列表"""
    log("测试服务列表...")
    
    url = f"{BASE_URL}/api/services"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        services = data.get("services", [])
        log(f"当前服务数: {len(services)}", "OK")
        for s in services:
            log(f"  - {s.get('name', 'N/A')} ({s.get('status', 'unknown')})")
        return services
    except Exception as e:
        log(f"获取服务列表异常: {e}", "ERROR")
        return []


def test_access_service(service_name):
    """测试访问已部署的服务"""
    log(f"测试访问服务: {service_name}...")
    
    url = f"{BASE_URL}/reports/{service_name}/"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            log(f"服务可访问! 内容长度: {len(r.text)} bytes", "OK")
            # Check if content looks like our report
            if "太仓基地" in r.text or "交流列头柜" in r.text:
                log("服务内容正确 - 包含报表数据", "OK")
            else:
                log("服务内容可能不正确 - 未找到预期的报表数据", "WARN")
            return True
        else:
            log(f"服务返回状态码: {r.status_code}", "WARN")
            return False
    except Exception as e:
        log(f"访问服务异常: {e}", "ERROR")
        return False


def main():
    print("=" * 70)
    print("Report Transformer Platform - 完整功能测试")
    print("=" * 70)
    print()
    
    # 1. 健康检查
    if not test_health():
        log("平台不可用，测试终止", "ERROR")
        return 1
    
    # 2. 检查样例文件
    html_path, skill_files = test_sample_files()
    if not html_path:
        return 1
    
    # 3. 上传
    upload_id = test_upload(html_path, skill_files)
    if not upload_id:
        return 1
    
    # 4. 解析
    parse_result = test_parse(upload_id)
    if not parse_result:
        return 1
    
    # 5. 生成
    generate_result = test_generate(upload_id, parse_result)
    if not generate_result:
        return 1
    
    service_name = generate_result["service_name"]
    
    # 6. 部署
    deploy_result = test_deploy(upload_id, service_name)
    
    # 7. 等待容器启动
    if deploy_result and deploy_result.get("start_success"):
        log("等待容器启动 (5秒)...")
        time.sleep(5)
        test_access_service(service_name)
    
    # 8. 服务列表
    services = test_services()
    
    # 总结
    print()
    print("=" * 70)
    print("测试总结")
    print("=" * 70)
    
    results = [
        ("平台健康", True),
        ("样例文件", html_path is not None),
        ("文件上传", upload_id is not None),
        ("解析结构", parse_result is not None),
        ("生成代码", generate_result is not None),
        ("部署服务", deploy_result is not None and deploy_result.get("success")),
        ("容器启动", deploy_result is not None and deploy_result.get("start_success")),
    ]
    
    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        level = "OK" if passed else "ERROR"
        log(f"{name}: {status}", level)
        if not passed:
            all_pass = False
    
    print()
    if all_pass:
        log("所有测试通过!", "OK")
        return 0
    else:
        log("部分测试失败，请检查日志", "WARN")
        return 1


if __name__ == "__main__":
    sys.exit(main())
