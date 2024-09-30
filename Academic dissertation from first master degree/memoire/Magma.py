import datetime
from doctest import testmod
from itertools import chain, product
from typing import Set, TypeVar, Generic, Optional, Tuple, Sequence, Dict

from Util import estimate_end

# Dans tous les fichiers, on utilisera la convention suivante.
# Une variable représenté par une et une seule lettre en majuscule correspond à un ensemble.
# E = {1, 2}
# Excepté dans le seul cas du typage générique T ci dessous.
T = TypeVar("T")


class Magma(Generic[T]):
    """ Un magma est une structure algébrique.
        Cette classe est constituée d'un ensemble et d'une seule opération binaire qui doit être interne.
        Typé par un type générique T qui est le type des éléments de l'ensemble.

    Attributs
    ----------
        :type E: List[T]
        :attribute E: Représente l'ensemble sous-jacent du Magma. Plus précisément, il s'agit d'une liste triée.

        :type dictionary: Dict[T, int]
        :attribute E: Un dictionnaire qui lie chaque élément de :E: avec un index unique.
        Utile afin de trouver l'index d'un élément situé dans :E: avec une complexité moyenne de O(1).

        :type operation_table: Sequence[Tuple[T, ...]]
        :attribute operation_table: La table des opérations pour chaque élément de :E:.

        :type cardinality: int
        :attribute cardinality: Le cardinal de :E:.

    Methodes
    -------
        op(self, a: T, b: T) -> T
            Opération binaire unique.
        identity_element(self) -> Union[T, None]
            Si le magma actuel a un élément neutre alors renvoyez-le.
            e ¤ x = x ¤ e = x
        is_associative(self) -> bool
            Vérifie si l'opération est associative.
            a ¤ (b ¤ c) = (a ¤ b) ¤ c
        is_invertible(self, e: T, x: T) -> bool
            Vérifie si x est inversible par e.
            x ¤ y = y ¤ x = e
        is_all_invertible(self) -> bool
            Vérifie si tous les éléments sont inversibles.
        is_group(self) -> Tuple[bool, str]
            Vérifie si le magma est un groupe.

    Doctest
    -------
        Magma d'addition modulos 3  : (Z/3Z, +).
        >>> magma = Magma({0, 1, 2}, [(0, 1, 2), (1, 2, 0), (2, 0, 1)])
        >>> magma.E
        [0, 1, 2]
        >>> magma.operation_table
        [(0, 1, 2), (1, 2, 0), (2, 0, 1)]
        >>> magma.dictionary
        {0: 0, 1: 1, 2: 2}
        >>> magma.identity_element()
        0
        >>> magma.is_associative()
        True
        >>> magma.is_all_invertible()
        True
        >>> magma.is_group()
        (True, '')

        Magma de multiplication modulo 4 : (Z/4Z, *) avec le tableau multiplicatif suivant:
        * | 0 1 2 3
        --+--------
        0 | 0 0 0 0
        1 | 0 1 2 3
        2 | 0 2 0 2
        3 | 0 3 2 1
        >>> magma = Magma({0, 1, 2, 3}, [(0, 0, 0, 0), (0, 1, 2, 3), (0, 2, 0, 2), (0, 3, 2, 1)])
        >>> magma.identity_element()
        1
        >>> magma.is_associative()
        True
        >>> magma.is_group()
        (False, 'Elements are not all invertible')
        """

    def __init__(self, E: Set[T], operation_table: Sequence[Tuple[T, ...]]):
        """
        Parametres
        ----------
            :type E: Set[T]
            :param E: L'ensemble de magma, ne doit pas être vide si: operation_table: n'est pas vide.
            :type operation_table: Sequence[Tuple[T]]
            :param operation_table: Une liste de liste d'élément ou chaque liste.
            d'élément correspond à la table d'opération de son élément associé.
            La longueur de la liste :operation_table: doit donc être égale au nombre d'élément de l'ensemble du magma.
            De plus, si un magma possede une loi interne alors chaque élément de chaque liste doit être
            dans l'ensemble du magma.

        Doctest
        -------
            >>> magma = Magma({1, 2, 3}, [(0, 0, 0), (1, 1, 1)])
            Traceback (most recent call last):
            AssertionError: 'E' size and 'operation_table' size are not the same.

            >>> magma = Magma({1, 2, 3}, [(0, 0), (1, 1), (2, 2)])
            Traceback (most recent call last):
            AssertionError: 'E' size and 'operation_table[0]' size are not the same.

            >>> magma = Magma({0, 1, 2}, [(3, 0, 0), (1, 1, 1), (2, 2, 2)])
            Traceback (most recent call last):
            AssertionError: This magma doesn't own an internal law, closure from operation_table is not respected.

            >>> magma = Magma(set(), ())
            >>> magma.E
            []
            >>> magma.operation_table
            ()
            >>> magma.cardinality
            0

            M | 1 2 3 4
            -----------
            1 | 1 2 3 4
            2 | 2 4 1 3
            3 | 3 1 4 2
            4 | 4 3 2 1
            >>> magma = Magma({1, 2, 3, 4}, [(1, 2, 3, 4), (2, 4, 1, 3), (3, 1, 4, 2), (4, 3, 2, 1)])
            >>> magma.E
            [1, 2, 3, 4]
            >>> magma.operation_table
            [(1, 2, 3, 4), (2, 4, 1, 3), (3, 1, 4, 2), (4, 3, 2, 1)]
            >>> magma.cardinality
            4
        """
        assert len(E) == len(operation_table), \
            "'E' size and 'operation_table' size are not the same."
        assert len(E) == 0 and len(operation_table) == 0 or len(E) == len(operation_table[0]), \
            "'E' size and 'operation_table[0]' size are not the same."
        assert E == set(chain(*operation_table)), \
            "This magma doesn't own an internal law, closure from operation_table is not respected."
        self.E = sorted(E)
        self.dictionary = dict(zip(self.E, range(0, len(E))))
        self.operation_table = operation_table
        self.cardinality = len(E)

    def __str__(self):
        """
        Doctest
        -------
            >>> magma = addition_modulo(5)
            >>> print(magma)
            E = [0, 1, 2, 3, 4]
            operation_table = [(0, 1, 2, 3, 4)
                              (1, 2, 3, 4, 0)
                              (2, 3, 4, 0, 1)
                              (3, 4, 0, 1, 2)
                              (4, 0, 1, 2, 3)]
            cardinality = 5
        """
        string = ["E = ", str(self.E), "\noperation_table = [", str(self.operation_table[0])]
        for i in range(1, self.cardinality):
            string.append("\n" + " " * len("operation_table = "))
            string.append(str(self.operation_table[i]))
        string.append("]\ncardinality = " + str(self.cardinality))
        return "".join(string)

    def is_group(self) -> Tuple[bool, str]:
        """ Vérifie si le magma est un groupe.
        Utilise les méthodes identity_element, is_all_invertible, et is_associative.
        Source : Définition 1.7 dans 1.1 Généralités dans la théorie des groupes.

        Retours
        -------
            :rtype: Tuple[bool, str]
            :return: Le tuple possède True si le magma est un groupe.
            Sinon le tuple possède False et explique pourquoi le magma n'est pas un groupe.

        Doctest
        -------
            >>> magma = Magma({0, 1, 2}, [(0, 1, 2), (1, 2, 0), (2, 0, 0)])
            >>> magma.is_group()
            (False, 'Operation is not associative')

            >>> magma = Magma({0, 1, 2}, [(0, 1, 0), (1, 2, 2), (2, 0, 1)])
            >>> magma.is_group()
            (False, "Identity doesn't exist")

            >>> magma = Magma({0, 1, 2, 3}, [(0, 0, 0, 0), (0, 1, 2, 3), (2, 0, 2, 0), (0, 3, 2, 1)])
            >>> magma.is_group()
            (False, 'Elements are not all invertible')

            >>> magma = Magma({0, 1, 2}, [(0, 1, 2), (1, 2, 0), (2, 0, 1)])
            >>> magma.is_group()
            (True, '')
        """
        if self.identity_element() is None:
            return False, "Identity doesn't exist"
        if not self.is_all_invertible():
            return False, "Elements are not all invertible"
        # if not self.is_associative_timer():
        if not self.is_associative():
            return False, "Operation is not associative"
        return True, ''

    def identity_element(self) -> Optional[T]:
        """ Découvre si le magma possède un élément neutre.
        Interprétation Mathématique:
             e ¤ x = x ¤ e = x
        Interprétation de la liste graphique:
            S'il existe au moins une liste égale à: self.E: alors l'élément d'identité existe, sinon non.

        Retours
        -------
            :rtype: Optional[T]
            :return: Si le magma a un élément d'identité, alors il retourne le premier élément identité trouvé,
            sinon None.
        Doctest
        -------
            Graphic: magma.operation_table[0] == magma.E. Then e = magma.E[0] = 0
            >>> magma = Magma({0, 1, 2}, [(0, 1, 2), (1, 2, 0), (2, 0, 1)])
            >>> magma.identity_element()
            0

            >>> magma = Magma({0, 1, 2}, [(0, 1, 0), (1, 2, 0), (2, 0, 0)])
            >>> magma.identity_element()

            Graphic: magma.operation_table[0] == magma.E. Then e = magma.E[0] = 1
            >>> magma = Magma({1, 2, 3, 4}, \
            [(1, 2, 3, 4), (2, 4, 1, 3), (3, 1, 4, 2), (4, 3, 2, 1)])
            >>> magma.identity_element()
            1
        """
        # Application mathématique
        # for x in self.E:
        #     equalities = 0
        #     for y in self.E:
        #         a = self.operation_table[self.dictionary[x]][self.dictionary[y]]
        #         b = self.operation_table[self.dictionary[y]][self.dictionary[x]]
        #         if a == b == y:
        #             equalities += 1
        #         if equalities == self.cardinality:
        #             return x
        # return None
        # Application graphique
        neutral_elements_index = [i for i in range(self.cardinality) if tuple(self.E) == tuple(self.operation_table[i])]
        if len(neutral_elements_index) > 0:
            return self.E[neutral_elements_index[0]]
        return None

    def is_all_invertible(self) -> bool:
        """ Vérifie si tous les éléments sont inversibles
        Utilise la méthode is_invertible.

        Retours
        -------
            :rtype: bool
            :return: Vrai si: x: est inversible par: e :, sinon Faux.

        Doctest
        -------
            >>> magma = Magma({0, 1, 2}, [(0, 1, 0), (1, 2, 2), (2, 0, 1)])
            >>> magma.identity_element()
            >>> magma.is_all_invertible()
            False

            >>> magma = Magma({0, 1, 2}, [(0, 1, 2), (1, 2, 0), (2, 0, 1)])
            >>> magma.identity_element()
            0
            >>> magma.is_all_invertible()
            True

            >>> magma = Magma({0, 1, 2, 3}, [(0, 0, 0, 0), (0, 1, 2, 3), (2, 0, 2, 0), (0, 3, 2, 1)])
            >>> magma.identity_element()
            1
            >>> magma.is_all_invertible()
            False
        """
        e = self.identity_element()
        if e is None:
            return False
        else:
            return all([self.is_invertible(e, x) for x in self.E])

    def is_invertible(self, e: T, x: T) -> bool:
        """ Vérifie si: x: est inversible par: e :.
        Utilise la méthode op.
        Source : Définition 1.5 dans 1.1 Généralités dans la théorie des groupes.

        Interprétation mathématique:
             x ¤ y = y ¤ x = e
        Interprétation de la liste graphique:
            S'il y a un élément :e: dans la table des éléments de x alors :x: est inversible par :e:, sinon non.

        Parametres
        ----------
            :type e: T
            :param e: Potentiellement un élément neutre de l'ensemble magma.
            :type x: T
            :param x: Un élément de l'ensemble magma.

        Retours
        -------
            :rtype: bool
            :return: Vrai si :x: est inversible par :e:. Sinon Faux.

        Doctest
        -------
            Mathematique: 0 ¤ y = y ¤ 0 = 2. Ensuite y = 2
            Graphique: 2 est dans self.E[0]
            >>> magma = Magma({0, 1, 2}, [(0, 1, 2), (1, 2, 0), (2, 1, 1)])
            >>> magma.is_invertible(2, 0)
            True

            Mathematique: 2 ¤ y = y ¤ 2 = 0:. Ainsi on n'a pas de solution.
            Graphique: 0 n'est pas dans self.E[2]
            >>> magma.is_invertible(0, 2)
            False
        """
        for element in self.E:
            if self.op(x, element) == self.op(element, x) == e:
                return True
        return False

    def is_associative(self) -> bool:
        """ Vérifie si l'opération est associative.
        Utilise la méthode op.

        Interprétation mathématique:
             a ¤ (b ¤ c) = (a ¤ b) ¤ c
        Interprétation de la liste graphique:
            Si l'on en trouve une, reduit considérablement le temps de calcul.

        Retours
        -------
            :rtype: bool
            :return: Vrai si l'opération est associative, sinon False.
        Doctest
        -------
            >>> magma = Magma({0, 1, 2}, [(0, 1, 2), (1, 2, 0), (2, 0, 1)])
            >>> magma.is_associative()
            True

            >>> magma = Magma({0, 1, 2}, [(0, 1, 2), (0, 2, 0), (2, 0, 0)])
            >>> magma.is_associative()
            False
        """
        z = 0
        for (i, j, k) in product(self.E, self.E, self.E):
            z += 1
            if not self.op(i, self.op(j, k)) == self.op(self.op(i, j), k):
                return False
        return True

    def is_associative_timer(self) -> bool:
        iteration_final = self.cardinality ** 3
        iteration = 0
        start = datetime.datetime.now()
        start_boucle = datetime.datetime.now()
        for i in range(self.cardinality):
            for j in range(self.cardinality):
                for k in range(self.cardinality):
                    iteration += 1
                    if not self.op(self.E[i], self.op(self.E[j], self.E[k], j, k), i) == self.op(
                            self.op(self.E[i], self.E[j], i, j), self.E[k], -1, k):
                        return False
                    if ((datetime.datetime.now() - start_boucle).total_seconds()) > 5:
                        estimate_end(str(iteration), iteration, iteration_final, start)
                        start_boucle = datetime.datetime.now()
        return True

    def op(self, a: T, b: T, index_a: int = -1, index_b: int = -1) -> T:
        """ Opération binaire unique.

        Parametres
        ----------
            :type a: T
            :param a: Premier opérande de :self.E:.
            :type b: T
            :param b: Deuxième opérande de :self.E:.
            :type index_a: int
            :param index_a: Correspond à l'index de a de la liste :self.E:. Utilisé pour un gain de temps.
            :type index_b: int
            :param index_b: Correspond à l'index de b de la liste :self.E:. Utilisé pour un gain de temps.

        Retours
        -------
            :rtype: T
            :return: L'opération entre :a: et :b: : a ¤ b.

        Doctest
        -------
            >>> magma = addition_modulo(3)
            >>> magma.op(-1, 1)
            Traceback (most recent call last):
            AssertionError: The operation have to be used only between elements from E.
            >>> magma.op(1, 1)
            2
            >>> magma.op(1, 2)
            0
        """
        assert a in self.E and b in self.E, \
            "The operation have to be used only between elements from E."
        if index_a >= 0 and index_b >= 0:
            return self.operation_table[index_a][index_b]  # 2 * O(1) Complexité pire cas
        elif index_a >= 0:
            return self.operation_table[index_a][self.dictionary[b]]
        elif index_b >= 0:
            return self.operation_table[self.dictionary[a]][index_b]
        else:
            return self.operation_table[self.dictionary[a]][self.dictionary[b]]  # 2 * O(1) Complexité moyenne
        # return self.operation_table[self.E.index(a)][self.E.index(b)]          # 2 * O(n)


def addition_modulo(n: int) -> Magma[int]:
    """ Crée et renvoie un magma qui correspond à un magma d'addition modulo n: (Z / n, +).

        Parametres
        ----------
            :type n: int
            :param n: Operation modulo.

        Retours
        -------
            :rtype: Magma[int]
            :return: Magma addition modulo n.
    """
    E = set(range(n))
    operation_table = [tuple((a + b) % n for a in range(n)) for b in range(n)]
    return Magma(E, operation_table)


if __name__ == '__main__':
    testmod()
