import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def format_suppliers():
    """读取 suppliers.json 并格式化为飞书消息文本"""
    try:
        with open('suppliers.json', 'r', encoding='utf-8') as f:
            suppliers = json.load(f)
    except Exception as e:
        print(f"❌ 读取 suppliers.json 失败: {e}")
        return None

    lines = []
    lines.append("📋 **国内尼龙胶板供应商名录**")
    lines.append("")
    for idx, s in enumerate(suppliers, 1):
        lines.append(f"**{idx}. {s.get('name', '')}**")
        if s.get('products'):
            lines.append(f"主营：{s.get('products')}")
        if s.get('phone'):
            lines.append(f"电话：{s.get('phone')}")
        if s.get('mobile'):
            lines.append(f"手机：{s.get('mobile')}")
        if s.get('fax'):
            lines.append(f"传真：{s.get('fax')}")
        if s.get('website'):
            lines.append(f"网址：{s.get('website')}")
        if s.get('address'):
            lines.append(f"地址：{s.get('address')}")
        if s.get('remark'):
            lines.append(f"备注：{s.get('remark')}")
        lines.append("")  # 空行分隔

    return "\n".join(lines)

def send_feishu_message(text):
    webhook_url = os.getenv("FEISHU_WEBHOOK")
    if not webhook_url:
        print("❌ 环境变量 FEISHU_WEBHOOK 未设置")
        return False
    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }
    try:
        resp = requests.post(webhook_url, json=payload)
        if resp.status_code == 200:
            print("✅ 飞书消息发送成功")
            return True
        else:
            print(f"❌ 飞书消息发送失败: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"❌ 飞书请求异常: {e}")
        return False

def main():
    message = format_suppliers()
    if message:
        send_feishu_message(message)
    else:
        print("⚠️ 未生成消息，请检查 suppliers.json 文件")

if __name__ == "__main__":
    main()
