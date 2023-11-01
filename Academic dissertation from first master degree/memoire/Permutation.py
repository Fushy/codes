from doctest import testmod
from itertools import permutations, chain
from typing import TypeVar, Tuple, Sequence, List, Set, Iterable

T = TypeVar("T")
Permutation = Sequence[T]
Permutation_int = Sequence[int]
Permutation_tuple = Tuple[T, ...]

"""
    Ce fichier contient des méthodes qui permettent de manipuler les structures de permutations.
    On a préféré ne pas créer de classe structure afin d'éviter d'initialisé un objet permutation
    à chaque fois que l'on veut en manipuler un.
    On aborde le sujet de permutation à partir de la 1e définition du 1.2 Groupe symétrique
    Une permutation est représenté sous la forme d'une Séquence
    ou chaque index s'envoie sur un élément de la permutation:
                      (1, 2, 3, 4, 5)
        permutation = (2, 5, 4, 3, 1)
"""


def fixator(permutation: Permutation_int, applications: List[Sequence[T]]) -> List[Sequence[T]]:
    """ Renvoie les fixateurs de :permutation:
    Ce sont les applications qui laissent inchangées les permutations après l'application de ces actions de groupe.
    Utilise la methode action.

    Parameters
    ----------
        :type permutation: Sequence[int]
        :param permutation:
        :type applications: List[Sequence[int]]
        :param applications: La liste de toutes les applications de l'ensemble sur lesquelles le groupe agit.

    Returns
    -------
        :rtype: List[Sequence[int]]
        :returns: Fixateur de :permutation:.

    """
    return [application for application in applications if action(permutation, application) == tuple(application)]


def action(permutation: Permutation_int, application: Sequence[T]) -> Permutation_tuple:
    """ Action de groupe: permutation.app = inv(app).permutation
    Utilise la méthode image_point.

    Parameters
    ----------
        :type permutation: Permutation_int
        :param permutation: une permutation du groupe symétrique
        :type application: Sequence[T]
        :param application: une application representee par une sequence
        (ex. coloration, grille de Sudoku: voir le mémoire)

    Returns
    -------
        :rtype: Permutation_tuple
        :returns: L'image de l'application :application: par :permutation:.

    Doctest
    -------
        >>> permutation = (2, 1)
        >>> application = ['A', 'B']
        >>> action(permutation, application)
        ('B', 'A')

        >>> permutation = (2,)
        >>> application = ['A', 'B']
        >>> action(permutation, application)
        ('B',)

        >>> permutation = (2, 1)
        >>> application = ['B']
        >>> action(permutation, application)
        Traceback (most recent call last):
        AssertionError: Wrong size, application is smaller than permutation
    """
    assert len(application) >= len(permutation), \
        "Wrong size, application is smaller than permutation"
    return tuple([application[image_point(permutation, i) - 1] for i in range(1, len(permutation) + 1)])


def is_fixed_point(permutation: Permutation_int, point: int) -> bool:
    """ Vérifie si le point :point: est un point fixe ou non.
    Utilise la méthode image_point.

    Parameters
    ----------
        :type permutation: Permutation
        :param permutation: La permutation sur la quelle la méthode agis.
        :type point: int
        :param point: Le point étudié de la permutation.

    Returns
    -------
        :rtype: bool
        :returns: Vrai si x est un point fixe, sinon Faux.

    Doctest
    -------
        >>> is_fixed_point([3, 2, 1], 2)
        True
        >>> is_fixed_point([3, 2, 1], 1)
        False
        >>> is_fixed_point([1, 2, 3], 4)
        False
    """
    return 1 <= point <= len(permutation) and (image_point(permutation, point) == point) or False


def image_point(permutation: Permutation, x: int) -> T:
    """ Calcule l'image d'un point d'une permutation.
    Source : Chapitre 1.2, Exemple 1.11

    Parameters
    ----------
        :type permutation: Permutation
        :param permutation: La permutation sur la quelle la méthode agis.
        :type x: int
        :param x: Le point de la permutation.

    Returns
    -------
        :rtype: T
        :returns: L'image du point :point: de la permutation.

    Doctest
    -------
        >>> permutation = ['a', 'b', 'c']
        >>> image_point(permutation, 1)
        'a'
        >>> image_point(permutation, 2) == image_point(permutation, 2 + len(permutation))
        True
    """
    return permutation[(x - 1) % len(permutation)]


def cycles_number(permutation: Permutation, k: int) -> int:
    """ Renvoie le nombre de cycles de longueur k dans la décomposition du cycle.
    Utilise la méthode to_cycles.

    Parameters
    ----------
        :type permutation: List[T]
        :param permutation: La permutation sur la quelle la méthode agis.
        :type k: int
        :param k: La longueur des cycles de décomposition calculé.

    Returns
    -------
        :rtype: int
        :returns: La somme des longueurs des cycles de décomposition de longueur :k: calculé.

    Doctest
    -------
    >>> permutation = [1, 2, 3, 4]
    >>> [cycles_number(permutation, i) for i in range(1, 5)]
    [4, 0, 0, 0]

    >>> permutation = [7, 4, 6, 2, 9, 1, 3, 8, 5]
    >>> to_cycles(permutation)
    [[1, 7, 3, 6], [2, 4], [5, 9], [8]]
    >>> [cycles_number(permutation, i) for i in range(1, 10)]
    [1, 2, 0, 1, 0, 0, 0, 0, 0]
    """
    return sum([len(cycle) == k for cycle in to_cycles(permutation)])


def inverse_permutation(permutation: Permutation) -> List[T]:
    """ Une permutation est dite paire si elle présente un nombre pair d'inversions, impaire sinon.
        Soient i < j deux entiers compris entre 1 et n.
        On dit que la paire {i, j} est en inversion pour σ si σ(i) > σ(j).
        La signature d'une permutation paire est 1 ; celle d'une permutation impaire est –1.
        Utilise la méthode from_cycles et to_cycles.

    Parameters
    ----------
        :type permutation: List[T]
        :param permutation: La permutation sur laquelle la méthode agis.

    Returns
    -------
        :rtype: List[T]
        :returns: Donne l'inverse de la permutation.

    Doctest
    -------
        >>> permutation = [1, 2, 3, 4, 5, 6]
        >>> to_cycles(permutation)
        [[1], [2], [3], [4], [5], [6]]
        >>> inverse_permutation(permutation)
        [1, 2, 3, 4, 5, 6]

        >>> permutation = [3, 5, 2, 4, 1]
        >>> to_cycles(permutation)
        [[1, 3, 2, 5], [4]]
        >>> inverse_permutation(permutation)
        [5, 3, 1, 4, 2]
    """
    return from_cycles([x[::-1] for x in to_cycles(permutation)])


def from_cycles(cycles: List[Permutation]) -> List[T]:
    """ Recompose les cycles en une permutation.

    Parameters
    ----------
        :type cycles: List[List[T]]
        :param cycles: La liste de cycles sur laquelle la méthode agis.

    Returns
    -------
        :rtype: List[T]
        :returns: Une permutation obtenu à partir de :cycles:

    Doctest
    -------
    >>> cycles = [[1], [2], [3], [4]]
    >>> from_cycles(cycles)
    [1, 2, 3, 4]

    >>> cycles = [[1, 7, 3, 6], [2, 4], [5, 9], [8]]
    >>> from_cycles(cycles)
    [7, 4, 6, 2, 9, 1, 3, 8, 5]

    >>> cycles = [[chr(i + ord('A')-1) for i in lst] for lst in [[1, 7, 3, 6], [2, 4], [5, 9], [8]]]
    >>> from_cycles(cycles)
    ['G', 'D', 'F', 'B', 'I', 'A', 'C', 'H', 'E']

    >>> cycles = [[1], ['2']]
    >>> from_cycles(cycles)
    Traceback (most recent call last):
    TypeError: '<' not supported between instances of 'str' and 'int'
    """
    n = sum([len(x) for x in cycles])
    permutation = [0] * n
    order_relation_E = dict(zip(sorted(chain(*cycles)), range(1, len(permutation) + 1)))
    for cycle in cycles:
        for i in range(len(cycle)):
            permutation[order_relation_E[cycle[i]] - 1] = cycle[(i + 1) % len(cycle)]
    return permutation


def to_cycles(permutation: Permutation) -> List[List[T]]:
    """ Décompose la permutation en cycles. 
    Source : Chapitre 1.2, Exemple 1.12

    Parameters
    ----------
        :type permutation: List[T]
        :param permutation: La permutation sur laquelle la méthode agis.

    Returns
    -------
        :rtype: List[List[T]]
        :returns: Une liste de cycles obtenu à partir de :permutation:

    Doctest
    -------
        >>> permutation = [1, 2, 3, 4, 5, 6]
        >>> to_cycles(permutation)
        [[1], [2], [3], [4], [5], [6]]

        >>> permutation = [7, 4, 6, 2, 9, 1, 3, 8, 5]
        >>> to_cycles(permutation)
        [[1, 7, 3, 6], [2, 4], [5, 9], [8]]

        >>> permutation = [chr(i + ord('A')-1) for i in [7, 4, 6, 2, 9, 1, 3, 8, 5]]
        >>> to_cycles(permutation)
        [['A', 'G', 'C', 'F'], ['B', 'D'], ['E', 'I'], ['H']]

        >>> permutation = [1, 2, '3']
        >>> to_cycles(permutation)
        Traceback (most recent call last):
        TypeError: '<' not supported between instances of 'str' and 'int'
    """
    cycles = []
    not_seen = sorted(permutation)
    order_relation_E = dict(zip(sorted(permutation), range(1, len(permutation) + 1)))
    while not_seen:
        cycle = []
        element = not_seen[0]
        while element not in cycle:
            not_seen.remove(element)
            cycle.append(element)
            element = permutation[order_relation_E[element] - 1]
        cycles.append(cycle)
    return cycles


def reflexions(permutation: Permutation, n: int) -> Set[T]:
    """ TODO
    Utilise la méthode composition et rotations.

    Parameters
    ----------
        :type permutation: Permutation
        :param permutation: La permutation sur laquelle la méthode agis.

        :type n: int
        :param n: Le nombre de rotation et de composition qu'on fait agir sur :permutation:.

    Returns
    -------
        :rtype: Set[T]
        :returns: Un ensemble obtenu à partir de :permutation:
        auquel on applique les méthodes composition et rotation.

    Doctest
    -------
        >>> reflexions(range(1, 4), 3)
        {(2, 1, 3), (1, 3, 2), (3, 2, 1)}
    """
    reflexion = (permutation[0],) + tuple(permutation[::-1][:n - 1])
    return {composition(reflexion, rotation) for rotation in rotations(permutation, n)}


def composition(perm_f: Permutation, perm_g: Permutation) -> Permutation_tuple:
    """ Calcule la composition de deux permutations.
    Effectue une application bijective de :perm_g: vers :perm_f:.

    Parameters
    ----------
        :type perm_f: Permutation
        :param perm_f: La permutation composé de la composition.
        :type perm_g: Permutation
        :param perm_g: La permutation composante de la composition.

    Returns
    -------
        :rtype: Permutation_tuple
        :returns: L'image de l'application des :elements: par :permutation:.

    Doctest
    -------
        >>> perm_g = (3, 5, 2, 4, 1)
        >>> perm_f = (2, 5, 4, 3, 1)
        >>> composition(perm_f, perm_g)
        (4, 1, 5, 3, 2)

        >>> perm_f = ('a', 'b', 'c')
        >>> perm_g = ('b', 'c', 'a')
        >>> composition(perm_f, perm_g)
        ('b', 'c', 'a')

        >>> composition((3, 2, 1), ('a', 'b', 'c'))
        Traceback (most recent call last):
        AssertionError: Permutations are not in the same group
    """
    assert (set(perm_f) == set(perm_g) and len(perm_f) == len(perm_g)), \
        'Permutations are not in the same group'
    order_relation_E = dict(zip(sorted(perm_f), range(1, len(perm_f) + 1)))
    return tuple(perm_f[order_relation_E[perm_g[i]] - 1] for i in range(len(perm_f)))
    # Ci-dessous, ne fonctionne qu'avec des int, réduit la complexité.
    # return tuple(perm_f[perm_g[i] - 1] for i in range(len(perm_f)))


def rotations(permutation: Permutation, n: int) -> Set[T]:
    """ Effectue :n: rotations sur une permutation.
    Utilisé pour transformer une figure, la faire tourner autour d'un point.

    Parameters
    ----------
        :type permutation: Permutation
        :param permutation: La permutation sur laquelle la méthode agis.

        :type n: int
        :param n: Le nombre de rotation qu'on fait agir sur :permutation:.

    Returns
    -------
        :rtype: Set[T]
        :returns: Un ensemble obtenu grâce à la rotation répété n fois à partir de la :permutation:.

    Doctest
    -------
        >>> sorted(rotations(range(1, 4), 3))
        [(1, 2, 3), (2, 3, 1), (3, 1, 2)]

        >>> sorted(rotations(('A', 2, (3,)), 3), key=lambda x: hash(x))
        [((3,), 'A', 2), ('A', 2, (3,)), (2, (3,), 'A')]
    """
    return {tuple(permutation[i:]) + tuple(permutation[:i]) for i in range(min(n, len(permutation)))}


def transpositions(permutation: Permutation, points: List[int]) -> Permutation_tuple:
    """ Effectue plusieurs transpositions entre deux points de la permutation.
    Chaque indice de :points: correspond au premier point de la transposition
    et sa valeur associé correspond au deuxième point.
    La succession de transposition s'effectuent les uns après les autres:
        transpositions(['A', 'B', 'C'], [2, 3]) se passe de la façon suivante:
        permutation[0] est échangé avec permutation[2-1] et celà vaut ('B', 'A', 'C') puis
        permutation[1] est échangé avec permutation[3-1] et celà vaut ('B', 'C', 'A')
    Utilise la méthode transposition.

    Parameters
    ----------
        :type permutation: Permutation
        :param permutation: La permutation sur la quelle la méthode agis.
        :type points: List[int]
        :param points: Les points allant être transposé.

    Returns
    -------
        :rtype: Permutation_tuple
        :returns: La permutation après les transpositions.

    Doctest
    -------
        >>> permutation = ['a', 'b', 'c']
        >>> transpositions(permutation, [2])
        ('b', 'a', 'c')
        >>> transpositions(permutation, [2, 3])
        ('b', 'c', 'a')

        >>> points = [1, 2, 3]
        >>> transpositions(permutation, points) == tuple(permutation)
        True
        >>> permutation = ['a', 'b']
        >>> points = [2, 1]
        >>> transpositions(permutation, points) == tuple(permutation)
        True

        >>> permutation = [1, 2, 3, 'A', 'B', 'C']
        >>> points = [3, 4, 5]
        >>> transpositions(permutation, points)
        (3, 'A', 'B', 2, 1, 'C')
    """
    modifier_perm = list(permutation)
    i = 1
    for point in points:
        modifier_perm = transposition(modifier_perm, i, point)
        i += 1
    return tuple(modifier_perm)


def transposition(permutation: Permutation, x: int, y: int) -> Permutation_tuple:
    """ Effectue une transposition entre deux points de la permutation.
    Utilise la méthode image_point.

    Parameters
    ----------
        :type permutation: Permutation
        :param permutation: La permutation sur la quelle la méthode agis.
        :type x: int
        :param x: Le premier point de la permutation.
        :type y: int
        :param y: Le deuxième point de la permutation.

    Returns
    -------
        :rtype: Permutation_tuple
        :returns: La permutation après la transpotion.

    Doctest
    -------
        >>> permutation = ['a', 'b', 'c']
        >>> transposition(permutation, 1, 3)
        ('c', 'b', 'a')
        >>> transposition(permutation, 3, 3) == tuple(permutation)
        True
    """
    modifier_perm = list(permutation)
    taille_permutation = len(permutation)
    modifier_perm[(x - 1) % taille_permutation], modifier_perm[(y - 1) % taille_permutation] \
        = image_point(permutation, y), image_point(permutation, x)
    return tuple(modifier_perm)


def list_permutations(E):
    """ Calcule toutes les permutations de :E: et les retournes sous forme d'une liste de liste.

    Parameters
    ----------
        :type E: Iterable[T]
        :param E: L'ensemble de base qui va générer toute les permutation.

    Returns
    -------
        :rtype: List[Tuple[T]]
        :returns: Le résultat des permutation sur l'ensemble :E: sous forme d'une liste de permutation.

    >>> list_permutations({1})
    [(1,)]
    >>> list_permutations(range(1, 4))
    [(1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), (3, 2, 1)]
    >>> list_permutations(('A', 2, [3]))
    [('A', 2, [3]), ('A', [3], 2), (2, 'A', [3]), (2, [3], 'A'), ([3], 'A', 2), ([3], 2, 'A')]
    """
    # if len(E) < 2:
    #     return [E]
    # return [(E[i],) + point for i in range(len(E)) for point in list_permutations(E[:i] + E[i + 1:])]
    return list(permutations(E))


if __name__ == '__main__':
    testmod()
