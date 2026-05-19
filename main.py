"""
main.py — 国际象棋教学游戏主程序
=====================================
面向儿童的国际象棋 Demo，使用 pygame 构建。
功能：
  - 人类执白（鼠标点击走子） vs AI 执黑（内置引擎或 Stockfish）
  - 右侧常驻「AI 老师」侧边栏，随时向 DeepSeek 大模型提问
  - 难度选择、走子动画、棋局高亮、坐标标签
  - 点击侧边栏输入框激活 AI 老师

【Python 学习要点】：
1. 模块化编程 (Modular Programming)：主程序通过 `import` 调用其他文件。
   - 应用场景：构建任何非玩具级别的项目。把复杂系统拆分成独立文件（如积木一样），需要时拼装起来。
2. 事件循环 (Event Loop)：`while game_active` 是游戏开发的核心结构。
   - 应用场景：不仅是游戏，像 PyQt 做桌面软件、甚至是 Node.js 这种后端框架的底层，也是靠“事件循环”一直运转并监听用户操作的。
3. 线程 (Threading)：使用 `threading.Thread` 让 AI 在后台思考，不卡顿画面。
   - 应用场景：当你需要程序同时做两件事时（比如一边下载大文件，一边还能让用户点按钮取消下载）。
4. 全局变量 (Global Variables)：了解 `global` 关键字在函数内部修改全局状态的用法。
   - 应用场景：偶尔用于简单的跨函数状态共享（如统计总数），但大项目中通常更推荐使用类（Class）来管理状态以避免混乱。
"""

import os
import threading
import time
import pygame
import chess

# 尝试导入 DeepSeek Agent 模块（如果 config.yaml 没配好或网络不通，游戏仍可正常运行）
_AGENT_IMPORT_ERROR = None
try:
    from chess_agent import ask_chess_agent, print_agent_result, format_kid_display

    _AGENT_AVAILABLE = True
except ImportError as e:
    _AGENT_AVAILABLE = False
    _AGENT_IMPORT_ERROR = str(e)

# 初始化 pygame 所有模块（显示、事件、字体等）
pygame.init()


# ==================== 字体工具：支持中英文混合渲染 ====================


def _get_font(size, bold=False):
    """
    Return a pygame Font using stable fonts available on macOS/Windows.
    Added CJK fonts to support Chinese text in the UI.
    Falls back to pygame default font if none of the candidates load.
    """
    _FONT_CANDIDATES = [
        "stheitimedium",  # macOS 黑体，笔画更粗，显示最清晰
        "pingfangsc",  # macOS 苹方字体，现代中文字体
        "microsoftyahei",  # Windows 微软雅黑
        "msyh",  # Windows 微软雅黑
        "arialunicode",  # macOS fallback that usually supports Chinese well
        "stheitilight",  # macOS Chinese
        "songti",  # macOS Chinese
        "simhei",  # Windows Chinese
        "simsun",  # Windows Chinese
        "menlo",  # monospace, good for UI
        "courier",  # monospace fallback
        "arial",  # proportional fallback
    ]
    for name in _FONT_CANDIDATES:
        path = pygame.font.match_font(name, bold=bold)
        if path is not None:
            try:
                font = pygame.font.Font(path, size)
                if bold and not font.get_bold():
                    font.set_bold(True)
                return font
            except Exception:
                pass
    return pygame.font.Font(None, size)


# ==================== Stockfish 引擎路径 ====================
# 优先使用项目自带的 Stockfish，其次尝试 Homebrew 安装的路径

_STOCKFISH_LOCAL = os.path.join(os.path.dirname(__file__), "stockfish_bin", "stockfish")
STOCKFISH_PATH = (
    _STOCKFISH_LOCAL
    if os.path.exists(_STOCKFISH_LOCAL)
    else "/opt/homebrew/bin/stockfish"
)


# ==================== 难度配置 ====================
# 三种难度：beginner（入门）/ normal（普通）/ master（大师）
# depth = alpha-beta 搜索深度，越大越强但越慢
# skill = Stockfish 技能等级（0~20）
# think_time = Stockfish 思考时间（秒）
#
# 【Python 学习要点】：
# 嵌套字典 (Nested Dictionary)：字典里的值也是字典。这是一种组织复杂数据的常用方式。
# - 应用场景：配置管理（如游戏中不同怪物的血量、攻击力配置）、API 返回的多层级 JSON 数据解析。

DIFFICULTY_CONFIG = {
    "beginner": {
        "label": "Beginner",
        "depth": 2,
        "use_stockfish": False,
        "skill": None,
        "think_time": None,
    },
    "normal": {
        "label": "Normal",
        "depth": 3,
        "use_stockfish": True,
        "skill": 10,
        "think_time": 0.3,
    },
    "master": {
        "label": "Master",
        "depth": 4,
        "use_stockfish": True,
        "skill": 20,
        "think_time": 1.0,
    },
    "auto": {
        "label": "Auto Play",
        "depth": 3,
        "use_stockfish": True,
        "skill": 10,
        "think_time": 0.3,
    },
}

# ==================== 动画帧数 ====================
ANIMATION_FRAMES = 8  # 走子动画的帧数，越大动画越流畅但越慢


# ==================== 窗口与棋盘布局 ====================

ROWS, COLS = 8, 8  # 棋盘 8 行 8 列
SQUARE_SIZE = 60  # 每格像素大小
MARGIN = 28  # 棋盘四周留白（用于坐标标签）
BOARD_LEFT = MARGIN  # 棋盘左边界
BOARD_TOP = MARGIN  # 棋盘上边界
BOARD_WIDTH = SQUARE_SIZE * COLS + MARGIN * 2  # 棋盘区宽度 536px
BOARD_HEIGHT = SQUARE_SIZE * ROWS + MARGIN * 2  # 棋盘区高度 536px
PANEL_WIDTH = 280  # 右侧侧边栏宽度
PANEL_GAP = 4  # 棋盘与侧边栏之间的间隙
WIDTH = BOARD_WIDTH + PANEL_GAP + PANEL_WIDTH  # 总窗口宽度 820px
HEIGHT = BOARD_HEIGHT  # 总窗口高度 536px
PANEL_X = BOARD_WIDTH + PANEL_GAP  # 侧边栏左边界 x 坐标

# ---- 颜色定义 ----
BOARD_BG = (44, 33, 22)  # 棋盘背景色（深木色）
LIGHT = (240, 217, 181)  # 棋盘浅色格
DARK = (181, 136, 99)  # 棋盘深色格

# 高亮颜色（RGBA，最后一个值表示透明度）
HIGHLIGHT_GREEN = (0, 255, 0, 80)  # 选中的棋子高亮
HIGHLIGHT_FROM = (255, 80, 80, 120)  # 上一步来源格（红色）
HIGHLIGHT_TO = (255, 255, 80, 120)  # 上一步目标格（黄色）

# UI 颜色
UI_BG = (30, 30, 30)  # 菜单背景
UI_BUTTON = (60, 60, 60)  # 按钮颜色
UI_BUTTON_HOVER = (100, 100, 100)  # 按钮悬停颜色
UI_TEXT = (220, 220, 220)  # 通用文字颜色
UI_TITLE = (255, 200, 50)  # 标题颜色（金色）
UI_DIFF_COLORS = {  # 各难度按钮的边框颜色
    "beginner": (100, 200, 100),  # 绿色
    "normal": (100, 150, 255),  # 蓝色
    "master": (255, 100, 100),  # 红色
    "auto": (200, 100, 255),  # 紫色
}

# 侧边栏颜色
PANEL_BG = (38, 38, 42)  # 侧边栏背景
PANEL_INPUT_BG = (52, 52, 56)  # 输入框背景
PANEL_BORDER = (80, 80, 86)  # 侧边栏边框

# 创建窗口
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Demo - AI Opponent")


# ==================== 棋子 Unicode 字符映射 ====================
# 大写 = 白方，小写 = 黑方

UNICODE_PIECES = {
    "K": "♔",
    "Q": "♕",
    "R": "♖",
    "B": "♗",
    "N": "♘",
    "P": "♙",  # 白方
    "k": "♚",
    "q": "♛",
    "r": "♜",
    "b": "♝",
    "n": "♞",
    "p": "♟",  # 黑方
}

# 棋子基础价值（用于 AI 评估，单位：厘兵，1 兵 = 100）
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}


# ==================== 棋子位置表 (Piece-Square Tables) ====================
# 每个格子有位置加分，不同棋子在棋盘不同位置的"好程度"不同。
# 例如：兵在中间比在边上好，马在中间比在角落好。
# 数组索引 0~63 对应 a8,b8,...,h8, a7,...,h1（从上到下、从左到右）

PST_PAWN = [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    50,
    50,
    50,
    50,
    50,
    50,
    50,
    50,
    10,
    10,
    20,
    30,
    30,
    20,
    10,
    10,
    5,
    5,
    10,
    25,
    25,
    10,
    5,
    5,
    0,
    0,
    0,
    20,
    20,
    0,
    0,
    0,
    5,
    -5,
    -10,
    0,
    0,
    -10,
    -5,
    5,
    5,
    10,
    10,
    -20,
    -20,
    10,
    10,
    5,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
]

PST_KNIGHT = [
    -50,
    -40,
    -30,
    -30,
    -30,
    -30,
    -40,
    -50,
    -40,
    -20,
    0,
    0,
    0,
    0,
    -20,
    -40,
    -30,
    0,
    10,
    15,
    15,
    10,
    0,
    -30,
    -30,
    5,
    15,
    20,
    20,
    15,
    5,
    -30,
    -30,
    0,
    15,
    20,
    20,
    15,
    0,
    -30,
    -30,
    5,
    10,
    15,
    15,
    10,
    5,
    -30,
    -40,
    -20,
    0,
    5,
    5,
    0,
    -20,
    -40,
    -50,
    -40,
    -30,
    -30,
    -30,
    -30,
    -40,
    -50,
]

PST_BISHOP = [
    -20,
    -10,
    -10,
    -10,
    -10,
    -10,
    -10,
    -20,
    -10,
    0,
    0,
    0,
    0,
    0,
    0,
    -10,
    -10,
    0,
    10,
    10,
    10,
    10,
    0,
    -10,
    -10,
    5,
    5,
    10,
    10,
    5,
    5,
    -10,
    -10,
    0,
    5,
    10,
    10,
    5,
    0,
    -10,
    -10,
    10,
    10,
    10,
    10,
    10,
    10,
    -10,
    -10,
    5,
    0,
    0,
    0,
    0,
    5,
    -10,
    -20,
    -10,
    -10,
    -10,
    -10,
    -10,
    -10,
    -20,
]

PST_ROOK = [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    5,
    10,
    10,
    10,
    10,
    10,
    10,
    5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    -5,
    0,
    0,
    0,
    0,
    0,
    0,
    -5,
    0,
    0,
    0,
    5,
    5,
    0,
    0,
    0,
]

PST_QUEEN = [
    -20,
    -10,
    -10,
    -5,
    -5,
    -10,
    -10,
    -20,
    -10,
    0,
    0,
    0,
    0,
    0,
    0,
    -10,
    -10,
    0,
    5,
    5,
    5,
    5,
    0,
    -10,
    -5,
    0,
    5,
    5,
    5,
    5,
    0,
    -5,
    0,
    0,
    5,
    5,
    5,
    5,
    0,
    -5,
    -10,
    5,
    5,
    5,
    5,
    5,
    0,
    -10,
    -10,
    0,
    5,
    0,
    0,
    0,
    0,
    -10,
    -20,
    -10,
    -10,
    -5,
    -5,
    -10,
    -10,
    -20,
]

# 国王在中局和残局用不同的位置表
# 中局：国王应该躲在角落安全
PST_KING_MIDDLE = [
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -30,
    -40,
    -40,
    -50,
    -50,
    -40,
    -40,
    -30,
    -20,
    -30,
    -30,
    -40,
    -40,
    -30,
    -30,
    -20,
    -10,
    -20,
    -20,
    -20,
    -20,
    -20,
    -20,
    -10,
    20,
    20,
    0,
    0,
    0,
    0,
    20,
    20,
    20,
    30,
    10,
    0,
    0,
    10,
    30,
    20,
]

# 残局：国王应该主动走向棋盘中间参与战斗
PST_KING_END = [
    -50,
    -40,
    -30,
    -20,
    -20,
    -30,
    -40,
    -50,
    -30,
    -20,
    -10,
    0,
    0,
    -10,
    -20,
    -30,
    -30,
    -10,
    20,
    30,
    30,
    20,
    -10,
    -30,
    -30,
    -10,
    30,
    40,
    40,
    30,
    -10,
    -30,
    -30,
    -10,
    30,
    40,
    40,
    30,
    -10,
    -30,
    -30,
    -10,
    20,
    30,
    30,
    20,
    -10,
    -30,
    -30,
    -30,
    0,
    0,
    0,
    0,
    -30,
    -30,
    -50,
    -30,
    -30,
    -30,
    -30,
    -30,
    -30,
    -50,
]

# 棋子类型 → 对应的位置表
PST = {
    chess.PAWN: PST_PAWN,
    chess.KNIGHT: PST_KNIGHT,
    chess.BISHOP: PST_BISHOP,
    chess.ROOK: PST_ROOK,
    chess.QUEEN: PST_QUEEN,
}

_search_nodes = 0  # 全局变量：统计搜索过的节点数（调试用）


# ==================== 内置 AI 引擎（Alpha-Beta 剪枝搜索） ====================
# 以下是国际象棋 AI 的核心算法。简单来说：
#   1. _evaluate() → 给当前局面打分（分数越高对黑方越有利）
#   2. _alpha_beta() → 递归搜索未来几步，找到最优走法
#   3. _quiescence() → 静态搜索，防止"地平线效应"（只看吃子走法）
#   4. _search_best_move() → 顶层入口，返回 AI 选择的最佳走法


def _evaluate(board):
    """
    局面评估函数。
    从黑方视角给当前局面打分：
      - 正值 = 对黑方有利
      - 负值 = 对白方有利
    考虑因素：棋子价值 + 位置加分 + 机动性（可走法数量）
    """
    # 将死：返回极大值
    if board.is_checkmate():
        return -200000 if board.turn == chess.BLACK else 200000
    # 逼和或子力不足：平局
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    total_material = 0

    # 遍历棋盘上每个格子
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        # 棋子基础价值
        value = PIECE_VALUES.get(piece.piece_type, 0)
        total_material += value

        # 加上位置表加分
        pst = PST.get(piece.piece_type)
        if pst is not None:
            rank = chess.square_rank(square)
            if piece.color == chess.BLACK:
                pst_index = rank * 8 + chess.square_file(square)
            else:
                # 白方的位置表需要翻转（因为白方从 rank 1 出发）
                pst_index = (7 - rank) * 8 + chess.square_file(square)
            value += pst[pst_index]

        # 黑方棋子加分，白方棋子减分
        if piece.color == chess.BLACK:
            score += value
        else:
            score -= value

    # 国王位置表：根据当前是中局还是残局选择不同的表
    is_endgame = total_material < 3000  # 总子力 < 3000 认为是残局
    for color in [chess.WHITE, chess.BLACK]:
        king_sq = board.king(color)
        if king_sq is None:
            continue
        rank = chess.square_rank(king_sq)
        f = chess.square_file(king_sq)
        if is_endgame:
            king_bonus = (
                PST_KING_END[rank * 8 + f]
                if color == chess.BLACK
                else PST_KING_END[(7 - rank) * 8 + f]
            )
        else:
            king_bonus = (
                PST_KING_MIDDLE[rank * 8 + f]
                if color == chess.BLACK
                else PST_KING_MIDDLE[(7 - rank) * 8 + f]
            )
        if color == chess.BLACK:
            score += king_bonus
        else:
            score -= king_bonus

    # 机动性加分：可走的步数越多越好
    mobility = len(list(board.legal_moves))
    if board.turn == chess.BLACK:
        score += mobility
    else:
        score -= mobility

    return score


def _move_priority(move, board):
    """
    走法排序函数（MVV-LVA：最有价值受害者-最没价值攻击者）。
    好的走法先搜索，能大幅提升 alpha-beta 剪枝效率。
    优先级规则：吃子 > 升变 > 将军 > 其他
    """
    priority = 0
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim is None and board.is_en_passant(move):
            # 吃过路兵：受害者是兵
            victim = chess.Piece(chess.PAWN, not board.turn)
        victim_val = PIECE_VALUES.get(victim.piece_type, 0) if victim else 0
        attacker_val = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
        priority = victim_val * 10 - attacker_val  # 用后吃兵 > 用兵吃后
    if move.promotion:
        priority += PIECE_VALUES.get(move.promotion, 0)
    # 走这步后如果将军，加额外分
    board_copy = board.copy()
    board_copy.push(move)
    if board_copy.is_check():
        priority += 50
    return priority


def _quiescence(board, alpha, beta, maximizing):
    """
    静态搜索（Quiescence Search）。
    只在搜索深度用完时继续搜索吃子走法，防止"地平线效应"——
    即 AI 在第 N 层看到一个好局面，但实际上第 N+1 层对方会吃回子力。
    """
    global _search_nodes
    _search_nodes += 1

    # 先评估当前局面的静态分数
    stand_pat = _evaluate(board)
    if maximizing:
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat
    else:
        if stand_pat <= alpha:
            return alpha
        if stand_pat < beta:
            beta = stand_pat

    # 只搜索吃子走法
    captures = [m for m in board.legal_moves if board.is_capture(m)]
    captures.sort(key=lambda m: _move_priority(m, board), reverse=True)

    for move in captures:
        board.push(move)
        score = _quiescence(board, alpha, beta, not maximizing)
        board.pop()

        if maximizing:
            if score > alpha:
                alpha = score
            if alpha >= beta:
                return beta
        else:
            if score < beta:
                beta = score
            if alpha >= beta:
                return alpha

    return alpha if maximizing else beta


def _alpha_beta(board, depth, alpha, beta, maximizing):
    """
    Alpha-Beta 剪枝搜索（带走法排序）。
    这是国际象棋 AI 最核心的算法：
      - alpha：当前搜索中，最大化方（黑方）已经保证能得到的最低分数
      - beta：当前搜索中，最小化方（白方）已经保证对方不会超过的最高分数
      - 如果 alpha >= beta，说明这个分支不会被选中，可以安全剪掉

    【Python 学习要点】：
    - 递归 (Recursion): 函数内部调用自己（`_alpha_beta` 内部调用 `_alpha_beta`）。
      - 应用场景：处理具有树状或图状结构的数据（如电脑上的文件夹目录遍历、HTML DOM 树解析）、以及这种需要预测未来分支的棋盘游戏 AI。
    - 必须要有一个结束条件（Base Case），否则会无限循环导致栈溢出。这里的结束条件是 `depth == 0` 或 `board.is_game_over()`。
    """
    global _search_nodes
    _search_nodes += 1

    if board.is_game_over():
        return _evaluate(board)
    if depth == 0:
        # 深度用完，进入静态搜索防止地平线效应
        return _quiescence(board, alpha, beta, maximizing)

    moves = list(board.legal_moves)
    moves.sort(key=lambda m: _move_priority(m, board), reverse=True)

    if maximizing:
        for move in moves:
            board.push(move)
            score = _alpha_beta(board, depth - 1, alpha, beta, False)
            board.pop()
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break  # Beta 剪枝：对手不会让这个局面发生
        return alpha
    else:
        for move in moves:
            board.push(move)
            score = _alpha_beta(board, depth - 1, alpha, beta, True)
            board.pop()
            if score < beta:
                beta = score
            if alpha >= beta:
                break  # Alpha 剪枝：我们不会选择这个分支
        return beta


def _search_best_move(board, depth):
    """
    顶层搜索函数：对当前局面执行 Alpha-Beta 搜索，返回黑方最佳走法。
    这是 AI 引擎对外暴露的接口。
    """
    global _search_nodes
    _search_nodes = 0

    start_time = time.time()
    legal_moves = list(board.legal_moves)

    # 只有一个合法走法时直接返回，不需要搜索
    if len(legal_moves) == 1:
        return legal_moves[0]

    # 走法排序：好的走法先搜，提高剪枝效率
    legal_moves.sort(key=lambda m: _move_priority(m, board), reverse=True)

    best_move = legal_moves[0]
    best_score = -999999
    alpha = -999999
    beta = 999999

    for move in legal_moves:
        board.push(move)
        score = _alpha_beta(board, depth - 1, alpha, beta, False)
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move
        if score > alpha:
            alpha = score

    elapsed = time.time() - start_time
    print(
        f"[AI] depth={depth}, nodes={_search_nodes}, "
        f"time={elapsed:.3f}s, best={best_move.uci()}, score={best_score}"
    )

    return best_move


# ==================== Stockfish 引擎接口（可选） ====================
# Stockfish 是世界上最强的国际象棋引擎之一。
# 如果安装了 Stockfish，高难度模式下优先使用它。


def _init_stockfish(skill_level):
    """初始化 Stockfish 引擎，失败时返回 None（自动降级到内置引擎）"""
    try:
        from stockfish import Stockfish

        engine = Stockfish(path=STOCKFISH_PATH)
        engine.set_skill_level(skill_level)
        return engine
    except FileNotFoundError:
        print(f"[WARNING] Stockfish not found: {STOCKFISH_PATH}")
        print("[HINT] macOS: brew install stockfish")
        return None
    except ImportError:
        print("[WARNING] stockfish package not installed: pip install stockfish")
        return None
    except Exception as e:
        print(f"[WARNING] Stockfish init failed: {e}")
        return None


def _get_stockfish_move(board, engine, think_time):
    """从 Stockfish 获取最佳走法，失败时降级到内置引擎"""
    engine.set_fen_position(board.fen())
    best_move = engine.get_best_move_time(int(think_time * 1000))
    if best_move is None:
        return _search_best_move(board, 2)
    return chess.Move.from_uci(best_move)


def get_ai_move(board, engine, difficulty_key):
    """AI 走法入口：优先用 Stockfish，不可用时用内置引擎"""
    config = DIFFICULTY_CONFIG[difficulty_key]
    if config["use_stockfish"] and engine is not None:
        return _get_stockfish_move(board, engine, config["think_time"])
    return _search_best_move(board, config["depth"])


# ==================== 棋子渲染 ====================


def _render_piece(symbol, size, font):
    """将单个 Unicode 棋子符号渲染到透明 Surface 上"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    text = font.render(UNICODE_PIECES[symbol], True, (0, 0, 0))
    text_rect = text.get_rect(center=(size // 2, size // 2))
    surf.blit(text, text_rect)
    return surf


def load_pieces(square_size):
    """
    加载所有 12 种棋子（白方 6 种 + 黑方 6 种）的渲染图像。
    返回字典：键 = 棋子符号（如 'K', 'q'），值 = pygame Surface
    """
    font_size = int(square_size * 0.85)
    font = None
    # 尝试多个支持棋子 Unicode 的字体
    for font_name in (
        "Apple Symbols",
        "Arial Unicode MS",
        "DejaVu Sans",
        "segoeuisymbol",
    ):
        f = pygame.font.SysFont(font_name, font_size)
        if f.render(UNICODE_PIECES["K"], True, (0, 0, 0)).get_width() > font_size // 2:
            font = f
            break
    if font is None:
        font = pygame.font.Font(None, font_size)

    pieces = {}
    for symbol in UNICODE_PIECES:
        pieces[symbol] = _render_piece(symbol, square_size, font)
    return pieces


# ==================== 坐标转换工具 ====================
# python-chess 用 0~63 的整数表示格子（a1=0, b1=1, ..., h8=63）
# pygame 用像素坐标表示位置
# 这两个函数负责在两种坐标系统之间转换


def square_to_pixel(square):
    """python-chess 格子编号 → pygame 像素坐标（含 margin 偏移）"""
    col = chess.square_file(square)  # 列：0=a, 1=b, ..., 7=h
    row = 7 - chess.square_rank(square)  # 行：pygame 的 y 轴向下，rank 8 在最上面
    return BOARD_LEFT + col * SQUARE_SIZE, BOARD_TOP + row * SQUARE_SIZE


def pixel_to_square(mouse_x, mouse_y):
    """鼠标像素坐标 → python-chess 格子编号（含 margin 偏移）"""
    col = (mouse_x - BOARD_LEFT) // SQUARE_SIZE
    row = (mouse_y - BOARD_TOP) // SQUARE_SIZE
    chess_row = 7 - row  # 反转：pygame 的 y=0 对应 rank 8
    return chess.square(col, chess_row)


# ==================== 难度选择菜单 ====================


def select_difficulty(win):
    """显示难度选择画面，点击按钮后返回难度 key（"beginner"/"normal"/"master"/"auto"）"""
    # 预加载字体
    title_font = _get_font(36, bold=True)
    subtitle_font = _get_font(16)
    button_font = _get_font(28, bold=True)
    hint_font = _get_font(13)
    detail_font = _get_font(14)

    descriptions = {
        "beginner": "Search depth 2 -- good for learning",
        "normal": "Search depth 3 -- intermediate challenge",
        "master": "Search depth 4 -- expert level play",
        "auto": "AI vs AI -- Watch the AI teacher play!",
    }

    # 计算四个按钮的位置（垂直排列，居中）
    button_w, button_h = 280, 56
    button_gap = 12
    start_y = 135
    buttons = {}
    for i, key in enumerate(["beginner", "normal", "master", "auto"]):
        bx = (BOARD_WIDTH - button_w) // 2
        by = start_y + i * (button_h + button_gap + 20)
        buttons[key] = pygame.Rect(bx, by, button_w, button_h)

    # 菜单主循环：等待玩家点击
    while True:
        mouse_pos = pygame.mouse.get_pos()
        win.fill(UI_BG)

        # 标题
        title_surf = title_font.render("Choose Difficulty", True, UI_TITLE)
        title_rect = title_surf.get_rect(center=(BOARD_WIDTH // 2, 45))
        win.blit(title_surf, title_rect)

        # 副标题
        sub_surf = subtitle_font.render(
            "White = You (mouse)    Black = AI", True, UI_TEXT
        )
        sub_rect = sub_surf.get_rect(center=(BOARD_WIDTH // 2, 85))
        win.blit(sub_surf, sub_rect)

        # 绘制四个难度按钮
        label_map = {
            "beginner": "Beginner",
            "normal": "Normal",
            "master": "Master",
            "auto": "Auto Play",
        }
        for key, rect in buttons.items():
            is_hover = rect.collidepoint(mouse_pos)
            btn_color = UI_BUTTON_HOVER if is_hover else UI_BUTTON
            border_color = UI_DIFF_COLORS[key]

            pygame.draw.rect(win, btn_color, rect, border_radius=12)
            pygame.draw.rect(win, border_color, rect, width=3, border_radius=12)

            label_text = button_font.render(label_map[key], True, border_color)
            label_rect = label_text.get_rect(center=rect.center)
            win.blit(label_text, label_rect)

            # 难度描述文字
            desc_surf = detail_font.render(descriptions[key], True, (160, 160, 160))
            desc_rect = desc_surf.get_rect(center=(BOARD_WIDTH // 2, rect.bottom + 12))
            win.blit(desc_surf, desc_rect)

        # 底部提示
        tip_surf = hint_font.render(
            "Click to start  |  Close window to quit", True, (120, 120, 120)
        )
        tip_rect = tip_surf.get_rect(center=(BOARD_WIDTH // 2, HEIGHT - 30))
        win.blit(tip_surf, tip_rect)

        pygame.display.update()

        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for key, rect in buttons.items():
                    if rect.collidepoint(event.pos):
                        return key


# ==================== 棋盘绘制 ====================


def draw_coordinates(win):
    """
    绘制棋盘坐标标签。
    底部：文件标签 a~h（列）
    左侧：行标签 1~8（从上到下）
    """
    coord_font = _get_font(15, bold=True)
    LIGHT_LABEL = (140, 100, 70)  # 浅色格上的标签颜色
    DARK_LABEL = (220, 195, 150)  # 深色格上的标签颜色

    # 底部：a~h
    for col in range(8):
        file_label = chr(ord("a") + col)
        label_color = DARK_LABEL if col % 2 == 0 else LIGHT_LABEL
        text = coord_font.render(file_label, True, label_color)
        x = BOARD_LEFT + col * SQUARE_SIZE + (SQUARE_SIZE - text.get_width()) // 2
        y = BOARD_TOP + 8 * SQUARE_SIZE + (MARGIN - text.get_height()) // 2
        win.blit(text, (x, y))

    # 左侧：8~1
    for row in range(8):
        rank_label = str(8 - row)
        label_color = DARK_LABEL if row % 2 == 0 else LIGHT_LABEL
        text = coord_font.render(rank_label, True, label_color)
        y = BOARD_TOP + row * SQUARE_SIZE + (SQUARE_SIZE - text.get_height()) // 2
        x = (MARGIN - text.get_width()) // 2
        win.blit(text, (x, y))


def draw_board(win):
    """绘制 8x8 棋盘格子（浅色和深色交替）"""
    for row in range(ROWS):
        for col in range(COLS):
            color = LIGHT if (row + col) % 2 == 0 else DARK
            rect = (
                BOARD_LEFT + col * SQUARE_SIZE,
                BOARD_TOP + row * SQUARE_SIZE,
                SQUARE_SIZE,
                SQUARE_SIZE,
            )
            pygame.draw.rect(win, color, rect)


def draw_last_move_highlight(win, last_move):
    """高亮上一步走法的起止格子：红色=来源格，黄色=目标格"""
    if last_move is None:
        return
    for square, color in [
        (last_move.from_square, HIGHLIGHT_FROM),
        (last_move.to_square, HIGHLIGHT_TO),
    ]:
        x, y = square_to_pixel(square)
        surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        surf.fill(color)
        win.blit(surf, (x, y))


def draw_highlights(win, selected_square, board):
    """
    高亮选中的棋子（绿色）及其合法目标格（小圆点）。
    帮助玩家看到可以走哪些位置。
    """
    if selected_square is None:
        return
    col = chess.square_file(selected_square)
    row = 7 - chess.square_rank(selected_square)

    # 绿色高亮选中的棋子
    highlight_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
    highlight_surf.fill(HIGHLIGHT_GREEN)
    win.blit(
        highlight_surf, (BOARD_LEFT + col * SQUARE_SIZE, BOARD_TOP + row * SQUARE_SIZE)
    )

    # 在合法目标格上画小圆点
    for move in board.legal_moves:
        if move.from_square != selected_square:
            continue
        to_col = chess.square_file(move.to_square)
        to_row = 7 - chess.square_rank(move.to_square)
        dot_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(
            dot_surf,
            (0, 0, 0, 40),
            (SQUARE_SIZE // 2, SQUARE_SIZE // 2),
            SQUARE_SIZE // 6,
        )
        win.blit(
            dot_surf,
            (BOARD_LEFT + to_col * SQUARE_SIZE, BOARD_TOP + to_row * SQUARE_SIZE),
        )


def draw_pieces(win, board, pieces):
    """根据当前棋局状态，在棋盘上放置所有棋子图像"""
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue
        col = chess.square_file(square)
        row = 7 - chess.square_rank(square)
        win.blit(
            pieces[piece.symbol()],
            (BOARD_LEFT + col * SQUARE_SIZE, BOARD_TOP + row * SQUARE_SIZE),
        )


def draw_game_over_overlay(win, board):
    """游戏结束遮罩层：显示结果 + 点击返回提示"""
    if not board.is_game_over():
        return

    # 判断结果
    outcome = board.outcome()
    if outcome is None:
        result_text = "Game Over"
    elif outcome.winner is None:
        result_text = "Draw!"
    elif outcome.winner == chess.WHITE:
        result_text = "You Win!"
    else:
        result_text = "AI Wins!"

    # 半透明黑色遮罩
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    win.blit(overlay, (0, 0))

    # 结果文字
    big_font = _get_font(48, bold=True)
    text_surf = big_font.render(result_text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 25))
    win.blit(text_surf, text_rect)

    # 返回提示
    small_font = _get_font(18)
    hint_surf = small_font.render("Click to return to menu", True, (200, 200, 200))
    hint_rect = hint_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
    win.blit(hint_surf, hint_rect)


# ==================== 走子动画 ====================


def animate_move(win, board, pieces, move, last_move):
    """
    平滑滑动动画：将棋子从来源格移动到目标格。
    使用线性插值，分 ANIMATION_FRAMES 帧完成。
    """
    # 起止像素位置
    fx, fy = square_to_pixel(move.from_square)
    tx, ty = square_to_pixel(move.to_square)
    piece_symbol = board.piece_at(move.from_square).symbol()
    moving_img = pieces[piece_symbol]

    for i in range(1, ANIMATION_FRAMES + 1):
        t = i / ANIMATION_FRAMES  # 插值系数 0→1
        cur_x = fx + (tx - fx) * t
        cur_y = fy + (ty - fy) * t

        # 重绘棋盘（不含移动中的棋子）
        draw_board(win)
        draw_last_move_highlight(win, last_move)

        for square in chess.SQUARES:
            if square == move.from_square:
                continue  # 跳过来源格（棋子正在移动中）
            piece = board.piece_at(square)
            if piece is None:
                continue
            col = chess.square_file(square)
            row = 7 - chess.square_rank(square)
            win.blit(
                pieces[piece.symbol()],
                (BOARD_LEFT + col * SQUARE_SIZE, BOARD_TOP + row * SQUARE_SIZE),
            )

        # 在插值位置绘制移动中的棋子
        win.blit(moving_img, (cur_x, cur_y))
        pygame.display.update()
        pygame.time.Clock().tick(60)


# ==================== 侧边栏：AI 老师 ====================
# 右侧常驻面板，使用 pygame 原生渲染文字输入/输出。
# 不阻塞棋盘操作，不依赖 tkinter/osascript（后者与 pygame SDL 冲突）。


def _wrap_text(text, font, max_width):
    """
    文字自动换行：把一个长字符串按字体宽度拆成多行。
    用于侧边栏结果展示，确保文字不超出面板宽度。
    """
    lines = []
    current = ""
    for ch in text:
        test = current + ch
        if font.render(test, True, (0, 0, 0)).get_width() <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def _draw_side_panel(win, panel):
    """
    绘制右侧 AI 老师侧边栏。
    包含：标题、输入框、发送按钮、状态提示、分析结果。

    【Python 学习要点】：
    - `pygame.draw.rect`：绘制矩形，这里用于绘制侧边栏背景和输入框。
    - 字体渲染：使用 `font.render` 将字符串转换为 Surface，然后用 `win.blit` 贴到屏幕上。
    """
    px = PANEL_X

    # 创建一个用于裁剪的 Surface（防止内容超出面板底部）
    # panel_rect = pygame.Rect(px, 0, PANEL_WIDTH, HEIGHT)
    # win.set_clip(panel_rect)

    # 背景
    panel_rect = pygame.Rect(px, 0, PANEL_WIDTH, HEIGHT)
    pygame.draw.rect(win, PANEL_BG, panel_rect)

    # Title
    title_font = _get_font(20, bold=True)
    title_surf = title_font.render("AI 老师", True, UI_TITLE)
    win.blit(title_surf, (px + 16, 18))

    # ---- 输入框 ----
    input_y = 52
    input_h = 34
    input_rect = pygame.Rect(px + 10, input_y, PANEL_WIDTH - 20, input_h)

    # 输入框边框（激活时高亮）
    if panel["active"]:
        border_color = UI_TITLE
        border_w = 2
    else:
        border_color = PANEL_BORDER
        border_w = 1
    pygame.draw.rect(win, (30, 30, 34), input_rect, border_radius=6)
    pygame.draw.rect(win, border_color, input_rect, width=border_w, border_radius=6)

    # 输入文字（或占位提示）
    input_font = _get_font(14)
    input_text = panel["input"]
    ime_text = panel.get("ime_text", "")

    # 将正在输入的拼音/临时文字显示在光标位置
    display_text = input_text
    if ime_text and panel["active"]:
        display_text = (
            input_text[: panel["cursor"]] + ime_text + input_text[panel["cursor"] :]
        )

    # 如果文字太长，向左滚动（只显示最后面的一部分）
    max_visible_w = input_rect.width - 12
    display_surf = input_font.render(display_text, True, (220, 220, 220))
    if display_surf.get_width() > max_visible_w:
        # 计算需要截取的起始位置（粗略估算）
        avg_char_w = display_surf.get_width() / max(1, len(display_text))
        chars_to_show = int(max_visible_w / avg_char_w)
        display_text = "..." + display_text[-(chars_to_show - 3) :]
        display_surf = input_font.render(display_text, True, (220, 220, 220))
        # 因为截断了，所以光标位置强制显示在最后
        cursor_offset = display_surf.get_width()
    else:
        # 没有超长，计算真实的光标位置
        prefix = input_text[: panel["cursor"]]
        if ime_text:
            prefix += ime_text
        cursor_offset = input_font.render(prefix, True, (0, 0, 0)).get_width()

    placeholder = "输入问题，按回车发送..."
    cursor_visible = panel["active"] and (int(time.time() * 2) % 2 == 0)

    if display_text:
        text_surf = display_surf
    else:
        text_surf = input_font.render(placeholder, True, (100, 100, 106))

    text_x = px + 16
    text_y = input_rect.centery - text_surf.get_height() // 2
    win.blit(text_surf, (text_x, text_y))

    # 光标闪烁（仅在输入框激活时）
    if cursor_visible and panel["active"]:
        cursor_x = text_x + cursor_offset
        pygame.draw.line(
            win,
            (220, 220, 220),
            (cursor_x, text_y),
            (cursor_x, text_y + text_surf.get_height()),
            2,
        )

    # ---- 发送按钮 ----
    btn_rect = pygame.Rect(px + 10, input_y + input_h + 8, 56, 26)
    pygame.draw.rect(win, UI_TITLE, btn_rect, border_radius=6)
    btn_font = _get_font(13, bold=True)
    btn_surf = btn_font.render("发送", True, (20, 20, 20))
    btn_text_rect = btn_surf.get_rect(center=btn_rect.center)
    win.blit(btn_surf, btn_text_rect)

    # ---- 悔棋按钮 ----
    undo_rect = pygame.Rect(px + 76, input_y + input_h + 8, 56, 26)
    pygame.draw.rect(win, (200, 80, 80), undo_rect, border_radius=6)
    undo_surf = btn_font.render("悔棋", True, (255, 255, 255))
    undo_text_rect = undo_surf.get_rect(center=undo_rect.center)
    win.blit(undo_surf, undo_text_rect)

    # 快捷键提示
    hint_font = _get_font(11)
    hint_text = "点击输入框激活" if not panel["active"] else "按 Esc 取消"
    hint_surf = hint_font.render(hint_text, True, (120, 120, 126))
    win.blit(
        hint_surf,
        (undo_rect.right + 10, btn_rect.centery - hint_surf.get_height() // 2),
    )

    # ---- 状态行：思考中 / 错误 ----
    status_y = btn_rect.bottom + 12
    if panel["thinking"]:
        dots = "." * ((int(time.time() * 3) % 4) + 1)
        status_surf = _get_font(14).render(f"思考中{dots}", True, UI_TITLE)
        win.blit(status_surf, (px + 14, status_y))
    elif panel["error"]:
        err_font = _get_font(12)
        err_surf = err_font.render(f"错误: {panel['error'][:40]}", True, (255, 90, 90))
        win.blit(err_surf, (px + 14, status_y))

    # ---- 结果展示区 ----
    result = panel.get("result")
    stream_result = panel.get("stream_result")

    display_data = None
    if not panel["thinking"] and result:
        display_data = result
    elif panel["thinking"] and stream_result:
        display_data = stream_result

    if display_data is None:
        if not panel["thinking"] and not panel["error"]:
            # 等待提问的空闲状态
            idle_font = _get_font(12)
            idle_surf = idle_font.render("请提问...", True, (100, 100, 106))
            win.blit(idle_surf, (px + 14, status_y + 4))
        # win.set_clip(None) # 取消裁剪
        return

    # 分隔线
    result_y = status_y + 24
    pygame.draw.line(
        win, PANEL_BORDER, (px + 10, result_y), (px + PANEL_WIDTH - 10, result_y)
    )

    # ==== 开始绘制可滚动的文本区域 ====
    scroll_y = panel.get("scroll_y", 0)
    y = result_y + 10 - scroll_y  # 应用滚动偏移

    # 获取面板底部边界
    panel_bottom = HEIGHT - 10

    small_font = _get_font(12)
    body_font = _get_font(13)
    max_text_w = PANEL_WIDTH - 28

    # 定义一个内部绘制函数，带裁剪检查，并记录总高度
    total_content_height = 0

    def draw_text_line(surf, x, y_pos):
        nonlocal total_content_height
        total_content_height = max(
            total_content_height,
            (y_pos + scroll_y) - (result_y + 10) + surf.get_height(),
        )
        # 只在面板可视区域内绘制
        if y_pos > result_y and y_pos + surf.get_height() < panel_bottom:
            win.blit(surf, (x, y_pos))

    # 显示用户刚才的问题（像聊天记录一样）
    last_q = panel.get("last_question")
    if last_q:
        q_lines = _wrap_text(f"你: {last_q}", body_font, max_text_w)
        for line in q_lines:
            q_surf = body_font.render(line, True, (200, 200, 200))
            draw_text_line(q_surf, px + 14, y)
            y += 18
        y += 8

    # 当前回合
    turn = "轮到白方" if display_data.get("side_to_move") == "white" else "轮到黑方"
    turn_surf = small_font.render(turn, True, (160, 160, 166))
    draw_text_line(turn_surf, px + 14, y)
    y += 20

    # 推荐走法（如果太长也要换行）
    best = display_data.get("best_move_san") or "(无)"
    best_text = f"推荐走法: {best}"
    best_lines = _wrap_text(best_text, body_font, max_text_w)
    for line in best_lines:
        # 使用更亮的黄色来凸显推荐走法
        move_surf = body_font.render(line, True, (255, 215, 0))
        draw_text_line(move_surf, px + 14, y)
        y += 18
    y += 4

    # 解释（自动换行，取消行数限制）
    exp = display_data.get("child_explanation", "")
    if exp:
        # 为了更清晰，使用略大的字号和更亮的白色，并增加行间距
        exp_font = _get_font(14)
        lines = _wrap_text(exp, exp_font, max_text_w)
        for line in lines:  # 移除 [:8] 限制
            exp_surf = exp_font.render(line, True, (240, 240, 245))
            draw_text_line(exp_surf, px + 14, y)
            y += 22

    # 多步计划（自动换行，取消行数限制）
    plan = display_data.get("plan", "")
    if plan:
        y += 4
        plan_label = small_font.render("--- 计划 ---", True, (140, 140, 146))
        draw_text_line(plan_label, px + 14, y)
        y += 18
        # 计划使用清新的淡绿色
        plan_font = _get_font(13)
        lines = _wrap_text(plan, plan_font, max_text_w)
        for line in lines:  # 移除 [:8] 限制
            plan_surf = plan_font.render(line, True, (180, 220, 180))
            draw_text_line(plan_surf, px + 14, y)
            y += 20

    # 战术警告（取消条数限制，每条也需要自动换行）
    warns = display_data.get("tactical_warnings", [])
    if warns:
        y += 4
        warn_font = _get_font(12)
        for w in warns:  # 移除 [:3] 限制
            warn_lines = _wrap_text(f"! {w}", warn_font, max_text_w)
            for line in warn_lines:
                warn_surf = warn_font.render(line, True, (255, 140, 80))
                draw_text_line(warn_surf, px + 14, y)
                y += 16

    # 走法合法性指示 (仅在非流式输出或流式结束时显示)
    if not panel["thinking"]:
        legal = display_data.get("is_legal")
        if legal is False:
            y += 4
            ill_surf = small_font.render("(不合法走法)", True, (255, 100, 100))
            draw_text_line(ill_surf, px + 14, y)
            y += 16

    # 计算并保存最大滚动范围
    visible_height = panel_bottom - (result_y + 10)
    if total_content_height > visible_height:
        panel["max_scroll_y"] = total_content_height - visible_height

        # 绘制滚动条提示 (只有当需要滚动时才显示)
        scroll_ratio = scroll_y / panel["max_scroll_y"]
        bar_h = max(20, visible_height * (visible_height / total_content_height))
        bar_y = result_y + 10 + scroll_ratio * (visible_height - bar_h)
        pygame.draw.rect(
            win, (80, 80, 85), (px + PANEL_WIDTH - 6, bar_y, 4, bar_h), border_radius=2
        )
    else:
        panel["max_scroll_y"] = 0
        panel["scroll_y"] = 0  # 内容变少时重置滚动


# ==================== 游戏主循环 ====================


def _agent_thread_fn(board, question, panel):
    """
    后台线程函数：调用 DeepSeek API 分析棋局。
    结果存入 panel 字典，由主线程在下次绘制时显示。
    """

    def on_stream(partial_result):
        # 将逐步提取出的部分结果更新给 panel，让 UI 实时渲染
        panel["stream_result"] = format_kid_display(partial_result)

    try:
        result = ask_chess_agent(
            board=board,
            user_question=question,
            move_history=list(board.move_stack),
            stream_callback=on_stream,
        )
        # Terminal 输出完整调试信息
        print_agent_result(result)
        # 提取关键信息给侧边栏
        kid = format_kid_display(result)
        panel["result"] = kid
        panel["stream_result"] = None
        panel["error"] = None
    except Exception as e:
        panel["error"] = str(e)
        import traceback

        traceback.print_exc()
    finally:
        panel["thinking"] = False


def _submit_question(board, panel):
    """
    提交侧边栏中的问题。
    在后台线程中调用 AI Agent，不阻塞 UI。

    【Python 学习要点】：
    - 多线程 (Threading): 使用 `threading.Thread` 创建新线程。
    - 网络请求（如调用大模型 API）通常很慢。如果不使用多线程，程序会"卡死"，玩家无法继续走棋或看到任何动画。
    - `daemon=True` 表示如果主程序退出，这个后台线程也会强制结束。
    """
    question = panel["input"].strip()
    if not question or panel["thinking"]:
        return
    print("\n" + "=" * 50)
    print(f"[Agent] Question: {question}")
    print("[Agent] Analysing, please wait...")

    panel["last_question"] = question
    panel["input"] = ""
    panel["cursor"] = 0
    panel["thinking"] = True
    panel["result"] = None
    panel["stream_result"] = None
    panel["error"] = None
    # 使用 board.copy() 确保线程安全：后台线程读取的是当前局面的快照
    worker = threading.Thread(
        target=_agent_thread_fn,
        args=(board.copy(), question, panel),
        daemon=True,
    )
    worker.start()


def run_game(win, pieces, difficulty_key):
    """
    运行一盘完整对局。
    人类执白（鼠标操作），AI 执黑（自动走子）。
    返回时机：玩家点击棋盘区（游戏结束状态）回到菜单。

    【Python 学习要点】：
    游戏主循环 (Game Loop) 模式：
    通常分为三步：
    1. 绘制当前状态到屏幕
    2. 更新游戏逻辑（如 AI 走子）
    3. 处理用户输入事件（键盘/鼠标）
    不断重复这个过程，直到游戏结束。
    """
    config = DIFFICULTY_CONFIG[difficulty_key]
    print(f"\n[GAME] Difficulty: {config['label']} (depth={config['depth']})")
    if _AGENT_AVAILABLE:
        print("[HINT] Click the side panel to ask the AI teacher")
    else:
        print(f"[HINT] DeepSeek Agent not loaded: {_AGENT_IMPORT_ERROR}")

    # ---- 初始化 AI 引擎 ----
    engine = None
    if config["use_stockfish"]:
        engine = _init_stockfish(config["skill"])
        if engine is not None:
            print(
                f"[Stockfish] loaded, skill={config['skill']}, think={config['think_time']}s"
            )
        else:
            print("[HINT] Stockfish unavailable; using built-in engine")

    # ---- 初始化棋局 ----
    board = chess.Board()  # 初始局面
    selected_square = None  # 当前选中的棋子格子（None = 未选中）
    last_move = None  # 上一步走法（用于高亮）

    # 启用按键长按重复事件 (delay_ms, interval_ms)
    pygame.key.set_repeat(300, 50)

    # ---- 侧边栏状态（用字典存储，方便传递给线程和绘制函数） ----
    panel = {
        "input": "",  # 输入框文字
        "ime_text": "",  # 输入法正在组合的临时文字
        "cursor": 0,  # 光标位置
        "active": False,  # 输入框是否处于激活状态
        "last_question": "",  # 上一次提问的问题（用于展示）
        "result": None,  # AI 分析结果
        "stream_result": None,  # AI 流式返回时的临时结果
        "thinking": False,  # 是否正在等待 AI 回复
        "error": None,  # 错误信息
    }

    clock = pygame.time.Clock()
    game_active = True

    # 侧边栏控件的位置（用于鼠标点击检测）
    input_rect = pygame.Rect(PANEL_X + 10, 52, PANEL_WIDTH - 20, 34)
    btn_rect = pygame.Rect(PANEL_X + 10, 52 + 34 + 8, 56, 26)
    undo_rect = pygame.Rect(PANEL_X + 76, 52 + 34 + 8, 56, 26)

    # ---- Auto Play 相关状态 ----
    auto_play = difficulty_key == "auto"
    white_waiting_for_agent = False
    white_delay_until = 0
    black_delay_until = 0

    # ---- 主游戏循环 ----
    while game_active:
        clock.tick(60)  # 限制帧率 60 FPS

        # === 第一步：绘制所有内容 ===
        win.fill(BOARD_BG)
        draw_board(win)
        draw_coordinates(win)
        draw_last_move_highlight(win, last_move)
        draw_highlights(win, selected_square, board)
        draw_pieces(win, board, pieces)
        draw_game_over_overlay(win, board)
        _draw_side_panel(win, panel)
        pygame.display.update()

        # === 第二步：AI 自动走子（轮到黑方时） ===
        if board.turn == chess.BLACK and not board.is_game_over():
            if black_delay_until == 0:
                black_delay_until = time.time() + 1.0  # 稍微停顿 1 秒，不要走太快
            elif time.time() >= black_delay_until:
                ai_move = get_ai_move(board, engine, difficulty_key)
                animate_move(win, board, pieces, ai_move, last_move)
                board.push(ai_move)
                last_move = ai_move
                selected_square = None
                black_delay_until = 0

        # === 第二点五步：Auto Play 白方自动走子 ===
        if auto_play and board.turn == chess.WHITE and not board.is_game_over():
            if not panel["thinking"] and not white_waiting_for_agent:
                # 触发 Agent 分析
                panel["input"] = "作为白方，请分析局势并推荐最佳走法。"
                _submit_question(board, panel)
                white_waiting_for_agent = True
            elif not panel["thinking"] and white_waiting_for_agent:
                # Agent 已经分析完毕，等待几秒钟让用户阅读面板
                if white_delay_until == 0:
                    white_delay_until = time.time() + 6.0  # 停留 6 秒
                elif time.time() >= white_delay_until:
                    res = panel.get("result")
                    move = None
                    if res and res.get("is_legal") and res.get("best_move_uci"):
                        try:
                            move = chess.Move.from_uci(res["best_move_uci"])
                        except Exception:
                            pass

                    if move is None or move not in board.legal_moves:
                        # Fallback: 如果 Agent 失败或返回不合法走法，直接调内置 AI 走
                        move = get_ai_move(board, engine, difficulty_key)

                    animate_move(win, board, pieces, move, last_move)
                    board.push(move)
                    last_move = move
                    selected_square = None

                    # 重置状态，准备下一次
                    white_waiting_for_agent = False
                    white_delay_until = 0
                    panel["input"] = ""
                    panel["result"] = None  # 清空面板准备下一回合

        # === 第三步：处理事件 ===
        for event in pygame.event.get():
            # 获取当前鼠标位置（用于滚轮事件等判断）
            mx, my = pygame.mouse.get_pos()

            # 关闭窗口
            if event.type == pygame.QUIT:
                if engine is not None:
                    del engine
                pygame.quit()
                exit()

            # ---- 键盘事件 ----
            if event.type == pygame.KEYDOWN:
                # 以下按键仅在输入框激活时生效
                if panel["active"]:
                    if event.key == pygame.K_RETURN:
                        # 如果正在输入拼音，回车是确认拼音，不要提交问题
                        if panel.get("ime_text", "") == "":
                            # Enter → 提交问题
                            _submit_question(board, panel)
                    elif event.key == pygame.K_ESCAPE:
                        # Esc → 取消输入
                        panel["active"] = False
                    elif event.key == pygame.K_BACKSPACE:
                        # 如果输入法（IME）正在组合拼音，让输入法自己处理退格，不删除已提交的汉字
                        if panel.get("ime_text", "") != "":
                            pass
                        else:
                            # Backspace → 删除光标前一个字符
                            if panel["cursor"] > 0:
                                panel["input"] = (
                                    panel["input"][: panel["cursor"] - 1]
                                    + panel["input"][panel["cursor"] :]
                                )
                                panel["cursor"] -= 1
                    elif event.key == pygame.K_DELETE:
                        # Delete → 删除光标后一个字符
                        if panel["cursor"] < len(panel["input"]):
                            panel["input"] = (
                                panel["input"][: panel["cursor"]]
                                + panel["input"][panel["cursor"] + 1 :]
                            )
                    elif event.key == pygame.K_LEFT:
                        # 左箭头 → 光标左移
                        if panel["cursor"] > 0:
                            panel["cursor"] -= 1
                    elif event.key == pygame.K_RIGHT:
                        # 右箭头 → 光标右移
                        if panel["cursor"] < len(panel["input"]):
                            panel["cursor"] += 1
                    elif event.key == pygame.K_HOME:
                        # Home → 光标跳到开头
                        panel["cursor"] = 0
                    elif event.key == pygame.K_END:
                        # End → 光标跳到末尾
                        panel["cursor"] = len(panel["input"])

            # ---- 文字输入事件（IME 输入法，支持中文） ----
            if event.type == pygame.TEXTINPUT:
                if panel["active"]:
                    # 提交了文字，清空拼音组合状态
                    panel["ime_text"] = ""
                    # 在光标位置插入输入的文字
                    panel["input"] = (
                        panel["input"][: panel["cursor"]]
                        + event.text
                        + panel["input"][panel["cursor"] :]
                    )
                    panel["cursor"] += len(event.text)

            if hasattr(pygame, "TEXTEDITING") and event.type == pygame.TEXTEDITING:
                if panel["active"]:
                    panel["ime_text"] = event.text

            # ---- 鼠标事件 ----
            if event.type == pygame.MOUSEWHEEL:
                # 鼠标滚轮滚动侧边栏
                if mx > PANEL_X:  # 只在侧边栏区域滚动
                    scroll_speed = 30
                    current_scroll = panel.get("scroll_y", 0)

                    # macOS 下 event.y 有时不可靠，直接使用 + event.y 尝试修复
                    # 很多时候 event.y 是正数表示向上滚动内容（向下滑动手指）
                    new_scroll = current_scroll + event.y * scroll_speed

                    # 限制滚动范围
                    panel["scroll_y"] = max(
                        0, min(new_scroll, panel.get("max_scroll_y", 0))
                    )

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                # 点击侧边栏区域
                if input_rect.collidepoint(mx, my):
                    # 点击输入框 → 激活
                    panel["active"] = True
                    panel["cursor"] = len(panel["input"])
                elif btn_rect.collidepoint(mx, my):
                    # 点击发送按钮 → 提交问题
                    _submit_question(board, panel)
                elif undo_rect.collidepoint(mx, my):
                    # 点击悔棋按钮
                    if len(board.move_stack) > 0:
                        if auto_play:
                            board.pop()
                            white_waiting_for_agent = False
                            white_delay_until = 0
                            black_delay_until = 0
                        else:
                            if board.turn == chess.WHITE:
                                # 轮到白方，说明黑方已经走完了，需要退两步
                                if len(board.move_stack) >= 2:
                                    board.pop()
                                    board.pop()
                                else:
                                    board.pop()
                            else:
                                # 轮到黑方，说明白方刚走完，黑方（AI）还在思考，退一步
                                board.pop()
                                black_delay_until = 0

                        # 更新界面状态
                        last_move = board.peek() if board.move_stack else None
                        selected_square = None
                        panel["result"] = None
                        panel["stream_result"] = None
                        panel["last_question"] = ""
                        panel["thinking"] = False
                elif mx > PANEL_X:
                    # 点击侧边栏其他位置 → 取消激活
                    panel["active"] = False
                else:
                    # 点击棋盘区域 → 处理走子操作
                    panel["active"] = False

                    # 游戏结束后点击棋盘 → 返回菜单
                    if board.is_game_over():
                        game_active = False
                        break

                    # 只有白方回合才能走子，且不能处于自动托管模式
                    if board.turn != chess.WHITE or auto_play:
                        continue

                    clicked_square = pixel_to_square(mx, my)

                    if selected_square is None:
                        # 第一步：选中一个白方棋子
                        piece = board.piece_at(clicked_square)
                        if piece is not None and piece.color == chess.WHITE:
                            selected_square = clicked_square
                    else:
                        # 第二步：点击目标格
                        if clicked_square == selected_square:
                            # 点击同一格 → 取消选中
                            selected_square = None
                        else:
                            piece = board.piece_at(clicked_square)
                            if piece is not None and piece.color == chess.WHITE:
                                # 点击了另一个白方棋子 → 切换选中
                                selected_square = clicked_square
                            else:
                                # 尝试走子（兵到达底线自动升变为皇后）
                                move = chess.Move(selected_square, clicked_square)
                                src_piece = board.piece_at(selected_square)
                                if (
                                    src_piece is not None
                                    and src_piece.piece_type == chess.PAWN
                                ):
                                    to_rank = chess.square_rank(clicked_square)
                                    if to_rank == 7 or to_rank == 0:
                                        move = chess.Move(
                                            selected_square,
                                            clicked_square,
                                            promotion=chess.QUEEN,
                                        )

                                # 走法合法 → 执行并播放动画
                                if move in board.legal_moves:
                                    animate_move(win, board, pieces, move, last_move)
                                    board.push(move)
                                    last_move = move
                                selected_square = None

    # 清理 Stockfish 引擎
    if engine is not None:
        del engine


# ==================== 程序入口 ====================


def main():
    """主函数：加载棋子图像 → 循环「难度选择 → 对局」"""
    pieces = load_pieces(SQUARE_SIZE)
    while True:
        difficulty = select_difficulty(WIN)
        run_game(WIN, pieces, difficulty)


if __name__ == "__main__":
    main()
