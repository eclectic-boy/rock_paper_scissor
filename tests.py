from unittest import TestCase
from unittest.mock import MagicMock, patch

from parameterized import parameterized

from main import Gesture, GestureSuit, Cell, GameMode, RockPaperScissor


class GestureTests(TestCase):
    def test_init(self):
        g = Gesture(GestureSuit.ROCK)
        self.assertEqual(g.suit, GestureSuit.ROCK)

    def test_gt(self):
        for gs1, gs2 in Gesture.SUIT_TO_WEAKER_SUIT.items():
            self.assertTrue(Gesture(gs1) > Gesture(gs2))

    def test_eq(self):
        for gs in GestureSuit:
            self.assertTrue(Gesture(gs) == Gesture(gs))

    def test_kill(self):
        g = Gesture(GestureSuit.ROCK)
        g.cell = Cell(MagicMock())

        g.kill()

        self.assertFalse(g.alive)
        self.assertIsNone(g.cell)

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

    @parameterized.expand([
        ("_challenge_transform", GameMode.TRANSFORM),
        ("_challenge_kill", GameMode.KILL),
    ])
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

        self.assertEqual(incoming_gesture, cell.gesture)

        cell._challenge_transform(incoming_gesture)

        self.assertEqual(cell.gesture.suit, incoming_suite)

        self.assertEqual(
            game.stats[f"remaining_{GestureSuit.SCISSOR.value}"], game.COUNT_SCISSOR
        )
