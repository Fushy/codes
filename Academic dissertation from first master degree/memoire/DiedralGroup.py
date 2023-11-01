from doctest import testmod
from typing import Set

from Permutation import reflexions, rotations
from SymmetryGroup import SymmetryGroup, permutation


class DiedralGroup(SymmetryGroup):
    def __init__(self, vertices: int):
        """" Représente le groupe diedral correspondant aux symétries d'un polygone régulier à n sommets.

        >>> DiedralGroup(10).identity
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        >>> DiedralGroup(10).cardinality
        20
        >>> DiedralGroup(10).polynome
        '(4*x[10] + x[1]**10 + 5*x[1]**2*x[2]**4 + 6*x[2]**5 + 4*x[5]**2)/20'
        """
        degree = vertices
        super().__init__(all_elements(vertices), degree)


def all_elements(vertices: int) -> Set[permutation]:
    """ Renvoie tous les éléments du groupe dièdre.
    Utilisé pour initialiser le groupe diedral à :vertices: sommets.
    """
    range_vertices = range(1, vertices + 1)
    return rotations(range_vertices, vertices).union(reflexions(range_vertices, vertices))


if __name__ == '__main__':
    testmod()
