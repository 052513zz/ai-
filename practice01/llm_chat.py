import os
import json
import urllib.request
import urllib.error
import time
import sys
from pathlib import Path

def load_env_file():
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    
    env_vars = {}
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"错误：找不到环境变量文件 {env_file}")
        print("请先复制env.example为.env并填写正确的参数")
        return None
    
    required_vars = ['LLM_BASE_URL', 'LLM_MODEL', 'LLM_API_KEY']
    for var in required_vars:
        if var not in env_vars or not env_vars[var]:
            print(f"错误：缺少必要的环境变量 {var}")
            return None
    
    return env_vars

def call_llm_api_stream(env_vars, messages):
    base_url = env_vars['LLM_BASE_URL']
    model = env_vars['LLM_MODEL']
    api_key = env_vars['LLM_API_KEY']
    
    url = f"{base_url}/chat/completions"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    data = {
        'model': model,
        'messages': messages,
        'stream': True
    }
    
    start_time = time.time()
    total_tokens = 0
    completion = ""
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            for line in response:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith(b'data: '):
                    line = line[6:]
                    if line == b'[DONE]':
                        break
                    
                    try:
                        chunk = json.loads(line)
                        if 'choices' in chunk:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                content = delta['content']
                                completion += content
                                print(content, end='', flush=True)
                            
                            if 'usage' in chunk:
                                total_tokens = chunk['usage'].get('total_tokens', 0)
                    except json.JSONDecodeError:
                        pass
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if response_time > 0:
            tokens_per_second = total_tokens / response_time
        else:
            tokens_per_second = 0
        
        return {
            'content': completion,
            'total_tokens': total_tokens,
            'response_time': response_time,
            'tokens_per_second': tokens_per_second
        }
        
    except urllib.error.HTTPError as e:
        end_time = time.time()
        response_time = end_time - start_time
        error_msg = f"HTTP错误 {e.code}: {e.reason}"
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            if 'error' in error_data:
                error_msg += f" - {error_data['error']}"
        except:
            pass
        return {
            'content': error_msg,
            'total_tokens': 0,
            'response_time': response_time,
            'tokens_per_second': 0
        }
    except urllib.error.URLError as e:
        end_time = time.time()
        response_time = end_time - start_time
        return {
            'content': f"URL错误：{e.reason}",
            'total_tokens': 0,
            'response_time': response_time,
            'tokens_per_second': 0
        }
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        return {
            'content': f"未知错误：{str(e)}",
            'total_tokens': 0,
            'response_time': response_time,
            'tokens_per_second': 0
        }

def main():
    print("LLM聊天客户端 - 支持流式输出和历史记录")
    print("=" * 60)
    print("输入消息与LLM聊天，按Ctrl+C退出")
    print("=" * 60)
    
    env_vars = load_env_file()
    if not env_vars:
        return
    
    print(f"配置信息：")
    print(f"  Base URL: {env_vars['LLM_BASE_URL']}")
    print(f"  Model: {env_vars['LLM_MODEL']}")
    print(f"  API Key: {env_vars['LLM_API_KEY'][:10]}...")
    print()
    
    # 初始化聊天历史
    chat_history = []
    
    try:
        while True:
            try:
                user_message = input("\n你: ")
                if not user_message.strip():
                    continue
                
                # 添加用户消息到历史记录
                chat_history.append({
                    'role': 'user',
                    'content': user_message
                })
                
                print("\nLLM:", end=' ', flush=True)
                
                # 调用API获取响应
                result = call_llm_api_stream(env_vars, chat_history)
                
                # 添加LLM响应到历史记录
                chat_history.append({
                    'role': 'assistant',
                    'content': result['content']
                })
                
                # 显示统计信息
                print("\n")
                print("-" * 60)
                print(f"  总Token数：{result['total_tokens']}")
                print(f"  响应时间：{result['response_time']:.2f}秒")
                print(f"  Token处理速度：{result['tokens_per_second']:.2f} tokens/秒")
                print(f"  当前历史记录消息数：{len(chat_history)}")
                print("-" * 60)
                
            except KeyboardInterrupt:
                print("\n\n退出聊天...")
                break
            except EOFError:
                print("\n\n退出聊天...")
                break
    except Exception as e:
        print(f"\n错误：{str(e)}")

if __name__ == "__main__":
    main()