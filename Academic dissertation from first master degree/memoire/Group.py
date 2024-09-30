from doctest import testmod
from itertools import product, combinations
from typing import List, Set, Optional, Tuple, Sequence

from Magma import Magma, T
from Permutation import fixator


class Group(Magma[T]):
    """ Un groupe est un magma qui est associatif, possédant un élément neutre et où tous les éléments sont inversible.
        Cette classe est typée par un type générique T qui est le type des éléments de l'ensemble.

    Attributs
    ---------
        :type E: list[T]
        :attribute E: Voir la doc de Magma.

        :type dictionary: Dict[T, int]
        :attribute dictionary: Voir la doc de Magma.

        :type operation_table: Sequence[Tuple[T, ...]]
        :attribute operation_table: Voir la doc de Magma.

        :type cardinality: int
        :attribute cardinality: Voir la doc de Magma.

        :type identity: T
        :attribute identity: L'élément d'identité du groupe.

    Methodes
    -------
        inverse(self, x: T) -> T
            Calcule l'inverse de :x: et le renvoie.
        sub_group_from_list(self, F: Set[T]) -> Optional["Group"]
            Renvoie le sous-groupe formé par :F: s'il existe.
        is_sub_group(self, group: "Group") -> Tuple[bool, str]
            Vérifie si le groupe :group: est un sous-groupe.
        all_sub_groups(self) -> List[Set[T]]
            Renvoie tous les sous-ensembles formant un sous-groupe.
        sub_groups(self, F: Set[T]) -> List[Set[T]]
            Calcule tous les sous-groupes qui contiennent :F:.
        sub_groups_fixed_size(self, F: Set[T], size: int) -> List[Set[T]]
            Renvoie tous les sous-ensembles de la taille de :size:.
        sg_generated(self, H: Set[T]) -> List[T]:
            Calcule le sous-groupe généré par :H:.
        sg_generated_by_one_element(self, sigma: T) -> List[T]:
            Calcule le sous-groupe généré par :sigma:.

    Doctest
    -------
        Modulo 5 multiplication group : (Z/5Z, *)
        >>> Z5 = Zn_mul(5)
        >>> Z5.inverse(3)
        2
        >>> print(Z5.sub_group_from_list({1, 4}))
        E = [1, 4]
        operation_table = [(1, 4)
                          (4, 1)]
        cardinality = 2
        identity = 1
        >>> Z5.is_sub_group(Group({1, 4}, [(1, 4), (4, 1)], 1))
        (True, '')
        >>> Z5.all_sub_groups()
        [{1}, {1, 4}, {1, 2, 3, 4}]
        >>> Z5.sub_groups({1})
        [{1}, {1, 4}]
        >>> Z5.sub_groups_fixed_size({1}, 2)
        [{1, 4}]
        >>> Z5.sg_generated({1, 2})
        [1, 2, 3, 4]
        >>> Z5.sg_generated_by_one_element(2)
        [1, 2, 4, 3]
    """

    def __init__(self, E: Set[T], operation_table: Sequence[Tuple[T, ...]], identity: T):
        """
        Parametres
        ----------
            :param E: Voir la doc de Magma.
            :param operation_table: Voir la doc de Magma.

            :type identity: T
            :param identity: L'élément d'identité du groupe.

        Doctest
        -------
            >>> Group({0, 1, 2}, [(0, 1, 2), (1, 2, 0), (2, 0, 1)], 1)
            Traceback (most recent call last):
            AssertionError: identity_element parameter doesn't correspond to the identity element from the magma.

            >>> Group({0, 1, 2, 3}, [(0, 0, 0, 0), (0, 1, 2, 3), (2, 0, 2, 0), (0, 3, 2, 1)], 1)
            Traceback (most recent call last):
            AssertionError: Object created is not a group algebraic structure.

            >>> group = Group({0, 1, 2}, [(0, 1, 2), (1, 2, 0), (2, 0, 1)], 0)
            >>> group.identity
            0
        """
        super().__init__(E, operation_table)
        assert identity == self.identity_element(), \
            "identity_element parameter doesn't correspond to the identity element from the magma."
        self.identity = identity
        # Ligne ci-dessous à enlever lorsqu'on est sûr que le Magma crée est un groupe. Afin d'accelerer les calculs.
        # assert self.is_group()[0], "Object created is not a group algebraic structure."

    def __str__(self):
        """
        Doctest
        -------
            >>> Z5 = Zn_mul(5)
            >>> print(Z5)
            E = [1, 2, 3, 4]
            operation_table = [(1, 2, 3, 4)
                              (2, 4, 1, 3)
                              (3, 1, 4, 2)
                              (4, 3, 2, 1)]
            cardinality = 4
            identity = 1
        """
        return super().__str__() + "\nidentity = " + str(self.identity)

    def sg_generated(self, H: Set[T]) -> List[T]:
        """ Calcule du sous-groupe généré par: H:
        Utilise la méthode sub_groups.

        Parametres
        ----------
            :type H: Set(T)
            :param H: Un sous-ensemble de :self.E:.

        Retours
        -------
            :rtype: List[T]
            :return: La liste des éléments du sous-groupe généré par: H :.

        Doctest
        -------
            >>> Z5 = Zn_mul(5)
            >>> elements = {1, 2}
            >>> Z5.sub_groups(set(elements))
            []
            >>> Z5.sg_generated(set(elements))
            [1, 2, 3, 4]

            >>> elements = {1}
            >>> Z5.sub_groups(set(elements))
            [{1}, {1, 4}]
            >>> Z5.sg_generated(set(elements))
            [1]
        """
        elements = list(self.E)
        for sub_group in self.sub_groups(H):
            if len(sub_group) < len(elements):
                elements = sorted(sub_group)
        return elements

    def sub_groups(self, F: Set[T]) -> List[Set[T]]:
        """ Calcule tous les sous-groupes qui contiennent :F:.
        Utilise la méthode all_sub_groups, sub_group_from_list et dividers.

        Parametres
        ----------
            :type F: Set[T]
            :param F: Combinaisons appropriées à partir de :F: former d'un sous-groupe.

        Retours
        -------
            :rtype: List[Set[T]]
            :return: La liste des sous ensemble du groupe.

        Doctest
        -------
            >>> Z5 = Zn_mul(5)
            >>> Z5.sub_groups({1})
            [{1}, {1, 4}]
        """
        if len(F) == 0:
            return self.all_sub_groups()
        return [set(H) for divider in dividers(self.cardinality, len(F))
                for H in combinations(self.E, divider)
                if (F.issubset(H) and self.sub_group_from_list(set(H)) is not None)]

    def all_sub_groups(self) -> List[Set[T]]:
        """ Renvoie tous les sous-ensembles formant un sous-groupe.
        Utilise la méthode sub_group_from_list et all_dividers.

        Retours
        -------
            :rtype: List[Set[T]]
            :return: La liste contenant tous les sous-ensembles de groupes valides.

        Doctest
        -------
            >>> Z5 = Zn_mul(5)
            >>> Z5.all_sub_groups()
            [{1}, {1, 4}, {1, 2, 3, 4}]
        """
        return [set(H) for divider in all_dividers(self.cardinality)
                for H in combinations(self.E, divider)
                if self.sub_group_from_list(set(H))]

    def sub_groups_fixed_size(self, F: Set[T], size: int) -> List[Set[T]]:
        """ Renvoie tous les sous-ensembles de la taille :size: qui forme un sous-groupe approprié et contenant :F:.
        Utilise la méthode sub_group_from_list.

        Parametres
        ----------
            :type F: Set[T]
            :param F: Un ensemble qu'on construit avec des combinaisons appropriées.
            :type size: int
            :param size: Une taille qui correspond au chercheur de longueur des sous-ensembles.

        Retours
        -------
            :rtype: List[Set[T]]
            :return: La liste des ensembles qui correspondent aux combinaisons appropriées avec la :size: longueur.

        Doctest
        -------
            >>> Z5 = Zn_mul(5)
            >>> Z5.sub_groups_fixed_size({1}, 2)
            [{1, 4}]
        """
        if size == 0 or self.cardinality % size or not F.issubset(self.E):
            return []
        return [set(H) for H in combinations(self.E, size)
                if F.issubset(H) and self.sub_group_from_list(set(H))]

    def sub_group_from_list(self, F: Set[T]) -> Optional["Group"]:
        """ Renvoie le sous-groupe formé par :F: s'il existe, sinon on renvoie None.
        Utilise la méthode sub_group_operation_table.

        Parametres
        ----------
            :type F: Set[T]
            :param F: Le sous groupe calculé sera formé de ces éléments.

        Retours
        -------
            :rtype: Optional[Group]
            :return: Le sous groupe calculé formé des éléments :F:.

        Doctest
        -------
            >>> Z5 = Zn_mul(5)
            >>> Z5.sub_group_from_list({1, 2})
            >>> print(Z5.sub_group_from_list({1, 4}))
            E = [1, 4]
            operation_table = [(1, 4)
                              (4, 1)]
            cardinality = 2
            identity = 1
        """
        if self.identity not in F:
            return None
        operation_table = sub_group_operation_table(self, F)
        if not operation_table:
            return None
        if not Magma(F, operation_table).is_group()[0]:
            return None
        return Group(F, operation_table, self.identity)

    def is_sub_group(self, group: "Group") -> Tuple[bool, str]:
        """ Vérifie si le :group: est un sous-groupe.

        Parametres
        ----------
            :type group: Group[T]
            :param group: Un autre groupe pour vérifier s'il s'agit d'un sous-groupe.

        Retours
        -------
            :rtype: Tuple[bool, str]
            :return: Un tuple possédant True si le :group: est un sous-groupe.
            Sinon il possède False et explique pourquoi :group: n'est pas un sous-groupe.

        Doctest
        -------
            >>> Z5 = Zn_mul(5)
            >>> Z5.is_sub_group(Group({-1, 4}, [(-1, 4), (4, -1)], -1))
            (False, 'group is not a subset')

            >>> Z5 = Zn_mul(5)
            >>> Z5.is_sub_group(Group({2, 4}, [(2, 4), (4, 2)], 2))
            (False, "group doesn't have the same identity element")

            >>> Z5 = Zn_mul(5)
            >>> Z5.is_sub_group(Zn_mul(3))
            (False, 'Not the same operation')

            >>> H = Group({1, 4}, [(1, 4), (4, 1)], 1)
            >>> Z5.is_sub_group(H)
            (True, '')
        """
        if not set(group.E).issubset(self.E):
            return False, "group is not a subset"
        if group.identity_element() != self.identity:
            return False, "group doesn't have the same identity element"
        for (x, y) in product(group.E, group.E):
            if group.op(x, y) != self.op(x, y):
                return False, "Not the same operation"
        return True, ''

    def sg_generated_by_one_element(self, sigma: T) -> List[T]:
        """ Calcule le sous-groupe généré par: sigma :.

        Parametres
        ----------
            :type sigma: T
            :param sigma: UIn élément de :self.E:.

        Retours
        -------
            :rtype: List[T]
            :return: Liste des éléments du sous-groupe généré par sigma.

        Doctest
        -------
            >>> Z5 = Zn_mul(5)
            >>> Z5.sg_generated_by_one_element(1)
            [1]

            >>> Z5.sg_generated_by_one_element(2)
            [1, 2, 4, 3]
        """
        if sigma == self.identity:
            return [sigma]
        elements = [self.identity, sigma]
        x = sigma
        while self.op(sigma, x) not in elements:
            x = self.op(sigma, x)
            elements.append(x)
        return elements

    def inverse(self, x: T) -> T:
        """ Calcule l'inverse de :x: et le renvoie.
        x ¤ y = y ¤ x = identity. Renvoie y.

        Parameters
        ----------
            :type x: T
            :param x: Un élément de :self.E:.

        Returns
        -------
            :rtype: T
            :returns: L'inverse de x.

        Doctest
        -------
            >>> Z5 = Zn_mul(5)
            >>> Z5.inverse(0)
            Traceback (most recent call last):
            AssertionError: x is not into the set.
            >>> Z5.inverse(3)
            2
        """
        assert x in self.E, \
            "x is not into the set."
        for y in self.E:
            if self.op(x, y) == self.op(y, x) == self.identity:
                return y

    def orbits_number(self, applications: List[Sequence[T]]) -> int:
        """ Application du lemme de Burnside.
        source : 2.2.3 Orbites

        Parameters
        ----------
            :type applications: List[Sequence[T]]
            :param applications: Une liste de toutes les rotations possibles d'une séquence.

        Returns
        -------
            :rtype: int
            :returns: Le nombre d'orbit.

        Doctest
        -------
            >>> from Util import all_colorations
            >>> from OctahedralGroup import OctahedralGroup

            >>> octahedral = OctahedralGroup()
            >>> octahedral.orbits_number(all_colorations(8, 2))
            23

            >>> octahedral = OctahedralGroup()
            >>> octahedral.orbits_number(all_colorations(6, 2))
            Traceback (most recent call last):
            AssertionError: Wrong size, application is smaller than permutation
        """
        orbits = sum([len(fixator(sigma, applications)) for sigma in self.E])
        assert (orbits / self.cardinality).is_integer(), \
            'orbits is not an integer'
        return orbits // self.cardinality


def dividers(n: int, k: int = 1) -> List[int]:
    """ Calcule tous les diviseurs propres de n à partir de k.

    Parametres
    ----------
        :type n: int
        :param n: Le nombre qui sera divisé.
        :type k: int
        :param k: Le premier nombre n qui est divisible et ensuite qu'on utilisera par la suite.

    Retours
    -------
        :rtype: List[int]
        :return: Tous les diviseurs appropriés trouvés.

    Doctest
    -------
        >>> dividers(12)
        [1, 2, 3, 4, 6]

        >>> dividers(12, 3)
        [3, 4, 6]
    """
    n = n > 0 and n or n * -1
    k = k > 0 and k or k * -1
    return [i for i in range(k, n) if n % i == 0]


def all_dividers(n: int) -> List[int]:
    """ Calcule tous les diviseurs de n.

    Parametres
    ----------
        :type n: int
        :param n: Le nombre qui sera divisé.

    Retours
    -------
        :rtype: List[int]
        :return: Tous les diviseurs trouvés.

    Doctest
    -------
        >>> all_dividers(12)
        [1, 2, 3, 4, 6, 12]

        >>> all_dividers(-12)
        [1, 2, 3, 4, 6, 12]
    """
    n = n > 0 and n or n * -1
    return [i for i in range(1, n + 1) if n % i == 0]


def Zn_mul(n: int) -> Group[int]:
    """ Création du groupe (Z/nZ, *).

    Parametres
    ----------
        :type n: int
        :param n: Modulo au groupe de multiplication généré. n doit être un nombre premier et> = 2.

    Retours
    -------
        :rtype: Group
        :return: Le groupe qui est cré.

    Doctest
    -------
        >>> Zn_mul(4)
        Traceback (most recent call last):
        AssertionError: n must be prime in Zn_mul(n)
        >>> Z5 = Zn_mul(5)
        >>> Z5.E
        [1, 2, 3, 4]
        >>> Z5.operation_table
        [(1, 2, 3, 4), (2, 4, 1, 3), (3, 1, 4, 2), (4, 3, 2, 1)]
        >>> Z5.cardinality
        4
        >>> Z5.identity
        1
    """

    def operation_table_mul(n):
        operation_table = []
        E = list(range(1, n))
        for element in E:
            table = tuple([(element * i) % n for i in range(1, n)])
            if not set(table).issubset(E):
                return None
            operation_table.append(table)
        return operation_table

    assert n >= 2, \
        'n must be >= 2'
    operation_table = operation_table_mul(n)
    assert operation_table, \
        'n must be prime in Zn_mul(n)'
    return Group(set(range(1, n)), operation_table, 1)


def Zn_add(n: int) -> Group[int]:
    """ Crée le groupe (Z/nZ, +)

    Parametres
    ----------
        :type n: int
        :param n: Modulo au groupe d'addition généré et n doit être> = 1.
    Retours
    -------
        :rtype: Group
        :return: Le groupe qui est crée.

    Doctest
    -------
        >>> Zn = Zn_add(3)
        >>> print(Zn)
        E = [0, 1, 2]
        operation_table = [(0, 1, 2)
                          (1, 2, 0)
                          (2, 0, 1)]
        cardinality = 3
        identity = 0
    """
    assert n, 'n must be >= 1'
    E = list(range(n))
    loi = [E]
    for i in range(1, n):
        loi.append(E[i:] + E[:i])
    return Group(set(E), list(map(tuple, loi)), 0)


def sub_group_operation_table(group: Group[T], elements: Set[T]) -> Optional[List[Tuple[T, ...]]]:
    """ Essaie de calculer l'operation_table formée des éléments d'un groupe.
    Si l'operation_table ne trouve aucun axiome de groupe alors il renvoie None.
    Sinon il renvoie l'axiome du groupe.

    Parametres
    ----------
        :type group: Group
        :param group: Un groupe
        :type elements: Set(T)
        :param elements: Un ensemble d'éléments qui construit une table d'opération.

    Retours
    -------
        :rtype: Optional[List[Tuple[T, ...]]]
        :return: L':operation_table: du :groupe: est réduit à l':elements: si la fermeture est respectée.
        Sinon None.

    Doctest
    -------
        >>> Z5 = Zn_mul(5)
        >>> sub_group_operation_table(Z5, {1, 2, 3})
        >>> sub_group_operation_table(Z5, {1, 4})
        [(1, 4), (4, 1)]
    """
    operation_table = [tuple([group.op(x, i) for i in elements]) for x in elements]
    for i in range(len(elements)):
        if not set(operation_table[i]).issubset(elements):
            return None
        if group.identity not in operation_table[i]:
            return None
    return operation_table


if __name__ == '__main__':
    testmod()
