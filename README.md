# Python AI智能体开发学习项目

## 项目简介

这是一个基于Python的AI智能体开发学习项目，旨在帮助学习者了解如何使用Python标准库与OpenAI兼容协议的LLM（大语言模型）进行交互。

## 目录结构

```
trae111/
├── practice01/              # 练习目录1：基础LLM交互
│   ├── __init__.py          # Python包初始化文件
│   ├── llm_client.py        # LLM客户端实现（基础版）
│   └── llm_chat.py          # LLM聊天客户端（高级版，支持流式输出和历史记录）
├── practice02/              # 练习目录2：工具调用功能
│   ├── __init__.py          # Python包初始化文件
│   ├── file_tools.py        # 文件操作工具函数
│   └── llm_toolcall.py      # LLM工具调用客户端
├── venv/                    # 虚拟环境
├── .env                     # 环境变量文件（用户创建）
├── .env.example             # 环境变量模板
├── .gitignore               # Git忽略文件
├── requirements.txt         # 项目依赖
└── README.md                # 项目说明文档
```

## Python代码功能用途

### 1. practice01/llm_client.py

**功能用途**：
- 读取项目根目录的.env文件，获取LLM配置信息
- 使用Python标准HTTP库（urllib）访问OpenAI兼容协议的LLM
- 发送用户输入的消息并获取LLM的响应
- 统计并显示token消耗、响应时间和token处理速度

**实现的教学目标**：
- 学习如何使用Python标准库处理HTTP请求
- 了解OpenAI API的请求格式和响应结构
- 学习如何读取和解析环境变量文件
- 掌握基本的错误处理和异常捕获
- 学习如何进行性能统计和数据分析
- 了解LLM的token消耗机制

### 2. practice01/llm_chat.py

**功能用途**：
- 支持终端界面输入聊天内容
- 支持流式输出LLM响应（逐字显示）
- 支持历史聊天记录自动添加到上下文
- 循环运行直到用户按Ctrl+C退出
- 显示token消耗、响应时间和处理速度统计

**实现的教学目标**：
- 学习如何实现流式API调用
- 了解如何管理和维护聊天历史记录
- 掌握终端交互和用户输入处理
- 学习如何处理KeyboardInterrupt等异常
- 了解如何实现循环聊天界面
- 掌握流式数据处理和实时显示

### 3. practice01/__init__.py

**功能用途**：
- 使practice01成为一个Python包，便于模块导入

**实现的教学目标**：
- 了解Python包的基本结构和初始化

### 4. practice02/file_tools.py

**功能用途**：
- 实现5个文件操作工具函数：
  1. `list_directory_files`：列出目录下的文件及其属性
  2. `rename_file`：重命名文件
  3. `delete_file`：删除文件
  4. `create_file`：创建文件并写入内容
  5. `read_file`：读取文件内容

**实现的教学目标**：
- 学习Python文件系统操作
- 掌握Pathlib库的使用
- 了解文件属性获取和处理
- 学习异常处理和错误提示
- 掌握函数设计和返回值规范

### 5. practice02/llm_toolcall.py

**功能用途**：
- 基于LLM实现工具调用功能
- 支持将文件操作工具作为系统提示词发送给LLM
- 解析LLM的工具调用请求并执行相应的文件操作
- 显示工具执行结果并获取LLM的最终响应
- 支持循环聊天直到用户按Ctrl+C退出

**实现的教学目标**：
- 学习如何实现LLM工具调用
- 了解系统提示词的设计和使用
- 掌握JSON解析和处理
- 学习如何将工具结果反馈给LLM
- 了解AI智能体的工具使用模式
- 掌握复杂交互流程的设计

## 环境配置

1. **创建虚拟环境**：
   ```bash
   python -m venv venv
   ```

2. **激活虚拟环境**：
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**：
   - 复制`env.example`为`.env`文件
   - 填写正确的LLM配置信息：
     ```
     LLM_BASE_URL=https://api.example.com/v1
     LLM_MODEL=gpt-3.5-turbo
     LLM_API_KEY=your_api_key_here
     ```

## 使用方法

### 方法1：运行基础版LLM客户端（单次交互）

1. **运行LLM客户端**：
   ```bash
   python practice01/llm_client.py
   ```

2. **输入消息**：
   - 程序启动后，会提示输入要发送给LLM的消息
   - 输入消息后按回车发送
   - 输入`quit`退出程序

3. **查看结果**：
   - 程序会显示LLM的响应内容
   - 同时显示统计信息，包括：
     - 输入Token数
     - 输出Token数
     - 总Token数
     - 响应时间
     - Token处理速度

### 方法2：运行高级版聊天客户端（流式输出+历史记录）

1. **运行聊天客户端**：
   ```bash
   python practice01/llm_chat.py
   ```

2. **开始聊天**：
   - 程序启动后，会显示配置信息
   - 输入消息后按回车发送
   - LLM会流式输出响应（逐字显示）
   - 聊天历史会自动添加到上下文中
   - 按Ctrl+C退出程序

3. **查看结果**：
   - 程序会实时显示LLM的响应内容
   - 每个回合结束后显示统计信息，包括：
     - 总Token数
     - 响应时间
     - Token处理速度
     - 当前历史记录消息数

### 方法3：运行工具调用客户端

1. **运行工具调用客户端**：
   ```bash
   python practice02/llm_toolcall.py
   ```

2. **使用工具**：
   - 程序启动后，会显示配置信息和支持的工具列表
   - 输入文件操作相关的请求，例如：
     - "列出当前目录下的文件"
     - "在当前目录创建一个名为test.txt的文件，内容为Hello World"
     - "读取当前目录下的test.txt文件内容"
     - "将test.txt重命名为example.txt"
     - "删除当前目录下的example.txt文件"
   - LLM会生成工具调用请求并执行相应的文件操作
   - 按Ctrl+C退出程序

3. **查看结果**：
   - 程序会显示LLM的响应和工具执行结果
   - 每个回合结束后显示统计信息，包括：
     - 总Token数
     - 响应时间
     - Token处理速度
     - 当前历史记录消息数

## 教学价值

1. **API调用实践**：学习如何通过HTTP请求与LLM API进行交互，包括流式API调用
2. **环境配置管理**：了解如何使用环境变量文件管理敏感配置
3. **性能分析**：学习如何统计和分析API调用的性能指标
4. **错误处理**：掌握基本的异常处理和错误提示，包括KeyboardInterrupt处理
5. **模块化设计**：了解如何组织Python项目结构
6. **流式数据处理**：学习如何处理和显示流式数据
7. **聊天历史管理**：了解如何维护和使用聊天上下文
8. **终端交互**：掌握终端界面的用户输入处理
9. **循环程序设计**：学习如何设计持续运行的程序

## 扩展建议

1. **添加更多LLM功能**：如流式响应、多轮对话等
2. **实现不同的模型提供商**：支持多种LLM服务
3. **添加缓存机制**：减少重复请求的API调用
4. **构建更复杂的AI智能体**：结合其他工具和API
5. **添加测试用例**：确保代码的可靠性

## 注意事项

- 请保护好您的API密钥，不要将其提交到版本控制系统
- 注意API调用的频率限制和token消耗
- 确保网络连接正常，以避免API调用失败
- 对于大型项目，考虑使用更高级的HTTP库如requests

---

**作者**：AI智能体开发学习项目
**日期**：2026-04-09