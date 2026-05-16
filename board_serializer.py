"""
board_serializer.py — 棋局状态序列化
=====================================
将 python-chess 的 Board 对象转换为 DeepSeek 大模型能理解的结构化文本。
核心思路：模型不是人类，不能"看"棋盘图片，所以需要把棋盘变成文字描述。
所有信息均来源于 board 对象的方法调用，不自行猜测。

【Python 学习要点】：
1. 类型提示 (Type Hints)：如 `board: chess.Board -> str`，指明参数和返回值的类型，方便阅读和排错。
   - 应用场景：几乎所有现代 Python 团队开发中都会使用，有助于 IDE（如 VSCode/PyCharm）自动补全代码并检查潜在错误。
2. 字典 (Dictionary)：使用 `{key: value}` 存储映射关系。
   - 应用场景：非常常用于实现配置表、状态映射（如 HTTP 状态码到描述的映射）、缓存计算结果等。
3. 列表推导式 (List Comprehension)：如 `[f(x) for x in list]`，用简短的代码生成列表。
   - 应用场景：常用于数据过滤、格式转换（如把一组数据库记录的某个字段单独提取出来变成一个列表）。
"""

import chess

# ==================== 符号定义 ====================

# 棋子符号映射字典 (Dictionary)
# 将 python-chess 的字母符号映射为双字母表示
# 第一个字母 = 颜色（W=白方 White, B=黑方 Black）
# 第二个字母 = 棋子类型（K/Q/R/B/N/P 对应 国王/皇后/车/象/马/兵）
PIECE_TO_SYMBOL = {
    "P": "WP",
    "N": "WN",
    "B": "WB",
    "R": "WR",
    "Q": "WQ",
    "K": "WK",
    "p": "BP",
    "n": "BN",
    "b": "BB",
    "r": "BR",
    "q": "BQ",
    "k": "BK",
}

# 棋子的英文名称映射（用于棋子列表的展示）
# chess.PAWN 等是 python-chess 库中定义的常量（通常是整数）
PIECE_NAME = {
    chess.PAWN: "Pawn",
    chess.KNIGHT: "Knight",
    chess.BISHOP: "Bishop",
    chess.ROOK: "Rook",
    chess.QUEEN: "Queen",
    chess.KING: "King",
}

# 颜色的英文名称映射
COLOR_NAME = {
    chess.WHITE: "White",
    chess.BLACK: "Black",
}


# ==================== 工具函数 ====================


def _square_to_coord(square: int) -> str:
    """
    将 python-chess 的格子编号（0~63，a1=0, b1=1, ..., h8=63）
    转换为标准国际象棋坐标字符串，如 'e4'、'g1'。

    【Python 学习要点】：
    - `chr()`: 将 ASCII 码数字转换为对应的字符。例如 chr(97) 是 'a'。
    - `ord()`: 将字符转换为对应的 ASCII 码数字。例如 ord('a') 是 97。
    - 应用场景：常用于处理底层的字符编码转换、加密解密算法、或者像国际象棋这种用字母和数字组合表示坐标的棋盘游戏。
    """
    file_char = chr(chess.square_file(square) + ord("a"))  # 0→a, 1→b, ..., 7→h
    rank_char = str(chess.square_rank(square) + 1)  # 0→1, 1→2, ..., 7→8
    return file_char + rank_char


# ==================== 各字段的序列化函数 ====================
# 每个函数负责将棋局的一个方面转换成结构化文本


def serialize_fen(board: chess.Board) -> str:
    """
    返回当前棋局的 FEN 字符串。
    FEN 是国际象棋的标准局面描述格式，包含所有信息。
    """
    return board.fen()


def serialize_turn(board: chess.Board) -> str:
    """
    返回当前轮到谁走，如 'White to move'。
    【Python 学习要点】：三元运算符 (Ternary Operator) `A if condition else B`
    - 应用场景：在根据条件给变量赋不同值时，能将 4 行的 `if-else` 语句简化为 1 行。常用于状态判断、配置默认值等。
    """
    color = "White" if board.turn == chess.WHITE else "Black"
    return f"{color} to move"


def serialize_board_matrix(board: chess.Board) -> list:
    """
    返回二维棋盘矩阵（用字母代码表示棋子）。
    【Python 学习要点】：
    - 嵌套循环 (Nested Loops)：用于遍历二维数据（如棋盘的行和列）。
      - 应用场景：图像处理（遍历像素点）、表格数据处理、矩阵运算、以及各类棋盘游戏。
    - `range(start, stop, step)`: 生成一个数字序列。这里 `range(7, -1, -1)` 表示从 7 倒数到 0。
      - 应用场景：需要倒序遍历列表，或者只需要每隔几个元素取一次值的情况。
    """
    matrix = []
    for rank in range(7, -1, -1):  # 从 rank 8(索引7) 到 rank 1(索引0)
        row = []
        for file in range(8):  # 从 a列(0) 到 h列(7)
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            if piece is None:
                row.append("--")  # 空格
            else:
                # dict.get(key, default) 安全地获取字典的值，如果键不存在则返回默认值 "--"
                row.append(PIECE_TO_SYMBOL.get(piece.symbol(), "--"))
        matrix.append(row)
    return matrix


def format_board_matrix(matrix: list) -> str:
    """
    将二维矩阵格式化为可读的多行字符串（给模型看）。
    【Python 学习要点】：
    - `enumerate()`: 在遍历列表的同时获取元素的索引（下标）。
      - 应用场景：当你既需要列表里的值，又需要知道它是第几个元素时（比如显示排名“第1名：张三”）。
    - `join()`: 将列表中的字符串用指定的分隔符连接起来。
      - 应用场景：把列表数据拼成一句话，如把 `['a', 'b', 'c']` 拼成逗号分隔的 CSV 格式 `"a,b,c"`。
    - f-string: `f"..."` 可以在字符串中直接嵌入变量，非常直观。
      - 应用场景：几乎所有需要把变量塞进文本里输出的地方，比如日志打印、提示信息拼接等。
    """
    lines = []
    for rank_idx, row in enumerate(matrix):
        rank_num = 8 - rank_idx  # 第一行是 rank 8
        lines.append(f"  Rank {rank_num}: [{', '.join(row)}]")
    return "\n".join(lines)


def serialize_piece_list(board: chess.Board) -> list:
    """
    返回棋盘上所有棋子的列表，按颜色和棋子类型分组排序。
    """
    pieces = []
    for color in [chess.WHITE, chess.BLACK]:
        # 按重要性排序：国王 > 皇后 > 车 > 象 > 马 > 兵
        for piece_type in [
            chess.KING,
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
            chess.PAWN,
        ]:
            squares = board.pieces(piece_type, color)
            for square in squares:
                coord = _square_to_coord(square)
                color_str = COLOR_NAME[color]
                piece_str = PIECE_NAME[piece_type]
                pieces.append(f"{color_str} {piece_str}: {coord}")
    return pieces


def serialize_legal_moves(board: chess.Board) -> list:
    """
    返回所有合法走法，每条同时提供 UCI 和 SAN 两种格式。
    【Python 学习要点】：使用列表推导式 (List Comprehension) 可以进一步简化代码，
    这里保留了基础的 for 循环写法，更适合初学者理解。
    """
    moves = []
    for move in board.legal_moves:
        uci = move.uci()
        san = board.san(move)
        moves.append(f"{uci} / {san}")
    return moves


def serialize_castling_rights(board: chess.Board) -> str:
    """
    返回王车易位权信息，如 'White O-O, Black O-O-O' 或 'None'。
    """
    rights = []
    if board.has_kingside_castling_rights(chess.WHITE):
        rights.append("White O-O")
    if board.has_queenside_castling_rights(chess.WHITE):
        rights.append("White O-O-O")
    if board.has_kingside_castling_rights(chess.BLACK):
        rights.append("Black O-O")
    if board.has_queenside_castling_rights(chess.BLACK):
        rights.append("Black O-O-O")
    return ", ".join(rights) if rights else "None"


def serialize_en_passant(board: chess.Board) -> str:
    """返回过路兵目标格坐标，如 'e3' 或 'None'"""
    if board.ep_square is not None:
        return _square_to_coord(board.ep_square)
    return "None"


def serialize_check_status(board: chess.Board) -> dict:
    """
    返回局面状态：是否被将军/将死/逼和/游戏结束。
    直接返回一个字典，非常清晰。
    """
    return {
        "is_check": board.is_check(),
        "is_checkmate": board.is_checkmate(),
        "is_stalemate": board.is_stalemate(),
        "is_game_over": board.is_game_over(),
    }


def serialize_move_history(move_history: list = None, board: chess.Board = None) -> str:
    """
    返回走法历史，用 SAN 格式（人类可读）。
    【Python 学习要点】：
    - 默认参数 (Default Arguments)：`move_history: list = None`。注意不要将可变对象（如空列表 `[]`）作为默认参数。
      - 应用场景：用于函数有常用默认行为，但偶尔需要定制的场景。
    - `try-except`: 异常处理机制。用于捕获可能发生的错误并安全处理，防止程序崩溃。
      - 应用场景：文件读写（文件可能不存在）、网络请求（可能断网）、数据解析（格式可能错误）等任何可能出错的地方。
    """
    # 巧妙的赋值：如果 move_history 存在则使用它，否则使用空列表
    moves = move_history if move_history else []

    if not moves and board is not None:
        moves = list(board.move_stack)

    if not moves:
        return "No moves yet"

    result_parts = []
    temp_board = chess.Board()
    for i, move in enumerate(moves):
        try:
            san = temp_board.san(move)
            temp_board.push(move)
            move_num = i // 2 + 1  # 计算回合数（// 是整数除法）
            if i % 2 == 0:
                result_parts.append(f"{move_num}. {san}")
            else:
                result_parts.append(san)
        except Exception:
            # 如果解析出错，使用基础的 UCI 格式作为备选方案 (Fallback)
            result_parts.append(move.uci())
            try:
                temp_board.push(move)
            except Exception:
                pass

    return "  ".join(result_parts)


# ==================== 可视化棋盘与描述 ====================


def serialize_visual_board(board: chess.Board) -> str:
    """
    返回一个由 Unicode 棋子组成的可视化棋盘。
    """
    lines = []
    for rank in range(7, -1, -1):
        row_parts = []
        for file in range(8):
            piece = board.piece_at(chess.square(file, rank))
            if piece is not None:
                row_parts.append(piece.unicode_symbol())
            else:
                row_parts.append("·")  # 空格用小圆点表示
        lines.append(f"  {rank + 1}  " + " ".join(row_parts))
    lines.append("     a b c d e f g h")
    return "\n".join(lines)


def serialize_board_description(board: chess.Board) -> str:
    """
    用中文自然语言描述当前棋盘上所有棋子的位置。
    """
    PIECE_CN = {
        chess.KING: "国王",
        chess.QUEEN: "皇后",
        chess.ROOK: "车",
        chess.BISHOP: "象",
        chess.KNIGHT: "马",
        chess.PAWN: "兵",
    }
    result = []
    for color in [chess.WHITE, chess.BLACK]:
        color_cn = "白方" if color == chess.WHITE else "黑方"
        parts = []
        for piece_type in [
            chess.KING,
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
            chess.PAWN,
        ]:
            squares = board.pieces(piece_type, color)
            if not squares:
                continue

            # 使用列表推导式快速转换坐标
            coords = [_square_to_coord(sq) for sq in squares]
            piece_cn = PIECE_CN[piece_type]
            parts.append(f"{piece_cn}在 {', '.join(coords)}")

        result.append(f"  {color_cn}：{'；'.join(parts)}")
    return "\n".join(result)


def serialize_threats(board: chess.Board) -> str:
    """
    分析当前局面的威胁：找出被对方攻击且无人保护的棋子（悬子）。
    【Python 学习要点】：
    - `continue`: 跳过当前循环的剩余部分，直接进入下一次循环。
      - 应用场景：在处理大量数据时，提前过滤掉不需要处理的无效数据（如跳过空行、空棋子），能让后续代码不用缩进，看起来更清爽。
    - 生成器表达式 (Generator Expression): `\n".join(f"  ⚠ {h}" for h in hanging)`，类似列表推导式但更省内存。
      - 应用场景：当要处理的数据量非常大（如几百万条）且只需要遍历一次时，使用生成器可以避免一次性把所有数据加载到内存中。
    """
    PIECE_CN = {
        chess.KING: "国王",
        chess.QUEEN: "皇后",
        chess.ROOK: "车",
        chess.BISHOP: "象",
        chess.KNIGHT: "马",
        chess.PAWN: "兵",
    }
    hanging = []
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        color = piece.color
        opponent = not color  # 颜色是布尔值（True/False），not 反转即可得到对手颜色

        # 检查该格子是否被对方攻击，且没有被己方保护
        if board.is_attacked_by(opponent, square) and not board.is_attacked_by(
            color, square
        ):
            coord = _square_to_coord(square)
            cn = "白方" if color == chess.WHITE else "黑方"
            pcn = PIECE_CN.get(piece.piece_type, "棋子")
            hanging.append(f"{cn} {coord} 的{pcn}无保护，可被吃")

    if not hanging:
        return "当前没有被攻击且无保护的棋子"

    return "\n".join(f"  ⚠ {h}" for h in hanging)


# ==================== 主序列化函数 ====================


def serialize_board(
    board: chess.Board, move_history: list = None, config: dict = None
) -> dict:
    """
    主要序列化函数：将 Board 对象转换为适合大模型理解的结构化字典。
    【Python 学习要点】：
    - `**kwargs` / `*args`: 可以在这里不用，但这里使用字典 `result` 动态添加键值对。
      - 应用场景：在函数需要接受数量不定的参数，或者需要把参数打包传递给另一个函数时非常有用。
    """
    # 默认配置字典的初始化
    if config is None:
        config = {
            k: True
            for k in [
                "include_fen",
                "include_board_matrix",
                "include_piece_list",
                "include_legal_moves",
                "include_turn",
                "include_castling_rights",
                "include_en_passant",
                "include_check_status",
                "include_move_history",
            ]
        }
    else:
        config = config.get("board_output", config)

    result = {}

    # 简化的配置检查
    if config.get("include_fen", True):
        result["fen"] = serialize_fen(board)

    if config.get("include_turn", True):
        result["turn"] = serialize_turn(board)

    # 以下三个是直观的表示方式（总是输出）
    result["visual_board"] = serialize_visual_board(board)
    result["board_description"] = serialize_board_description(board)
    result["threats"] = serialize_threats(board)

    if config.get("include_board_matrix", True):
        matrix = serialize_board_matrix(board)
        result["board_matrix"] = matrix
        result["board_matrix_formatted"] = format_board_matrix(matrix)

    if config.get("include_piece_list", True):
        result["piece_list"] = serialize_piece_list(board)

    if config.get("include_legal_moves", True):
        result["legal_moves"] = serialize_legal_moves(board)

    if config.get("include_castling_rights", True):
        result["castling_rights"] = serialize_castling_rights(board)

    if config.get("include_en_passant", True):
        result["en_passant_square"] = serialize_en_passant(board)

    if config.get("include_check_status", True):
        result["check_status"] = serialize_check_status(board)

    if config.get("include_move_history", True):
        result["move_history"] = serialize_move_history(move_history, board)

    result["halfmove_clock"] = board.halfmove_clock
    result["fullmove_number"] = board.fullmove_number

    return result


# ==================== 用户 Prompt 构建 ====================


def build_user_prompt(serialized: dict, user_question: str) -> str:
    """
    将序列化后的棋局状态拼接为发送给 DeepSeek 的完整用户 prompt。
    【Python 学习要点】：
    - `list.append()`: 高效地将字符串逐个加入列表，最后统一用 `\n".join()` 连接。这比使用 `+=` 拼接字符串性能更好。
      - 应用场景：当你需要拼接大量文本（如生成一篇很长的文章、构建 HTML 网页、生成几十行 Prompt）时，一定要用列表收集再 `join()`，不要用 `+=`，否则程序会变慢。
    """
    parts = []
    parts.append("Below is the current chess position.")

    if "visual_board" in serialized:
        parts.append("[Visual Board]")
        parts.append("UPPERCASE = White pieces, lowercase = Black pieces")
        parts.append("Symbols: K/Q/R/B/N/P = King/Queen/Rook/Bishop/Knight/Pawn")
        parts.append(serialized["visual_board"] + "\n")

    if "board_description" in serialized:
        parts.append("[Piece Locations]")
        parts.append(serialized["board_description"] + "\n")

    if "turn" in serialized:
        parts.append("[Side to Move]")
        parts.append(serialized["turn"] + "\n")

    if "move_history" in serialized:
        parts.append("[Move History]")
        parts.append(serialized["move_history"] + "\n")

    if "legal_moves" in serialized:
        parts.append("[Legal Moves] (UCI / SAN)")
        # 列表推导式结合 join，写法更简洁
        parts.append("\n".join(f"  {m}" for m in serialized["legal_moves"]) + "\n")

    if "check_status" in serialized:
        parts.append("[Position Status]")
        cs = serialized["check_status"]
        parts.append(f"  In check: {'Yes' if cs['is_check'] else 'No'}")
        parts.append(f"  Checkmate: {'Yes' if cs['is_checkmate'] else 'No'}")
        parts.append(f"  Stalemate: {'Yes' if cs['is_stalemate'] else 'No'}\n")

    if "threats" in serialized:
        parts.append("[Threat Analysis]")
        parts.append(serialized["threats"] + "\n")

    if "castling_rights" in serialized:
        parts.append("[Castling Rights]")
        parts.append(serialized["castling_rights"] + "\n")

    if "en_passant_square" in serialized:
        parts.append("【过路兵目标格】")
        parts.append(serialized["en_passant_square"] + "\n")

    # 用户问题
    parts.append("=" * 40)
    parts.append(f"【用户问题】\n{user_question}\n")
    parts.append(
        "请你根据当前棋局，利用可视化棋盘和棋子位置描述来理解局面，然后回答用户的问题。"
    )
    parts.append(
        "你的回答要具体，要提到具体格子的坐标（比如 e4、f3），不要只说抽象概念。"
    )

    return "\n".join(parts)
