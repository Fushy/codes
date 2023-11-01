from doctest import testmod
from typing import Tuple, Iterable, Sequence, List

from Group import Group, T
from Permutation import is_fixed_point, composition, list_permutations

Permutation = Sequence[T]
Permutation_tuple = Tuple[T, ...]


class SymmetricGroup(Group[T]):
    """ Le groupe symétrique S(n) est le groupe de toutes les permutations d'un ensemble à n éléments.

    Attributs
    ---------
    :type identity: T
        :attribute identity: L'élément d'identité du groupe.

    :type E: list[T]
        :attribute E: Voir la doc de Magma.

    :type operation_table: Sequence[Tuple[T, ...]]
        :attribute operation_table: Voir la doc de Magma.

    :type n: int
            :param n: Le degré du groupe symétrique.
    """

    def __init__(self, n: int):
        """
        Parametres
        ----------
            :type n: int
            :param n: Le degré du groupe symétrique.

        Doctest
        -------
            >>> symmetric_group = SymmetricGroup(3)
            >>> print(symmetric_group)
            E = [(1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), (3, 2, 1)]
            operation_table = [[(1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), (3, 2, 1)]
                              [(1, 3, 2), (1, 2, 3), (3, 1, 2), (3, 2, 1), (2, 1, 3), (2, 3, 1)]
                              [(2, 1, 3), (2, 3, 1), (1, 2, 3), (1, 3, 2), (3, 2, 1), (3, 1, 2)]
                              [(2, 3, 1), (2, 1, 3), (3, 2, 1), (3, 1, 2), (1, 2, 3), (1, 3, 2)]
                              [(3, 1, 2), (3, 2, 1), (1, 3, 2), (1, 2, 3), (2, 3, 1), (2, 1, 3)]
                              [(3, 2, 1), (3, 1, 2), (2, 3, 1), (2, 1, 3), (1, 3, 2), (1, 2, 3)]]
            cardinality = 6
            identity = (1, 2, 3)
        """
        identity = tuple(range(1, n + 1))
        E = list_permutations(identity)
        operation_table = create_operation_table(E)
        super().__init__(set(E), operation_table, identity)
        self.degree = n

    def stabilizer(self, point: int) -> List[Permutation_tuple]:
        """ Renvoie les permutations qui possèdent comme point fixe :point:. """
        return [permutation for permutation in self.E if is_fixed_point(permutation, point)]


def create_operation_table(permutations: Iterable[Permutation]) -> List[Permutation]:
    # def create_operation_table(n) -> List[Permutation]:
    """ Creer la table d'operation d'un groupe symétrique à partir d'un ensemble de permutation
    qui doivent posséder le même ensemble.

    Parametres
    ----------
        :type permutations: Iterable[Sequence[int]]
        :param permutations: Une suite d'éléments représentants des permutations d'un même ensemble.

    Retours
    -------
        :type permutations: Sequence[Permutation_tuple]
        :return: L':operation_table: des compositions des permutations.

    Doctest
    -------
        >>> permutations = list_permutations((1, 2))
        >>> permutations
        [(1, 2), (2, 1)]
        >>> create_operation_table(permutations)
        [((1, 2), (2, 1)), ((2, 1), (1, 2))]
        >>> create_operation_table([(1, 2), (3, 1)])
        Traceback (most recent call last):
        AssertionError: Permutations are not in the same group
    """
    return [[composition(permutation, element) for element in permutations] for permutation in permutations]


if __name__ == '__main__':
    testmod()
