import datetime
import math
from itertools import combinations, permutations, product
from typing import Set, Tuple

from Permutation import composition

permutation = Tuple[int, ...]


def util_affiche_date(millisecondes: int) -> str:
    """ Prend en entrée un entier qui correspond à des millisecondes et l'affiche sous forme de date ou d'heure."""
    format = ""

    annee = millisecondes / 1000 / 60 / 60 / 24 / 30 / 12
    if annee >= 1:
        annee_ecrit = math.floor(annee)
        format = str(annee_ecrit) + "A "
        millisecondes -= 1000 * 60 * 60 * 24 * 30 * 12 * annee_ecrit

    mois = millisecondes / 1000 / 60 / 60 / 24 / 30
    if mois >= 1:
        mois_ecrit = math.floor(mois)
        format += str(mois_ecrit) + "M "
        millisecondes -= 1000 * 60 * 60 * 24 * 30 * mois_ecrit

    jours = millisecondes / 1000 / 60 / 60 / 24
    if jours >= 1:
        jours_ecrit = math.floor(jours)
        format += str(jours_ecrit) + "J "
        millisecondes -= 1000 * 60 * 60 * 24 * jours_ecrit

    heures = millisecondes / 1000 / 60 / 60
    if heures >= 1:
        heures_ecrit = math.floor(heures)
        format += str(heures_ecrit) + "h "
        millisecondes -= 1000 * 60 * 60 * heures_ecrit

    minutes = millisecondes / 1000 / 60
    if minutes >= 1:
        minutes_ecrit = math.floor(minutes)
        format += str(minutes_ecrit) + "m "
        millisecondes -= 1000 * 60 * minutes_ecrit

    secondes = millisecondes / 1000
    if secondes >= 1:
        secondes_ecrit = math.floor(secondes)
        format += str(secondes_ecrit) + "s "
        millisecondes -= 1000 * secondes_ecrit

    return format


def all_colorations(n, k):
    if n == 0:
        return [tuple()]
    if k == 0:
        return []
    return [(i,) + p for i in range(1, k + 1) for p in all_colorations(n - 1, k)]


def colorations_without_repetition(n, k):
    if k < n:
        return []
    if k == n:
        return permutations(tuple(range(1, n + 1)))
    return [x for perm in combinations(list(range(1, k + 1)), n) for x in permutations(perm)]


def all_grids():
    g1 = (1, 2, 3, 4, 3, 4, 1, 2, 2, 1, 4, 3, 4, 3, 2, 1)
    g2 = (1, 2, 4, 3, 3, 4, 1, 2, 2, 1, 3, 4, 4, 3, 2, 1)
    g3 = (1, 2, 3, 4, 3, 4, 2, 1, 2, 1, 4, 3, 4, 3, 1, 2)
    g4 = (1, 2, 4, 3, 3, 4, 2, 1, 2, 1, 3, 4, 4, 3, 1, 2)
    g5 = (1, 2, 3, 4, 3, 4, 1, 2, 4, 1, 2, 3, 2, 3, 4, 1)
    g6 = (1, 2, 4, 3, 3, 4, 2, 1, 4, 1, 3, 2, 2, 3, 1, 4)
    g7 = (1, 2, 3, 4, 3, 4, 1, 2, 2, 3, 4, 1, 4, 1, 2, 3)
    g8 = (1, 2, 4, 3, 3, 4, 2, 1, 2, 3, 1, 4, 4, 1, 3, 2)
    g9 = (1, 2, 3, 4, 3, 4, 1, 2, 4, 3, 2, 1, 2, 1, 4, 3)
    g10 = (1, 2, 4, 3, 3, 4, 1, 2, 4, 3, 2, 1, 2, 1, 3, 4)
    g11 = (1, 2, 3, 4, 3, 4, 2, 1, 4, 3, 1, 2, 2, 1, 4, 3)
    g12 = (1, 2, 4, 3, 3, 4, 2, 1, 4, 3, 1, 2, 2, 1, 3, 4)
    return [g1, g2, g3, g4, g5, g6, g7, g8, g9, g10, g11, g12]


def all_elements(E: Set[permutation]) -> Set[permutation]:
    """ S'utilise pour initialiser un groupe.
    Retourne tous les éléments d'un groupe. """
    for (sigma, gamma) in product(E, E):
        comp = composition(sigma, gamma)
        if comp not in E:
            E.add(comp)
    return E


def timeit(name):
    """ Décorateur qui s'utilise avec une méthode ou une fonction et qui affiche son temps d'exécution. """

    def wrap(method):
        def wrapped(*args, **kw):
            start = datetime.datetime.now()
            result = method(*args, **kw)
            end = datetime.datetime.now()
            time_elapsed = end - start
            if time_elapsed.total_seconds() * 100 > 5:
                print(method.__name__, time_elapsed.total_seconds(), "from", name)
            # print(method.__name__, time_elapsed, "from", name)
            return result

        return wrapped

    return wrap


def for_all_methods(decorator):
    """ Utilisé pour décorer toutes les méthodes d'une classe. """

    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate


def decorate_all_in_module(module, decorator):
    """ Utilisé pour décorer toutes les fonctions d'un module. """
    for attr in module.__dict__:
        if callable(getattr(module, attr)):
            setattr(module, attr, decorator(getattr(module, attr)))


def estimate_end(title: str, currentrly, max, start_time: datetime, extra_info: str = ""):
    """ Utilisé pour estimer un temps de calculs. """
    print(title)
    print(currentrly, "\t/\t", max, "\t", currentrly / max * 100, "%", extra_info)
    print((util_affiche_date((datetime.datetime.now() - start_time).total_seconds() * 1000)), "\t\t/\t",
          util_affiche_date((datetime.datetime.now() - start_time).total_seconds()
                            * max / currentrly * 1000))
    print(".")
