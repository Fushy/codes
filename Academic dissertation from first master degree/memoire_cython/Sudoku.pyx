from __future__ import print_function
import datetime
from functools import reduce
from itertools import combinations, permutations, product
from math import sqrt, pow, factorial, floor

cdef class SudokuStructure(object):
    cdef int seed
    cdef int degree
    cdef tuple permutation

    def __cinit__(self, int seed):
        self.seed = seed
        cdef int lines = seed, columns = seed
        self.degree = lines * columns
        self.permutation = tuple(range(1, self.degree ** 2 + 1))

    def __str__(self) -> str:
        return "self.degree = " + str(self.degree) + "\n" + str(self.permutation) + "\n" \
               + tostr_permutation_as_sudoku(self.permutation)

    cdef tuple permute_band(self, int line_1, int line_2):
        cdef tuple permut
        cdef list permuts
        cdef SudokuStructure grid
        grid = SudokuStructure(self.seed)
        grid.permutation = self.permutation
        permuts = self.split_grid()
        permuts = list(zip(permuts[line_1 - 1], permuts[line_2 - 1]))
        for permut in permuts:
            grid.permutation = grid.permute_line(permut[0], permut[1])
        return grid.permutation

    cdef tuple permute_stack(self, int column_1, int column_2):
        cdef tuple permut
        cdef list permuts
        cdef SudokuStructure grid
        grid = SudokuStructure(self.seed)
        grid.permutation = self.permutation
        permuts = self.split_grid()
        permuts = list(zip(permuts[column_1 - 1], permuts[column_2 - 1]))
        for permut in permuts:
            grid.permutation = grid.permute_column(permut[0], permut[1])
        return grid.permutation

    cdef tuple permute_line(self, int line1, int line2):
        cdef tuple line_1, line_2
        cdef list grid
        cdef int column
        line_1 = tuple([self.get_case(line1, i) for i in range(1, self.degree + 1)])
        line_2 = tuple([self.get_case(line2, i) for i in range(1, self.degree + 1)])
        grid = list(self.permutation)
        for column in range(self.degree):
            grid[line_1[column] - 1], grid[line_2[column] - 1] = line_2[column], line_1[column]
        return tuple(grid)

    cdef tuple permute_column(self, int column1, int column2):
        cdef tuple column_1, column_2
        cdef list grid
        cdef int line
        column_1 = tuple([self.get_case(i, column1) for i in range(1, self.degree + 1)])
        column_2 = tuple([self.get_case(i, column2) for i in range(1, self.degree + 1)])
        grid = list(self.permutation)
        for line in range(self.degree):
            grid[column_1[line] - 1], grid[column_2[line] - 1] = column_2[line], column_1[line]
        return tuple(grid)

    cdef tuple diagonal_reflexion(self):
        cdef list grid = list(self.permutation)
        cdef int i, j
        for (i, j) in product(range(1, self.degree + 1), range(1, self.degree + 1)):
            grid[self.get_case(i, j) - 1] = self.permutation[self.get_case(j, i) - 1]
        return tuple(grid)

    cdef int get_case(self, int line, int column):
        return (line - 1) * self.degree + column

    cdef list to_permute(self):
        return [combinaison(split, 2) for split in self.split_grid()]

    cdef list split_grid(self):
        cdef int i
        cdef list values
        cdef list lst
        values = []
        lst = list(range(1, self.degree + 1))
        for i in range(int(sqrt(self.degree))):
            values.append(lst[i * int(sqrt(self.degree)):(i + 1) * int(sqrt(self.degree))])
        return values

cdef class SudokusStructure(SudokuStructure):
    cdef set E

    def __cinit__(self, int seed):
        self.seed = seed
        self.degree = seed ** 2
        super().__init__(seed)
        self.E = {tuple(self.permutation)}

    def __str__(self) -> str:
        result = ""
        for sudoku_structure in self.E:
            result += str(sudoku_structure)
        return result

    cdef void add(self, tuple permutation):
        self.E.add(permutation)

    cdef void all_elements(self):
        cdef int i
        cdef int old
        cdef long long permutation_max
        start = datetime.datetime.now()
        self.generator_set()
        result = set(self.E)
        permutation_max = int(pow(factorial(self.seed), (2 * self.seed + 2)) * 2)
        i = 2
        old = 0
        start_boucle = datetime.datetime.now()
        while len(result) < permutation_max:
            for combination in combinations(self.E, i):
                if ((datetime.datetime.now() - start_boucle).total_seconds()) > 5:
                    estimate_end(str(i), len(result), permutation_max, start, "\t gained+" + str(len(result) - old))
                    old = len(result)
                    start_boucle = datetime.datetime.now()
                for permutation in permutations(combination):
                    result.add(self.reduce_permutation_by_composition(permutation))
            i += 1
        self.E = result

    cdef void generator_set(self):
        cdef int i = 0
        cdef list permuts
        cdef tuple permut
        for permuts in self.to_permute():
            for permut in permuts:
                if i == 0:
                    self.add(self.permute_band(permut[0], permut[1]))
                    self.add(self.permute_stack(permut[0], permut[1]))
                self.add(self.permute_line(permut[0], permut[1]))
                self.add(self.permute_column(permut[0], permut[1]))
            i += 1
        self.add(self.diagonal_reflexion())

    cdef tuple reduce_permutation_by_composition(self, tuple permutations):
        return reduce(composition, permutations)

    def tostr_permutations_as_sudoku(self):
        return "\n\n".join([str(permutation) + "\n" +
                            tostr_permutation_as_sudoku(permutation) for permutation in sorted(self.E)])

cdef tuple composition(tuple perm_f, tuple perm_g):
    return tuple(perm_f[perm_g[i] - 1] for i in range(len(perm_f)))  # Ne fonctionne qu'avec des int

cdef list combinaison(list E, int k):
    return sorted(tuple(sorted(partie)) for partie in combinations(E, k))

cdef str tostr_permutation_as_sudoku(tuple permutation):
    result = "{: ^5}".format("") + "|"
    degree = sqrt(len(permutation))
    degree = int(degree)
    separator = sqrt(degree)
    for column in range(0, degree):
        result += "{: ^6}".format("C" + str(column + 1))
        result += (column + 1) % separator == 0 and column != degree - 1 and "|" * 3 or "|"
    separe_size = len(result) - 7
    result += "\n" + "{: ^6}".format("") + "-" * separe_size
    for line in range(0, len(permutation)):
        if line % degree == 0:
            result += "\n{: ^6}".format("L" + str(line // degree + 1) + "-|")
        result += "{: ^6}".format(str(permutation[line])) + "|"
        result += (line + 1) % separator == 0 and (line + 1) % degree != 0 and "|" * 2 or ""
        if (line + 1) % (degree * separator) == 0:
            result += "\n" + "{: ^6}".format("") + "-" * separe_size
    return result

def util_affiche_date(millisecondes: int) -> str:
    format = ""

    annee = millisecondes / 1000 / 60 / 60 / 24 / 30 / 12
    if annee >= 1:
        annee_ecrit = floor(annee)
        format = str(annee_ecrit) + "A "
        millisecondes -= 1000 * 60 * 60 * 24 * 30 * 12 * annee_ecrit

    mois = millisecondes / 1000 / 60 / 60 / 24 / 30
    if mois >= 1:
        mois_ecrit = floor(mois)
        format += str(mois_ecrit) + "M "
        millisecondes -= 1000 * 60 * 60 * 24 * 30 * mois_ecrit

    jours = millisecondes / 1000 / 60 / 60 / 24
    if jours >= 1:
        jours_ecrit = floor(jours)
        format += str(jours_ecrit) + "J "
        millisecondes -= 1000 * 60 * 60 * 24 * jours_ecrit

    heures = millisecondes / 1000 / 60 / 60
    if heures >= 1:
        heures_ecrit = floor(heures)
        format += str(heures_ecrit) + "h "
        millisecondes -= 1000 * 60 * 60 * heures_ecrit

    minutes = millisecondes / 1000 / 60
    if minutes >= 1:
        minutes_ecrit = floor(minutes)
        format += str(minutes_ecrit) + "m "
        millisecondes -= 1000 * 60 * minutes_ecrit

    secondes = millisecondes / 1000
    if secondes >= 1:
        secondes_ecrit = floor(secondes)
        format += str(secondes_ecrit) + "s "
        millisecondes -= 1000 * secondes_ecrit

    return format

def estimate_end(title: str, currentrly, max, start_time: datetime, extra_info: str = ""):
    print(title)
    print(currentrly, "\t/\t", max, "\t", currentrly / max * 100, "%", extra_info)
    print((util_affiche_date((datetime.datetime.now() - start_time).total_seconds() * 1000)), "\t\t/\t",
          util_affiche_date((datetime.datetime.now() - start_time).total_seconds()
                            * max / currentrly * 1000))
    print(".")

print(tostr_permutation_as_sudoku((1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)))

cdef SudokusStructure sudokus = SudokusStructure(2)
sudokus.all_elements()
print(len(sudokus.E))
