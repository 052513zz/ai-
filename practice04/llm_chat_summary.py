"""
Practice04: 聊天记录总结功能
当聊天超过5轮或上下文长度超过3k后，自动触发LLM执行聊天记录总结
对前70%左右的内容进行压缩，最后30%左右保留原文
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
    
    Args:
        messages: 消息列表
    
    Returns:
        int: 上下文字符串总长度
    """
    total_length = 0
    for msg in messages:
        total_length += len(msg.get('content', ''))
    return total_length


def count_conversation_rounds(messages):
    """
    计算对话轮数（排除系统消息）
    
    Args:
        messages: 消息列表
    
    Returns:
        int: 对话轮数
    """
    rounds = 0
    for msg in messages:
        if msg.get('role') == 'user':
            rounds += 1
    return rounds


def should_summarize(messages, max_rounds=5, max_length=3000):
    """
    判断是否需要执行聊天记录总结
    
    Args:
        messages: 消息列表
        max_rounds: 最大对话轮数（默认5轮）
        max_length: 最大上下文字符长度（默认3000）
    
    Returns:
        tuple: (是否需要总结, 原因)
    """
    # 排除系统消息
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
    
    Args:
        env_vars: 环境变量字典
        messages: 消息列表
    
    Returns:
        dict: 总结结果
    """
    print("\n" + "=" * 60)
    print("📝 检测到聊天历史过长，正在执行总结压缩...")
    print("=" * 60)
    
    # 计算需要保留的消息
    total_messages = len(messages)
    
    # 计算分割点（前70%压缩，保留后30%）
    # 但至少保留系统消息和前1-2条消息
    system_messages = [msg for msg in messages if msg.get('role') == 'system']
    non_system_messages = [msg for msg in messages if msg.get('role') != 'system']
    
    # 保留最后30%的消息
    preserve_count = max(1, len(non_system_messages) // 3)
    preserved_messages = non_system_messages[-preserve_count:]
    messages_to_summarize = non_system_messages[:-preserve_count]
    
    print(f"\n📊 总结统计:")
    print(f"   总消息数: {total_messages}")
    print(f"   系统消息: {len(system_messages)}")
    print(f"   需要压缩: {len(messages_to_summarize)}")
    print(f"   保留原文: {len(preserved_messages)}")
    
    # 构建总结提示
    summarize_prompt = f"""请总结以下对话内容，生成一个简洁的摘要。

需要总结的对话内容：
{json.dumps(messages_to_summarize, ensure_ascii=False, indent=2)}

请按照以下格式总结：
1. 对话主题：
2. 关键信息：
3. 用户需求：
4. 重要结论：

摘要应该简洁明了，便于后续对话参考。"""
    
    # 调用 LLM 进行总结
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
    
    # 构建压缩后的消息列表
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


def print_header():
    """
    打印欢迎信息
    """
    print("\n" + "=" * 60)
    print("🚀 Practice04: 聊天记录总结功能")
    print("=" * 60)
    print("\n💡 提示:")
    print("   - 当聊天超过5轮或上下文长度超过3k时，自动执行总结")
    print("   - 前70%左右的内容会被压缩，最后30%保留原文")
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
当聊天历史较长时，系统会自动对其进行压缩总结，以便保持对话的连贯性。"""
    
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
