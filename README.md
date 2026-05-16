# Chess Agent

国际象棋教学 Demo：人类执白（鼠标操作）vs AI 执黑，或者观看 Auto Play 教学局。
项目采用 **Stockfish + DeepSeek 混合架构**：由最强引擎 Stockfish 负责绝对精确的棋局计算，再由 DeepSeek 大模型将复杂的战术翻译成儿童能听懂的中文解说。

## 项目结构

```
chess-agent/
├── main.py               # 主程序（pygame 棋盘 + AI 对手 + 侧边栏）
├── board_serializer.py   # 棋局状态序列化（→ 大模型可读文本）
├── deepseek_client.py    # DeepSeek API 客户端
├── chess_agent.py        # 棋局分析 Agent（混合架构编排模块）
├── config.yaml           # 配置文件（含 API Key，不提交 Git）
├── config.example.yaml   # 配置文件示例
├── requirements.txt      # Python 依赖
├── readme.md             # 本文件
├── claude.md             # 工程规范与设计文档
└── stockfish/            # Stockfish 引擎（已自带）
    └── stockfish         # macOS Apple Silicon 二进制
```

## 依赖安装

建议在 Conda 环境中运行：

```bash
conda create -n chess-agent python=3.13
conda activate chess-agent
pip install -r requirements.txt
```

或者手动安装：

```bash
pip install pygame python-chess pyyaml openai stockfish
```

## 🎓 Python 初学者学习指南（代码观看顺序）

如果你是 Python 初学者，建议按照由浅入深的顺序阅读本项目代码。代码中已经贴心地标注了 `【Python 学习要点】`，你可以全局搜索这个关键词。

**第一步：[deepseek_client.py](deepseek_client.py)（入门级）**
*   **字数最少，逻辑最简单**。
*   **学习目标**：掌握 Python 如何读取本地文件（`with open`）、如何处理异常（`try...except`）防止程序崩溃，以及如何使用别人写好的包（`openai` SDK）发送网络请求。

**第二步：[board_serializer.py](board_serializer.py)（进阶级）**
*   **纯数据处理，没有复杂的交互**。
*   **学习目标**：掌握 Python 核心数据结构（列表 `List`、字典 `Dict`）、`for` 循环、字符串格式化（`f-string`），以及写出优雅代码的利器——列表推导式（List Comprehension）。

**第三步：[chess_agent.py](chess_agent.py)（应用级）**
*   **把前两步的功能组合起来**，属于业务逻辑的“大脑”。
*   **学习目标**：学习模块化编程（如何 `import` 其他文件）、如何处理外部返回的 JSON 数据（`json.loads` 和字典的 `.get()` 方法），以及多行字符串（Prompt）的编写。

**第四步：[main.py](main.py)（挑战级）**
*   **全项目最长、最复杂的文件**，包含 UI 渲染、动画、和并发处理。
*   **学习目标**：理解游戏开发的灵魂（**Game Loop 事件循环**）、掌握**多线程 (Threading)**（让后台思考和前台动画同时进行不卡顿），以及了解算法中经典的**递归 (Recursion)**思想。

## 配置 DeepSeek Agent

1. 复制配置文件：

```bash
cp config.example.yaml config.yaml
```

2. 编辑 `config.yaml`，填写你的 DeepSeek API Key：

```yaml
deepseek:
  api_key: "sk-你的真实API-Key"
  base_url: "https://api.deepseek.com"
  model_name: "deepseek-v4-flash"
```

> 如果你还没有 DeepSeek API Key，请前往 [platform.deepseek.com](https://platform.deepseek.com) 注册获取。

## 运行

```bash
python main.py
```

## 玩法模式

启动后可以选择以下 4 种模式：

| 难度 | 搜索深度 | 说明 |
|------|---------|------|
| Beginner | 2 | 内置 α-β 引擎，适合入门 |
| Normal | 3 | Stockfish Lv10 |
| Master | 4 | Stockfish Lv20（特级大师水平） |
| **Auto Play** | 混合 | **观赏教学模式**：白方由 AI 托管（最强算力+解说），黑方为 Stockfish Lv5 陪练 |

### 人类对战模式 (Beginner / Normal / Master)
1. 白方（人类）：鼠标点击选中棋子 → 再点目标格走子
2. 黑方（AI）：自动走子，带滑动动画
3. **AI 老师互动**：在对局中点击右侧输入框，输入你的问题（如：“下一步该怎么走？”或者简单的“你好”）。AI 老师会在右侧面板为你进行流式（逐字打出）的分析解说。
4. **悔棋功能**：下错棋了？点击右侧的红色“悔棋”按钮，系统会自动智能撤销上一步操作。
5. **滚动查看**：如果 AI 老师的解说太长，可以将鼠标移动到侧边栏区域并滑动滚轮，上下翻阅解说记录。

### 自动教学模式 (Auto Play)
1. 完全解放双手，像看直播一样观看对局。
2. 轮到白方时，系统会自动请求 AI 老师进行局势分析。
3. 右侧面板会实时显示**推荐走法**、**儿童易懂的战术解释**、**多步计划**和**战术警告**。
4. 解说展示后会停留 6 秒钟供你阅读，然后白方自动执行最优走法。

## 核心技术：混合架构 (Hybrid Architecture)

本项目解决了一般大语言模型“算力不足、容易产生幻觉”的问题：
1. **左脑（逻辑区） - Stockfish 16.1**：在后台静默运行，计算当前局面的绝对评分、发现战术漏洞，并给出 100% 合法且最优的走法。
2. **右脑（语言区） - DeepSeek V4**：接收 Stockfish 的绝对真理，发挥 LLM 强大的语言组织能力，把枯燥的数学评分和 UCI 符号，翻译成生动、亲切、有教育意义的中文解说（采用 Generator 流式输出，响应极速）。
