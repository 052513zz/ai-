"""
Practice02: LLM 工具调用客户端
基于 practice01 的 llm_client.py，实现工具调用功能
支持 6 个工具：list_files, rename_file, delete_file, create_file, read_file, curl_web
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# 导入文件操作工具
from file_tools import (
    list_files,
    rename_file,
    delete_file,
    create_file,
    read_file,
    curl_web,
    get_tool_definition
)


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


def call_llm_api(env_vars, messages, stream=False):
    """
    调用 LLM API
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
        "stream": stream
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


def parse_tool_call(content):
    """
    解析 LLM 返回的工具调用请求
    
    Args:
        content: LLM 返回的内容
    
    Returns:
        dict: 工具调用信息，包含 tool_name 和 parameters
    """
    try:
        # 尝试解析 JSON 格式的工具调用
        if content.strip().startswith('{') and content.strip().endswith('}'):
            tool_call = json.loads(content)
            
            # 检查是否包含工具调用信息
            if 'tool' in tool_call or 'function' in tool_call:
                tool_name = tool_call.get('tool') or tool_call.get('function')
                parameters = tool_call.get('params', {})
                
                return {
                    'has_tool_call': True,
                    'tool_name': tool_name,
                    'parameters': parameters
                }
        
        # 尝试解析 "toolcall: {"tool": "...", "params": {...}}" 格式
        if 'toolcall:' in content.lower() or 'tool_call:' in content.lower():
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    tool_call = json.loads(line)
                    if 'tool' in tool_call or 'name' in tool_call:
                        tool_name = tool_call.get('tool') or tool_call.get('name')
                        parameters = tool_call.get('params', {})
                        
                        return {
                            'has_tool_call': True,
                            'tool_name': tool_name,
                            'parameters': parameters
                        }
        
        return {
            'has_tool_call': False,
            'tool_name': None,
            'parameters': None
        }
    
    except Exception as e:
        return {
            'has_tool_call': False,
            'tool_name': None,
            'parameters': None,
            'error': str(e)
        }


def execute_tool_call(tool_name, parameters):
    """
    执行工具调用
    
    Args:
        tool_name: 工具名称
        parameters: 工具参数
    
    Returns:
        dict: 工具执行结果
    """
    tool_functions = {
        'list_files': list_files,
        'rename_file': rename_file,
        'delete_file': delete_file,
        'create_file': create_file,
        'read_file': read_file,
        'curl_web': curl_web
    }
    
    if tool_name not in tool_functions:
        return {
            'success': False,
            'error': f'未知工具: {tool_name}'
        }
    
    try:
        tool_func = tool_functions[tool_name]
        result = tool_func(**parameters)
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f'工具执行失败: {str(e)}'
        }


def print_result(result):
    """
    打印 API 调用结果和统计信息
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


def print_tool_result(result):
    """
    打印工具执行结果
    """
    print("\n" + "=" * 60)
    print("🔧 工具执行结果")
    print("=" * 60)
    
    if result['success']:
        print(f"✅ 工具执行成功")
        if 'message' in result:
            print(f"   {result['message']}")
        if 'files' in result:
            print(f"   找到 {result['count']} 个文件:")
            for file_info in result['files'][:10]:
                print(f"     - {file_info['name']} ({file_info['type']}, {file_info['size_human']})")
        if 'content' in result:
            print(f"   文件内容:")
            print("   " + "-" * 50)
            for line in result['content'].split('\n')[:20]:
                print(f"   {line}")
            print("   " + "-" * 50)
    else:
        print(f"❌ 工具执行失败: {result['error']}")
    
    print("=" * 60 + "\n")


def main():
    """
    主函数：演示工具调用功能
    """
    print("🚀 Practice02: LLM 工具调用客户端")
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
    
    # 2. 构建系统提示词（包含工具定义）
    tools_def = get_tool_definition()
    
    system_prompt = f"""你是一个智能助手，可以使用以下工具来帮助用户完成文件操作任务。

可用的工具：
{tools_def}

使用工具的规则：
1. 当用户需要操作文件时，使用相应的工具
2. 工具调用的格式为 JSON：{{"tool": "工具名称", "params": {{"参数名": "参数值"}}}}
3. 例如：{{"tool": "list_files", "params": {{"directory": "."}}}}
4. 执行工具后，将结果告诉用户
5. 如果不需要使用工具，直接回答用户的问题

当前工作目录：{os.getcwd()}
"""
    
    # 3. 交互式对话
    print("\n💬 开始对话（输入 'quit' 或按 Ctrl+C 退出）:")
    print("=" * 60)
    
    conversation_history = [
        {"role": "system", "content": system_prompt}
    ]
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("👋 再见！")
                break
            
            if not user_input:
                continue
            
            # 添加用户消息到历史
            conversation_history.append({"role": "user", "content": user_input})
            
            # 调用 LLM
            print("\n🤖 正在调用 LLM...")
            result = call_llm_api(env_vars, conversation_history)
            
            if not result['success']:
                print(f"❌ LLM 调用失败: {result['error']}")
                continue
            
            # 解析工具调用
            tool_call = parse_tool_call(result['content'])
            
            if tool_call['has_tool_call']:
                print(f"\n🔧 检测到工具调用: {tool_call['tool_name']}")
                print(f"   参数: {json.dumps(tool_call['parameters'], ensure_ascii=False)}")
                
                # 执行工具
                tool_result = execute_tool_call(tool_call['tool_name'], tool_call['parameters'])
                print_tool_result(tool_result)
                
                # 将工具结果添加到对话历史
                tool_result_str = json.dumps(tool_result, ensure_ascii=False, indent=2)
                conversation_history.append({
                    "role": "assistant",
                    "content": result['content']
                })
                conversation_history.append({
                    "role": "user",
                    "content": f"工具执行结果：{tool_result_str}\n\n请根据这个结果回答用户的问题。"
                })
                
                # 再次调用 LLM 获取最终回答
                print("\n🤖 正在生成最终回答...")
                final_result = call_llm_api(env_vars, conversation_history)
                
                if final_result['success']:
                    print(f"\n📝 最终回答:")
                    print("-" * 60)
                    print(final_result['content'])
                    print("-" * 60)
                    
                    conversation_history.append({
                        "role": "assistant",
                        "content": final_result['content']
                    })
                else:
                    print(f"❌ 生成最终回答失败: {final_result['error']}")
            else:
                # 直接回答
                print(f"\n📝 回答:")
                print("-" * 60)
                print(result['content'])
                print("-" * 60)
                
                conversation_history.append({
                    "role": "assistant",
                    "content": result['content']
                })
            
            # 打印性能统计
            print("\n📊 性能统计:")
            print(f"  总 Token 数: {result['total_tokens']}")
            print(f"  响应时间: {result['elapsed_time']:.2f} 秒")
            print(f"  Token 处理速度: {result['tokens_per_second']:.2f} tokens/秒")
        
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")


if __name__ == "__main__":
    main()
