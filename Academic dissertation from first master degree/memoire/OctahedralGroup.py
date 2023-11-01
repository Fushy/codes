from doctest import testmod
from typing import Set

from SymmetryGroup import SymmetryGroup, permutation
from Util import all_elements


class OctahedralGroup(SymmetryGroup):
    """ Représente le groupe octaédral qui est le groupe de symétries de l'octaèdre régulier. """

    def __init__(self):
        """
            >>> OctahedralGroup().identity
            (1, 2, 3, 4, 5, 6, 7, 8)
            >>> OctahedralGroup().cardinality
            24
            >>> OctahedralGroup().polynome
            '(x[1]**8 + 8*x[1]**2*x[3]**2 + 9*x[2]**4 + 6*x[4]**2)/24'
        """
        degree = 8
        super().__init__(all_elements(generator_set()), degree)


def generator_set() -> Set[permutation]:
    """ Genère l'ensemble des permutations du groupe de symétries de l'octaèdre régulier."""
    E = {tuple(range(1, 9))}
    # rotations autour de l'axe horizontal (ox)
    E.add((4, 3, 8, 7, 2, 1, 6, 5))
    E.add((7, 8, 5, 6, 3, 4, 1, 2))
    E.add((6, 5, 2, 1, 8, 7, 4, 3))
    # rotations autour de l'axe vertical (oy)
    E.add((2, 3, 4, 1, 8, 5, 6, 7))
    E.add((3, 4, 1, 2, 7, 8, 5, 6))
    E.add((4, 1, 2, 3, 6, 7, 8, 5))
    # rotations autour de l'axe perpendiculaire (oz)
    E.add((2, 5, 8, 3, 6, 1, 4, 7))
    E.add((5, 6, 7, 8, 1, 2, 3, 4))
    E.add((6, 1, 4, 7, 2, 5, 8, 3))
    return E


if __name__ == '__main__':
    testmod()
