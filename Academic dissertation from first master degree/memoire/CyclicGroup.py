from doctest import testmod

from Permutation import rotations
from SymmetryGroup import SymmetryGroup


class CyclicGroup(SymmetryGroup):
    """ Représente le groupe cyclique d'ordre n correspondant au groupe des symétries du collier à n perles. """

    def __init__(self, pearls: int):
        degree = pearls
        super().__init__(rotations(range(1, pearls + 1), pearls), degree)


if __name__ == '__main__':
    testmod()
