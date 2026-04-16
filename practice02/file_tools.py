import os
import stat
from pathlib import Path
import time

def list_directory_files(directory):
    """
    列出目录下的文件信息
    
    Args:
        directory (str): 目录路径
        
    Returns:
        dict: 包含文件信息的字典
    """
    try:
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            return {
                "success": False,
                "error": f"目录不存在或不是有效目录: {directory}"
            }
        
        files_info = []
        for item in dir_path.iterdir():
            item_stat = item.stat()
            file_info = {
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
                "size": item_stat.st_size,
                "mode": stat.filemode(item_stat.st_mode),
                "mtime": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item_stat.st_mtime)),
                "atime": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item_stat.st_atime))
            }
            files_info.append(file_info)
        
        return {
            "success": True,
            "files": files_info
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"列出目录文件时出错: {str(e)}"
        }

def rename_file(directory, old_name, new_name):
    """
    修改文件名字
    
    Args:
        directory (str): 目录路径
        old_name (str): 旧文件名
        new_name (str): 新文件名
        
    Returns:
        dict: 操作结果
    """
    try:
        old_path = Path(directory) / old_name
        new_path = Path(directory) / new_name
        
        if not old_path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {old_path}"
            }
        
        if new_path.exists():
            return {
                "success": False,
                "error": f"新文件名已存在: {new_path}"
            }
        
        old_path.rename(new_path)
        return {
            "success": True,
            "message": f"文件已成功重命名: {old_name} -> {new_name}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"重命名文件时出错: {str(e)}"
        }

def delete_file(directory, file_name):
    """
    删除文件
    
    Args:
        directory (str): 目录路径
        file_name (str): 文件名
        
    Returns:
        dict: 操作结果
    """
    try:
        file_path = Path(directory) / file_name
        
        if not file_path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }
        
        if file_path.is_dir():
            return {
                "success": False,
                "error": f"无法删除目录: {file_path}"
            }
        
        file_path.unlink()
        return {
            "success": True,
            "message": f"文件已成功删除: {file_name}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"删除文件时出错: {str(e)}"
        }

def create_file(directory, file_name, content):
    """
    新建文件并写入内容
    
    Args:
        directory (str): 目录路径
        file_name (str): 文件名
        content (str): 文件内容
        
    Returns:
        dict: 操作结果
    """
    try:
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            return {
                "success": False,
                "error": f"目录不存在或不是有效目录: {directory}"
            }
        
        file_path = dir_path / file_name
        if file_path.exists():
            return {
                "success": False,
                "error": f"文件已存在: {file_path}"
            }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"文件已成功创建: {file_name}",
            "path": str(file_path)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"创建文件时出错: {str(e)}"
        }

def read_file(directory, file_name):
    """
    读取文件内容
    
    Args:
        directory (str): 目录路径
        file_name (str): 文件名
        
    Returns:
        dict: 包含文件内容的字典
    """
    try:
        file_path = Path(directory) / file_name
        
        if not file_path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }
        
        if file_path.is_dir():
            return {
                "success": False,
                "error": f"无法读取目录: {file_path}"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "path": str(file_path),
            "size": file_path.stat().st_size
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"读取文件时出错: {str(e)}"
        }

# 测试代码
if __name__ == "__main__":
    test_dir = "."
    
    print("测试列出目录文件:")
    result = list_directory_files(test_dir)
    print(result)
    
    print("\n测试创建文件:")
    result = create_file(test_dir, "test.txt", "Hello, World!")
    print(result)
    
    print("\n测试读取文件:")
    result = read_file(test_dir, "test.txt")
    print(result)
    
    print("\n测试重命名文件:")
    result = rename_file(test_dir, "test.txt", "test_renamed.txt")
    print(result)
    
    print("\n测试删除文件:")
    result = delete_file(test_dir, "test_renamed.txt")
    print(result)