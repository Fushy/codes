from __future__ import print_function
import itertools
import datetime
import math

cdef class SymmetricGroup(Group):
    cdef int degree

    @staticmethod
    def create(degree: int) -> SymmetricGroup:
        """ Creation d'un groupe symmetrique """
        cdef SymmetricGroup sym
        identity = tuple(range(1, degree + 1))
        E = list_permutations(identity)
        operation_table = create_operation_table(E)
        return SymmetricGroup(set(E), operation_table)

    def __cinit__(self, set E, list operation_table):
        print("Start __cinit__ SymmetricGroup")
        self.degree = len(list(E)[0])
        cdef tuple identity
        identity = tuple(range(1, self.degree + 1))
        cdef list ens = list_permutations(identity)
        super().__init__(ens, operation_table, identity)
        print("End __cinit__ SymmetricGroup")

cdef class Group(Magma):
    cdef tuple identity

    def __cinit__(self, set E, list operation_table):
        print("Start __cinit__ Group")
        super().__init__(E, operation_table)
        self.identity = self.identity_element()
        # assert self.is_associative_timer(), "Object created is not a group algebraic structure."
        print("End __cinit__ Group")

cdef class Magma:
    cdef list E
    cdef dict dictionary
    cdef list operation_table
    cdef long long cardinality

    def __cinit__(self, set Ee, list operation_table):
        print("Start __cinit__ Magma")
        self.E = sorted(Ee)
        self.dictionary = dict(zip(self.E, range(0, len(Ee))))
        self.operation_table = operation_table
        self.cardinality = len(Ee)
        print("End __cinit__ Magma")

    def __str__(self):
        string = ["E = ", str(self.E), "\noperation_table = [", str(self.operation_table[0])]
        for i in range(1, self.cardinality):
            string.append("\n" + " " * len("operation_table = "))
            string.append(str(self.operation_table[i]))
        string.append("]\ncardinality = " + str(self.cardinality))
        return "".join(string)

    cdef op(self, tuple a, tuple b, int index_a = -1, int index_b = -1):
        if index_a >= 0 and index_b >= 0:
            return self.operation_table[index_a][index_b]
        elif index_a >= 0:
            return self.operation_table[index_a][self.dictionary[b]]
        elif index_b >= 0:
            return self.operation_table[self.dictionary[a]][index_b]
        else:
            return self.operation_table[self.dictionary[a]][self.dictionary[b]]

    def identity_element(self):
        neutral_elements_index = [i for i in range(self.cardinality) if tuple(self.E) == tuple(self.operation_table[i])]
        if len(neutral_elements_index) > 0:
            return self.E[neutral_elements_index[0]]
        return None

    cdef is_associative(self):
        for (i, j, k) in itertools.product(self.E, self.E, self.E):
            if not self.op(i, self.op(j, k)) == self.op(self.op(i, j), k):
                return False
        return True

    cdef is_associative_timer(self):
        print("START is_associative_timer")
        cdef long long count_iteration = self.cardinality ** 3
        cdef long i, j, k
        z = 0
        start = datetime.datetime.now()
        start_boucle = datetime.datetime.now()
        for i in range(self.cardinality):
            for j in range(self.cardinality):
                for k in range(self.cardinality):
                    z += 1
                    if not self.op(self.E[i], self.op(self.E[j], self.E[k], j, k), i) == self.op(
                            self.op(self.E[i], self.E[j], i, j), self.E[k], -1, k):
                        return False
                    if ((datetime.datetime.now() - start_boucle).total_seconds()) > 5:
                        print(z, "\t/\t", count_iteration, "\t", z / count_iteration * 100, "%")
                        print((util_affiche_date((datetime.datetime.now() - start).total_seconds() * 1000)), "\t\t/\t",
                              util_affiche_date(
                                  (datetime.datetime.now() - start).total_seconds() * count_iteration / z * 1000))
                        print(".")
                        start_boucle = datetime.datetime.now()
        return True

    cdef is_invertible(self, tuple e, tuple x):
        for element in self.E:
            if self.op(x, element) == self.op(element, x) == e:
                return True
        return False

    cdef is_all_invertible(self):
        cdef tuple e
        e = self.identity_element()
        if e is None:
            return False
        else:
            return all([self.is_invertible(e, x) for x in self.E])

    cdef tuple is_group(self):
        if self.identity_element() is None:
            return False, "Identity doesn't exist"
        if not self.is_all_invertible():
            return False, "Elements are not all invertible"
        # if not self.is_associative():
        if not self.is_associative_timer():
            return False, "Operation is not associative"
        return True, ''

cdef list_permutations(tuple E):
    return list(itertools.permutations(E))

cdef composition(tuple perm_f, tuple perm_g):
    cdef int i
    return tuple(perm_f[perm_g[i] - 1] for i in range(len(perm_f)))

def estimate_end(title: str, currentrly, max, start_time: datetime, extra_info: str = ""):
    print(title)
    print(currentrly, "\t/\t", max, "\t", currentrly / max * 100, "%", extra_info)
    print((util_affiche_date((datetime.datetime.now() - start_time).total_seconds() * 1000)), "\t\t/\t",
          util_affiche_date((datetime.datetime.now() - start_time).total_seconds()
                            * max / currentrly * 1000))
    print(".")

cdef list create_operation_table(list permutations):
    print("Start create_operation_table", len(permutations))
    cdef tuple permutation
    cdef tuple element
    cdef list result, comp
    result = []
    start = datetime.datetime.now()
    start_boucle = datetime.datetime.now()
    for permutation in permutations:
        comp = []
        for element in permutations:
            comp.append(composition(permutation, element))
        result.append(tuple(comp))
        if ((datetime.datetime.now() - start_boucle).total_seconds()) > 5:
            estimate_end("", len(result), len(permutations), start)
            start_boucle = datetime.datetime.now()
    print(len(result))
    print("End create_operation_table")
    return result
    # return [tuple([composition(permutation, element) for element in permutations]) for permutation in permutations]

def util_affiche_date(millisecondes):
    secondes_ecrit, annee_ecrit, mois_ecrit, jours_ecrit, heures_ecrit, minutes_ecrit = 0, 0, 0, 0, 0, 0

    annee = millisecondes / 1000 / 60 / 60 / 24 / 30 / 12
    if annee >= 1:
        annee_ecrit = math.floor(annee)
        millisecondes -= 1000 * 60 * 60 * 24 * 30 * 12 * annee_ecrit

    mois = millisecondes / 1000 / 60 / 60 / 24 / 30
    if mois >= 1:
        mois_ecrit = math.floor(mois)
        millisecondes -= 1000 * 60 * 60 * 24 * 30 * mois_ecrit

    jours = millisecondes / 1000 / 60 / 60 / 24
    if jours >= 1:
        jours_ecrit = math.floor(jours)
        millisecondes -= 1000 * 60 * 60 * 24 * jours_ecrit

    heures = millisecondes / 1000 / 60 / 60
    if heures >= 1:
        heures_ecrit = math.floor(heures)
        millisecondes -= 1000 * 60 * 60 * heures_ecrit

    minutes = millisecondes / 1000 / 60
    if minutes >= 1:
        minutes_ecrit = math.floor(minutes)
        millisecondes -= 1000 * 60 * minutes_ecrit

    secondes = millisecondes / 1000
    if secondes >= 1:
        secondes_ecrit = math.floor(secondes)
        millisecondes -= 1000 * secondes_ecrit

    format = ""
    if secondes_ecrit:
        format = str(secondes_ecrit) + "s "
    if minutes_ecrit:
        format = str(minutes_ecrit) + "m " + format
    if heures_ecrit:
        format = str(heures_ecrit) + "h " + format
    if jours_ecrit:
        format = str(jours_ecrit) + "J " + format
    if mois_ecrit:
        format = str(mois_ecrit) + "M " + format
    if annee_ecrit:
        format = str(annee_ecrit) + "A " + format
    return format

degree = 7

start = datetime.datetime.now()
SymmetricGroup.create(degree)
end = datetime.datetime.now()
print("degree", degree, ":", (end - start).total_seconds(), "s")
