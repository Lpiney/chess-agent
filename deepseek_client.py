"""
deepseek_client.py — DeepSeek API 客户端
=========================================
使用 OpenAI 兼容的 SDK 调用 DeepSeek Chat Completion API。
因为 DeepSeek 的 API 和 OpenAI 的接口格式完全一样，
所以我们可以直接用官方的 openai 这个 Python 包来调用。

【Python 学习要点】：
1. 模块导入 (Imports)：`os` 和 `sys` 是 Python 标准库，用于处理文件路径和系统退出等。
   - 应用场景：几乎所有需要和操作系统打交道的代码，比如读取本地文件、获取当前目录、或者在发生严重错误时直接退出程序。
2. 异常处理 (Exception Handling)：通过 `try...except` 块来防止程序因为网络或密钥错误直接崩溃。
   - 应用场景：任何不可控的外部操作（如请求网络、读取用户文件、连接数据库）。使用它可以让程序在出错时给出友好的提示，而不是直接闪退。
"""

import os
import sys
import yaml
from openai import OpenAI

# 自动获取当前文件所在的目录，并拼接出 config.yaml 的绝对路径
# __file__ 是 Python 的内置变量，代表当前脚本的文件名
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


# ==================== 配置加载 ====================


def _exit_with_message(*lines: str) -> None:
    """
    打印配置错误信息，然后退出程序。
    把重复的 print + sys.exit(1) 收拢到一个地方，更容易维护。
    """
    for line in lines:
        print(line)
    sys.exit(1)


def load_config(config_path: str = None) -> dict:
    """
    加载 config.yaml 配置文件，返回完整配置字典。

    【Python 学习要点】：
    - `with open(...) as f:` 这是一个上下文管理器。它可以确保文件在读取完毕后自动关闭，防止内存泄漏。
      - 应用场景：当你需要打开文件、连接数据库、或者获取锁等需要“用完即还”的资源时，它是最佳实践。
    - `sys.exit(1)`: 如果发生致命错误，立即退出程序。`1` 代表异常退出。
      - 应用场景：在程序启动时检查必备条件（如缺少配置文件、缺少 API Key），如果不满足则没必要继续运行。
    """
    # 如果调用时没传路径，就使用默认的 CONFIG_PATH
    path = config_path or CONFIG_PATH

    # 检查配置文件是否存在
    if not os.path.exists(path):
        _exit_with_message(
            "请先创建 config.yaml，并填写 DeepSeek API Key。",
            "可以参考 config.example.yaml 创建。",
        )

    # 读取 YAML 文件
    with open(path, "r", encoding="utf-8") as f:
        # 使用 safe_load 将 yaml 文件内容解析为 Python 字典
        config = yaml.safe_load(f)

    # 检查内容是否为空
    if config is None:
        _exit_with_message("config.yaml 内容为空，请填写配置。")

    # 获取深层字典中的值时，推荐使用 .get() 连续调用以防止 KeyError
    api_key = config.get("deepseek", {}).get("api_key", "")
    if not api_key or api_key == "在这里填写你的 DeepSeek API Key":
        _exit_with_message("DeepSeek API Key 为空，请先在 config.yaml 中填写 api_key。")

    return config


# ==================== 客户端创建 ====================


def create_client(config: dict) -> OpenAI:
    """
    根据配置字典创建 OpenAI 兼容客户端。
    因为传入了 base_url 指向 DeepSeek，所以实际上调用的是 DeepSeek。
    """
    ds_config = config["deepseek"]
    return OpenAI(
        api_key=ds_config["api_key"],
        base_url=ds_config["base_url"],
        timeout=ds_config.get("timeout", 60),  # 如果没有设置 timeout，默认给 60 秒
    )


# ==================== 对话补全 ====================


def chat_completion(
    client: OpenAI,
    config: dict,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    调用 API，发送对话并获取模型回复。

    【Python 学习要点】：
    - 字典列表：`messages` 是一个包含多个字典的列表，用于表示对话历史。
      - 应用场景：API 请求和响应中最常见的数据结构，非常适合表示结构化的列表数据（如多轮对话、商品列表等）。
    - `in` 关键字：可以用来判断字符串是否包含某个子串（如 `"timeout" in error_msg.lower()`）。
      - 应用场景：判断一个元素是否在列表里、或者一个单词是否在一句话里。非常直观。
    - 大语言模型调用：注意参数如 temperature (控制回答的随机性) 和 max_tokens (控制回答长度)。
    """
    # 从配置中提取模型参数，使用 .get() 提供安全默认值
    ds_config = config["deepseek"]
    model_name = ds_config.get("model_name", "deepseek-v4-flash")
    temperature = ds_config.get("temperature", 0.3)
    max_tokens = ds_config.get("max_tokens", 1500)

    # 构造消息列表（包含系统设定和用户输入）
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        # 发送网络请求，调用大模型 (开启 stream=True)
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        # 如果请求失败（比如没网、超时等），捕获异常并返回友好的中文提示
        raw_error = str(e)
        error_msg = raw_error.lower()
        if "timeout" in error_msg or "timed out" in error_msg:
            yield "[错误] API 调用超时。请检查网络连接或增加 config.yaml 中的 timeout 值。"
        elif "connection" in error_msg:
            yield f"[错误] 网络连接失败，请检查网络。详细信息: {raw_error}"
        elif "api_key" in error_msg or "authentication" in error_msg:
            yield f"[错误] API Key 认证失败，请检查 config.yaml 中的 api_key。详细信息: {raw_error}"
        else:
            yield f"[错误] API 调用发生未知错误: {raw_error}"
