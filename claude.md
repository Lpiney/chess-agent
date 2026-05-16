# Chess Agent 项目规范

## 项目概述

一个面向儿童的国际象棋教学 Demo，使用 pygame 构建棋盘界面。人类执白（鼠标操作）对战 AI 执黑，同时集成 **Stockfish + DeepSeek 混合架构**作为 AI 老师，提供绝对精确的棋局分析和生动易懂的走法建议。支持 Auto Play 纯观赏教学模式。

## 项目目的

该项目是为python初学者学习而设计的，通过一个实际的项目象棋教学，帮助初学者理解python的基本语法和编程思想。并同时培养编程者使用AI辅助编程的能力

## 工程规范

因为该项目是给初学者学习python所设计，所有的代码应该尽可能的简单简洁，并有中文注释，方便初学者学习理解。

## 技术栈

- **Python 3.13+**
- **pygame** — 棋盘渲染、交互、动画
- **python-chess** — 棋局状态管理、走法合法性验证
- **Stockfish** — 核心算力引擎，负责计算最佳走法和局势评分
- **DeepSeek API**（通过 `openai` SDK 兼容接口调用）— 语言解说引擎，将数学评分转化为中文教学
- **PyYAML** — 配置文件解析

## 项目结构

```
chess-agent/
├── main.py               # 主程序入口（pygame 界面 + 侧边栏 + AI 对手）
├── chess_agent.py         # 混合架构 Agent（Stockfish 算棋 + DeepSeek 解说）
├── board_serializer.py    # 棋局状态序列化（→ 大模型可读文本）
├── deepseek_client.py     # DeepSeek API 客户端
├── config.yaml            # 配置文件（含 API Key，不提交 Git）
├── config.example.yaml    # 配置文件示例
├── requirements.txt       # Python 依赖
├── claude.md              # 本文件：工程规范
├── readme.md              # 使用说明
└── stockfish/             # Stockfish 引擎二进制（已内置）
    └── stockfish          # macOS Apple Silicon 二进制
```
