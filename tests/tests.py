import signal
from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock, patch

from parameterized import parameterized

from game.main import Cell, GameMode, Gesture, GestureSuit, RockPaperScissor


def abort_after_timeout(timeout):
    def decorator(f):
        def wrapper(*args, **kwargs):
            def signal_handler(signum, frame):
                raise OSError(f"Aborted function as it reached {timeout}s")

            signal.signal(signal.SIGALRM, signal_handler)
            signal.alarm(timeout)

            f(*args, **kwargs)

            signal.alarm(0)

        return wrapper

    return decorator


class GestureTests(TestCase):
    def test_init(self):
        g = Gesture(GestureSuit.ROCK)
        self.assertEqual(g.suit, GestureSuit.ROCK)

    def test_gt(self):
        for gs1, gs2 in Gesture.SUIT_TO_WEAKER_SUIT.items():
            self.assertTrue(Gesture(gs1) > Gesture(gs2))

    def test_equals(self):
        for gs in GestureSuit:
            g1 = Gesture(gs)
            g2 = Gesture(gs)
            self.assertTrue(g1.equals(g2))

    def test_transform(self):
        g = Gesture(GestureSuit.ROCK)
        g.transform(GestureSuit.PAPER)

        self.assertEqual(g.suit, GestureSuit.PAPER)


class CellTests(TestCase):
    @patch.object(Cell, "_assign_gesture")
    def test_init_no_gesture(self, _assign_gesture):
        cell = Cell(MagicMock())

        self.assertIsNone(cell.gesture)
        self.assertFalse(_assign_gesture.called)

    @patch.object(Cell, "_assign_gesture")
    def test_init_with_gesture(self, _assign_gesture):
        g = Gesture(GestureSuit.ROCK)
        cell = Cell(MagicMock(), g)

        self.assertIsNotNone(cell.gesture)
        _assign_gesture.assert_called_once_with(g)

    def test_is_empty_true(self):
        cell = Cell(MagicMock())
        self.assertTrue(cell._is_empty)

    def test_is_empty_false(self):
        cell = Cell(MagicMock(), Gesture(GestureSuit.ROCK))
        self.assertFalse(cell._is_empty)

    def test_stats(self):
        cell = Cell(MagicMock())
        self.assertEqual(cell.stats, cell.game.stats)

    def test_assign_gesture(self):
        cell = Cell(MagicMock())
        g = Gesture(GestureSuit.ROCK)
        cell._assign_gesture(g)

        self.assertEqual(cell.gesture, g)
        self.assertEqual(g.cell, cell)

    def test_remove_gesture(self):
        cell = Cell(MagicMock())
        g = Gesture(GestureSuit.ROCK)
        cell._assign_gesture(g)

        cell.remove_gesture()

        self.assertIsNone(cell.gesture)
        self.assertIsNone(g.cell)

    @parameterized.expand(
        [
            ("_challenge_transform", GameMode.TRANSFORM),
        ]
    )
    def test_get_challenge_function(self, function_name, mode):
        game = MagicMock(GAME_MODE=mode)
        cell = Cell(game)
        self.assertEqual(getattr(cell, function_name), cell._get_challenge_function())

    def test_run_challenge_empty(self):
        game = MagicMock()

        incoming_gesture = Gesture(GestureSuit.ROCK)
        cell_from = Cell(game)
        cell_from._assign_gesture(incoming_gesture)

        cell_to = Cell(game)

        cell_from.remove_gesture = MagicMock()
        cell_to._assign_gesture = MagicMock()

        cell_to.run_challenge(incoming_gesture)

        cell_from.remove_gesture.assert_called_once_with()
        cell_to._assign_gesture.assert_called_once_with(incoming_gesture)

    @patch.object(Cell, "_get_challenge_function")
    def test_run_challenge_not_empty(self, _get_challenge_function):
        game = MagicMock()

        incoming_gesture = Gesture(GestureSuit.ROCK)
        cell_from = Cell(game)
        cell_from._assign_gesture(incoming_gesture)

        cell_to = Cell(game)
        cell_to._assign_gesture(Gesture(GestureSuit.ROCK))

        challenge_function = MagicMock()
        _get_challenge_function.return_value = challenge_function

        cell_to.run_challenge(incoming_gesture)

        challenge_function.assert_called_once_with(incoming_gesture)

    def test_challenge_transform_incoming_is_greater(self):
        game = RockPaperScissor()

        suite = GestureSuit.SCISSOR
        cell = Cell(game, gesture=Gesture(suite))
        incoming_suite = GestureSuit.ROCK
        incoming_gesture = Gesture(incoming_suite)

        self.assertGreater(incoming_gesture, cell.gesture)

        cell._challenge_transform(incoming_gesture)

        self.assertEqual(cell.gesture.suit, incoming_suite)

        self.assertEqual(
            game.stats[f"remaining_{GestureSuit.ROCK.value}"], game.COUNT_ROCK + 1
        )
        self.assertEqual(
            game.stats[f"remaining_{GestureSuit.SCISSOR.value}"], game.COUNT_SCISSOR - 1
        )

    def test_challenge_transform_incoming_is_lower(self):
        game = RockPaperScissor()

        suite = GestureSuit.ROCK
        cell = Cell(game, gesture=Gesture(suite))
        incoming_suite = GestureSuit.SCISSOR
        incoming_gesture = Gesture(incoming_suite)

        self.assertGreater(cell.gesture, incoming_gesture)

        cell._challenge_transform(incoming_gesture)

        self.assertEqual(cell.gesture.suit, suite)

        self.assertEqual(
            game.stats[f"remaining_{GestureSuit.ROCK.value}"], game.COUNT_ROCK + 1
        )
        self.assertEqual(
            game.stats[f"remaining_{GestureSuit.SCISSOR.value}"], game.COUNT_SCISSOR - 1
        )

    def test_challenge_transform_incoming_is_equal(self):
        game = RockPaperScissor()

        suite = GestureSuit.SCISSOR
        cell = Cell(game, gesture=Gesture(suite))
        incoming_suite = GestureSuit.SCISSOR
        incoming_gesture = Gesture(incoming_suite)

        self.assertTrue(incoming_gesture.equals(cell.gesture))

        cell._challenge_transform(incoming_gesture)

        self.assertEqual(cell.gesture.suit, incoming_suite)

        self.assertEqual(
            game.stats[f"remaining_{GestureSuit.SCISSOR.value}"], game.COUNT_SCISSOR
        )


class RockPaperScissorTests(TestCase):
    @patch("game.main.random.shuffle")
    def test_init(self, shuffle):
        game = RockPaperScissor(
            height=3,
            width=5,
            count_rock=2,
            count_paper=3,
            count_scissor=4,
        )
        self.assertEqual(15, game.COUNT_CELLS)
        self.assertEqual(9, game.COUNT_GESTURES)

        r = GestureSuit.ROCK
        p = GestureSuit.PAPER
        s = GestureSuit.SCISSOR
        n = None

        self.assertEqual(
            [
                [r, r, p, p, p],
                [s, s, s, s, n],
                [n, n, n, n, n],
            ],
            [
                [cell.gesture and cell.gesture.suit for cell in row]
                for row in game.matrix
            ],
        )

        self.assertEqual(0, game.stats["round_number"])
        self.assertEqual(2, game.stats[f"remaining_{GestureSuit.ROCK.value}"])
        self.assertEqual(3, game.stats[f"remaining_{GestureSuit.PAPER.value}"])
        self.assertEqual(4, game.stats[f"remaining_{GestureSuit.SCISSOR.value}"])

    def test_get_all_surrounding_cells(self):
        game = RockPaperScissor()

        # top-left corner
        self.assertEqual(
            [
                game.matrix[0][1],
                game.matrix[1][0],
                game.matrix[1][1],
            ],
            game._get_all_surrounding_cells(game.matrix[0][0]),
        )

        # top-right corner
        self.assertEqual(
            [
                game.matrix[0][-2],
                game.matrix[1][-2],
                game.matrix[1][-1],
            ],
            game._get_all_surrounding_cells(game.matrix[0][-1]),
        )

        # bottom-right corner
        self.assertEqual(
            [
                game.matrix[-2][-2],
                game.matrix[-2][-1],
                game.matrix[-1][-2],
            ],
            game._get_all_surrounding_cells(game.matrix[-1][-1]),
        )

        # bottom-left corner
        self.assertEqual(
            [
                game.matrix[-2][0],
                game.matrix[-2][1],
                game.matrix[-1][1],
            ],
            game._get_all_surrounding_cells(game.matrix[-1][0]),
        )

        # top side
        self.assertEqual(
            [
                game.matrix[0][4],
                game.matrix[0][6],
                game.matrix[1][4],
                game.matrix[1][5],
                game.matrix[1][6],
            ],
            game._get_all_surrounding_cells(game.matrix[0][5]),
        )

        # right side
        self.assertEqual(
            [
                game.matrix[4][-2],
                game.matrix[4][-1],
                game.matrix[5][-2],
                game.matrix[6][-2],
                game.matrix[6][-1],
            ],
            game._get_all_surrounding_cells(game.matrix[5][-1]),
        )

        # bottom side
        self.assertEqual(
            [
                game.matrix[-2][4],
                game.matrix[-2][5],
                game.matrix[-2][6],
                game.matrix[-1][4],
                game.matrix[-1][6],
            ],
            game._get_all_surrounding_cells(game.matrix[-1][5]),
        )

        # left side
        self.assertEqual(
            [
                game.matrix[4][0],
                game.matrix[4][1],
                game.matrix[5][1],
                game.matrix[6][0],
                game.matrix[6][1],
            ],
            game._get_all_surrounding_cells(game.matrix[5][0]),
        )

        # Central
        self.assertEqual(
            [
                game.matrix[4][2],
                game.matrix[4][3],
                game.matrix[4][4],
                game.matrix[5][2],
                game.matrix[5][4],
                game.matrix[6][2],
                game.matrix[6][3],
                game.matrix[6][4],
            ],
            game._get_all_surrounding_cells(game.matrix[5][3]),
        )

    @patch.object(RockPaperScissor, "_get_all_surrounding_cells")
    def test_get_available_cells_to_move_to(self, _get_all_surrounding_cells):
        game = RockPaperScissor()
        cell = Cell(game, Gesture(GestureSuit.ROCK))

        c0 = Cell(game)
        c1 = Cell(game, Gesture(GestureSuit.ROCK))
        c2 = Cell(game)
        c3 = Cell(game, Gesture(GestureSuit.SCISSOR))
        c4 = Cell(game)
        c5 = Cell(game)
        c6 = Cell(game, Gesture(GestureSuit.PAPER))
        c7 = Cell(game, Gesture(GestureSuit.ROCK))

        _get_all_surrounding_cells.return_value = [c0, c1, c2, c3, c4, c5, c6, c7]
        filtered_cells = game._get_available_cells_to_move_to(cell.gesture)

        self.assertEqual([c0, c2, c3, c4, c5, c6], filtered_cells)
        _get_all_surrounding_cells.assert_called_once_with(cell)

    @patch("game.main.random.choice")
    @patch.object(RockPaperScissor, "_get_available_cells_to_move_to")
    def test_move_gesture(self, _get_available_cells_to_move_to, random_choice):
        game = RockPaperScissor()

        c0 = Cell(game)
        c0.run_challenge = MagicMock()

        c1 = Cell(game, Gesture(GestureSuit.ROCK))
        c2 = Cell(game)
        _get_available_cells_to_move_to.return_value = [c0, c1, c2]

        random_choice.side_effect = lambda cells: cells[0]

        gesture = Gesture(GestureSuit.SCISSOR)
        game._move_gesture(gesture)

        _get_available_cells_to_move_to.assert_called_once_with(gesture)
        c0.run_challenge.assert_called_once_with(gesture)

    @patch.object(Cell, "run_challenge")
    @patch.object(RockPaperScissor, "_get_available_cells_to_move_to")
    def test_move_gesture_no_available_cells(
        self, _get_available_cells_to_move_to, run_challenge
    ):
        game = RockPaperScissor()

        _get_available_cells_to_move_to.return_value = []

        gesture = Gesture(GestureSuit.SCISSOR)
        game._move_gesture(gesture)

        _get_available_cells_to_move_to.assert_called_once_with(gesture)
        self.assertFalse(run_challenge.called)

    @patch.object(RockPaperScissor, "_move_gesture")
    def test_move_gestures(self, _move_gesture):
        game = RockPaperScissor()
        game._move_gestures()
        self.assertEqual(len(game.gestures), len(_move_gesture.call_args_list))

    @patch.object(RockPaperScissor, "_move_gestures")
    @patch.object(RockPaperScissor, "_print_board")
    def test_play_round(self, _print_board, _move_gestures):
        game = RockPaperScissor()

        self.assertEqual(0, game.stats["round_number"])
        game._play_round()
        self.assertEqual(1, game.stats["round_number"])

        _print_board.assert_called()
        _move_gestures.assert_called()

    @patch("game.main.os.name", "posix")
    @patch("game.main.os.system")
    def test_clear_screen_posix(self, os_system):
        game = RockPaperScissor()
        game._clear_screen()
        os_system.assert_called_once_with("clear")

    @patch("game.main.os.name", "abc")
    @patch("game.main.os.system")
    def test_clear_screen_not_posix(self, os_system):
        game = RockPaperScissor()
        game._clear_screen()
        os_system.assert_called_once_with("cls")

    @patch("sys.stdout", new_callable=StringIO)
    @patch.object(RockPaperScissor, "_clear_screen")
    def test_print_board(self, _clear_screen, mock_out):
        game = RockPaperScissor()
        game._print_board()

        _clear_screen.assert_called()

        self.assertIn(
            """
[=========================]
[    Rock-Paper-Scissor   ]
[=========================]
            """.strip(),
            mock_out.getvalue(),
        )

    @parameterized.expand(
        [
            (0, 0, 0, False),
            (9, 9, 9, False),
            (9, 9, 0, False),
            (9, 0, 9, False),
            (0, 9, 9, False),
            (9, 0, 0, True),
            (0, 9, 0, True),
            (0, 0, 9, True),
        ]
    )
    def test_is_game_over(
        self, remaining_rock, remaining_paper, remaining_scissor, is_game_over
    ):
        game = RockPaperScissor()

        game.stats[f"remaining_{GestureSuit.ROCK.value}"] = remaining_rock
        game.stats[f"remaining_{GestureSuit.PAPER.value}"] = remaining_paper
        game.stats[f"remaining_{GestureSuit.SCISSOR.value}"] = remaining_scissor

        self.assertEqual(game.is_game_over, is_game_over)

    def test_get_winning_suit_game(self):
        game = RockPaperScissor()

        game.stats[f"remaining_{GestureSuit.ROCK.value}"] = 10
        game.stats[f"remaining_{GestureSuit.PAPER.value}"] = 10
        game.stats[f"remaining_{GestureSuit.SCISSOR.value}"] = 10

        with self.assertRaisesRegex(Exception, "The game is not over yet"):
            game.get_winning_suit()

    def test_get_winning_suit_game_is_not_over(self):
        game = RockPaperScissor()

        game.stats[f"remaining_{GestureSuit.ROCK.value}"] = 0
        game.stats[f"remaining_{GestureSuit.PAPER.value}"] = 10
        game.stats[f"remaining_{GestureSuit.SCISSOR.value}"] = 0

        self.assertEqual(GestureSuit.PAPER, game.get_winning_suit())

    @abort_after_timeout(10)
    @patch("sys.stdout", new_callable=StringIO)
    @patch.object(RockPaperScissor, "_clear_screen")
    def test_integration(self, _clear_screen, mock_out):
        game = RockPaperScissor(round_delay=0)
        game.play()
