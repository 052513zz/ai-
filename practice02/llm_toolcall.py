import os
import json
import urllib.request
import urllib.error
import time
import sys
from pathlib import Path
from file_tools import list_directory_files, rename_file, delete_file, create_file, read_file

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

def get_system_prompt():
    """
    获取系统提示词，包含工具调用的能力
    """
    return """
你是一个智能助手，能够使用以下工具来帮助用户完成文件操作任务：

工具列表：

1. list_directory_files
   - 功能：列出某个目录下有哪些文件(包括文件的基本属性、大小等信息)
   - 参数：directory (str) - 目录路径
   - 示例：{"toolcall": {"name": "list_directory_files", "params": {"directory": "./"}}}

2. rename_file
   - 功能：修改某个目录下某个文件的名字
   - 参数：directory (str) - 目录路径, old_name (str) - 旧文件名, new_name (str) - 新文件名
   - 示例：{"toolcall": {"name": "rename_file", "params": {"directory": "./", "old_name": "old.txt", "new_name": "new.txt"}}}

3. delete_file
   - 功能：删除某个目录下的某个文件
   - 参数：directory (str) - 目录路径, file_name (str) - 文件名
   - 示例：{"toolcall": {"name": "delete_file", "params": {"directory": "./", "file_name": "file.txt"}}}

4. create_file
   - 功能：在某个目录下新建1个文件，并且写入内容
   - 参数：directory (str) - 目录路径, file_name (str) - 文件名, content (str) - 文件内容
   - 示例：{"toolcall": {"name": "create_file", "params": {"directory": "./", "file_name": "new.txt", "content": "Hello World"}}}

5. read_file
   - 功能：读取某个目录下的某个文件的内容
   - 参数：directory (str) - 目录路径, file_name (str) - 文件名
   - 示例：{"toolcall": {"name": "read_file", "params": {"directory": "./", "file_name": "file.txt"}}}

使用工具的格式：
当你需要使用工具时，请以JSON格式输出，例如：
{"toolcall": {"name": "工具名称", "params": {"参数1": "值1", "参数2": "值2"}}}

当你收到工具执行结果后，请用自然语言总结结果给用户。

请根据用户的需求，选择合适的工具来完成任务。
"""

def execute_tool(tool_name, params):
    """
    执行工具调用
    """
    if tool_name == "list_directory_files":
        return list_directory_files(params.get("directory"))
    elif tool_name == "rename_file":
        return rename_file(
            params.get("directory"),
            params.get("old_name"),
            params.get("new_name")
        )
    elif tool_name == "delete_file":
        return delete_file(
            params.get("directory"),
            params.get("file_name")
        )
    elif tool_name == "create_file":
        return create_file(
            params.get("directory"),
            params.get("file_name"),
            params.get("content")
        )
    elif tool_name == "read_file":
        return read_file(
            params.get("directory"),
            params.get("file_name")
        )
    else:
        return {"success": False, "error": f"未知工具: {tool_name}"}

def call_llm_api(env_vars, messages):
    """
    调用LLM API
    """
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
        'messages': messages
    }
    
    start_time = time.time()
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            response_data = response.read().decode('utf-8')
            result = json.loads(response_data)
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                total_tokens = result.get('usage', {}).get('total_tokens', 0)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if response_time > 0:
                    tokens_per_second = total_tokens / response_time
                else:
                    tokens_per_second = 0
                
                return {
                    'content': content,
                    'total_tokens': total_tokens,
                    'response_time': response_time,
                    'tokens_per_second': tokens_per_second
                }
            else:
                end_time = time.time()
                response_time = end_time - start_time
                return {
                    'content': "错误：API返回的数据格式不正确",
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
    print("LLM工具调用客户端")
    print("=" * 60)
    print("支持文件操作工具：list_directory_files, rename_file, delete_file, create_file, read_file")
    print("按Ctrl+C退出")
    print("=" * 60)
    
    env_vars = load_env_file()
    if not env_vars:
        return
    
    print(f"配置信息：")
    print(f"  Base URL: {env_vars['LLM_BASE_URL']}")
    print(f"  Model: {env_vars['LLM_MODEL']}")
    print(f"  API Key: {env_vars['LLM_API_KEY'][:10]}...")
    print()
    
    # 初始化聊天历史，添加系统提示词
    chat_history = [{
        'role': 'system',
        'content': get_system_prompt()
    }]
    
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
                result = call_llm_api(env_vars, chat_history)
                response_content = result['content']
                
                print(response_content)
                
                # 检查是否需要工具调用
                try:
                    tool_call = json.loads(response_content)
                    if "toolcall" in tool_call:
                        print("\n执行工具调用...")
                        tool_name = tool_call["toolcall"]["name"]
                        tool_params = tool_call["toolcall"]["params"]
                        
                        # 执行工具
                        tool_result = execute_tool(tool_name, tool_params)
                        
                        # 显示工具执行结果
                        print(f"工具执行结果: {json.dumps(tool_result, ensure_ascii=False, indent=2)}")
                        
                        # 将工具结果添加到聊天历史
                        chat_history.append({
                            'role': 'assistant',
                            'content': response_content
                        })
                        chat_history.append({
                            'role': 'user',
                            'content': f"工具执行结果: {json.dumps(tool_result, ensure_ascii=False)}"
                        })
                        
                        # 再次调用API获取最终响应
                        print("\n获取最终响应...")
                        final_result = call_llm_api(env_vars, chat_history)
                        print(f"\nLLM: {final_result['content']}")
                        
                        # 添加最终响应到历史记录
                        chat_history.append({
                            'role': 'assistant',
                            'content': final_result['content']
                        })
                    else:
                        # 普通响应，添加到历史记录
                        chat_history.append({
                            'role': 'assistant',
                            'content': response_content
                        })
                except json.JSONDecodeError:
                    # 非JSON响应，直接添加到历史记录
                    chat_history.append({
                        'role': 'assistant',
                        'content': response_content
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