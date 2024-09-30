import functools
from doctest import testmod
from typing import Set, Tuple

import sympy

from Group import Group, T
from Permutation import cycles_number
from SymmetricGroup import create_operation_table

permutation = Tuple[int, ...]


class SymmetryGroup(Group[T]):
    """ Une classe représentant un groupe de symétrie quelconque.
    Donc un sous-groupe du groupe symétrique.
    """

    def __init__(self, E: Set[T], n: int):
        identity = tuple(range(1, n + 1))
        operation_table = create_operation_table(sorted(E))
        super().__init__(E, operation_table, identity)
        self.degree = n

    def __getattr__(self, item):
        if item == "polynome":
            self.polynome = self.cycle_index_polynomial()
            return self.polynome
        raise AttributeError(item)

    def cycle_index_polynomial(self) -> str:
        """ Calcule le polynôme d'indice de cycle du groupe G.

        Retours
        -------
            :rtype: str
            :return: Retourne le polynome indicateur de cycles de :symmetric_group:

        Doctest
        -------
            >>> symmetry_group = SymmetryGroup({(1, 2), (2, 1)}, 2)
            >>> symmetry_group.cycle_index_polynomial()
            '(x[1]**2 + x[2])/2'
        """
        x = sympy.IndexedBase('x')
        return str(sympy.together((sum(
            [functools.reduce(lambda i, j: i * j,
                              [x[k] ** cycles_number(sigma, k) for k in range(1, self.degree + 1)])
             for sigma in self.E])) / self.cardinality))


if __name__ == '__main__':
    testmod()
