from flask import Flask, request, jsonify, Response
from qiniu import Auth, BucketManager
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
import json
import os
from openai import OpenAI

app = Flask(__name__)
# 配置参数
app.config.update({
    'UPLOAD_FOLDER': 'uploads',
    # 'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'LLM_BASE_URL': 'https://api.qnaigc.com/v1/chat/completions',
})
app.config['LLM_API_KEY'] = os.getenv('LLM_API_KEY', 'default-key')


# 七牛云配置（请替换为你的实际配置）
QINIU_ACCESS_KEY = '_-5PY-C2FBhnyZxIIYX8f82w8ZGSWYeQgOto82Ho'
QINIU_SECRET_KEY = 'vDb9HJd0dAUZaUUYP6tN8cTREOQ4MfPF-1ZtdHuL'
QINIU_BUCKET = 'art-insight-poc1'
QINIU_DOMAIN = 'http://swei02p5t.hd-bkt.clouddn.com'  # 如：http://xxx.bkt.clouddn.com

# 配置加载（建议使用环境变量或配置文件）
CONFIG = {
    "qiniu": {
        "access_key": QINIU_ACCESS_KEY,
        "secret_key": QINIU_SECRET_KEY,
        "bucket": QINIU_BUCKET
    }
}

# 初始化客户端
qiniu_auth = Auth(CONFIG['qiniu']['access_key'], CONFIG['qiniu']['secret_key'])


llm_api_key = app.config['LLM_API_KEY']  # 替换为你的 API Key 配置
url = app.config['LLM_BASE_URL']  # 替换为你的 API 基础 URL（如非默认）
client = OpenAI(    
        base_url=url,
        api_key=llm_api_key
    )  # 需先初始化客户端（需配置API Key，通常通过环境变量或参数传入）

def get_qiniu_file_info(file_key):
    bucket = BucketManager(qiniu_auth)
    ret, info = bucket.stat(CONFIG['qiniu']['bucket'], file_key)
    return ret if ret else None

import requests

import report_string as report_string

def call_qnyun_ai(image_url):
    url = "https://api.qnaigc.com/v1/chat/completions"
    payload = {
        "stream": True,
        "model": "doubao-1.5-vision-pro",        
        "messages": [
            {
                "role": "user",
                "content": [
                {
                    "type": "text",
                    "text": report_string.report_color
                },
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]
    }
    headers = {
        "Authorization": "Bearer sk-a01996924f84ee46c7fb19c209778896ef87f40ec8c618e4355c285bcc873adc",
        "Content-Type": "application/json"
    }

    try:
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=30) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    try:
                        # 提取 SSE 格式中的实际数据（去掉 data: 前缀）
                        chunk = line.decode('utf-8').strip()
                        if chunk.startswith('data: '):
                            json_str = chunk[len('data: '):].strip()  # 移除 "data: " 前缀
                            
                            # 处理流结束标记
                            if json_str == '[DONE]':
                                yield None  # 表示流结束
                                continue
                            
                            # 解析有效 JSON
                            json_data = json.loads(json_str)
                            if 'choices' in json_data and json_data['choices']:
                                content = json_data['choices'][0].get('delta', {}).get('content', '')
                                if content:
                                    yield content
                        else:
                            print(f"非 SSE 格式数据: {chunk}")
                    except json.JSONDecodeError as e:
                        print(f"解析JSON失败: {e}，原始内容: {json_str}")  # 打印实际解析的字符串
                    except Exception as e:
                        print(f"处理异常: {e}")
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
    except Exception as e:
        print(f"未知错误: {e}")

@app.route('/api/process', methods=['POST'])
def process_request():
    data = request.json
    service_type = data.get('service_type')

    if service_type == 'qnyun_ai':
        # 收集生成器内容时过滤 None 值
        response_content = [content for content in call_qnyun_ai("http://swei02p5t.hd-bkt.clouddn.com/sample/sumiao.jpg") if content is not None]
        full_response = ''.join(response_content)
        return jsonify({"response": full_response})
    elif service_type == 'qiniu':
        return jsonify(get_qiniu_file_info(data.get('payload', {}).get('file_key')))
    else:
        return jsonify(error="无效的服务类型"), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
    