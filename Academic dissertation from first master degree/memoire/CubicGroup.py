from doctest import testmod
from typing import Set

from SymmetryGroup import SymmetryGroup, permutation
from Util import all_elements


class CubicGroup(SymmetryGroup):
    """ Représente le groupe cubique qui est le groupe de symétries du cube. """

    def __init__(self):
        """
            >>> CubicGroup().identity
            (1, 2, 3, 4, 5, 6)
            >>> CubicGroup().cardinality
            24
            >>> CubicGroup().polynome
            '(x[1]**6 + 3*x[1]**2*x[2]**2 + 6*x[1]**2*x[4] + 6*x[2]**3 + 8*x[3]**2)/24'
        """
        degree = 6
        super().__init__(all_elements(generator_set()), degree)


def generator_set() -> Set[permutation]:
    """ Genère l'ensemble des permutations du groupe de symétries du cube."""
    E = {(1, 2, 3, 4, 5, 6)}
    # rotations autour de l'axe horizontal (ox)
    E.add((4, 1, 2, 3, 5, 6))
    E.add((3, 4, 1, 2, 5, 6))
    E.add((2, 3, 4, 1, 5, 6))
    # rotations autour de l'axe vertical (oy)
    E.add((6, 2, 5, 4, 1, 3))
    E.add((3, 2, 1, 4, 6, 5))
    E.add((5, 2, 6, 4, 3, 1))
    # rotations autour de l'axe perpendiculaire (oz)
    E.add((1, 5, 3, 6, 4, 2))
    E.add((1, 4, 3, 2, 6, 5))
    E.add((1, 6, 3, 5, 2, 4))
    return E


if __name__ == '__main__':
    testmod()
