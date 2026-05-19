"""
Practice07: 聊天记录总结 + 关键信息提取 + 聊天历史搜索 + AnythingLLM 查询 + 技能系统 + 链式工具调用
优化版本：自动检测工具调用、自动加载技能、增强文件系统和网络访问能力
"""

import os
import json
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


# 全局变量
SKILLS_DIR = None
TOOLS = {}


def init_global_vars():
    """
    初始化全局变量
    """
    global SKILLS_DIR
    current_dir = Path(__file__).parent.parent
    SKILLS_DIR = current_dir / '.agents' / 'skills'
    
    # 注册工具
    register_tools()


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
        yield f'\n\n错误: {str(e)}'


def summarize_chat_history(env_vars, messages):
    """
    对聊天历史进行总结压缩
    """
    print("\n" + "=" * 60)
    print("检测到聊天历史过长，正在执行总结压缩...")
    print("=" * 60)
    
    total_messages = len(messages)
    
    system_messages = [msg for msg in messages if msg.get('role') == 'system']
    non_system_messages = [msg for msg in messages if msg.get('role') != 'system']
    
    preserve_count = max(1, len(non_system_messages) // 3)
    preserved_messages = non_system_messages[-preserve_count:]
    messages_to_summarize = non_system_messages[:-preserve_count]
    
    print(f"\n总结统计:")
    print(f"   总消息数: {total_messages}")
    print(f"   系统消息: {len(system_messages)}")
    print(f"   需要压缩: {len(messages_to_summarize)}")
    print(f"   保留原文: {len(preserved_messages)}")
    
    summarize_prompt = f"""请总结以下对话内容，生成一个简洁的摘要。

需要总结的对话内容：
{json.dumps(messages_to_summarize, ensure_ascii=False, indent=2)}

请以以下格式输出总结：
1. 对话主题
2. 关键信息
3. 用户需求
4. 重要结论"""
    
    summarize_messages = [
        {"role": "system", "content": "你是一个对话总结助手，擅长将长对话压缩成简洁的摘要。"},
        {"role": "user", "content": summarize_prompt}
    ]
    
    print("\n正在调用 LLM 生成摘要...")
    result = call_llm_api(env_vars, summarize_messages)
    
    if not result['success']:
        print(f"\n总结失败: {result['error']}")
        return {
            'success': False,
            'error': result['error']
        }
    
    summary = result['content']
    
    print(f"\n生成的摘要:")
    print("-" * 60)
    print(summary)
    print("-" * 60)
    
    new_messages = []
    
    for msg in system_messages:
        new_messages.append(msg)
    
    new_messages.append({
        "role": "system",
        "content": f"以下是之前对话的总结：\n{summary}"
    })
    
    for msg in preserved_messages:
        new_messages.append(msg)
    
    print(f"\n已将 {total_messages} 条消息压缩为 {len(new_messages)} 条")
    
    return {
        'success': True,
        'messages': new_messages,
        'original_count': total_messages,
        'compressed_count': len(new_messages),
        'compression_rate': (total_messages - len(new_messages)) / total_messages * 100
    }


def extract_key_info(env_vars, messages):
    """
    从聊天记录中提取关键信息（5W规则）
    """
    print("\n" + "=" * 60)
    print("正在提取关键信息（5W规则）...")
    print("=" * 60)
    
    non_system_messages = [msg for msg in messages if msg.get('role') != 'system']
    
    extract_prompt = f"""请从以下对话中提取关键信息，按照5W规则进行分析。

对话内容：
{json.dumps(non_system_messages, ensure_ascii=False, indent=2)}

请按照以下格式输出：
【关键信息 1】
- Who（谁）：
- What（做了什么事）：
- When（什么时候）：（可选）
- Where（在何处）：（可选）
- Why（为什么要做这个事）：（可选）

【关键信息 2】
- Who（谁）：
- What（做了什么事）：
...

如果有多个关键信息，请提取多条。"""
    
    extract_messages = [
        {"role": "system", "content": "你是一个信息提取助手，擅长从对话中提取关键信息。"},
        {"role": "user", "content": extract_prompt}
    ]
    
    print("\n正在调用 LLM 提取关键信息...")
    result = call_llm_api(env_vars, extract_messages)
    
    if not result['success']:
        print(f"\n提取失败: {result['error']}")
        return {
            'success': False,
            'error': result['error']
        }
    
    key_info = result['content']
    
    print(f"\n提取的关键信息:")
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
    """
    try:
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"已创建目录: {log_dir}")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = f"\n{'='*60}\n"
        log_entry += f"时间: {timestamp}\n"
        log_entry += f"{'='*60}\n"
        log_entry += f"{key_info}\n"
        log_entry += f"{'='*60}\n"
        
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(f"关键信息已保存到: {log_path}")
        
        return {
            'success': True,
            'log_path': log_path
        }
    
    except Exception as e:
        print(f"保存日志失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def search_chat_history(env_vars, user_query, log_path="D:\\chat-log\\log.txt"):
    """
    搜索聊天历史
    """
    print("\n" + "=" * 60)
    print("正在搜索聊天历史...")
    print("=" * 60)
    
    if not os.path.exists(log_path):
        print(f"警告：日志文件不存在: {log_path}")
        return {
            'success': False,
            'error': '日志文件不存在'
        }
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        print(f"已读取日志文件: {log_path}")
        print(f"日志文件大小: {len(log_content)} 字符\n")
    
    except Exception as e:
        print(f"读取日志失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
    
    search_prompt = f"""请根据以下聊天历史日志回答用户的问题。

聊天历史日志：
{log_content}

用户问题：
{user_query}

请基于日志内容给出准确的回答。如果日志中没有相关信息，请说明。"""
    
    search_messages = [
        {"role": "system", "content": "你是一个聊天历史搜索助手，擅长从历史记录中查找和总结信息。"},
        {"role": "user", "content": search_prompt}
    ]
    
    print("正在调用 LLM 搜索...")
    result = call_llm_api(env_vars, search_messages)
    
    if not result['success']:
        print(f"\n搜索失败: {result['error']}")
        return {
            'success': False,
            'error': result['error']
        }
    
    search_result = result['content']
    
    print(f"\n搜索结果:")
    print("-" * 60)
    print(search_result)
    print("-" * 60)
    
    return {
        'success': True,
        'search_result': search_result
    }


# ==================== 文件系统工具 ====================

def list_files(directory='.', recursive=False):
    """
    列出目录下的文件
    
    Args:
        directory: 目录路径
        recursive: 是否递归列出
    
    Returns:
        str: 文件列表
    """
    try:
        files = []
        
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                level = root.replace(directory, '').count(os.sep)
                indent = ' ' * 2 * level
                files.append(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    size = os.path.getsize(filepath)
                    files.append(f"{subindent}{filename} ({format_size(size)})")
        else:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    files.append(f"📄 {filename} ({format_size(size)})")
                elif os.path.isdir(filepath):
                    files.append(f"📁 {filename}/")
        
        return "\n".join(files)
    
    except Exception as e:
        return f"❌ 列出文件失败: {str(e)}"


def format_size(bytes_size):
    """
    格式化文件大小
    
    Args:
        bytes_size: 字节数
    
    Returns:
        str: 格式化后的大小字符串
    """
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.2f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


def read_file(file_path):
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
    
    Returns:
        str: 文件内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 如果文件太大，只返回前5000字符
        if len(content) > 5000:
            return f"文件内容（前5000字符）:\n{content[:5000]}\n\n...（文件被截断，共 {len(content)} 字符）"
        
        return content
    
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
            if len(content) > 5000:
                return f"文件内容（前5000字符，GBK编码）:\n{content[:5000]}\n\n...（文件被截断）"
            return content
        except Exception as e:
            return f"❌ 读取文件失败（编码错误）: {str(e)}"
    except Exception as e:
        return f"❌ 读取文件失败: {str(e)}"


def create_file(file_path, content):
    """
    创建新文件
    
    Args:
        file_path: 文件路径
        content: 文件内容
    
    Returns:
        str: 执行结果
    """
    try:
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"✅ 文件创建成功: {file_path}"
    
    except Exception as e:
        return f"❌ 创建文件失败: {str(e)}"


def update_file(file_path, content, append=False):
    """
    更新文件内容
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
        append: 是否追加模式
    
    Returns:
        str: 执行结果
    """
    try:
        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
        
        action = "追加" if append else "覆盖"
        return f"✅ 文件{action}成功: {file_path}"
    
    except Exception as e:
        return f"❌ 更新文件失败: {str(e)}"


def rename_file(old_path, new_path):
    """
    重命名文件
    
    Args:
        old_path: 原路径
        new_path: 新路径
    
    Returns:
        str: 执行结果
    """
    try:
        os.rename(old_path, new_path)
        return f"✅ 文件重命名成功: {old_path} -> {new_path}"
    
    except Exception as e:
        return f"❌ 重命名文件失败: {str(e)}"


def delete_file(file_path):
    """
    删除文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        str: 执行结果
    """
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            return f"✅ 文件删除成功: {file_path}"
        elif os.path.isdir(file_path):
            import shutil
            shutil.rmtree(file_path)
            return f"✅ 目录删除成功: {file_path}"
        else:
            return f"❌ 文件或目录不存在: {file_path}"
    
    except Exception as e:
        return f"❌ 删除失败: {str(e)}"


def get_file_info(file_path):
    """
    获取文件信息
    
    Args:
        file_path: 文件路径
    
    Returns:
        str: 文件信息
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ 文件不存在: {file_path}"
        
        stat = os.stat(file_path)
        info = []
        info.append(f"📁 路径: {file_path}")
        info.append(f"📊 大小: {format_size(stat.st_size)}")
        info.append(f"🕐 创建时间: {datetime.fromtimestamp(stat.st_ctime)}")
        info.append(f"🕐 修改时间: {datetime.fromtimestamp(stat.st_mtime)}")
        info.append(f"🕐 访问时间: {datetime.fromtimestamp(stat.st_atime)}")
        
        if os.path.isfile(file_path):
            info.append(f"📄 类型: 文件")
        elif os.path.isdir(file_path):
            info.append(f"📁 类型: 目录")
            num_files = len(os.listdir(file_path))
            info.append(f"📂 包含: {num_files} 个文件/子目录")
        
        return "\n".join(info)
    
    except Exception as e:
        return f"❌ 获取文件信息失败: {str(e)}"


# ==================== 网络访问工具 ====================

def curl_web(url, timeout=30, method='GET', headers=None, data=None):
    """
    访问网页内容，支持多种HTTP方法和自定义请求头
    
    Args:
        url: 网页地址
        timeout: 超时时间（默认30秒）
        method: HTTP方法（GET/POST/PUT/DELETE，默认GET）
        headers: 自定义请求头（字典格式）
        data: POST请求的数据（字符串或字典）
    
    Returns:
        str: 网页内容和响应信息
    """
    try:
        start_time = time.time()
        print(f"🌐 正在访问: {url}")
        print(f"🔧 方法: {method}, 超时: {timeout}秒")
        
        # 默认请求头
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        # 合并自定义请求头
        if headers:
            default_headers.update(headers)
        
        # 处理请求数据
        request_data = None
        if data:
            if isinstance(data, dict):
                request_data = urllib.parse.urlencode(data).encode('utf-8')
            elif isinstance(data, str):
                request_data = data.encode('utf-8')
        
        # 创建请求对象
        req = urllib.request.Request(url, data=request_data, headers=default_headers, method=method)
        
        # 发送请求
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read()
            status_code = response.getcode()
            response_headers = response.info()
            
            # 尝试多种编码解码
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = content.decode('gbk')
                except UnicodeDecodeError:
                    content = content.decode('utf-8', errors='ignore')
        
        elapsed_time = time.time() - start_time
        
        # 构建结果
        result = f"✅ 访问成功 (状态码: {status_code})\n"
        result += f"⏱️ 响应时间: {elapsed_time:.2f}秒\n"
        result += f"� URL: {url}\n"
        result += f"\n📋 响应头:\n"
        result += "-" * 60 + "\n"
        
        # 添加响应头信息
        header_count = 0
        for key, value in response_headers.items():
            if header_count < 10:  # 最多显示10个响应头
                result += f"{key}: {value}\n"
                header_count += 1
        
        result += "\n� 网页内容（前5000字符）:\n"
        result += "=" * 60 + "\n"
        
        if len(content) > 5000:
            result += content[:5000] + "\n...（内容被截断，共 {} 字符）".format(len(content))
        else:
            result += content
        
        return result
    
    except urllib.error.HTTPError as e:
        return f"❌ HTTP 错误: {e.code} - {e.reason}\nURL: {url}"
    except urllib.error.URLError as e:
        return f"❌ URL 错误: {e.reason}\nURL: {url}"
    except ValueError as e:
        return f"❌ 参数错误: {str(e)}"
    except Exception as e:
        return f"❌ 访问网页失败: {str(e)}\nURL: {url}"


def download_file(url, save_path):
    """
    下载文件
    
    Args:
        url: 文件地址
        save_path: 保存路径
    
    Returns:
        str: 执行结果
    """
    try:
        print(f"📥 正在下载: {url}")
        
        # 确保目录存在
        dir_path = os.path.dirname(save_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        urllib.request.urlretrieve(url, save_path)
        
        if os.path.exists(save_path):
            size = os.path.getsize(save_path)
            return f"✅ 文件下载成功: {save_path} ({format_size(size)})"
        else:
            return f"❌ 文件下载失败"
    
    except Exception as e:
        return f"❌ 下载文件失败: {str(e)}"


def get_web_headers(url):
    """
    获取网页响应头信息
    
    Args:
        url: 网页地址
    
    Returns:
        str: 响应头信息
    """
    try:
        req = urllib.request.Request(url, method='HEAD')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            headers = response.info()
            result = ["📋 响应头信息:"]
            
            for key, value in headers.items():
                result.append(f"  {key}: {value}")
            
            return "\n".join(result)
    
    except Exception as e:
        return f"❌ 获取响应头失败: {str(e)}"


# ==================== 技能系统 ====================

def list_available_skills(skills_dir=None):
    """
    自动读取技能列表，返回所有可用技能的信息
    """
    if skills_dir is None:
        skills_dir = SKILLS_DIR
    
    skills = []
    
    try:
        if not skills_dir.exists():
            print(f"警告：技能目录不存在: {skills_dir}")
            return skills
        
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / 'SKILL.md'
                if skill_file.exists():
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if content.startswith('---'):
                        front_matter_end = content.find('---', 3)
                        if front_matter_end != -1:
                            front_matter = content[3:front_matter_end].strip()
                            skill_info = {}
                            for line in front_matter.split('\n'):
                                line = line.strip()
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    skill_info[key.strip()] = value.strip()
                            
                            if 'name' in skill_info and 'description' in skill_info:
                                skills.append({
                                    'name': skill_info['name'],
                                    'description': skill_info['description']
                                })

    except Exception as e:
        print(f"读取技能列表失败: {str(e)}")
    
    return skills


def load_skill_content(skill_name, skills_dir=None):
    """
    加载技能内容
    """
    if skills_dir is None:
        skills_dir = SKILLS_DIR
    
    skill_file = skills_dir / skill_name / 'SKILL.md'
    
    try:
        if skill_file.exists():
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.startswith('---'):
                front_matter_end = content.find('---', 3)
                if front_matter_end != -1:
                    return content[front_matter_end + 3:].strip()
            
            return content.strip()
        else:
            return f"技能 {skill_name} 不存在"
    
    except Exception as e:
        return f"加载技能失败: {str(e)}"


# ==================== 工具注册系统 ====================

def register_tools():
    """
    注册所有可用工具
    """
    global TOOLS
    
    TOOLS = {
        # 文件系统工具
        'list_files': {
            'name': 'list_files',
            'description': '列出目录下的文件',
            'parameters': {
                'directory': {'type': 'string', 'description': '目录路径', 'required': True},
                'recursive': {'type': 'boolean', 'description': '是否递归列出', 'required': False}
            },
            'function': list_files
        },
        'read_file': {
            'name': 'read_file',
            'description': '读取文件内容',
            'parameters': {
                'file_path': {'type': 'string', 'description': '文件路径', 'required': True}
            },
            'function': read_file
        },
        'create_file': {
            'name': 'create_file',
            'description': '创建新文件',
            'parameters': {
                'file_path': {'type': 'string', 'description': '文件路径', 'required': True},
                'content': {'type': 'string', 'description': '文件内容', 'required': True}
            },
            'function': create_file
        },
        'update_file': {
            'name': 'update_file',
            'description': '更新文件内容',
            'parameters': {
                'file_path': {'type': 'string', 'description': '文件路径', 'required': True},
                'content': {'type': 'string', 'description': '要写入的内容', 'required': True},
                'append': {'type': 'boolean', 'description': '是否追加模式', 'required': False}
            },
            'function': update_file
        },
        'rename_file': {
            'name': 'rename_file',
            'description': '重命名文件或目录',
            'parameters': {
                'old_path': {'type': 'string', 'description': '原路径', 'required': True},
                'new_path': {'type': 'string', 'description': '新路径', 'required': True}
            },
            'function': rename_file
        },
        'delete_file': {
            'name': 'delete_file',
            'description': '删除文件或目录',
            'parameters': {
                'file_path': {'type': 'string', 'description': '文件或目录路径', 'required': True}
            },
            'function': delete_file
        },
        'get_file_info': {
            'name': 'get_file_info',
            'description': '获取文件或目录的详细信息',
            'parameters': {
                'file_path': {'type': 'string', 'description': '文件或目录路径', 'required': True}
            },
            'function': get_file_info
        },
        # 网络工具
        'curl_web': {
            'name': 'curl_web',
            'description': '访问网页内容，支持GET/POST/PUT/DELETE等HTTP方法',
            'parameters': {
                'url': {'type': 'string', 'description': '网页地址', 'required': True},
                'timeout': {'type': 'integer', 'description': '超时时间(秒)', 'required': False},
                'method': {'type': 'string', 'description': 'HTTP方法(GET/POST/PUT/DELETE)', 'required': False},
                'headers': {'type': 'object', 'description': '自定义请求头(字典格式)', 'required': False},
                'data': {'type': 'object', 'description': 'POST请求数据(字典或字符串)', 'required': False}
            },
            'function': curl_web
        },
        'download_file': {
            'name': 'download_file',
            'description': '下载文件',
            'parameters': {
                'url': {'type': 'string', 'description': '文件地址', 'required': True},
                'save_path': {'type': 'string', 'description': '保存路径', 'required': True}
            },
            'function': download_file
        },
        'get_web_headers': {
            'name': 'get_web_headers',
            'description': '获取网页响应头信息',
            'parameters': {
                'url': {'type': 'string', 'description': '网页地址', 'required': True}
            },
            'function': get_web_headers
        }
    }


def get_all_tools():
    """
    获取所有已注册的工具列表
    """
    return TOOLS


def get_tool_definitions():
    """
    获取工具定义的 JSON 格式，用于发送给 LLM
    """
    definitions = []
    
    for tool_name, tool_info in TOOLS.items():
        params = {}
        for param_name, param_info in tool_info['parameters'].items():
            params[param_name] = {
                'type': param_info['type'],
                'description': param_info['description']
            }
        
        definitions.append({
            'name': tool_info['name'],
            'description': tool_info['description'],
            'parameters': params
        })
    
    return json.dumps(definitions, ensure_ascii=False, indent=2)


def execute_tool(tool_name, arguments):
    """
    执行工具调用
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
    
    Returns:
        工具执行结果
    """
    if tool_name not in TOOLS:
        return f"❌ 未知工具: {tool_name}"
    
    tool_info = TOOLS[tool_name]
    func = tool_info['function']
    
    try:
        # 提取参数
        params = {}
        for param_name, param_info in tool_info['parameters'].items():
            if param_info.get('required', False) and param_name not in arguments:
                return f"❌ 缺少必需参数: {param_name}"
            
            if param_name in arguments:
                params[param_name] = arguments[param_name]
        
        # 调用函数
        result = func(**params)
        return result
    
    except Exception as e:
        return f"❌ 工具执行失败: {str(e)}"


# ==================== 自动检测工具调用 ====================

def detect_tool_need(user_input):
    """
    自动检测用户输入是否需要调用工具
    
    Args:
        user_input: 用户输入
    
    Returns:
        tuple: (是否需要调用工具, 工具名称或 None, 建议参数)
    """
    user_input_lower = user_input.lower().strip()
    
    # 文件系统相关关键词
    file_keywords = {
        'list_files': ['列出', '显示', '查看', '目录', '文件列表', '有什么文件'],
        'read_file': ['读取', '查看', '打开', '内容', '文件内容'],
        'create_file': ['创建', '新建', '生成', '写一个'],
        'update_file': ['修改', '更新', '编辑', '追加'],
        'rename_file': ['重命名', '改名'],
        'delete_file': ['删除', '移除'],
        'get_file_info': ['信息', '属性', '详细信息']
    }
    
    # 网络相关关键词
    web_keywords = {
        'curl_web': ['访问', '打开', '浏览', '网页', '网站', '网址'],
        'download_file': ['下载', '保存', '获取'],
        'get_web_headers': ['响应头', 'headers']
    }
    
    # 检查文件工具
    for tool_name, keywords in file_keywords.items():
        for keyword in keywords:
            if keyword in user_input_lower:
                # 尝试提取路径参数
                args = extract_path_from_input(user_input)
                return True, tool_name, args
    
    # 检查网络工具
    for tool_name, keywords in web_keywords.items():
        for keyword in keywords:
            if keyword in user_input_lower:
                # 尝试提取URL参数
                args = extract_url_from_input(user_input)
                return True, tool_name, args
    
    return False, None, None


def extract_path_from_input(user_input):
    """
    从用户输入中提取文件路径
    
    Args:
        user_input: 用户输入
    
    Returns:
        dict: 包含路径参数的字典
    """
    import re
    
    args = {}
    
    # 匹配路径模式
    path_patterns = [
        r'([A-Za-z]:[\\/][^"\'<>|*?\n]+)',  # Windows 路径
        r'(\.[\\/][^"\'<>|*?\n]+)',          # 相对路径
        r'(\/[^"\'<>|*?\n]+)',               # Unix 路径
        r'([\w-]+\.(txt|md|py|json|csv|doc|docx|pdf))'  # 常见文件名
    ]
    
    for pattern in path_patterns:
        matches = re.findall(pattern, user_input)
        if matches:
            path = matches[0]
            if isinstance(path, tuple):
                path = path[0]
            args['file_path'] = path.strip()
            args['directory'] = os.path.dirname(path.strip()) if os.path.dirname(path.strip()) else '.'
            break
    
    # 如果没有找到路径，尝试提取目录名
    if not args:
        dir_keywords = ['当前目录', '当前文件夹', '这里', '此目录', '本目录']
        for keyword in dir_keywords:
            if keyword in user_input:
                args['directory'] = '.'
                break
    
    return args


def extract_url_from_input(user_input):
    """
    从用户输入中提取URL
    
    Args:
        user_input: 用户输入
    
    Returns:
        dict: 包含URL参数的字典
    """
    import re
    
    args = {}
    
    # 匹配 URL 模式
    url_pattern = r'https?://[^\s"\'<>|]+'
    matches = re.findall(url_pattern, user_input)
    
    if matches:
        args['url'] = matches[0]
    
    return args


# ==================== 链式调用上下文管理器 ====================

class ChainedCallContext:
    """
    链式调用上下文管理器
    用于在多个工具调用之间传递数据和状态
    """
    
    def __init__(self, max_iterations=10):
        self.max_iterations = max_iterations
        self.iteration = 0
        self.history = []
        self.variables = {}
        self.user_request = ""
        self.final_answer = None
    
    def add_step(self, tool_name, arguments, result):
        """添加一步工具调用记录"""
        self.iteration += 1
        self.history.append({
            'iteration': self.iteration,
            'tool_name': tool_name,
            'arguments': arguments,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        # 自动提取有用的变量
        self._extract_variables(result)
    
    def _extract_variables(self, result):
        """从工具执行结果中提取有用的变量"""
        import re
        
        # 提取文件路径
        path_pattern = r'([A-Za-z]:[\\/][^\s]+)'
        paths = re.findall(path_pattern, str(result))
        if paths:
            self.set_variable('last_file_path', paths[-1])
        
        # 提取URL
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, str(result))
        if urls:
            self.set_variable('last_url', urls[-1])
    
    def set_variable(self, name, value):
        """设置中间变量"""
        self.variables[name] = value
    
    def get_variable(self, name, default=None):
        """获取中间变量"""
        return self.variables.get(name, default)
    
    def is_max_iterations_reached(self):
        """判断是否达到最大迭代次数"""
        return self.iteration >= self.max_iterations
    
    def get_history_summary(self):
        """获取历史记录摘要"""
        if not self.history:
            return "尚未执行任何步骤。"
        
        summary = "已执行的步骤：\n"
        for step in self.history:
            summary += f"步骤 {step['iteration']}: 调用工具 '{step['tool_name']}'\n"
            summary += f"  参数: {json.dumps(step['arguments'], ensure_ascii=False)}\n"
            result_str = str(step['result'])
            if len(result_str) > 150:
                result_str = result_str[:150] + "..."
            summary += f"  结果: {result_str}\n"
        
        return summary
    
    def get_context_json(self):
        """获取上下文的 JSON 表示"""
        return json.dumps({
            'iteration': self.iteration,
            'max_iterations': self.max_iterations,
            'history': self.history,
            'variables': self.variables
        }, ensure_ascii=False, indent=2)


def build_analysis_prompt(user_request, context):
    """
    构建分析提示词
    
    Args:
        user_request: 用户原始请求
        context: ChainedCallContext 实例
    
    Returns:
        str: 分析提示词
    """
    tools_json = get_tool_definitions()
    
    prompt = f"""你是一个智能助手，需要根据用户请求和已执行的步骤历史，决定下一步操作。

用户原始请求：
{user_request}

{context.get_history_summary()}

当前可用的中间变量：
{json.dumps(context.variables, ensure_ascii=False, indent=2)}

可用工具列表：
{tools_json}

决策规则：
1. 分析用户请求和已执行的步骤，判断任务是否已完成
2. 如果任务已完成，直接给出最终回答
3. 如果任务未完成，选择合适的工具继续执行
4. 工具调用可以链式进行，前一个工具的输出可以作为后一个工具的输入
5. 优先使用已获取的中间变量，避免重复操作
6. 最多执行 {context.max_iterations} 步，请高效完成任务

【重要】输出格式要求：
- 必须且只能输出有效的 JSON 格式
- 不要在 JSON 前后添加任何解释性文字
- 不要使用 Markdown 代码块标记（如 ```json）
- 直接输出 JSON 对象

任务完成时的 JSON 格式：
{{
  "done": true,
  "answer": "最终回答内容"
}}

需要继续调用工具时的 JSON 格式：
{{
  "done": false,
  "tool_call": {{
    "name": "工具名称",
    "arguments": {{
      "参数名": "参数值"
    }}
  }}
}}

请严格按照上述 JSON 格式输出，不要包含任何其他内容。"""
    
    return prompt


def execute_chained_tool_call(env_vars, user_request):
    """
    执行链式工具调用的完整流程
    
    Args:
        env_vars: 环境变量字典
        user_request: 用户请求
    
    Returns:
        dict: 执行结果
    """
    print("\n" + "=" * 60)
    print("🔗 开始执行自动链式工具调用")
    print("=" * 60)
    print(f"用户请求: {user_request}")
    print("=" * 60)
    
    context = ChainedCallContext(max_iterations=10)
    context.user_request = user_request
    
    messages = [
        {"role": "system", "content": "你是一个智能助手，能够进行链式工具调用。"}
    ]
    
    for iteration in range(context.max_iterations):
        print(f"\n--- 第 {iteration + 1} 轮迭代 ---")
        
        analysis_prompt = build_analysis_prompt(user_request, context)
        
        decision_messages = messages + [
            {"role": "user", "content": analysis_prompt}
        ]
        
        print("🧠 正在分析下一步操作...")
        result = call_llm_api(env_vars, decision_messages)
        
        if not result['success']:
            print(f"❌ LLM 调用失败: {result['error']}")
            return {
                'success': False,
                'error': f"LLM 调用失败: {result['error']}"
            }
        
        decision_content = result['content'].strip()
        print(f"📝 LLM 决策结果:\n{decision_content}")
        
        # 检查返回内容是否为空
        if not decision_content:
            print(f"⚠️ LLM 返回空内容，尝试重新请求...")
            # 添加更明确的提示
            retry_messages = messages + [
                {"role": "user", "content": analysis_prompt + "\n\n重要：请务必返回有效的 JSON 格式，不要返回空内容。"}
            ]
            retry_result = call_llm_api(env_vars, retry_messages)
            
            if not retry_result['success']:
                return {
                    'success': False,
                    'error': f"LLM 重试失败: {retry_result['error']}"
                }
            
            decision_content = retry_result['content'].strip()
            print(f"📝 重试后的 LLM 决策结果:\n{decision_content}")
            
            if not decision_content:
                return {
                    'success': False,
                    'error': 'LLM 返回空内容，无法继续执行'
                }
        
        # 解析决策
        try:
            decision = json.loads(decision_content)
        except json.JSONDecodeError as e:
            print(f"⚠️ 解析 JSON 失败: {e}")
            print(f"原始内容: {repr(decision_content[:200])}")
            
            # 尝试提取 JSON
            start_idx = decision_content.find('{')
            end_idx = decision_content.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                try:
                    json_str = decision_content[start_idx:end_idx]
                    print(f"提取的 JSON: {json_str}")
                    decision = json.loads(json_str)
                except json.JSONDecodeError as e2:
                    return {
                        'success': False,
                        'error': f"无法解析 LLM 响应: {e2}\n内容: {decision_content[:200]}"
                    }
            else:
                return {
                    'success': False,
                    'error': f"无法解析 LLM 响应，未找到有效的 JSON 格式\n内容: {decision_content[:200]}"
                }
        
        # 判断任务是否完成
        if decision.get('done', False):
            final_answer = decision.get('answer', '')
            print(f"\n✅ 任务完成!")
            print(f"最终回答:\n{final_answer}")
            return {
                'success': True,
                'answer': final_answer,
                'context': context.get_context_json(),
                'iterations': iteration + 1
            }
        
        # 需要继续调用工具
        tool_call = decision.get('tool_call', {})
        tool_name = tool_call.get('name', '')
        arguments = tool_call.get('arguments', {})
        
        if not tool_name:
            print("❌ 工具名称为空")
            return {
                'success': False,
                'error': '工具名称为空'
            }
        
        print(f"🔧 准备调用工具: {tool_name}")
        print(f"📋 参数: {json.dumps(arguments, ensure_ascii=False)}")
        
        # 执行工具调用
        tool_result = execute_tool(tool_name, arguments)
        
        # 记录到上下文
        context.add_step(tool_name, arguments, tool_result)
        
        messages.append({
            "role": "system",
            "content": f"工具调用结果 - {tool_name}: {str(tool_result)[:500]}..."
        })
        
        print(f"✅ 工具执行完成")
    
    print(f"\n⚠️ 已达到最大迭代次数 ({context.max_iterations})")
    return {
        'success': False,
        'error': f"达到最大迭代次数 {context.max_iterations}，任务未完成",
        'context': context.get_context_json(),
        'iterations': context.max_iterations
    }


# ==================== 主程序 ====================

def print_header():
    """打印欢迎信息"""
    print("\n" + "=" * 60)
    print("Practice07 [优化版]: 智能助手 - 自动工具调用")
    print("=" * 60)
    print("\n功能特性:")
    print("   📁 文件系统访问: 自动检测并执行文件操作")
    print("   🌐 网络资源访问: 自动访问网页和下载文件")
    print("   ⚡ 链式工具调用: 自动执行多步骤任务")
    print("   🧠 智能决策: LLM 自主决定下一步操作")
    print("\n使用说明:")
    print("   - 直接描述你的需求，系统会自动判断是否需要调用工具")
    print("   - 支持的操作: 列出文件、读取文件、创建文件、访问网页等")
    print("   - 输入 '/chain 请求' 强制使用链式调用模式")
    print("   - 输入 '/search 查询内容' 搜索聊天历史")
    print("   - 输入 'clear' 清空聊天历史")
    print("   - 输入 'history' 查看聊天历史")
    print("   - 输入 'tools' 列出所有可用工具")
    print("   - 输入 'skills' 列出所有可用技能")
    print("   - 按 Ctrl+C 退出程序")
    print("=" * 60 + "\n")


def print_available_tools():
    """打印所有可用工具"""
    print("\n" + "=" * 60)
    print("📋 可用工具列表")
    print("=" * 60)
    
    tools = get_all_tools()
    
    for tool_name, tool_info in tools.items():
        print(f"\n🔧 {tool_name}")
        print(f"   描述: {tool_info['description']}")
        print(f"   参数:")
        for param_name, param_info in tool_info['parameters'].items():
            required = " (必需)" if param_info.get('required', False) else ""
            print(f"      - {param_name} ({param_info['type']}){required}: {param_info['description']}")
    
    print("\n" + "=" * 60 + "\n")


def print_available_skills():
    """打印所有可用技能"""
    print("\n" + "=" * 60)
    print("📚 可用技能列表")
    print("=" * 60)
    
    skills = list_available_skills()
    
    if not skills:
        print("   暂无可用技能")
    else:
        for skill in skills:
            print(f"\n🎯 {skill['name']}")
            print(f"   描述: {skill['description']}")
    
    print("\n" + "=" * 60 + "\n")


def main():
    """主函数"""
    global conversation_history, system_prompt
    
    # 初始化全局变量
    init_global_vars()
    
    print_header()
    
    # 加载环境变量
    print("⚙️ 正在加载环境变量...")
    env_vars = load_env_file()
    
    if not env_vars:
        print("❌ 无法加载环境变量，请检查 .env 文件")
        return
    
    print(f"✅ 已加载配置:")
    print(f"   Base URL: {env_vars.get('LLM_BASE_URL', '未设置')}")
    print(f"   Model: {env_vars.get('LLM_MODEL', '未设置')}")
    print(f"   Timeout: {env_vars.get('LLM_TIMEOUT', '3600')} 秒\n")
    
    # 加载技能列表
    print("📚 正在加载技能列表...")
    skills = list_available_skills()
    print(f"✅ 已加载 {len(skills)} 个技能")
    
    # 初始化系统提示词
    tools_json = get_tool_definitions()
    skills_json = json.dumps({"skills": skills}, ensure_ascii=False, indent=2)
    
    system_prompt = f"""你是一个智能助手，能够自动调用工具完成任务。

可用工具列表：
{tools_json}

可用技能列表：
{skills_json}

自动工具调用规则：
1. 当用户请求需要执行具体操作时，自动选择合适的工具
2. 支持链式调用：前一个工具的输出可以作为后一个工具的输入
3. 最多执行5步，请高效完成任务
4. 任务完成后给出清晰的总结回答

请输出详细的思考过程，然后使用工具调用或直接回答。"""
    
    conversation_history = [
        {"role": "system", "content": system_prompt}
    ]
    
    chat_round_counter = 0
    KEY_INFO_EXTRACT_INTERVAL = 5
    
    print("🚀 开始聊天（按 Ctrl+C 退出）:")
    print("=" * 60 + "\n")
    
    try:
        while True:
            try:
                user_input = input("你: ").strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() == 'clear':
                    conversation_history = [{"role": "system", "content": system_prompt}]
                    print("\n✅ 聊天历史已清空\n")
                    continue
                elif user_input.lower() == 'history':
                    print("\n" + "=" * 60)
                    print("聊天历史")
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
                    continue
                elif user_input.lower() == 'tools':
                    print_available_tools()
                    continue
                elif user_input.lower() == 'skills':
                    print_available_skills()
                    continue
                elif user_input.lower() in ['quit', 'exit', '退出']:
                    print("\n👋 再见！")
                    break
                
                # 检查是否是链式调用请求
                if user_input.lower().startswith('/chain'):
                    chain_request = user_input[6:].strip()
                    if not chain_request:
                        print("请提供链式调用的请求内容，格式: /chain 你的请求")
                        continue
                    
                    result = execute_chained_tool_call(env_vars, chain_request)
                    
                    if result['success']:
                        print(f"\n🎉 链式调用完成!")
                        print(f"最终回答:\n{result['answer']}")
                        print(f"迭代次数: {result['iterations']}")
                    else:
                        print(f"\n❌ 链式调用失败: {result['error']}")
                    
                    continue
                
                # 检查是否是搜索请求
                if user_input.lower().startswith('/search'):
                    search_query = user_input[7:].strip()
                    if not search_query:
                        print("请提供搜索查询内容")
                        continue
                    
                    search_result = search_chat_history(env_vars, search_query)
                    
                    if search_result['success']:
                        print(f"\n🔍 搜索结果:\n{search_result['search_result']}\n")
                    else:
                        print(f"\n❌ 搜索失败: {search_result['error']}\n")
                    
                    continue
                
                # 自动检测是否需要调用工具
                need_tool, tool_name, suggested_args = detect_tool_need(user_input)
                
                if need_tool:
                    print(f"\n🤖 检测到需要调用工具: {tool_name}")
                    if suggested_args:
                        print(f"💡 建议参数: {json.dumps(suggested_args, ensure_ascii=False)}")
                    
                    # 使用链式调用执行
                    result = execute_chained_tool_call(env_vars, user_input)
                    
                    if result['success']:
                        print(f"\n🎯 任务完成!")
                        print(f"回答:\n{result['answer']}")
                    else:
                        print(f"\n❌ 工具调用失败: {result['error']}")
                    
                    conversation_history.append({"role": "user", "content": user_input})
                    conversation_history.append({"role": "assistant", "content": result.get('answer', '工具调用失败')})
                    chat_round_counter += 1
                    continue
                
                # 检查是否需要总结
                need_summarize, reason = should_summarize(conversation_history)
                if need_summarize:
                    print(f"\n📝 触发总结: {reason}")
                    summarize_result = summarize_chat_history(env_vars, conversation_history)
                    if summarize_result['success']:
                        conversation_history = summarize_result['messages']
                
                # 普通聊天请求
                conversation_history.append({"role": "user", "content": user_input})
                
                print("🤖 AI: ", end='', flush=True)
                assistant_response = ""
                
                for chunk in call_llm_api_stream(env_vars, conversation_history):
                    print(chunk, end='', flush=True)
                    assistant_response += chunk
                
                print("\n")
                
                conversation_history.append({"role": "assistant", "content": assistant_response})
                
                chat_round_counter += 1
                
                if chat_round_counter % KEY_INFO_EXTRACT_INTERVAL == 0:
                    key_info_result = extract_key_info(env_vars, conversation_history)
                    if key_info_result['success']:
                        save_key_info_to_log(key_info_result['key_info'])
            
            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {str(e)}")
    
    except KeyboardInterrupt:
        print("\n\n👋 再见！")


if __name__ == "__main__":
    conversation_history = []
    system_prompt = ""
    main()