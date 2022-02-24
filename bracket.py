from collections import namedtuple
from itertools import zip_longest
import random


class Matchup:
    def __init__(self, player1=None, player2=None):
        self.player1 = player1
        self.player2 = player2
        self.winner = None

    def __getitem__(self, value):
        value = int(value)
        if value not in (0, 1):
            raise ValueError("Must be 0 for player1 or 1 for player2.")

        if value == 0:
            player_won = self.player1 and self.player1 == self.winner
            return '%s%s' % (self.player1 or '',
                             '_[W]' if player_won else '')
        else:
            player_won = self.player2 and self.player2 == self.winner
            return '%s%s' % (self.player2 or ('BYE' if self.player1
                                                    else ''),
                             '_[W]' if player_won else '')

    def __setitem__(self, index, value):
        index = int(index)
        if index not in (0, 1):
            raise ValueError("Must be 0 for player1 or 1 for player2.")

        if index == 0:
            self.player1 = str(value)
        else:
            self.player2 = str(value)

    def declare_winner(self, winner=None):
        if self.player1 is None:
            raise RuntimeError("It is too early to declare a winner in "
                               "this matchup.")

        if winner not in (self.player1, self.player2):
            raise RuntimeError("%s cannot win the match since they're "
                               "not playing." % winner)

        if self.player2 is None:
            self.winner = self.player1
        else:
            self.winner = winner

        return self

    def __repr__(self):
        p1, p2 = self.player1, self.player2

        if p1 is None:
            return 'Blank Matchup'
        elif p2 is None:
            return '%s (Bye)' % p1

        p1won = p1 and p1 == self.winner
        p2won = p2 and p2 == self.winner
        return '%s%s vs %s%s' % (
            p1, ' [W]' if p1won else '',
            p2, ' [W]' if p2won else '',
        )


class Bracket:
    def __init__(self, *args):
        self.contenders = list(map(str, args))
        if not (3 < len(self.contenders) <= 32):
            raise ValueError("Brackets of this size are not supported.")

        self.padding = max(max(map(len, self.contenders)), 3) + 3
        for i in range(2, 6):
            if 2**i >= len(self.contenders):
                self.rounds = i
                self.byes = 2**i - len(self.contenders)
                break

        self._bracket = None

    def __getitem__(self, value: int):
        return self._bracket[int(value)]

    def __setitem__(self, index: int, value: 'BracketRound'):
        self._bracket[int(index)] = value

    def __iter__(self):
        return iter(self._bracket)

    def __len__(self):
        return len(self._bracket)

    def __repr__(self):
        return self.draw()

    @property
    def champion(self):
        return self[-2][0].winner

    @property
    def finals(self):
        if self.rounds < 3:
            return None

        finalists = list()
        for matchup in self[2]:
            finalists.extend([matchup[0], matchup[1]])

        finals_bracket = Bracket(*finalists).populate(randomize=False)
        for i in range(3, self.rounds + 1):
            for j, matchup in enumerate(self[i]):
                finals_bracket[i - 2][j] = matchup

        return finals_bracket

    @property
    def width(self):
        width = (self.padding + 2) * (self.rounds + 1)
        for i in range(self.rounds):
            width += 2**i
        return width

    def draw(self):
        lines = [('_' if i % 2 == 0 else '')
                 for i in range(2**(self.rounds + 1) - 1)]

        p = 0
        for i in range(0, len(lines), 2):
            lines[i] += self[0][i // 4][p].ljust(self.padding + 1, '_')
            if p == 1:
                lines[i] += '/'
                p = 0
            else:
                p = 1

        j, p = 0, 0
        for i in range(1, len(lines), 2):
            if i % 4 == 1:
                lines[i] += '%s%s_%s_' % (' ' * (self.padding + 2),
                                          '\\',
                                          ((self[1][j][p] or '')
                                                .ljust(self.padding, '_')))
                if p == 1:
                    p = 0
                    j += 1
                else:
                    p = 1

        pad = self.padding
        for i in range(1, min(self.rounds, 2)):
            start = 2 ** i
            for matchup in self[i]:
                num_spaces = pad + 2
                for j in range(2**i):
                    idx = start + j

                    extra_pad = 0
                    if not lines[idx]:
                        extra_pad = (pad + 2) * i
                    elif j > (2 ** (i - 1) - 1) > 0:
                        extra_pad = pad + 2
                        if len(lines[idx]) == pad + 3 and j != 2:
                            extra_pad += pad + 2
                        elif (i > 2 and j > 3 and i % 2 != j % 2 and
                                len(lines[idx]) <= 2 * pad + 6):
                            extra_pad += pad + 2

                    if (i > 3 and j > (2**(i - 2) + 2**(i - 1) - 1) and
                            i % 2 == j % 2):
                        extra_pad += pad + 2

                    lines[idx] += '\\'.rjust(num_spaces + extra_pad + 1)
                    num_spaces += 2

                lines[(start + 2**i) - 1] += '_%s_' % ((matchup.winner or '')
                                                        .ljust(pad, '_'))
                for j in range(2**i, (2**(i + 1) - 1)):
                    idx = start + j
                    num_spaces -= 2

                    extra_pad = 0
                    if i > 1 and 2**i <= j < (2**i + 2**(i - 1) - 1):
                        extra_pad = pad + 2
                        if i > 2 and j == 2**i:
                            extra_pad += pad + 2
                    lines[idx] += '/'.rjust(num_spaces + extra_pad + 1)

                lines[start + (2 ** (i + 1) - 1)] += '/'
                start += 2**(i + 2)

        return '\n'.join(lines)

    def fill(self):
        for rnd in self:
            for matchup in rnd:
                matchup.declare_winner(matchup[0])
            self.update()
        return self

    def populate(self, randomize=True):
        if self._bracket is not None:
            return

        self._bracket = [BracketRound(self, d)
                         for d in range(self.rounds, -1, -1)]

        if randomize:
            random.shuffle(self.contenders)
            first_half = self.contenders[:2 ** (self.rounds - 1)]
            second_half = self.contenders[2 ** (self.rounds - 1):]
        else:
            first_half = self.contenders[::2]
            second_half = self.contenders[1::2]

        first_round = self._bracket[0]
        for pair in zip_longest(first_half, second_half):
            first_round.add_match(Matchup(*pair))

        for i in range(1, self.rounds):
            for j in range(2 ** (self.rounds - (i + 1))):
                self._bracket[i].add_match(Matchup())

        for matchup in first_round:
            if matchup[1] == 'BYE':
                matchup.declare_winner()

        self.update()
        return self

    def update(self):
        for i in range(self.rounds):
            for j, matchup in enumerate(self[i]):
                if matchup.winner and matchup.winner != self.champion:
                    self[i + 1][j // 2][j % 2] = matchup.winner
        return self


class BracketRound:
    """
    A single round is a collection of matchups, a column in the bracket.
    """
    def __init__(self, bracket: Bracket, distance_from_championship: int=0):
        self.bracket = bracket
        self.distance_from_championship = int(distance_from_championship)
        self.max_matchups = (2 ** self.distance_from_championship) / 2
        self._matchups = list()

    def __getitem__(self, value: int):
        return self._matchups[int(value)]

    def __setitem__(self, index: int, value: Matchup):
        self._matchups[int(index)] = value

    def __len__(self):
        return len(self._matchups)

    def add_match(self, matchup: Matchup):
        if len(self._matchups) <= self.max_matchups:
            self._matchups.append(matchup)
        else:
            raise ValueError("This round is full. No more matchups "
                             "can be added.")

    def __repr__(self):
        titles = {
            0: 'Champion',
            1: 'Finals',
            2: 'Semifinals',
            3: 'Quarterfinals',
        }

        dist = self.distance_from_championship
        try:
            return titles[dist]
        except KeyError:
            return 'Round %i' % (self.bracket.rounds - dist + 1)
