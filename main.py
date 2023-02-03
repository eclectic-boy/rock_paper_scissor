import os
import random
import sys
from enum import Enum
from time import sleep
from typing import Self


class GestureSuit(Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSOR = "scissor"


class GameMode(Enum):
    KILL = "kill"
    TRANSFORM = "transform"


class Gesture:
    SUIT_TO_EMOJI = {
        GestureSuit.ROCK: "🪨",
        GestureSuit.PAPER: "📃",
        GestureSuit.SCISSOR: "🪚",
    }

    SUIT_TO_WEAKER_SUIT: [GestureSuit, GestureSuit] = {
        GestureSuit.ROCK: GestureSuit.SCISSOR,
        GestureSuit.PAPER: GestureSuit.ROCK,
        GestureSuit.SCISSOR: GestureSuit.PAPER,
    }

    def __init__(self, suit: GestureSuit):
        self.suit: GestureSuit = suit
        self.cell: Cell | None = None
        self.alive = True

    def __str__(self) -> str:
        return self.SUIT_TO_EMOJI[self.suit]

    def __gt__(self, other: Self):
        return self.SUIT_TO_WEAKER_SUIT[self.suit] == other.suit

    def equals(self, other: Self):
        return self.suit == other.suit

    def kill(self):
        self.alive = False
        self.cell = None

    def transform(self, suit: GestureSuit):
        self.suit = suit


class Cell:
    GAME_MODE_TO_FUNCTION_NAME = {
        item: f"_challenge_{item.value}" for item in GameMode
    }

    def __init__(self, game: "RockPaperScissor", gesture: Gesture | None = None):
        self.game = game
        self.m = None  # y coordinate
        self.n = None  # x coordinate

        self.gesture: Gesture | None = gesture

        if self.gesture:
            self._assign_gesture(self.gesture)

    @property
    def _is_empty(self):
        return self.gesture is None

    @property
    def stats(self):
        return self.game.stats

    def _assign_gesture(self, gesture: Gesture):
        self.gesture = gesture
        self.gesture.cell = self

    def remove_gesture(self):
        self.gesture.cell = None
        self.gesture = None

    def _challenge_kill(self, incoming: Gesture):
        incoming.cell.remove_gesture()

        if self.gesture > incoming:
            incoming.kill()
            self.stats[f"remaining_{incoming.suit.value}"] -= 1

        else:
            self.gesture.kill()
            self.stats[f"remaining_{self.gesture.suit.value}"] -= 1
            self._assign_gesture(incoming)

    def _challenge_transform(self, incoming: Gesture):
        if self.gesture > incoming:
            self.stats[f"remaining_{incoming.suit.value}"] -= 1
            incoming.transform(self.gesture.suit)
            self.stats[f"remaining_{self.gesture.suit.value}"] += 1

        else:
            self.stats[f"remaining_{self.gesture.suit.value}"] -= 1
            self.gesture.transform(incoming.suit)
            self.stats[f"remaining_{incoming.suit.value}"] += 1

    def _get_challenge_function(self):
        return getattr(self, self.GAME_MODE_TO_FUNCTION_NAME[self.game.GAME_MODE])

    def run_challenge(self, incoming: Gesture):
        if self._is_empty:
            incoming.cell.remove_gesture()
            self._assign_gesture(incoming)
        else:
            challenge_function = self._get_challenge_function()
            challenge_function(incoming)

    def __str__(self) -> str:
        if self._is_empty:
            return "  "
        return str(self.gesture)


class RockPaperScissor:
    def __init__(
        self,
        height: int = 15,
        width: int = 15,
        count_rock: int = 50,
        count_paper: int = 50,
        count_scissor: int = 50,
        game_mode: GameMode = GameMode.TRANSFORM,
        round_delay: float = 0.2,
    ):
        self.M = height
        self.N = width
        self.COUNT_CELLS = self.M * self.N

        self.COUNT_ROCK = count_rock
        self.COUNT_PAPER = count_paper
        self.COUNT_SCISSOR = count_scissor
        self.COUNT_GESTURES = self.COUNT_ROCK + self.COUNT_PAPER + self.COUNT_SCISSOR

        self.ROUND_DELAY = round_delay

        self.GAME_MODE = game_mode
        self.gestures: list[Gesture] = []
        self._init_gestures()

        self.matrix: list[list[Cell]] = []
        self._init_matrix()

        self.stats = {
            "round_number": 0,
            f"remaining_{GestureSuit.ROCK.value}": self.COUNT_ROCK,
            f"remaining_{GestureSuit.PAPER.value}": self.COUNT_PAPER,
            f"remaining_{GestureSuit.SCISSOR.value}": self.COUNT_SCISSOR,
        }

    def _init_gestures(self):
        self.gestures = [
            Gesture(GestureSuit.ROCK) for _ in range(self.COUNT_ROCK)
        ] + [
            Gesture(GestureSuit.PAPER) for _ in range(self.COUNT_PAPER)
        ] + [
            Gesture(GestureSuit.SCISSOR) for _ in range(self.COUNT_SCISSOR)
        ]

    def _init_matrix(self):
        cells = [Cell(self, gesture) for gesture in self.gestures]
        cells += [Cell(self) for _ in range(self.COUNT_CELLS - self.COUNT_GESTURES)]
        random.shuffle(cells)

        self.matrix = []
        x = 0
        for i in range(self.M):
            row = []
            for j in range(self.N):
                cell = cells[x]
                cell.m = i
                cell.n = j
                row.append(cell)
                x += 1
            self.matrix.append(row)

    def _get_all_surrounding_cells(self, cell: Cell):
        m = cell.m
        n = cell.n

        coords_list = (
            (m - 1, n - 1), (m - 1, n), (m - 1, n + 1),
            (m, n - 1), (m, n + 1),
            (m + 1, n - 1), (m + 1, n), (m + 1, n + 1),
        )

        return [
            self.matrix[i][j] for i, j in coords_list if 0 <= i < self.M and 0 <= j < self.N
        ]

    def _get_available_cells_to_move_to(self, gesture: Gesture):
        all_surrounding_cells = self._get_all_surrounding_cells(gesture.cell)
        filtered_cells = [
            c for c in all_surrounding_cells if not c.gesture or not c.gesture.equals(gesture)
        ]
        return filtered_cells

    def _move_gesture(self, gesture: Gesture):
        surrounding_cells = self._get_available_cells_to_move_to(gesture)
        if not surrounding_cells:
            return

        new_cell = random.choice(surrounding_cells)
        new_cell.run_challenge(gesture)

    def _remove_not_alive_gestures(self):
        self.gestures = [g for g in self.gestures if g.alive]

    def _move_gestures(self):
        random.shuffle(self.gestures)

        for gesture in self.gestures:
            # gesture objs can become not alive while in this loop
            if not gesture.alive:
                continue
            self._move_gesture(gesture)

        self._remove_not_alive_gestures()

    def _play_round(self):
        self.stats["round_number"] += 1

        self._move_gestures()

        self._print_board()

    @staticmethod
    def _clear_screen():
        if os.name == "posix":
            os.system("clear")
        else:
            os.system("cls")

    def _print_board(self):
        self._clear_screen()
        sys.stdout.write(f"""
[=========================]
[    Rock-Paper-Scissor   ]
[=========================]

Mode: {self.GAME_MODE.value.title()}
Round: {self.stats["round_number"] or "-":<4}
{GestureSuit.ROCK.value.title()}: {self.stats[f"remaining_{GestureSuit.ROCK.value}"]:<3}   {GestureSuit.PAPER.value.title()}: {self.stats[f"remaining_{GestureSuit.PAPER.value}"]:<3}   {GestureSuit.SCISSOR.value.title()}: {self.stats[f"remaining_{GestureSuit.SCISSOR.value}"]:<3}
        \n""")

        for row in self.matrix:
            sys.stdout.write("|" + "·".join(f"{str(cell):^0}" for cell in row) + "|\n")

        sys.stdout.write("\n")

    @property
    def is_game_over(self) -> bool:
        counts = [self.stats[f"remaining_{suite.value}"] for suite in GestureSuit]
        greater_than_zero_counts = [c for c in counts if c > 0]
        return len(greater_than_zero_counts) == 1

    def get_winning_suit(self):
        if not self.is_game_over:
            raise Exception("The game is not over yet")

        for suite in GestureSuit:
            if self.stats[f"remaining_{suite.value}"]:
                return suite

    def play(self):
        self._print_board()

        while True:
            self._play_round()
            if self.is_game_over:
                break

            sleep(self.ROUND_DELAY)

        sys.stdout.write(f"""
The winner is {self.get_winning_suit().value.title()}!!!
        \n\n""")


if __name__ == "__main__":
    game = RockPaperScissor()

    try:
        game.play()
    except KeyboardInterrupt:
        pass
