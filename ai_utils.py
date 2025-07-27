import os
import requests
import json

KEY_FILE = "user_openai_key.txt"

def get_api_key_path():
    return os.path.abspath(KEY_FILE)

def get_api_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r") as f:
            return f.read().strip()
    return ""

def set_api_key(key):
    with open(KEY_FILE, "w") as f:
        f.write(key)

def ai_chat(prompt, api_key=None, system_prompt="你是专业的投资分析AI，请用简明中文回答。", model="qwen-plus"):
    api_key = api_key or get_api_key()
    if not api_key:
        return "未设置API Key"
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            return f"AI调用失败: {response.status_code} {response.text}"
    except Exception as e:
        return f"AI调用失败: {e}" 