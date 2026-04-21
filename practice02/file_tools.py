"""
Practice02: 文件操作工具
实现 6 个基本的文件操作和网络访问功能，供 LLM 工具调用使用
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path


def list_files(directory):
    """
    列出某个目录下的所有文件（包括文件的基本属性、大小等信息）
    
    Args:
        directory: 目录路径
    
    Returns:
        dict: 包含文件列表和每个文件信息的字典
    """
    try:
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return {
                'success': False,
                'error': f'目录不存在: {directory}'
            }
        
        if not dir_path.is_dir():
            return {
                'success': False,
                'error': f'路径不是目录: {directory}'
            }
        
        files_info = []
        
        for item in dir_path.iterdir():
            try:
                stat = item.stat()
                files_info.append({
                    'name': item.name,
                    'path': str(item),
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': stat.st_size if item.is_file() else 0,
                    'size_human': format_size(stat.st_size) if item.is_file() else 'N/A',
                    'modified': stat.st_mtime
                })
            except Exception as e:
                files_info.append({
                    'name': item.name,
                    'path': str(item),
                    'type': 'error',
                    'error': str(e)
                })
        
        return {
            'success': True,
            'directory': directory,
            'count': len(files_info),
            'files': files_info
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'列出文件失败: {str(e)}'
        }


def rename_file(directory, old_name, new_name):
    """
    修改某个目录下某个文件的名字
    
    Args:
        directory: 目录路径
        old_name: 原文件名
        new_name: 新文件名
    
    Returns:
        dict: 操作结果
    """
    try:
        dir_path = Path(directory)
        old_path = dir_path / old_name
        new_path = dir_path / new_name
        
        if not old_path.exists():
            return {
                'success': False,
                'error': f'文件不存在: {old_name}'
            }
        
        if new_path.exists():
            return {
                'success': False,
                'error': f'目标文件已存在: {new_name}'
            }
        
        old_path.rename(new_path)
        
        return {
            'success': True,
            'message': f'文件重命名成功: {old_name} -> {new_name}',
            'old_path': str(old_path),
            'new_path': str(new_path)
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'重命名失败: {str(e)}'
        }


def delete_file(directory, filename):
    """
    删除某个目录下的某个文件
    
    Args:
        directory: 目录路径
        filename: 文件名
    
    Returns:
        dict: 操作结果
    """
    try:
        dir_path = Path(directory)
        file_path = dir_path / filename
        
        if not file_path.exists():
            return {
                'success': False,
                'error': f'文件不存在: {filename}'
            }
        
        if file_path.is_dir():
            return {
                'success': False,
                'error': f'路径是目录，不是文件: {filename}'
            }
        
        file_path.unlink()
        
        return {
            'success': True,
            'message': f'文件删除成功: {filename}',
            'deleted_path': str(file_path)
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'删除失败: {str(e)}'
        }


def create_file(directory, filename, content=''):
    """
    在某个目录下新建一个文件，并写入内容
    
    Args:
        directory: 目录路径
        filename: 文件名
        content: 文件内容（可选，默认为空）
    
    Returns:
        dict: 操作结果
    """
    try:
        dir_path = Path(directory)
        file_path = dir_path / filename
        
        if not dir_path.exists():
            return {
                'success': False,
                'error': f'目录不存在: {directory}'
            }
        
        if file_path.exists():
            return {
                'success': False,
                'error': f'文件已存在: {filename}'
            }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'success': True,
            'message': f'文件创建成功: {filename}',
            'file_path': str(file_path),
            'content_length': len(content)
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'创建文件失败: {str(e)}'
        }


def read_file(directory, filename):
    """
    读取某个目录下的某个文件的内容
    
    Args:
        directory: 目录路径
        filename: 文件名
    
    Returns:
        dict: 操作结果和文件内容
    """
    try:
        dir_path = Path(directory)
        file_path = dir_path / filename
        
        if not file_path.exists():
            return {
                'success': False,
                'error': f'文件不存在: {filename}'
            }
        
        if not file_path.is_file():
            return {
                'success': False,
                'error': f'路径不是文件: {filename}'
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            'success': True,
            'file_path': str(file_path),
            'content': content,
            'content_length': len(content),
            'line_count': content.count('\n') + 1 if content else 0
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'读取文件失败: {str(e)}'
        }


def curl_web(url):
    """
    通过 curl 访问网页并返回网页内容
    
    Args:
        url: 网页 URL
    
    Returns:
        dict: 操作结果和网页内容
    """
    try:
        # 验证 URL 格式
        if not url.startswith(('http://', 'https://')):
            return {
                'success': False,
                'error': f'URL 格式不正确，必须以 http:// 或 https:// 开头'
            }
        
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 创建请求
        req = urllib.request.Request(url, headers=headers)
        
        # 发送请求
        with urllib.request.urlopen(req, timeout=30) as response:
            # 获取响应内容
            content = response.read().decode('utf-8', errors='ignore')
            
            # 获取响应头信息
            content_type = response.headers.get('Content-Type', 'text/plain')
            content_length = len(content)
            
            return {
                'success': True,
                'url': url,
                'content': content,
                'content_length': content_length,
                'content_type': content_type,
                'status_code': response.getcode()
            }
    
    except urllib.error.HTTPError as e:
        return {
            'success': False,
            'error': f'HTTP 错误 {e.code}: {e.reason}',
            'url': url
        }
    
    except urllib.error.URLError as e:
        return {
            'success': False,
            'error': f'URL 错误: {e.reason}',
            'url': url
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'访问网页失败: {str(e)}',
            'url': url
        }


def format_size(size_bytes):
    """
    格式化文件大小为人类可读格式
    
    Args:
        size_bytes: 文件大小（字节）
    
    Returns:
        str: 格式化后的文件大小
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f'{size_bytes:.2f} {unit}'
        size_bytes /= 1024.0
    return f'{size_bytes:.2f} TB'


def get_tool_definition():
    """
    获取工具定义，用于发送给 LLM
    
    Returns:
        str: 工具定义的 JSON 字符串
    """
    tools = {
        "list_files": {
            "description": "列出某个目录下的所有文件（包括文件的基本属性、大小等信息）",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "目录路径"
                    }
                },
                "required": ["directory"]
            }
        },
        "rename_file": {
            "description": "修改某个目录下某个文件的名字",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "目录路径"
                    },
                    "old_name": {
                        "type": "string",
                        "description": "原文件名"
                    },
                    "new_name": {
                        "type": "string",
                        "description": "新文件名"
                    }
                },
                "required": ["directory", "old_name", "new_name"]
            }
        },
        "delete_file": {
            "description": "删除某个目录下的某个文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "目录路径"
                    },
                    "filename": {
                        "type": "string",
                        "description": "文件名"
                    }
                },
                "required": ["directory", "filename"]
            }
        },
        "create_file": {
            "description": "在某个目录下新建一个文件，并写入内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "目录路径"
                    },
                    "filename": {
                        "type": "string",
                        "description": "文件名"
                    },
                    "content": {
                        "type": "string",
                        "description": "文件内容（可选）"
                    }
                },
                "required": ["directory", "filename"]
            }
        },
        "read_file": {
            "description": "读取某个目录下的某个文件的内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "目录路径"
                    },
                    "filename": {
                        "type": "string",
                        "description": "文件名"
                    }
                },
                "required": ["directory", "filename"]
            }
        },
        "curl_web": {
            "description": "通过 curl 访问网页并返回网页内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "网页 URL（必须以 http:// 或 https:// 开头）"
                    }
                },
                "required": ["url"]
            }
        }
    }
    
    return json.dumps(tools, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("📁 文件操作工具测试")
    print("=" * 60)
    
    # 测试列出文件
    print("\n1. 测试列出当前目录文件:")
    result = list_files(".")
    if result['success']:
        print(f"✅ 成功列出 {result['count']} 个项目")
        for file_info in result['files'][:5]:
            print(f"   - {file_info['name']} ({file_info['type']}, {file_info['size_human']})")
    else:
        print(f"❌ 失败: {result['error']}")
    
    # 测试创建文件
    print("\n2. 测试创建文件:")
    result = create_file(".", "test_file.txt", "这是一个测试文件")
    print(f"{'✅' if result['success'] else '❌'} {result.get('message', result.get('error'))}")
    
    # 测试读取文件
    print("\n3. 测试读取文件:")
    result = read_file(".", "test_file.txt")
    if result['success']:
        print(f"✅ 文件内容: {result['content']}")
    else:
        print(f"❌ 失败: {result['error']}")
    
    # 测试重命名文件
    print("\n4. 测试重命名文件:")
    result = rename_file(".", "test_file.txt", "test_file_renamed.txt")
    print(f"{'✅' if result['success'] else '❌'} {result.get('message', result.get('error'))}")
    
    # 测试删除文件
    print("\n5. 测试删除文件:")
    result = delete_file(".", "test_file_renamed.txt")
    print(f"{'✅' if result['success'] else '❌'} {result.get('message', result.get('error'))}")
