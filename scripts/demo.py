"""端到端演示脚本。

一键跑通：上传合同 -> 创建审查任务 -> 等待完成 -> 获取风险 -> 获取报告
使用方式：python scripts/demo.py
"""
import json
import sys
import time
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000/api"
EXAMPLE_CONTRACT = (
    Path(__file__).parent.parent / "examples" / "供应商采购合同.txt"
)


def main() -> None:
    print("=" * 60)
    print("企业合同智能审查与风险辅助 Agent - 端到端演示")
    print("=" * 60)

    # 1. 上传合同
    print("\n[1/5] 上传合同...")
    if not EXAMPLE_CONTRACT.exists():
        print(f"错误：示例合同不存在 {EXAMPLE_CONTRACT}")
        sys.exit(1)

    with open(EXAMPLE_CONTRACT, "rb") as f:
        resp = httpx.post(
            f"{BASE_URL}/contracts/upload",
            files={"file": ("供应商采购合同.txt", f, "text/plain")},
            timeout=30,
        )
    if resp.status_code != 200:
        print(f"上传失败：{resp.status_code} {resp.text}")
        sys.exit(1)
    upload_result = resp.json()
    contract_id = upload_result["contract_id"]
    print(f"  -> 合同ID: {contract_id}")

    # 2. 创建审查任务
    print("\n[2/5] 创建审查任务...")
    resp = httpx.post(
        f"{BASE_URL}/reviews/create",
        json={"contract_id": contract_id, "review_type": "full"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"创建任务失败：{resp.status_code} {resp.text}")
        sys.exit(1)
    task_id = resp.json()["task_id"]
    print(f"  -> 任务ID: {task_id}")

    # 3. 轮询状态
    print("\n[3/5] 等待审查完成...")
    max_wait = 60
    waited = 0
    while waited < max_wait:
        resp = httpx.get(f"{BASE_URL}/reviews/{task_id}/status", timeout=30)
        status = resp.json()
        print(f"  -> 状态: {status['status']} (进度 {status['progress']}%)"
              f" - 当前步骤: {status['current_step']}")
        if status["status"] in ("completed", "failed"):
            break
        time.sleep(2)
        waited += 2

    if status["status"] == "failed":
        print(f"\n审查失败：{status.get('error_message')}")
        sys.exit(1)

    # 4. 获取风险
    print("\n[4/5] 获取风险结果...")
    resp = httpx.get(f"{BASE_URL}/reviews/{task_id}/risks", timeout=30)
    risks = resp.json()
    print(f"  -> 发现 {len(risks)} 个风险：")
    for r in risks:
        print(f"    [{r['risk_level']}] {r['risk_type']} - "
              f"{r['description']}（建议：{r['suggestion']}）")

    # 5. 获取报告
    print("\n[5/5] 获取审查报告...")
    resp = httpx.get(f"{BASE_URL}/reviews/{task_id}/report", timeout=30)
    report = resp.json()
    stats = report.get("risk_statistics", {})
    print(f"  -> 综合风险等级: {report.get('overall_level')}")
    print(f"  -> 风险统计: 高 {stats.get('high')} / "
          f"中 {stats.get('medium')} / 低 {stats.get('low')}")
    print(f"  -> 摘要: {report.get('summary')}")
    if report.get("key_concerns"):
        print("  -> 重点关注：")
        for c in report["key_concerns"]:
            print(f"    * {c}")

    print("\n" + "=" * 60)
    print("演示完成！")
    print(f"合同ID: {contract_id}")
    print(f"任务ID: {task_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
