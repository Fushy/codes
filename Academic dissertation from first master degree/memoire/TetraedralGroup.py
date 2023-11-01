from doctest import testmod
from typing import Set

from SymmetryGroup import SymmetryGroup, permutation
from Util import all_elements


# TODO doc
class TetraedralGroup(SymmetryGroup):
    """ Représente le groupe tétraédral qui est le groupe de symétries du tétraèdre régulier. """

    def __init__(self):
        """
            >>> TetraedralGroup().identity
            (1, 2, 3, 4)
            >>> TetraedralGroup().cardinality
            12
            >>> TetraedralGroup().polynome
            '(x[1]**4 + 8*x[1]*x[3] + 3*x[2]**2)/12'
        """
        degree = 4
        super().__init__(all_elements(generator_set()), degree)


def generator_set() -> Set[permutation]:
    """ Genère l'ensemble des permutations du groupe de symétries du tétraédral régulier."""
    E = {tuple(range(1, 5))}
    # rotations autour de l'axe perpendiculaire à la face 1.
    E.add((1, 4, 2, 3))
    E.add((1, 3, 4, 2))
    # rotations autour de l'axe perpendiculaire à la face 2.
    E.add((4, 2, 1, 3))
    E.add((3, 2, 4, 1))
    # rotations autour de l'axe perpendiculaire à la face 3.
    E.add((4, 1, 3, 2))
    E.add((2, 4, 3, 1))
    # rotations autour de l'axe perpendiculaire à la face 4.
    E.add((3, 1, 2, 4))
    E.add((2, 3, 1, 4))
    return E


if __name__ == '__main__':
    testmod()
