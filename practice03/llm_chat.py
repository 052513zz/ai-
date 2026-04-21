"""
Practice03: 流式输出聊天客户端
支持终端界面输入聊天内容、流式输出、历史聊天记录自动添加到上下文
直到用户 Ctrl+C 退出终端，否则一直循环
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path


def load_env_file(env_path=None):
    """
    读取 .env 文件，返回环境变量字典
    """
    if env_path is None:
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
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def call_llm_api_stream(env_vars, messages):
    """
    调用 LLM API（流式输出）
    
    Args:
        env_vars: 环境变量字典
        messages: 消息列表
    
    Yields:
        str: 流式输出的文本片段
    """
    base_url = env_vars.get('LLM_BASE_URL', 'http://127.0.0.1:1234/v1')
    model = env_vars.get('LLM_MODEL', 'qwen3.5-4b')
    api_key = env_vars.get('LLM_API_KEY', 'local')
    timeout = int(env_vars.get('LLM_TIMEOUT', '3600'))
    
    url = f"{base_url}/chat/completions"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    request_data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048,
        "stream": True
    }
    
    try:
        data = json.dumps(request_data).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            for line in response:
                line = line.decode('utf-8').strip()
                
                if not line:
                    continue
                
                if line.startswith('data: '):
                    data_str = line[6:]
                    
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data_json = json.loads(data_str)
                        
                        if 'choices' in data_json and len(data_json['choices']) > 0:
                            delta = data_json['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            
                            if content:
                                yield content
                    
                    except json.JSONDecodeError:
                        continue
    
    except urllib.error.HTTPError as e:
        error_msg = f'HTTP 错误 {e.code}: {e.reason}'
        yield f'\n\n❌ {error_msg}'
    
    except urllib.error.URLError as e:
        error_msg = f'URL 错误: {e.reason}'
        yield f'\n\n❌ {error_msg}'
    
    except Exception as e:
        error_msg = f'未知错误: {str(e)}'
        yield f'\n\n❌ {error_msg}'


def call_llm_api(env_vars, messages):
    """
    调用 LLM API（非流式，用于获取统计信息）
    
    Args:
        env_vars: 环境变量字典
        messages: 消息列表
    
    Returns:
        dict: API 响应结果
    """
    base_url = env_vars.get('LLM_BASE_URL', 'http://127.0.0.1:1234/v1')
    model = env_vars.get('LLM_MODEL', 'qwen3.5-4b')
    api_key = env_vars.get('LLM_API_KEY', 'local')
    timeout = int(env_vars.get('LLM_TIMEOUT', '3600'))
    
    url = f"{base_url}/chat/completions"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    request_data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048,
        "stream": False
    }
    
    start_time = time.time()
    
    try:
        data = json.dumps(request_data).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_data = response.read().decode('utf-8')
            result = json.loads(response_data)
        
        elapsed_time = time.time() - start_time
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0].get('message', {}).get('content', '')
        else:
            content = ''
        
        usage = result.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', prompt_tokens + completion_tokens)
        
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
    
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            'success': False,
            'error': str(e),
            'elapsed_time': elapsed_time,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'tokens_per_second': 0
        }


def print_header():
    """
    打印欢迎信息
    """
    print("\n" + "=" * 60)
    print("🚀 Practice03: 流式输出聊天客户端")
    print("=" * 60)
    print("\n💡 提示:")
    print("   - 输入消息与 AI 对话")
    print("   - 输入 'clear' 清空聊天历史")
    print("   - 输入 'history' 查看聊天历史")
    print("   - 按 Ctrl+C 退出程序")
    print("=" * 60 + "\n")


def print_stats(result):
    """
    打印统计信息
    """
    print("\n" + "-" * 60)
    print(f"📊 总 Token 数: {result['total_tokens']}")
    print(f"   响应时间: {result['elapsed_time']:.2f} 秒")
    print(f"   Token 处理速度: {result['tokens_per_second']:.2f} tokens/秒")
    print(f"   当前历史记录消息数: {len(conversation_history) // 2}")
    print("-" * 60 + "\n")


def print_history():
    """
    打印聊天历史
    """
    print("\n" + "=" * 60)
    print("📜 聊天历史")
    print("=" * 60)
    
    for i, msg in enumerate(conversation_history):
        role = msg['role']
        content = msg['content']
        
        if role == 'user':
            print(f"\n👤 用户: {content}")
        elif role == 'assistant':
            print(f"\n🤖 AI: {content}")
    
    print("\n" + "=" * 60 + "\n")


def clear_history():
    """
    清空聊天历史
    """
    global conversation_history
    conversation_history = [
        {"role": "system", "content": system_prompt}
    ]
    print("\n✅ 聊天历史已清空\n")


def main():
    """
    主函数：流式输出聊天客户端
    """
    global conversation_history, system_prompt
    
    print_header()
    
    # 1. 加载环境变量
    print("📂 正在加载环境变量...")
    env_vars = load_env_file()
    
    if not env_vars:
        print("❌ 无法加载环境变量，请检查 .env 文件")
        return
    
    print(f"✅ 已加载配置:")
    print(f"   Base URL: {env_vars.get('LLM_BASE_URL', '未设置')}")
    print(f"   Model: {env_vars.get('LLM_MODEL', '未设置')}")
    print(f"   Timeout: {env_vars.get('LLM_TIMEOUT', '3600')} 秒\n")
    
    # 2. 初始化聊天历史
    system_prompt = "你是一个乐于助人的助手，能够回答各种问题。"
    conversation_history = [
        {"role": "system", "content": system_prompt}
    ]
    
    # 3. 开始聊天循环
    print("💬 开始聊天（按 Ctrl+C 退出）:")
    print("=" * 60 + "\n")
    
    try:
        while True:
            try:
                # 获取用户输入
                user_input = input("你: ").strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() == 'clear':
                    clear_history()
                    continue
                elif user_input.lower() == 'history':
                    print_history()
                    continue
                elif user_input.lower() in ['quit', 'exit', '退出']:
                    print("\n👋 再见！")
                    break
                
                # 添加用户消息到历史
                conversation_history.append({"role": "user", "content": user_input})
                
                # 流式输出
                print("AI: ", end='', flush=True)
                assistant_response = ""
                
                for chunk in call_llm_api_stream(env_vars, conversation_history):
                    print(chunk, end='', flush=True)
                    assistant_response += chunk
                
                print()  # 换行
                
                # 添加助手响应到历史
                conversation_history.append({"role": "assistant", "content": assistant_response})
                
                # 获取统计信息
                result = call_llm_api(env_vars, conversation_history)
                
                # 打印统计信息
                print_stats(result)
            
            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except EOFError:
                print("\n\n👋 再见！")
                break
    
    except KeyboardInterrupt:
        print("\n\n👋 再见！")


if __name__ == "__main__":
    main()
