"""
Practice01: LLM 基础客户端
使用 Python 标准 HTTP 库访问 OpenAI 兼容协议的 LLM API
功能：读取 .env 配置、访问 LLM、统计 token 消耗和性能指标
"""

import os
import json
import time
import urllib.request
import urllib.error
from pathlib import Path


def load_env_file(env_path=None):
    """
    读取 .env 文件，返回环境变量字典
    
    Args:
        env_path: .env 文件路径，默认为项目根目录下的 .env 文件
    
    Returns:
        dict: 环境变量键值对
    """
    if env_path is None:
        # 获取项目根目录（当前文件的上级目录）
        current_dir = Path(__file__).parent.parent
        env_path = current_dir / '.env'
    
    env_vars = {}
    
    if not os.path.exists(env_path):
        print(f"警告：找不到 .env 文件: {env_path}")
        print("请复制 env.example 为 .env 并填写正确参数")
        return env_vars
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            # 解析键值对
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def call_llm_api(env_vars, messages, stream=False):
    """
    调用 LLM API
    
    Args:
        env_vars: 环境变量字典
        messages: 消息列表，格式为 [{"role": "user", "content": "消息内容"}]
        stream: 是否使用流式输出
    
    Returns:
        dict: API 响应结果，包含内容和统计信息
    """
    base_url = env_vars.get('LLM_BASE_URL', 'http://127.0.0.1:1234/v1')
    model = env_vars.get('LLM_MODEL', 'qwen3.5-4b')
    api_key = env_vars.get('LLM_API_KEY', 'local')
    timeout = int(env_vars.get('LLM_TIMEOUT', '3600'))
    
    # 构建 API URL
    url = f"{base_url}/chat/completions"
    
    # 构建请求头
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 构建请求数据
    request_data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048,
        "stream": stream
    }
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 创建请求
        data = json.dumps(request_data).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method='POST'
        )
        
        # 发送请求
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_data = response.read().decode('utf-8')
            result = json.loads(response_data)
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        # 提取响应内容
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0].get('message', {}).get('content', '')
        else:
            content = ''
        
        # 提取 token 统计
        usage = result.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', prompt_tokens + completion_tokens)
        
        # 计算 token/s 速度
        tokens_per_second = completion_tokens / elapsed_time if elapsed_time > 0 else 0
        
        return {
            'success': True,
            'content': content,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'elapsed_time': elapsed_time,
            'tokens_per_second': tokens_per_second,
            'model': result.get('model', model)
        }
    
    except urllib.error.HTTPError as e:
        elapsed_time = time.time() - start_time
        error_body = e.read().decode('utf-8') if e.read() else str(e)
        return {
            'success': False,
            'error': f'HTTP 错误 {e.code}: {e.reason}',
            'error_details': error_body,
            'elapsed_time': elapsed_time,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'tokens_per_second': 0
        }
    
    except urllib.error.URLError as e:
        elapsed_time = time.time() - start_time
        return {
            'success': False,
            'error': f'URL 错误: {e.reason}',
            'elapsed_time': elapsed_time,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'tokens_per_second': 0
        }
    
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            'success': False,
            'error': f'未知错误: {str(e)}',
            'elapsed_time': elapsed_time,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'tokens_per_second': 0
        }


def print_result(result):
    """
    打印 API 调用结果和统计信息
    
    Args:
        result: call_llm_api 返回的结果字典
    """
    print("\n" + "=" * 60)
    
    if result['success']:
        print("✅ LLM 响应成功")
        print("\n响应内容:")
        print("-" * 60)
        print(result['content'])
    else:
        print("❌ LLM 调用失败")
        print(f"\n错误信息: {result['error']}")
        if 'error_details' in result:
            print(f"错误详情: {result['error_details']}")
    
    print("\n" + "-" * 60)
    print("📊 性能统计:")
    print(f"  总 Token 数: {result['total_tokens']}")
    print(f"  输入 Token: {result['prompt_tokens']}")
    print(f"  输出 Token: {result['completion_tokens']}")
    print(f"  响应时间: {result['elapsed_time']:.2f} 秒")
    print(f"  Token 处理速度: {result['tokens_per_second']:.2f} tokens/秒")
    print("=" * 60 + "\n")


def main():
    """
    主函数：演示如何使用 LLM 客户端
    """
    print("🚀 Practice01: LLM 基础客户端")
    print("=" * 60)
    
    # 1. 加载环境变量
    print("\n📂 正在加载环境变量...")
    env_vars = load_env_file()
    
    if not env_vars:
        print("❌ 无法加载环境变量，请检查 .env 文件")
        return
    
    print(f"✅ 已加载配置:")
    print(f"   Base URL: {env_vars.get('LLM_BASE_URL', '未设置')}")
    print(f"   Model: {env_vars.get('LLM_MODEL', '未设置')}")
    print(f"   Timeout: {env_vars.get('LLM_TIMEOUT', '3600')} 秒")
    
    # 2. 准备消息
    print("\n💬 请输入您的问题（直接回车使用默认问题）:")
    user_input = input("> ").strip()
    
    if not user_input:
        user_input = "你好，请介绍一下你自己。"
        print(f"使用默认问题: {user_input}")
    
    messages = [
        {"role": "system", "content": "你是一个乐于助人的助手。"},
        {"role": "user", "content": user_input}
    ]
    
    # 3. 调用 LLM API
    print("\n🤖 正在调用 LLM API...")
    result = call_llm_api(env_vars, messages)
    
    # 4. 打印结果
    print_result(result)


if __name__ == "__main__":
    main()
