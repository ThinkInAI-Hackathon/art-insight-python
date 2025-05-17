import requests
import time
from datetime import datetime
QINIU_DOMAIN = 'http://swei02p5t.hd-bkt.clouddn.com' 

class AIAgent:
    def __init__(self, server_url="http://localhost:5001"):
        self.server_url = server_url

    def generate_prompt(self, style_type: str, image_url: str) -> str:
        """（保持原有逻辑不变）"""
        style_prompts = {
            "色彩": f"分析这张图片的色彩构成，用专业术语描述主色调和配色方案（图片URL：{image_url}）",
            "速写": f"总结这张速写作品的线条特点和动态表现（图片URL：{image_url}）",
            "素描": f"分析这张素描的明暗层次和体积表现（图片URL：{image_url}）"
        }
        return style_prompts.get(style_type, f"分析这张{style_type}风格图片的艺术特点（图片URL：{image_url}）")
    
    def send_to_mcp_server(self, service_type, payload):
        """发送流式请求到MCP Server（生成器实现）"""
        try:
            # 发送请求时设置stream=True开启流式模式
            response = requests.post(
                f"{self.server_url}/api/process",
                json={"service_type": service_type, "payload": payload},
                timeout=300,
                stream=True  # 关键参数：开启流式响应
            )
            response.raise_for_status()
            
            # 逐行读取流式响应（适用于Server-Sent Events格式）
            # 若服务器返回原始字节流，可改为response.iter_content(chunk_size=1024)
            for line in response.iter_lines():
                if line:  # 跳过空行
                    yield line.decode('utf-8')  # 解码为字符串并返回
                
        except requests.exceptions.RequestException as e:
            print(f"请求异常：{str(e)}")
            yield f"[ERROR] {str(e)}"  # 以流式方式返回错误信息

    def process_image(self, image_key, style_type):
        print(f"开始处理图片：{image_key}，风格类型：{style_type}")
        image_url = f"{QINIU_DOMAIN}/{image_key}"
        prompt = self.generate_prompt(style_type, image_url)
        
        # 调用流式接口（返回生成器）
        stream_generator = self.send_to_mcp_server(
            service_type="qnyun_ai",
            payload={"prompt": prompt, "image_url": image_url}
        )
        
        # 处理流式数据（可扩展为实时展示/存储）
        results = []
        for chunk in stream_generator:
            # 将Unicode转义字符串解码为汉字
            decoded_chunk = chunk.encode('ascii').decode('unicode_escape')
            # print(f"接收到流式数据：{decoded_chunk}")  # 实时打印汉字
            results.append(decoded_chunk)  # 收集解码后的汉字数据
        
        clean_str = results[1].replace("\"response\": \"","")
        clean_str = md_to_html(remove_trailing_quote(clean_str))
        return clean_str  # 返回处理后的字符串
        # return {"success": True, "stream_data": results}  # 返回汉字结果
    
import markdown

def md_to_html(md_content: str) -> str:
    """
    将Markdown内容转换为HTML
    
    :param md_content: 输入的Markdown文本内容
    :return: 转换后的HTML字符串
    """
    try:
        # 启用扩展：表格、代码块、任务列表等常用功能
        html_content = markdown.markdown(
            md_content,
            extensions=[
                'markdown.extensions.tables',    # 支持表格
                # 'markdown.extensions.tasklist',  # 支持任务列表
                'markdown.extensions.fenced_code'  # 支持代码块
            ]
        )
        return html_content
    except Exception as e:
        print(f"转换过程中发生错误: {str(e)}")
        return ""
    
def remove_trailing_quote(s: str) -> str:
    """去除字符串末尾的双引号（如果存在）"""
    if len(s) > 0 and s.endswith(' "'):  # 检查字符串非空且以"结尾
        return s[:-2]  # 切片去除最后一个字符
    return s  # 无末尾"时直接返回原字符串
    
if __name__ == '__main__':
    agent = AIAgent()
    test_file_key = "色彩/色彩_1747490254.jpg"
    test_style_type = "色彩"
    
    print("开始处理...")
    response = agent.process_image(test_file_key, test_style_type)
    print("处理结果:", response)
    # clean_str = response.get("stream_data")[1].replace("\"response\": \"","")
    # clean_str = md_to_html(remove_trailing_quote(clean_str))
    
    # print("最终处理结果:", clean_str)
    