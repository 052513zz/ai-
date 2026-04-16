import os
import json
import urllib.request
import urllib.error
import time
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

def call_llm_api(env_vars, user_message):
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
        'messages': [
            {
                'role': 'user',
                'content': user_message
            }
        ]
    }
    
    start_time = time.time()
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = response.read().decode('utf-8')
            result = json.loads(response_data)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                
                # 统计token消耗
                prompt_tokens = result.get('usage', {}).get('prompt_tokens', 0)
                completion_tokens = result.get('usage', {}).get('completion_tokens', 0)
                total_tokens = result.get('usage', {}).get('total_tokens', 0)
                
                # 计算token/s速度
                if response_time > 0:
                    tokens_per_second = total_tokens / response_time
                else:
                    tokens_per_second = 0
                
                return {
                    'content': content,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'response_time': response_time,
                    'tokens_per_second': tokens_per_second
                }
            else:
                end_time = time.time()
                response_time = end_time - start_time
                return {
                    'content': "错误：API返回的数据格式不正确",
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                    'response_time': response_time,
                    'tokens_per_second': 0
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
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'response_time': response_time,
            'tokens_per_second': 0
        }
    except urllib.error.URLError as e:
        end_time = time.time()
        response_time = end_time - start_time
        return {
            'content': f"URL错误：{e.reason}",
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'response_time': response_time,
            'tokens_per_second': 0
        }
    except json.JSONDecodeError:
        end_time = time.time()
        response_time = end_time - start_time
        return {
            'content': "错误：无法解析API返回的JSON数据",
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'response_time': response_time,
            'tokens_per_second': 0
        }
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        return {
            'content': f"未知错误：{str(e)}",
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'response_time': response_time,
            'tokens_per_second': 0
        }

def main():
    print("LLM客户端 - 读取环境变量并调用API")
    print("=" * 50)
    
    env_vars = load_env_file()
    if not env_vars:
        return
    
    print(f"配置信息：")
    print(f"  Base URL: {env_vars['LLM_BASE_URL']}")
    print(f"  Model: {env_vars['LLM_MODEL']}")
    print(f"  API Key: {env_vars['LLM_API_KEY'][:10]}...")
    print()
    
    user_message = input("请输入要发送给LLM的消息（或输入'quit'退出）：")
    
    if user_message.lower() == 'quit':
        print("退出程序")
        return
    
    print("\n正在发送请求...")
    result = call_llm_api(env_vars, user_message)
    
    print("\nLLM响应：")
    print("-" * 50)
    print(result['content'])
    print("-" * 50)
    
    # 显示统计信息
    print("\n统计信息：")
    print("-" * 50)
    print(f"  输入Token数：{result['prompt_tokens']}")
    print(f"  输出Token数：{result['completion_tokens']}")
    print(f"  总Token数：{result['total_tokens']}")
    print(f"  响应时间：{result['response_time']:.2f}秒")
    print(f"  Token处理速度：{result['tokens_per_second']:.2f} tokens/秒")
    print("-" * 50)

if __name__ == "__main__":
    main()