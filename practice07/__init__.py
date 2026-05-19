"""
Practice07: 链式工具调用 - 优化版
自动检测工具调用、自动加载技能、增强文件系统和网络访问能力
"""

from .llm_chat_analyzer import (
    # 核心类
    ChainedCallContext,
    
    # 链式调用函数
    execute_chained_tool_call,
    build_analysis_prompt,
    
    # 工具注册和执行
    register_tools,
    get_all_tools,
    get_tool_definitions,
    execute_tool,
    
    # 自动检测工具调用
    detect_tool_need,
    extract_path_from_input,
    extract_url_from_input,
    
    # 技能系统
    list_available_skills,
    load_skill_content,
    
    # 文件系统工具
    list_files,
    read_file,
    create_file,
    update_file,
    rename_file,
    delete_file,
    get_file_info,
    
    # 网络工具
    curl_web,
    download_file,
    get_web_headers,
    
    # 环境配置
    load_env_file,
    
    # 聊天历史和总结
    summarize_chat_history,
    extract_key_info,
    save_key_info_to_log,
    search_chat_history
)

__all__ = [
    'ChainedCallContext',
    'execute_chained_tool_call',
    'build_analysis_prompt',
    'register_tools',
    'get_all_tools',
    'get_tool_definitions',
    'execute_tool',
    'detect_tool_need',
    'extract_path_from_input',
    'extract_url_from_input',
    'list_available_skills',
    'load_skill_content',
    'list_files',
    'read_file',
    'create_file',
    'update_file',
    'rename_file',
    'delete_file',
    'get_file_info',
    'curl_web',
    'download_file',
    'get_web_headers',
    'load_env_file',
    'summarize_chat_history',
    'extract_key_info',
    'save_key_info_to_log',
    'search_chat_history'
]