import datetime
import itertools
from doctest import testmod
from functools import reduce
from itertools import combinations, permutations, product
from math import factorial, pow, sqrt
from typing import Tuple, Union, Any, Sequence, List

from Permutation import composition, T
from SymmetryGroup import SymmetryGroup


class SudokuGroup(SymmetryGroup):
    """ Représente le SymmetryGroup d'un sudoku.
        >>> sudoku = SudokuGroup(2)
        >>> sudoku.cardinality
        128
        >>> sudoku.identity
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.degree = seed ** 2
        sudoku = SudokusStructure(seed)
        sudoku.all_elements()
        super().__init__(sudoku.E, self.degree ** 2)


class SudokuStructure(object):
    """ Représente un sudoku sous la forme d'une permutation.
    Une permutation est de longueur correspondant aux nombres de cases et ces éléments aux cases.
    On lit la permutation de haut gauche vers bas droit.

    Attributs
    ---------

    Methodes
    --------
        permute_band(self, line_1: int, line_2: int) -> List[int]
            La permutation d'une bande à une autre bande.
        permute_stack(self, column_1: int, column_2: int) -> List[int]
            La permutation d'une pile à une autre pile.
        permute_line(self, line_1: int, line_2: int) -> List[int]
            La permutation d'une ligne à une autre ligne.
        permute_column(self, column_1: int, column_2: int) -> List[int]
            permutation d'une colonne à une autre colonne.
        diagonal_reflexion(self) -> List[int]
        get_line(self, line: int) -> List[int]
        get_column(self, column: int) -> List[int]
        get_case(self, line: int, column: int) -> int
        to_permute(self) -> List[List[Tuple[int, ...]]]
        split_grid(self) -> List[List[int]]

    Doctest
    -------
        >>> sudoku = SudokuStructure(2)
        >>> print(sudoku)
        self.degree = 4
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
             |  C1  |  C2  |||  C3  |  C4  |
              -----------------------------
         L1-|   1   |  2   |||  3   |  4   |
         L2-|   5   |  6   |||  7   |  8   |
              -----------------------------
         L3-|   9   |  10  |||  11  |  12  |
         L4-|   13  |  14  |||  15  |  16  |
              -----------------------------

        >>> sudoku_solved = SudokuStructure(2, (1, 2, 3, 4, 2, 1, 4, 3, 3, 4, 1, 2, 4, 3, 2, 1))
        >>> print(sudoku_solved)
        self.degree = 4
        (1, 2, 3, 4, 2, 1, 4, 3, 3, 4, 1, 2, 4, 3, 2, 1)
             |  C1  |  C2  |||  C3  |  C4  |
              -----------------------------
         L1-|   1   |  2   |||  3   |  4   |
         L2-|   2   |  1   |||  4   |  3   |
              -----------------------------
         L3-|   3   |  4   |||  1   |  2   |
         L4-|   4   |  3   |||  2   |  1   |
              -----------------------------
    """

    def __init__(self, seed: int, permutation: Union[Sequence[int], Any] = 0):
        self.seed = seed
        self.degree = seed ** 2
        if isinstance(permutation, Sequence):
            assert self.degree ** 2 == len(permutation), \
                "Wrong permutation initialisation."
            self.permutation = permutation
        else:
            self.permutation = list(range(1, self.degree ** 2 + 1))

    def __str__(self) -> str:
        return "self.degree = " + str(self.degree) + "\n" + str(self.permutation) + "\n" \
               + tostr_permutation_as_sudoku(self.permutation)

    def permute_band(self, line_1: int, line_2: int) -> List[int]:
        """ On permute deux bandes entre elles de groupe de ligne différentes.
        Utilise la méthode get_case.

        Parametres
        ----------
            :type line_1: int
            :param line_1: La bande 1 qu'on change avec la bande 2.
            :type line_2: int
            :param line_2:  La bande 2 qu'on change avec la bande 1.

        Retours
        -------
            :type: List[int]
            :return: Le résultat du sudoku sous forme de liste.

        >>> sudoku = SudokuStructure(2)
        >>> sudoku.permute_band(2, 1)
        [9, 10, 11, 12, 13, 14, 15, 16, 1, 2, 3, 4, 5, 6, 7, 8]
        >>> print(tostr_permutation_as_sudoku(_))
             |  C1  |  C2  |||  C3  |  C4  |
              -----------------------------
         L1-|   9   |  10  |||  11  |  12  |
         L2-|   13  |  14  |||  15  |  16  |
              -----------------------------
         L3-|   1   |  2   |||  3   |  4   |
         L4-|   5   |  6   |||  7   |  8   |
              -----------------------------
        >>> sudoku = SudokuStructure(2)
        >>> SudokuStructure(2).permutation == sudoku.permute_band(2, 2)
        True
        >>> sudoku = SudokuStructure(2)
        >>> sudoku.permute_band(1, 3)
        Traceback (most recent call last):
        AssertionError: Wrong range index: (1 : 3)
        """
        assert 1 <= line_1 <= sqrt(self.degree) and 1 <= line_2 <= sqrt(self.degree), \
            "Wrong range index: (" + str(line_1) + " : " + str(line_2) + ")"
        grid = SudokuStructure(self.seed, self.permutation)
        permuts = self.split_grid()
        permuts = list(zip(permuts[line_1 - 1], permuts[line_2 - 1]))
        for permut in permuts:
            grid.permutation = list(grid.permute_line(*permut))
        return grid.permutation

    def permute_stack(self, column_1: int, column_2: int) -> List[int]:
        """ On permute deux piles entre elles de groupe de pile différentes.
        Utilise la méthode get_case.

        Parametres
        ----------
            :type column_1: int
            :param column_1: La pile 1 qu'on change avec la pile 2.
            :type column_2: int
            :param column_2:  La pile 2 qu'on change avec la pile 1.

        Retours
        -------
            :type: List[int]
            :return: Le résultat du sudoku sous forme de liste.

        Doctest
        -------
            >>> sudoku = SudokuStructure(2)
            >>> sudoku.permute_stack(2, 1)
            [3, 4, 1, 2, 7, 8, 5, 6, 11, 12, 9, 10, 15, 16, 13, 14]
            >>> print(tostr_permutation_as_sudoku(_))
                 |  C1  |  C2  |||  C3  |  C4  |
                  -----------------------------
             L1-|   3   |  4   |||  1   |  2   |
             L2-|   7   |  8   |||  5   |  6   |
                  -----------------------------
             L3-|   11  |  12  |||  9   |  10  |
             L4-|   15  |  16  |||  13  |  14  |
                  -----------------------------
            >>> sudoku = SudokuStructure(2)
            >>> SudokuStructure(2).permutation == sudoku.permute_stack(2, 2)
            True
            >>> sudoku = SudokuStructure(2)
            >>> sudoku.permute_stack(1, 3)
            Traceback (most recent call last):
            AssertionError: Wrong range index: (1 : 3)
        """
        assert 1 <= column_1 <= sqrt(self.degree) and 1 <= column_2 <= sqrt(self.degree), \
            "Wrong range index: (" + str(column_1) + " : " + str(column_2) + ")"
        grid = SudokuStructure(self.seed, self.permutation)
        permuts = self.split_grid()
        permuts = list(zip(permuts[column_1 - 1], permuts[column_2 - 1]))
        for permut in permuts:
            grid.permutation = list(grid.permute_column(*permut))
        return grid.permutation

    def permute_line(self, line_1: int, line_2: int) -> List[int]:
        """ On permute deux lignes entre elles.
        Utilise la méthode get_case.

        Parametres
        ----------
            :type line_1: int
            :param line_1: La ligne 1 qu'on change avec la ligne 2.
            :type line_2: int
            :param line_2:  La ligne 2 qu'on change avec la ligne 1.

        Retours
        -------
            :type: List[int]
            :return: Le résultat du sudoku sous forme de liste.

        Doctest
        -------
            >>> sudoku = SudokuStructure(2)
            >>> sudoku.permute_line(1, 2)
            [5, 6, 7, 8, 1, 2, 3, 4, 9, 10, 11, 12, 13, 14, 15, 16]
            >>> print(tostr_permutation_as_sudoku(_))
                 |  C1  |  C2  |||  C3  |  C4  |
                  -----------------------------
             L1-|   5   |  6   |||  7   |  8   |
             L2-|   1   |  2   |||  3   |  4   |
                  -----------------------------
             L3-|   9   |  10  |||  11  |  12  |
             L4-|   13  |  14  |||  15  |  16  |
                  -----------------------------
            """
        assert 1 <= line_1 <= self.degree ** 2 and 1 <= line_2 <= self.degree ** 2, \
            "A line index chosen isn't into the sudoku."
        line_1 = tuple([self.get_case(line_1, i) for i in range(1, self.degree + 1)])
        line_2 = tuple([self.get_case(line_2, i) for i in range(1, self.degree + 1)])
        grid = list(self.permutation)
        for column in range(self.degree):
            grid[line_1[column] - 1], grid[line_2[column] - 1] = line_2[column], line_1[column]
        return grid

    def permute_column(self, column_1: int, column_2: int) -> List[int]:
        """ On permute deux colonnes entre elles.
        Utilise la méthode get_case.

        Parametres
        ----------
            :type column_1: int
            :param column_1: La colonne 1 qu'on change avec la colonne 2.
            :type column_2: int
            :param column_2:  La colonne 2 qu'on change avec la colonne 1.

        Retours
        -------
            :type: List[int]
            :return: Le résultat du sudoku sous forme de liste.

            >>> sudoku = SudokuStructure(2)
            >>> sudoku.permute_column(1, 2)
            [2, 1, 3, 4, 6, 5, 7, 8, 10, 9, 11, 12, 14, 13, 15, 16]
            >>> print(tostr_permutation_as_sudoku(_))
                 |  C1  |  C2  |||  C3  |  C4  |
                  -----------------------------
             L1-|   2   |  1   |||  3   |  4   |
             L2-|   6   |  5   |||  7   |  8   |
                  -----------------------------
             L3-|   10  |  9   |||  11  |  12  |
             L4-|   14  |  13  |||  15  |  16  |
                  -----------------------------
        """
        assert 1 <= column_1 <= self.degree ** 2 and 1 <= column_2 <= self.degree ** 2, \
            "A column index chosen isn't into the sudoku."
        column_1 = tuple([self.get_case(i, column_1) for i in range(1, self.degree + 1)])
        column_2 = tuple([self.get_case(i, column_2) for i in range(1, self.degree + 1)])
        grid = list(self.permutation)
        for line in range(self.degree):
            grid[column_1[line] - 1], grid[column_2[line] - 1] = column_2[line], column_1[line]
        return grid

    def diagonal_reflexion(self) -> List[int]:
        """  La réflexion, ou symétrie, est une transformation géométrique qui permet d'obtenir la figure image
        «miroir» de la figure initiale par rapport à une droite appelée axe de réflexion.
                    1 | 2          1 | 3
        Par exemple ----- devient  -----
                    3 | 4          2 | 4
        diagonal_reflexion utilise la méthode get_case.

        Retours
        -------
            :type: List[int]
            :return: Le résultat du sudoku sous forme de liste.

        Doctest
        -------
            >>> sudoku = SudokuStructure(2)
            >>> sudoku.diagonal_reflexion()
            [1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15, 4, 8, 12, 16]
            >>> print(tostr_permutation_as_sudoku(_))
                 |  C1  |  C2  |||  C3  |  C4  |
                  -----------------------------
             L1-|   1   |  5   |||  9   |  13  |
             L2-|   2   |  6   |||  10  |  14  |
                  -----------------------------
             L3-|   3   |  7   |||  11  |  15  |
             L4-|   4   |  8   |||  12  |  16  |
                  -----------------------------
        """
        grid = list(self.permutation)
        for (i, j) in product(range(1, self.degree + 1), range(1, self.degree + 1)):
            grid[self.get_case(i, j) - 1] = self.permutation[self.get_case(j, i) - 1]
        return grid

    def get_line(self, line: int) -> List[int]:
        """ Retourne la ligne numéro :line: du sudoku.
        >>> sudoku = SudokuStructure(2)
        >>> sudoku.get_line(2)
        [5, 6, 7, 8]
        """
        return [self.get_case(line, column) for column in range(1, self.degree + 1)]

    def get_column(self, column: int) -> List[int]:
        """ Retourne la colonne numéro :column: du sudoku.
        >>> sudoku = SudokuStructure(2)
        >>> sudoku.get_column(2)
        [2, 6, 10, 14]
        """
        return [self.get_case(line, column) for line in range(1, self.degree + 1)]

    def get_case(self, line: int, column: int) -> int:
        """ Renvoie une case correspondant à la ligne numéro :line: et à la colonne numéro :column: du sudoku.

        Parametres
        ----------
            :type line: int
            :param line: La ligne x de la case (x,y) du sudoku à renvoyer
            :type column: int
            :param column: La colonne y de la case (x,y) du sudoku à renvoyer

        Retours
        -------
            :type: List[int]
            :return: La case (x,y) du sudoku demander.

        Doctest
        -------
            >>> sudoku = SudokuStructure(2)
            >>> sudoku.get_case(2, 1)
            5
            >>> sudoku = SudokuStructure(2)
            >>> sudoku.get_case(2, 10)
            Traceback (most recent call last):
            AssertionError: Wrong range index: (2, 10)
        """
        assert 1 <= line <= self.degree and 1 <= column <= self.degree, \
            "Wrong range index: (" + str(line) + ", " + str(column) + ")"
        return (line - 1) * self.degree + column

    def to_permute(self) -> List[List[Tuple[int, ...]]]:
        """ Les lignes et colonnes qui devront être permuté.

        Retours
        -------
            :type: List[List[Tuple[int, ...]]]
            :return: La liste des lignes et colonnes à permuter.

        Doctest
        -------
            >>> sudoku = SudokusStructure(3)
            >>> sudoku.to_permute()
            [[(1, 2), (1, 3), (2, 3)], [(4, 5), (4, 6), (5, 6)], [(7, 8), (7, 9), (8, 9)]]
        """
        return [combinaison(split, 2) for split in self.split_grid()]

    def split_grid(self) -> List[List[int]]:
        """ Sépare la grille d'un sudoku en :self.seed: liste de longeur :self.seed:.

        Retours
        -------
            :type: List[List[int]]
            :return: Renvoie un grille :self.seed: * :self.seed:.

        Doctest
        -------
            >>> sudoku = SudokusStructure(3)
            >>> sudoku.split_grid()
            [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        """
        split = []
        lst = list(range(1, self.degree + 1))
        for i in range(int(sqrt(self.degree))):
            split.append(lst[i * int(sqrt(self.degree)):(i + 1) * int(sqrt(self.degree))])
        return split


class SudokusStructure(SudokuStructure):
    """ Représente un ensemble de SudokuStructure.

        Methodes
        --------
            add(self, permutation : Tuple[int]) -> None
                " Ajoute une permutation correspondant à un sudoku dans l'ensemble :E: sous forme de tuple"
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.degree = seed ** 2
        super().__init__(seed)
        self.E = {tuple(self.permutation)}

    def __str__(self) -> str:
        result = ""
        for sudoku_structure in self.E:
            result += str(sudoku_structure)
        return result

    def all_elements(self) -> None:
        """ Génere tous les éléments du groupe en répétant des compositions jursqu'à obtenir la bonne cardinalité.
        Utilise la fonction add, generator_set et reduce_permutation_by_composition.
        Utilise la fonction composition
            du fichier Permutation.py.
        """
        self.generator_set()
        result = set(self.E)
        permutation_max = int(pow(factorial(self.seed), (2 * self.seed + 2)) * 2)
        i = 2
        old = 0
        start = datetime.datetime.now()
        start_boucle = datetime.datetime.now()
        while len(result) < permutation_max:
            for combination in set(combinations(self.E, i)) - self.E:
                # if ((datetime.datetime.now() - start_boucle).total_seconds()) > 0.1:
                #     estimate_end(str(i), len(result), permutation_max, start,
                #                  "\t gained+" + str(len(result) - old))
                #     old = len(result)
                #     start_boucle = datetime.datetime.now()
                for permutation in permutations(combination):
                    result.add(self.reduce_permutation_by_composition(permutation))
            i += 1
        self.E = result

    def generator_set(self) -> None:
        """ Genere l'ensemble de base qui servira de générateur pour la méthode all_elements.
        Utilise les méthodes permute_column, permute_line, permute_band, permute_stack et diagonal_reflexion.
        """
        i = 0
        for permuts in self.to_permute():
            for permut in permuts:
                if i == 0:
                    self.add(self.permute_band(*permut))
                    self.add(self.permute_stack(*permut))
                self.add(self.permute_line(*permut))
                self.add(self.permute_column(*permut))
            i += 1
        self.add(self.diagonal_reflexion())

    def reduce_permutation_by_composition(self, permutations):
        """ Réduits des permutations grâce à la fonction composition.
        Utilise la méthode composition du fichier Permutation.py.
        """
        return reduce(composition, permutations)

    def add(self, permutation) -> None:
        " Ajoute une permutation correspondant à un sudoku dans l'ensemble :E: sous forme de tuple"
        self.E.add(tuple(permutation))

    def tostr_permutations_as_sudoku(self):
        return "\n\n".join([str(permutation) + "\n" +
                            tostr_permutation_as_sudoku(permutation) for permutation in sorted(self.E)])


def composition(perm_f, perm_g):
    return tuple(perm_f[perm_g[i] - 1] for i in range(len(perm_f)))  # Ne fonctionne qu'avec des int


def combinaison(E, k) -> List[Tuple[int, ...]]:
    """
    >>> combinaison((1, 2, 3), 2)
    [(1, 2), (1, 3), (2, 3)]
    """
    return sorted(tuple(sorted(partie)) for partie in itertools.combinations(E, k))


def tostr_permutation_as_sudoku(permutation: Sequence[T]) -> str:
    result = "{: ^5}".format("") + "|"
    degree = sqrt(len(permutation))
    assert degree.is_integer(), \
        "permutation doesn't correspond to a valide sudoku format."
    degree = int(degree)
    separator = sqrt(degree)
    for column in range(0, degree):
        result += "{: ^6}".format("C" + str(column + 1))
        result += (column + 1) % separator == 0 and column != degree - 1 and "|" * 3 or "|"
    separe_size = len(result) - 7
    result += "\n" + "{: ^6}".format("") + "-" * separe_size
    for line in range(0, len(permutation)):
        if line % degree == 0:
            result += "\n{: ^6}".format("L" + str(line // degree + 1) + "-|")
        result += "{: ^6}".format(str(permutation[line])) + "|"
        result += (line + 1) % separator == 0 and (line + 1) % degree != 0 and "|" * 2 or ""
        if (line + 1) % (degree * separator) == 0:
            result += "\n" + "{: ^6}".format("") + "-" * separe_size
    return result


if __name__ == '__main__':
    testmod()
