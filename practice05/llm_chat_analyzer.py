"""
Practice05: 聊天记录总结 + 关键信息提取 + 聊天历史搜索 + AnythingLLM 查询
基于 llm_chat_analyzer.py，新增：
1. 每5次聊天提取一次关键信息（5W规则）
2. 将关键信息记录到 D:\chat-log\log.txt，增量更新
3. 支持 /search 命令搜索聊天历史
4. 支持 AnythingLLM 文档仓库查询
"""

import os
import json
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


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


def calculate_context_length(messages):
    """
    计算上下文字符串的总长度
    """
    total_length = 0
    for msg in messages:
        total_length += len(msg.get('content', ''))
    return total_length


def count_conversation_rounds(messages):
    """
    计算对话轮数（排除系统消息）
    """
    rounds = 0
    for msg in messages:
        if msg.get('role') == 'user':
            rounds += 1
    return rounds


def should_summarize(messages, max_rounds=5, max_length=3000):
    """
    判断是否需要执行聊天记录总结
    """
    non_system_messages = [msg for msg in messages if msg.get('role') != 'system']
    
    rounds = count_conversation_rounds(non_system_messages)
    length = calculate_context_length(messages)
    
    if rounds > max_rounds:
        return True, f"对话轮数 {rounds} 超过限制 {max_rounds}"
    
    if length > max_length:
        return True, f"上下文长度 {length} 超过限制 {max_length}"
    
    return False, None


def call_llm_api(env_vars, messages):
    """
    调用 LLM API（非流式）
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
            'tokens_per_second': tokens_per_second
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'elapsed_time': time.time() - start_time,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'tokens_per_second': 0
        }


def call_llm_api_stream(env_vars, messages):
    """
    调用 LLM API（流式输出）
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
    
    except Exception as e:
        yield f'\n\n❌ 错误: {str(e)}'


def summarize_chat_history(env_vars, messages):
    """
    对聊天历史进行总结压缩
    """
    print("\n" + "=" * 60)
    print("📝 检测到聊天历史过长，正在执行总结压缩...")
    print("=" * 60)
    
    total_messages = len(messages)
    
    system_messages = [msg for msg in messages if msg.get('role') == 'system']
    non_system_messages = [msg for msg in messages if msg.get('role') != 'system']
    
    preserve_count = max(1, len(non_system_messages) // 3)
    preserved_messages = non_system_messages[-preserve_count:]
    messages_to_summarize = non_system_messages[:-preserve_count]
    
    print(f"\n📊 总结统计:")
    print(f"   总消息数: {total_messages}")
    print(f"   系统消息: {len(system_messages)}")
    print(f"   需要压缩: {len(messages_to_summarize)}")
    print(f"   保留原文: {len(preserved_messages)}")
    
    summarize_prompt = f"""请总结以下对话内容，生成一个简洁的摘要。

需要总结的对话内容：
{json.dumps(messages_to_summarize, ensure_ascii=False, indent=2)}

请按照以下格式总结：
1. 对话主题：
2. 关键信息：
3. 用户需求：
4. 重要结论：

摘要应该简洁明了，便于后续对话参考。"""
    
    summarize_messages = [
        {"role": "system", "content": "你是一个对话总结助手，擅长将长对话压缩成简洁的摘要。"},
        {"role": "user", "content": summarize_prompt}
    ]
    
    print("\n🤖 正在调用 LLM 生成摘要...")
    result = call_llm_api(env_vars, summarize_messages)
    
    if not result['success']:
        print(f"\n❌ 总结失败: {result['error']}")
        return {
            'success': False,
            'error': result['error']
        }
    
    summary = result['content']
    
    print("\n📋 生成的摘要:")
    print("-" * 60)
    print(summary)
    print("-" * 60)
    
    compressed_messages = system_messages + [{"role": "system", "content": f"【对话摘要】{summary}"}] + preserved_messages
    
    print(f"\n✅ 总结完成！")
    print(f"   原始消息数: {total_messages}")
    print(f"   压缩后消息数: {len(compressed_messages)}")
    print(f"   压缩率: {(1 - len(compressed_messages)/total_messages)*100:.1f}%")
    
    return {
        'success': True,
        'summary': summary,
        'compressed_messages': compressed_messages,
        'original_count': total_messages,
        'compressed_count': len(compressed_messages)
    }


def extract_key_info(env_vars, messages):
    """
    从聊天记录中提取关键信息（5W规则）
    
    Args:
        env_vars: 环境变量字典
        messages: 消息列表
    
    Returns:
        dict: 提取结果
    """
    print("\n" + "=" * 60)
    print("🔍 正在提取关键信息（5W规则）...")
    print("=" * 60)
    
    # 过滤出非系统消息
    non_system_messages = [msg for msg in messages if msg.get('role') != 'system']
    
    if len(non_system_messages) < 2:
        print("⚠️ 聊天记录不足，跳过关键信息提取")
        return {
            'success': False,
            'error': '聊天记录不足'
        }
    
    extract_prompt = f"""请从以下对话中提取关键信息，按照5W规则进行分析。

对话内容：
{json.dumps(non_system_messages, ensure_ascii=False, indent=2)}

请按照以下格式提取多条关键信息（如果有多条，请分别列出）：

【关键信息 1】
- Who（谁）：
- What（做了什么事）：
- When（什么时候，可选）：
- Where（在何处，可选）：
- Why（为什么要做这个事，可选）：

【关键信息 2】
- Who（谁）：
- What（做了什么事）：
- When（什么时候，可选）：
- Where（在何处，可选）：
- Why（为什么要做这个事，可选）：

（如果还有更多关键信息，请继续添加...）

请确保提取的信息准确、完整。"""
    
    extract_messages = [
        {"role": "system", "content": "你是一个信息提取助手，擅长从对话中提取关键信息。"},
        {"role": "user", "content": extract_prompt}
    ]
    
    print("\n🤖 正在调用 LLM 提取关键信息...")
    result = call_llm_api(env_vars, extract_messages)
    
    if not result['success']:
        print(f"\n❌ 提取失败: {result['error']}")
        return {
            'success': False,
            'error': result['error']
        }
    
    key_info = result['content']
    
    print("\n📋 提取的关键信息:")
    print("-" * 60)
    print(key_info)
    print("-" * 60)
    
    return {
        'success': True,
        'key_info': key_info
    }


def save_key_info_to_log(key_info, log_path="D:\\chat-log\\log.txt"):
    """
    将关键信息保存到 log.txt 文件（增量更新）
    
    Args:
        key_info: 关键信息文本
        log_path: 日志文件路径
    """
    try:
        # 确保目录存在
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"✅ 已创建目录: {log_dir}")
        
        # 获取当前时间
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建日志条目
        log_entry = f"\n{'=' * 60}\n"
        log_entry += f"📅 时间: {timestamp}\n"
        log_entry += f"{'=' * 60}\n"
        log_entry += f"{key_info}\n"
        
        # 追加到文件
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(f"✅ 关键信息已保存到: {log_path}")
        
        return {
            'success': True,
            'log_path': log_path
        }
    
    except Exception as e:
        print(f"❌ 保存日志失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def search_chat_history(env_vars, user_query, log_path="D:\\chat-log\\log.txt"):
    """
    搜索聊天历史
    
    Args:
        env_vars: 环境变量字典
        user_query: 用户查询
        log_path: 日志文件路径
    
    Returns:
        dict: 搜索结果
    """
    print("\n" + "=" * 60)
    print("🔍 正在搜索聊天历史...")
    print("=" * 60)
    
    # 检查日志文件是否存在
    if not os.path.exists(log_path):
        print(f"⚠️ 日志文件不存在: {log_path}")
        return {
            'success': False,
            'error': '日志文件不存在'
        }
    
    # 读取日志文件
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        print(f"📂 已读取日志文件: {log_path}")
        print(f"📊 日志文件大小: {len(log_content)} 字符\n")
    
    except Exception as e:
        print(f"❌ 读取日志失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
    
    # 构建搜索提示
    search_prompt = f"""用户查询：{user_query}

聊天历史记录：
{log_content}

请根据用户查询，从聊天历史中找到相关信息，并给出详细的回答。

回答要求：
1. 准确引用聊天历史中的相关内容
2. 提供清晰的解释和总结
3. 如果没有找到相关信息，请明确告知"""
    
    search_messages = [
        {"role": "system", "content": "你是一个聊天历史搜索助手，擅长从历史记录中查找和总结信息。"},
        {"role": "user", "content": search_prompt}
    ]
    
    print("🤖 正在调用 LLM 搜索...")
    result = call_llm_api(env_vars, search_messages)
    
    if not result['success']:
        print(f"\n❌ 搜索失败: {result['error']}")
        return {
            'success': False,
            'error': result['error']
        }
    
    search_result = result['content']
    
    print("\n📋 搜索结果:")
    print("-" * 60)
    print(search_result)
    print("-" * 60)
    
    return {
        'success': True,
        'search_result': search_result
    }


def anythingllm_query(env_vars, message):
    """
    使用 subprocess 调用 curl 访问 AnythingLLM 的聊天 API
    
    Args:
        env_vars: 环境变量字典
        message: 查询消息
    
    Returns:
        dict: 查询结果
    """
    print("\n" + "=" * 60)
    print("📚 正在查询 AnythingLLM 文档仓库...")
    print("=" * 60)
    
    # 从环境变量获取配置
    api_key = env_vars.get('ANYTHINGLLM_API_KEY')
    workspace_slug = env_vars.get('ANYTHINGLLM_WORKSPACE_SLUG', 'default')
    
    if not api_key:
        print("❌ 未配置 ANYTHINGLLM_API_KEY")
        return {
            'success': False,
            'error': '未配置 ANYTHINGLLM_API_KEY'
        }
    
    # 构建 API URL
    base_url = "http://localhost:3001"
    endpoint = f"{base_url}/api/v1/workspace/{workspace_slug}/chat"
    
    # 构建请求数据
    request_data = {
        "message": message,
        "stream": False
    }
    
    # 构建 curl 命令
    curl_cmd = [
        "curl",
        "-X", "POST",
        endpoint,
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(request_data, ensure_ascii=False)
    ]
    
    print(f"📡 正在访问: {endpoint}")
    print(f"💬 查询内容: {message[:100]}...")
    
    try:
        # 执行 curl 命令
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        
        print(f"\n📊 命令执行结果:")
        print(f"   退出码: {result.returncode}")
        
        if result.returncode != 0:
            print(f"❌ 错误输出: {result.stderr}")
            return {
                'success': False,
                'error': f'命令执行失败: {result.stderr}',
                'status_code': result.returncode
            }
        
        # 解析响应
        try:
            response_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"❌ 解析响应失败: {result.stdout}")
            return {
                'success': False,
                'error': '解析响应失败',
                'response': result.stdout
            }
        
        # 提取结果
        if 'response' in response_data:
            anythingllm_response = response_data['response']
            print("\n📋 查询结果:")
            print("-" * 60)
            print(anythingllm_response)
            print("-" * 60)
            
            return {
                'success': True,
                'response': anythingllm_response,
                'status_code': 200
            }
        else:
            print(f"❌ 响应格式错误: {response_data}")
            return {
                'success': False,
                'error': '响应格式错误',
                'response': response_data
            }
    
    except subprocess.TimeoutExpired:
        print("❌ 请求超时")
        return {
            'success': False,
            'error': '请求超时'
        }
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def is_search_request(user_input):
    """
    判断用户输入是否是搜索请求
    
    Args:
        user_input: 用户输入
    
    Returns:
        bool: 是否是搜索请求
    """
    user_input_lower = user_input.lower().strip()
    
    # 检查是否以 /search 开头
    if user_input_lower.startswith('/search'):
        return True
    
    # 检查是否包含"查找聊天历史"、"搜索历史"等关键词
    search_keywords = [
        '查找聊天历史',
        '搜索历史',
        '查找历史',
        '搜索聊天',
        '查找记录',
        '搜索记录'
    ]
    
    for keyword in search_keywords:
        if keyword in user_input:
            return True
    
    return False


def is_anythingllm_request(user_input):
    """
    判断用户输入是否是 AnythingLLM 查询请求
    
    Args:
        user_input: 用户输入
    
    Returns:
        bool: 是否是 AnythingLLM 查询请求
    """
    user_input_lower = user_input.lower().strip()
    
    # 检查是否包含"文档仓库"、"文件仓库"、"仓库"等关键词
    anythingllm_keywords = [
        '文档仓库',
        '文件仓库',
        '仓库',
        'anythingllm',
        '文档库',
        '知识库'
    ]
    
    for keyword in anythingllm_keywords:
        if keyword in user_input:
            return True
    
    return False


def print_header():
    """
    打印欢迎信息
    """
    print("\n" + "=" * 60)
    print("🚀 Practice05: 聊天记录总结 + 关键信息提取 + 聊天历史搜索 + AnythingLLM 查询")
    print("=" * 60)
    print("\n💡 提示:")
    print("   - 当聊天超过5轮或上下文长度超过3k时，自动执行总结")
    print("   - 每5次聊天自动提取关键信息（5W规则）并保存到日志")
    print("   - 输入 '/search 查询内容' 搜索聊天历史")
    print("   - 提到 '文档仓库'、'文件仓库'、'仓库' 时查询 AnythingLLM")
    print("   - 输入 'clear' 清空聊天历史")
    print("   - 输入 'history' 查看聊天历史")
    print("   - 按 Ctrl+C 退出程序")
    print("=" * 60 + "\n")


def print_stats(result, conversation_history):
    """
    打印统计信息
    """
    rounds = count_conversation_rounds(conversation_history)
    length = calculate_context_length(conversation_history)
    
    print("\n" + "-" * 60)
    print(f"📊 总 Token 数: {result.get('total_tokens', 0)}")
    print(f"   响应时间: {result.get('elapsed_time', 0):.2f} 秒")
    print(f"   Token 处理速度: {result.get('tokens_per_second', 0):.2f} tokens/秒")
    print(f"   当前对话轮数: {rounds}")
    print(f"   当前上下文长度: {length}")
    print("-" * 60 + "\n")


def print_history():
    """
    打印聊天历史
    """
    print("\n" + "=" * 60)
    print("📜 聊天历史")
    print("=" * 60)
    
    for msg in conversation_history:
        role = msg['role']
        content = msg['content']
        
        if role == 'user':
            print(f"\n👤 用户: {content}")
        elif role == 'assistant':
            print(f"\n🤖 AI: {content}")
        elif role == 'system':
            print(f"\n⚙️ 系统: {content[:50]}...")
    
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
    主函数
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
    system_prompt = """你是一个乐于助人的助手，能够回答各种问题。
当聊天历史较长时，系统会自动对其进行压缩总结，以便保持对话的连贯性。
每5次聊天，系统会自动提取关键信息并保存到日志文件中。
用户可以使用 /search 命令搜索聊天历史。
当用户提到'文档仓库'、'文件仓库'、'仓库'等关键词时，系统会自动查询 AnythingLLM 文档仓库。"""
    
    conversation_history = [
        {"role": "system", "content": system_prompt}
    ]
    
    # 3. 初始化聊天轮数计数器
    chat_round_counter = 0
    KEY_INFO_EXTRACT_INTERVAL = 5  # 每5次聊天提取一次关键信息
    
    # 4. 开始聊天循环
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
                
                # 检查是否是搜索请求
                if is_search_request(user_input):
                    # 提取搜索查询
                    if user_input.lower().startswith('/search'):
                        search_query = user_input[7:].strip()
                    else:
                        search_query = user_input
                    
                    if not search_query:
                        print("⚠️ 请提供搜索查询内容")
                        continue
                    
                    # 执行搜索
                    search_result = search_chat_history(env_vars, search_query)
                    
                    if search_result['success']:
                        print(f"\n🤖 搜索结果:\n{search_result['search_result']}\n")
                    else:
                        print(f"\n❌ 搜索失败: {search_result['error']}\n")
                    
                    continue
                
                # 检查是否是 AnythingLLM 查询请求
                if is_anythingllm_request(user_input):
                    # 执行 AnythingLLM 查询
                    anythingllm_result = anythingllm_query(env_vars, user_input)
                    
                    if anythingllm_result['success']:
                        print(f"\n🤖 文档仓库查询结果:\n{anythingllm_result['response']}\n")
                    else:
                        print(f"\n❌ 文档仓库查询失败: {anythingllm_result['error']}\n")
                    
                    continue
                
                # 添加用户消息到历史
                conversation_history.append({"role": "user", "content": user_input})
                chat_round_counter += 1
                
                # 检查是否需要总结
                need_summarize, reason = should_summarize(conversation_history)
                
                if need_summarize:
                    print(f"\n💡 {reason}")
                    summarize_result = summarize_chat_history(env_vars, conversation_history)
                    
                    if summarize_result['success']:
                        conversation_history = summarize_result['compressed_messages']
                        print(f"✅ 已将 {summarize_result['original_count']} 条消息压缩为 {summarize_result['compressed_count']} 条")
                    else:
                        print("⚠️ 总结失败，继续使用原始聊天历史")
                
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
                print_stats(result, conversation_history)
                
                # 检查是否需要提取关键信息
                if chat_round_counter % KEY_INFO_EXTRACT_INTERVAL == 0:
                    print(f"\n💡 已完成 {chat_round_counter} 次聊天，正在提取关键信息...")
                    
                    extract_result = extract_key_info(env_vars, conversation_history)
                    
                    if extract_result['success']:
                        save_result = save_key_info_to_log(extract_result['key_info'])
                        
                        if save_result['success']:
                            print(f"✅ 关键信息已成功保存")
                        else:
                            print(f"⚠️ 保存失败: {save_result['error']}")
                    else:
                        print(f"⚠️ 提取失败: {extract_result['error']}")
            
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
