import os
import time
import random
from flask import Flask, request, jsonify, render_template
from ai_agent_stream import AIAgent  # 导入 AI Agent 类

# 七牛云配置（请替换为你的实际配置）
QINIU_ACCESS_KEY = '_-5PY-C2FBhnyZxIIYX8f82w8ZGSWYeQgOto82Ho'
QINIU_SECRET_KEY = 'vDb9HJd0dAUZaUUYP6tN8cTREOQ4MfPF-1ZtdHuL'
QINIU_BUCKET = 'art-insight-poc1'
QINIU_DOMAIN = 'http://swei02p5t.hd-bkt.clouddn.com'  # 如：http://xxx.bkt.clouddn.com

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB限制

# 初始化 AI Agent（注意根据实际 MCP Server 地址调整）
ai_agent = AIAgent(server_url="http://localhost:5001")  # 假设 MCP Server 运行在 5001 端口

def qiniu_upload(file_path, target_key):
    """七牛云文件上传（需安装qiniu库：pip install qiniu）"""
    try:
        from qiniu import Auth, put_file
        q = Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)
        token = q.upload_token(QINIU_BUCKET, target_key, 3600)
        ret, info = put_file(token, target_key, file_path)
        print(f"七牛云上传结果：{info}")  
        os.remove(file_path)
        return ret is not None and ret.get('key') == target_key
    except Exception as e:
        print(f"上传异常：{str(e)}") 
        return False

def parse_style_type_from_file_key(file_key):
    """从 file_key 中解析风格类型（格式：风格类型/风格类型_时间戳.扩展名）"""
    try:
        return file_key.split('/')[0]  # 例如 "色彩/色彩_1715923200.jpg" 会返回 "色彩"
    except:
        return None

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify(success=False, message='未找到文件')
    
    file = request.files['file']
    style_type = request.form.get('style_type')
    if not style_type or style_type not in ['色彩', '速写', '素描']:
        return jsonify(success=False, message='无效的风格类型')

    # 校验文件类型
    allowed_extensions = {'jpg', 'jpeg', 'png'}
    ext = file.filename.split('.')[-1].lower()
    if ext not in allowed_extensions:
        return jsonify(success=False, message='仅支持JPG/PNG格式文件')

    timestamp = int(time.time())
    target_key = f"{style_type}/{style_type}_{timestamp}.{ext}"
    
    temp_path = f"temp_{timestamp}.{ext}"
    file.save(temp_path)
    
    if qiniu_upload(temp_path, target_key):
        return jsonify(
            success=True,
            message='上传成功',
            file_key=target_key,
            file_url=f"{QINIU_DOMAIN}/{target_key}"
        )
    return jsonify(success=False, message='七牛云上传失败')

@app.route('/evaluate', methods=['POST'])
def evaluate_image():
    data = request.json
    file_key = data.get('file_key')
    if not file_key:
        return jsonify(success=False, message='缺少file_key参数')
    
    """真实 AI 评估逻辑（调用 AI Agent）"""
    # 从 file_key 中解析风格类型
    style_type = parse_style_type_from_file_key(file_key)
    if not style_type or style_type not in ['色彩', '速写', '素描']:
        return {"error": "无效的风格类型"}
    
    # 调用 AI Agent 处理图片
    try:
        result = ai_agent.process_image(file_key, style_type)
    except Exception as e:
        print(f"AI 评估异常：{str(e)}")
        return {"error": "AI 评估失败"}
    
    print("处理结果aaaaaaaaaaaaa:", result)
    return result    
    # return jsonify(
    #     success=True,
    #     comment=result
    # )

if __name__ == '__main__':
    os.makedirs('temp', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)    