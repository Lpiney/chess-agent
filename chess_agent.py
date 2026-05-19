"""
chess_agent.py — 国际象棋教学 Agent
=====================================
组合 board_serializer（棋局→文本） + deepseek_client（调用 DeepSeek API），
实现完整的棋局分析流程：
  1. 读取当前棋局状态
  2. 构造 system prompt + user prompt
  3. 先调用 Stockfish 计算最佳走法
  4. 再调用 DeepSeek 生成教学解说
  5. 解析模型返回的标签文本
  5. 用 python-chess 验证推荐走法是否合法
  6. 返回结构化分析结果

【Python 学习要点】：
1. 模块组合 (Module Composition)：将不同功能的 Python 文件导入并组合使用。
   - 应用场景：当项目变大时，千万不要把所有代码写在一个文件里。按功能拆分成多个模块（如 UI、网络、数据处理）然后组装，是工程化开发的基础。
2. 文本解析：从带标签的文本里提取字段。
   - 应用场景：当外部系统返回的不是标准 JSON，而是固定格式文本时，可以用正则或字符串处理把信息拆出来。
3. 字典取值 (Dictionary `.get()`): 深入学习如何使用 `.get()` 方法安全获取数据并提供默认值。
   - 应用场景：当你处理从外部（如大模型、网络请求）返回的数据时，你永远不能 100% 确定某个字段一定存在，用 `.get()` 可以避免程序因为找不到字段而崩溃。
"""

import os
import re
import chess
import board_serializer
import deepseek_client

# ==================== Stockfish 引擎路径 ====================
_STOCKFISH_LOCAL = os.path.join(os.path.dirname(__file__), "stockfish_bin", "stockfish")
STOCKFISH_PATH = (
    _STOCKFISH_LOCAL
    if os.path.exists(_STOCKFISH_LOCAL)
    else "/opt/homebrew/bin/stockfish"
)

# ==================== 系统提示词（System Prompt） ====================
# 这是给 DeepSeek 模型的"人设"和"规则"。
# 模型会根据这段提示词来决定如何回复用户的棋局问题。
# 定位：一位教小孩子下棋的老师，用语简单、亲切。
#
# 【Python 学习要点】：多行字符串 (Multi-line Strings) 使用三个引号 `"""`。
#   - 应用场景：编写大段的说明文字、构建发送给大模型的 Prompt 提示词、或者编写函数的详细注释文档（Docstring）。
SYSTEM_PROMPT = """You are a warm, encouraging, and playful chess teacher, and your students are children just starting to learn chess.
Please explain things in simple, friendly, and lively Chinese to help them understand the position and suggest the next move.
When the user says hello or asks non-chess questions, respond with a warm and cute greeting (like "你好呀！我是你的国际象棋老师，准备好和我一起下棋了吗？"), but STILL provide the chess analysis if a board state is provided.

You will receive complete board information, AND you will also receive the absolute correct analysis from Stockfish (the world's strongest chess engine), including:
- Stockfish evaluation (advantage/disadvantage in centipawns or mate)
- Stockfish best move (UCI format)
- A visual board (Unicode pieces, UPPERCASE=White, lowercase=Black)
- Natural language piece location descriptions
- Move history, legal moves list, and position status

Look at the board carefully and use the Stockfish analysis as the absolute truth. Your job is to translate Stockfish's mathematical analysis into a friendly, educational explanation for a child.

Rules:
1. First, identify whose turn it is (White or Black).
2. The recommended move MUST be exactly the Stockfish best move.
3. best_move_uci must use UCI format, e.g. e2e4, g1f3.
4. best_move_san must include a parenthetical explanation so kids understand. Examples:
   "e4 (白方小兵从 e2 走到 e4)", "Nf3 (白方骑士从 g1 跳到 f3)",
   "O-O (王车易位 — 国王躲进安全的角落)". Keep it friendly and in Chinese.
5. Explain WHY Stockfish chose this move in simple, playful Chinese. Use metaphors! For example, "controlling the center" is "占领棋盘的大操场", "protecting a piece" is "给小伙伴当保镖", "preparing an attack" is "偷偷准备一个小陷阱".
6. Do NOT use jargon like "centipawns", "engine evaluation", "alpha-beta". Just say things like "白方现在优势很大" (White has a big advantage) or "这步棋非常安全" (This move is very safe).
7. tactical_warnings: only list real dangers in Chinese based on the evaluation (e.g. if the score drops significantly or if the king is under attack). Use an empty array if none.
8. position_summary: use conversational, encouraging Chinese to summarize who is winning or if it's an even game, based on the Stockfish score. ALWAYS start with a direct response to the user's input (e.g. if they say "你好", start with "你好呀！现在的局势是...").
9. plan: a simple 2-3 step plan in kid-friendly Chinese, building upon the best move. Example: "第一步，把 e4 的兵推到中心。第二步，出动骑士到 f3 保护它。最后，王车易位把国王藏到安全的 g1 格子里。这样你的棋子就准备好进攻啦！"

You must output your response in the following EXACT text format using these tags (Do NOT use JSON, just output the plain text with tags):

[UCI] e2e4
[SAN] e4 (白方小兵从 e2 走到 e4)
[TURN] white (or black)
[SUMMARY] 热情地回应用户的输入，并一句话总结当前局势（谁占优）
[EXPLANATION] 用生动可爱、带比喻的话解释这步棋的好处，最多3句话
[PLAN] 一个2-3步的简单计划，用孩子能听懂的话，最多3句话
[WARNINGS] 战术警告1 | 战术警告2 (如果没有警告，请填写"无")
"""

# ==================== 文本解析工具 ====================


def _extract_tags(raw_response: str) -> dict:
    """
    从流式或完整的文本中提取带标签的字段。
    """
    result = {}

    def extract(tag):
        # 匹配 [TAG] 后面的内容，直到下一个 [ 或者字符串结尾
        pattern = rf"\[{tag}\](.*?)(?=\n\[|$)"
        m = re.search(pattern, raw_response, re.DOTALL)
        return m.group(1).strip() if m else None

    result["best_move_uci"] = extract("UCI")
    result["best_move_san"] = extract("SAN")
    result["side_to_move"] = extract("TURN")
    result["position_summary"] = extract("SUMMARY")
    result["child_explanation"] = extract("EXPLANATION")
    result["plan"] = extract("PLAN")

    warns = extract("WARNINGS")
    if warns and warns != "无":
        result["tactical_warnings"] = [w.strip() for w in warns.split("|") if w.strip()]
    else:
        result["tactical_warnings"] = []

    return result


# ==================== 走法验证 ====================


def _validate_move(board: chess.Board, uci_str: str) -> dict:
    """
    用 python-chess 验证 UCI 格式的走法是否在当前棋局中合法。
    这是安全检查：防止模型"编造"不存在的走法。

    【Python 学习要点】：
    - 异常捕获机制: 使用 `except Exception as e` 可以捕获所有未知的错误，保证程序不会因为大模型输出的奇怪内容而崩溃。
    """
    # 检查是否为空字符串
    if not uci_str:
        return {
            "is_legal": False,
            "message": "best_move_uci 为空，无法验证。",
            "move": None,
        }

    # 尝试将字符串解析为走法对象
    try:
        move = chess.Move.from_uci(uci_str)
    except chess.InvalidMoveError:
        return {
            "is_legal": False,
            "message": f"UCI 格式无效: {uci_str}",
            "move": None,
        }
    except Exception as e:
        return {
            "is_legal": False,
            "message": f"UCI 解析异常: {e}",
            "move": None,
        }

    # 检查这个走法是不是合法的走法之一
    if move in board.legal_moves:
        san = board.san(move)
        return {
            "is_legal": True,
            "message": f"模型推荐走法合法: {uci_str} / {san}",
            "move": move,
            "san": san,
        }
    else:
        return {
            "is_legal": False,
            "message": f"模型推荐走法 {uci_str} 不在当前合法走法列表中。",
            "move": move,
        }


def _build_stockfish_analysis(board: chess.Board) -> tuple[str, str | None]:
    """
    调用 Stockfish，并把分析结果整理成追加到 prompt 的文本。
    返回值：
    - analysis_text: 给大模型看的补充说明
    - error_msg: 如果调用失败，返回错误信息
    """
    engine = None
    try:
        from stockfish import Stockfish

        engine = Stockfish(path=STOCKFISH_PATH)
        engine.set_fen_position(board.fen())
        engine.set_depth(15)

        best_move = engine.get_best_move()
        evaluation = engine.get_evaluation()
        top_moves = engine.get_top_moves(3)

        analysis_lines = [
            "",
            "",
            "[STOCKFISH ANALYSIS (ABSOLUTE TRUTH)]",
            f"- Best move: {best_move}",
        ]

        if evaluation["type"] == "cp":
            score = evaluation["value"] / 100.0
            analysis_lines.append(
                "- Evaluation: "
                f"{score} (positive=White advantage, negative=Black advantage)"
            )
        elif evaluation["type"] == "mate":
            analysis_lines.append(f"- Evaluation: Mate in {evaluation['value']} moves")

        analysis_lines.append("- Top candidate moves:")
        for index, move_info in enumerate(top_moves, 1):
            centipawn = move_info.get("Centipawn")
            mate = move_info.get("Mate")
            score_text = (
                f"Centipawn: {centipawn}"
                if centipawn is not None
                else f"Mate: {mate}"
            )
            analysis_lines.append(f"  {index}. {move_info['Move']} ({score_text})")

        return "\n".join(analysis_lines), None
    except Exception as exc:
        return "", f"Stockfish 引擎调用失败，无法进行棋局分析: {exc}"
    finally:
        if engine is not None:
            del engine


def _build_agent_error_result(serialized: dict, error_msg: str) -> dict:
    """
    构造统一的失败返回值，避免异常分支里重复拼字典。
    """
    return {
        "raw_response": "",
        # 这里沿用 parsed_json 这个字段名，是为了兼容现有 UI 调用。
        "parsed_json": None,
        "json_parse_error": error_msg,
        "best_move_uci": None,
        "best_move_san": None,
        "is_legal": False,
        "validation_message": error_msg,
        "candidate_moves": [],
        "position_summary": "抱歉，算力引擎掉线了，我没法帮你看棋了。",
        "child_explanation": "哎呀，我的超级大脑(Stockfish)罢工了，现在算不出准确的走法，请检查一下配置哦！",
        "plan": "",
        "tactical_warnings": [],
        "serialized_board": serialized,
    }


# ==================== Agent 主入口 ====================


def ask_chess_agent(
    board: chess.Board,
    user_question: str,
    move_history: list = None,
    config: dict = None,
    stream_callback=None,
) -> dict:
    """
    棋局分析 Agent 的主入口函数。一次调用完成整个分析流程。

    【Python 学习要点】：
    - `del` 关键字：手动删除对象以释放内存，在 finally 块中使用可以确保执行。
      - 应用场景：当你启动了一个外部程序（如这个项目中的 Stockfish 引擎），或者打开了一个大文件，在不用时一定要释放它，防止电脑卡死。
    - `try...finally`: 无论 try 块是否出错，finally 块都会执行，常用于资源清理。
      - 应用场景：数据库操作完毕后必须断开连接；或者锁定某个文件后，不管操作成没成功都必须解锁。
    """
    # ---- 1. 加载配置 ----
    if config is None:
        config = deepseek_client.load_config()

    # ---- 2. 序列化棋局 → 构造 prompt ----
    serialized = board_serializer.serialize_board(board, move_history, config)
    user_prompt = board_serializer.build_user_prompt(serialized, user_question)

    # ---- 3. 调用 Stockfish 引擎进行绝对准确的计算 ----
    stockfish_analysis, error_msg = _build_stockfish_analysis(board)
    if error_msg is not None:
        print(f"[Agent] Error: {error_msg}")
        return _build_agent_error_result(serialized, error_msg)

    user_prompt += stockfish_analysis

    # ---- 4. 调用 DeepSeek API ----
    client = deepseek_client.create_client(config)

    raw_response = ""
    for chunk in deepseek_client.chat_completion(
        client=client,
        config=config,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    ):
        raw_response += chunk
        if stream_callback:
            parsed_tags = _extract_tags(raw_response)
            partial_result = {
                "parsed_json": parsed_tags,
                "best_move_uci": parsed_tags.get("best_move_uci"),
                "best_move_san": parsed_tags.get("best_move_san"),
                "is_legal": None,
            }
            stream_callback(partial_result)

    # ---- 5. 解析最终文本 ----
    parsed_tags = _extract_tags(raw_response)
    parse_error = None

    # ---- 6. 提取关键字段 ----
    # 给定默认值
    best_move_uci = None
    best_move_san = None
    is_legal = None
    validation_message = None
    candidate_moves = []
    position_summary = ""
    child_explanation = ""
    plan = ""
    tactical_warnings = []

    if parsed_tags is not None:
        # 使用 dict.get() 安全地获取键值。如果键不存在，则返回指定的默认值。
        best_move_uci = parsed_tags.get("best_move_uci")
        best_move_san = parsed_tags.get("best_move_san")
        # 当前标签格式没有返回候选走法，这里保留字段是为了兼容现有展示结构。
        candidate_moves = parsed_tags.get("candidate_moves", [])
        position_summary = parsed_tags.get("position_summary", "")
        child_explanation = parsed_tags.get("child_explanation", "")
        plan = parsed_tags.get("plan", "")
        tactical_warnings = parsed_tags.get("tactical_warnings", [])

        # ---- 7. 验证推荐走法是否合法 ----
        if best_move_uci:
            validation = _validate_move(board, best_move_uci)
            is_legal = validation["is_legal"]
            validation_message = validation["message"]

            # 逻辑或 (or): 如果 best_move_san 是空的，就用 validation["san"]
            if validation.get("san"):
                best_move_san = best_move_san or validation["san"]
        else:
            validation_message = "模型没有返回可验证的 UCI 走法。"
    else:
        validation_message = f"模型输出无法解析为标签文本。解析错误: {parse_error}"

    # 返回组装好的完整结果字典
    return {
        "raw_response": raw_response,
        # 为了兼容现有 UI，这里继续沿用 parsed_json 这个键名。
        "parsed_json": parsed_tags,
        "json_parse_error": parse_error,
        "best_move_uci": best_move_uci,
        "best_move_san": best_move_san,
        "is_legal": is_legal,
        "validation_message": validation_message,
        "candidate_moves": candidate_moves,
        "position_summary": position_summary,
        "child_explanation": child_explanation,
        "plan": plan,
        "tactical_warnings": tactical_warnings,
        "serialized_board": serialized,
    }


# ==================== 结果格式化输出 ====================


def print_agent_result(result: dict) -> None:
    """
    将结果格式化打印到 Terminal。

    【Python 学习要点】：
    - `print(f"...")`: f-string 可以让你很方便地格式化输出。
      - 应用场景：需要向控制台打印带变量的调试信息时，比如 `print(f"用户 {name} 登录成功，当前时间是 {time}")`，写起来比拼接字符串爽得多。
    """
    print("\n" + "=" * 60)
    print("  ♟️  DeepSeek 棋局分析 Agent")
    print("=" * 60)

    fen = result.get("serialized_board", {}).get("fen", "N/A")
    print(f"\n📋 当前棋局 FEN:\n  {fen}")

    print("\n🎯 模型推荐走法:")
    if result["best_move_uci"]:
        print(f"  UCI: {result['best_move_uci']}")
        print(f"  SAN: {result.get('best_move_san', 'N/A')}")
    else:
        print("  (模型未返回推荐走法)")

    print("\n✅ 合法性验证:")
    # 嵌套的三元运算符
    legality_text = (
        "是"
        if result["is_legal"]
        else ("否" if result["is_legal"] is False else "无法判断")
    )
    print(f"  合法: {legality_text}")
    print(f"  说明: {result['validation_message']}")

    if result["is_legal"] is False and result["best_move_uci"]:
        print(f"\n⚠️  警告：模型返回了非法走法: {result['best_move_uci']}")
        print("  当前合法走法包括:")
        legal_moves = result.get("serialized_board", {}).get("legal_moves", [])
        for m in legal_moves[:20]:  # 切片：最多显示前 20 条
            print(f"    {m}")
        if len(legal_moves) > 20:
            print(f"    ... 还有 {len(legal_moves) - 20} 条")

    if result.get("position_summary"):
        print(f"\n📊 局势总结:\n  {result['position_summary']}")

    if result.get("child_explanation"):
        print(f"\n🧒 给孩子听得懂的解释:\n  {result['child_explanation']}")

    if result.get("plan"):
        print(f"\n🗺️  建议计划:\n  {result['plan']}")

    candidates = result.get("candidate_moves", [])
    if candidates:
        print("\n📋 候选走法:")
        # enumerate(list, 1) 表示从 1 开始计数
        for i, cm in enumerate(candidates, 1):
            print(f"  {i}. {cm.get('move_uci', '?')} / {cm.get('move_san', '?')}")
            if cm.get("reason"):
                print(f"     理由: {cm['reason']}")
            if cm.get("risk"):
                print(f"     风险: {cm['risk']}")

    warnings = result.get("tactical_warnings", [])
    if warnings:
        print("\n⚠️  战术警告:")
        for w in warnings:
            print(f"  - {w}")

    if result.get("json_parse_error"):
        print("\n⚠️  标签解析失败，以下为模型原始回复:")
        print("---")
        print(result.get("raw_response", "(空)"))
        print("---")

    print("\n" + "=" * 60)
    print("  注意: Agent 只做分析建议，不会自动替你走棋。")
    print("=" * 60 + "\n")


# ==================== 侧边栏展示数据提取 ====================


def format_kid_display(result: dict) -> dict:
    """
    提取关键信息，返回适合侧边栏展示的简化字典。
    """
    info = {
        "side_to_move": "white",
        "best_move_san": "",
        "best_move_uci": "",
        "child_explanation": "",
        "plan": "",
        "tactical_warnings": [],
        "is_legal": result.get("is_legal"),
    }

    parsed = result.get("parsed_json")
    if parsed is not None:
        info["side_to_move"] = parsed.get("side_to_move", "white")
        # 巧妙利用 or 来做后备：如果前面是空的，就用后面的
        info["best_move_san"] = (
            parsed.get("best_move_san") or result.get("best_move_san") or ""
        )
        info["best_move_uci"] = (
            parsed.get("best_move_uci") or result.get("best_move_uci") or ""
        )

        # 将热情的回应（summary）和解释（explanation）合并，展示给小孩子
        summary = parsed.get("position_summary") or ""
        explanation = parsed.get("child_explanation") or ""

        if summary and explanation:
            info["child_explanation"] = f"{summary}\n{explanation}"
        elif summary:
            info["child_explanation"] = summary
        else:
            info["child_explanation"] = explanation

        info["plan"] = parsed.get("plan") or ""
        info["tactical_warnings"] = parsed.get("tactical_warnings") or []
    else:
        # 标签解析失败时的降级处理
        info["best_move_san"] = result.get("best_move_san") or ""
        info["best_move_uci"] = result.get("best_move_uci") or ""
        info["child_explanation"] = result.get("child_explanation") or ""
        info["plan"] = result.get("plan") or ""

    # 如果模型没返回 child_explanation，用 position_summary 替代
    if not info["child_explanation"] and parsed:
        ps = parsed.get("position_summary", "")
        if ps:
            info["child_explanation"] = ps

    return info
