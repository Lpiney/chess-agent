import os
import tempfile
import unittest

import chess

import board_serializer
import chess_agent
import deepseek_client


class ChessAgentTests(unittest.TestCase):
    def test_extract_tags_parses_expected_fields(self):
        raw_response = """
[UCI] e2e4
[SAN] e4 (白方小兵从 e2 走到 e4)
[TURN] white
[SUMMARY] 你好呀！现在白方更主动一些。
[EXPLANATION] 这步棋先占住中心，还帮后面的棋子打开路。
[PLAN] 先走 e4，再出马到 f3，最后王车易位。
[WARNINGS] 黑方可能争夺中心 | 注意国王安全
""".strip()

        parsed = chess_agent._extract_tags(raw_response)

        self.assertEqual(parsed["best_move_uci"], "e2e4")
        self.assertEqual(parsed["side_to_move"], "white")
        self.assertIn("占住中心", parsed["child_explanation"])
        self.assertEqual(len(parsed["tactical_warnings"]), 2)

    def test_validate_move_accepts_legal_move(self):
        board = chess.Board()

        result = chess_agent._validate_move(board, "e2e4")

        self.assertTrue(result["is_legal"])
        self.assertEqual(result["san"], "e4")

    def test_validate_move_rejects_illegal_move(self):
        board = chess.Board()

        result = chess_agent._validate_move(board, "e2e5")

        self.assertFalse(result["is_legal"])
        self.assertIn("不在当前合法走法列表中", result["message"])


class BoardSerializerTests(unittest.TestCase):
    def test_serialize_move_history_uses_san(self):
        board = chess.Board()
        moves = [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")]

        history = board_serializer.serialize_move_history(moves, board)

        self.assertEqual(history, "1. e4  e5")

    def test_build_user_prompt_contains_key_sections(self):
        board = chess.Board()
        serialized = board_serializer.serialize_board(board)

        prompt = board_serializer.build_user_prompt(serialized, "下一步该怎么走？")

        self.assertIn("[Visual Board]", prompt)
        self.assertIn("[Move History]", prompt)
        self.assertIn("下一步该怎么走？", prompt)


class DeepSeekClientTests(unittest.TestCase):
    def test_load_config_reads_valid_yaml(self):
        config_text = """
deepseek:
  api_key: "test-key"
  base_url: "https://api.deepseek.com/v1"
  model_name: "deepseek-v4-flash"
""".strip()

        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(config_text)
            temp_path = temp_file.name

        try:
            config = deepseek_client.load_config(temp_path)
        finally:
            os.remove(temp_path)

        self.assertEqual(config["deepseek"]["api_key"], "test-key")
        self.assertEqual(config["deepseek"]["model_name"], "deepseek-v4-flash")


if __name__ == "__main__":
    unittest.main()
