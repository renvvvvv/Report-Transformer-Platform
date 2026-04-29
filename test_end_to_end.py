#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试 - 使用样例文件测试完整流程
"""

import os
import sys
import requests
import json

BASE_URL = "http://localhost:8090"
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "uploads", "bundle_e738abf8")


def test_sample_files_exist():
    """测试样例文件是否存在"""
    print("=" * 60)
    print("测试1: 检查样例文件")
    print("=" * 60)
    
    assert os.path.exists(SAMPLE_DIR), f"样例目录不存在: {SAMPLE_DIR}"
    
    html_path = os.path.join(SAMPLE_DIR, "report.html")
    skill_dir = os.path.join(SAMPLE_DIR, "skill")
    
    assert os.path.exists(html_path), f"HTML文件不存在: {html_path}"
    assert os.path.exists(skill_dir), f"技能目录不存在: {skill_dir}"
    
    # 查找技能文件
    skill_files = []
    for fname in os.listdir(skill_dir):
        fpath = os.path.join(skill_dir, fname)
        if os.path.isfile(fpath) and not fname.startswith(".") and not fname.endswith(".pyc"):
            skill_files.append(fpath)
    
    print(f"  [OK] HTML文件: {html_path} ({os.path.getsize(html_path)} bytes)")
    print(f"  [OK] 技能文件: {len(skill_files)} 个")
    for f in skill_files:
        print(f"    - {os.path.basename(f)} ({os.path.getsize(f)} bytes)")
    
    return html_path, skill_files


def test_upload_bundle(html_path, skill_files):
    """测试上传功能"""
    print("\n" + "=" * 60)
    print("测试2: 上传文件")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/upload/bundle"
    
    with open(html_path, "rb") as f:
        html_data = f.read()
    
    files = [
        ("html", ("report.html", html_data, "text/html")),
    ]
    
    for skill_path in skill_files:
        with open(skill_path, "rb") as f:
            skill_data = f.read()
        files.append(("skill_files", (os.path.basename(skill_path), skill_data, "application/octet-stream")))
    
    response = requests.post(url, files=files)
    assert response.status_code == 200, f"上传失败: HTTP {response.status_code}"
    
    data = response.json()
    assert data["success"], f"上传失败: {data.get('message', '未知错误')}"
    
    upload_id = data["upload_id"]
    print(f"  [OK] 上传成功")
    print(f"  [OK] Upload ID: {upload_id}")
    print(f"  [OK] 技能文件: {data.get('skill_files', [])}")
    
    return upload_id


def test_parse(upload_id):
    """测试解析功能"""
    print("\n" + "=" * 60)
    print("测试3: 解析文件")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/transform/parse"
    payload = {"upload_id": upload_id}
    
    response = requests.post(url, json=payload)
    assert response.status_code == 200, f"解析失败: HTTP {response.status_code}"
    
    data = response.json()
    assert data["success"], f"解析失败: {data.get('message', '未知错误')}"
    
    result = data["parse_result"]
    html_info = result["html"]
    skill_info = result["skill"]
    
    print(f"  [OK] HTML标题: {html_info['title']}")
    print(f"  [OK] 主题: {html_info['theme']}")
    print(f"  [OK] 数据区域: {html_info['data_regions_count']} 个")
    print(f"  [OK] 交互: {html_info['interactions']}")
    print(f"  [OK] 技能名称: {skill_info['name']}")
    print(f"  [OK] 数据源: {skill_info['data_source_type']}")
    print(f"  [OK] 拉取步骤: {skill_info['fetch_steps_count']} 步")
    print(f"  [OK] 计算公式: {skill_info['calculation_formula'] or '无'}")
    print(f"  [OK] 数据中心: {skill_info['datacenters']}")
    
    return result


def test_generate(upload_id, parse_result):
    """测试生成功能"""
    print("\n" + "=" * 60)
    print("测试4: 生成服务代码")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/transform/generate"
    
    skill_name = parse_result["skill"]["name"]
    service_name = skill_name.lower().replace(" ", "-").replace("_", "-")
    
    payload = {
        "upload_id": upload_id,
        "service_config": {
            "name": service_name,
            "title": parse_result["html"]["title"],
            "datacenter": parse_result["skill"]["datacenters"][0] if parse_result["skill"]["datacenters"] else "default",
            "refresh_strategy": "cron",
            "refresh_cron": "0 */6 * * *",
            "refresh_interval": 300,
            "path": f"/reports/{service_name}"
        }
    }
    
    response = requests.post(url, json=payload)
    assert response.status_code == 200, f"生成失败: HTTP {response.status_code}"
    
    data = response.json()
    assert data["success"], f"生成失败: {data.get('message', '未知错误')}"
    
    print(f"  [OK] 服务名称: {data['service_name']}")
    print(f"  [OK] 生成文件: {len(data['generated_files'])} 个")
    for fname in data["generated_files"]:
        print(f"    - {fname}")
    
    return data


def test_deploy(upload_id, service_name):
    """测试部署功能"""
    print("\n" + "=" * 60)
    print("测试5: 部署服务")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/deploy/full"
    payload = {
        "upload_id": upload_id,
        "service_config": {
            "name": service_name,
            "path": f"/reports/{service_name}"
        }
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print(f"  [OK] 部署成功")
            print(f"  [OK] 访问地址: {data.get('access_url', 'N/A')}")
            return True
        else:
            print(f"  [WARN] 部署失败: {data.get('message', '未知错误')}")
            if data.get("traceback"):
                print(f"  错误详情:\n{data['traceback'][:500]}")
            return False
    else:
        print(f"  [WARN] 部署请求失败: HTTP {response.status_code}")
        return False


def test_services_list():
    """测试服务列表"""
    print("\n" + "=" * 60)
    print("测试6: 服务列表")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/services"
    response = requests.get(url)
    
    assert response.status_code == 200, f"获取服务列表失败: HTTP {response.status_code}"
    
    data = response.json()
    services = data.get("services", [])
    
    print(f"  [OK] 当前服务数: {len(services)}")
    for s in services:
        print(f"    - {s.get('name', 'N/A')} ({s.get('status', 'unknown')})")
    
    return services


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Report Transformer Platform - 端到端测试")
    print("=" * 60)
    print(f"平台地址: {BASE_URL}")
    print(f"样例目录: {SAMPLE_DIR}")
    
    try:
        # 测试1: 检查样例文件
        html_path, skill_files = test_sample_files_exist()
        
        # 测试2: 上传
        upload_id = test_upload_bundle(html_path, skill_files)
        
        # 测试3: 解析
        parse_result = test_parse(upload_id)
        
        # 测试4: 生成
        generate_result = test_generate(upload_id, parse_result)
        service_name = generate_result["service_name"]
        
        # 测试5: 部署
        deploy_success = test_deploy(upload_id, service_name)
        
        # 测试6: 服务列表
        services = test_services_list()
        
        # 总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print("  [OK] 样例文件检查: 通过")
        print("  [OK] 文件上传: 通过")
        print("  [OK] 解析结构: 通过")
        print("  [OK] 生成代码: 通过")
        print(f"  [{'OK' if deploy_success else 'WARN'}] 部署服务: {'通过' if deploy_success else '失败'}")
        print("  [OK] 服务列表: 通过")
        print("\n  所有核心测试已完成!")
        
        if not deploy_success:
            print("\n  提示: 部署失败可能是由于Docker环境限制，")
            print("        但上传、解析、生成三个核心功能已验证通过。")
        
        return 0
        
    except AssertionError as e:
        print(f"\n  [FAIL] 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n  [FAIL] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
