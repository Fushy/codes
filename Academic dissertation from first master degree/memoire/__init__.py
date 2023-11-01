import datetime

import SymmetricGroup
import TetraedralGroup
import OctahedralGroup
import CubicGroup
import DiedralGroup
import Permutation
import SudokuGroup
import Util


def launch_SymmetryGroup():
    start = datetime.datetime.now()
    G = CubicGroup.CubicGroup()
    G = OctahedralGroup.OctahedralGroup()
    G = TetraedralGroup.TetraedralGroup()
    G = DiedralGroup.DiedralGroup(5)
    print(G.polynome)
    print(G.orbits_number(Util.all_colorations(6, 2)))
    end = datetime.datetime.now()
    print("SymmetryGroup", end - start, "s")


def launch_SymmetricGroup(n):
    start = datetime.datetime.now()
    symmetric_group = SymmetricGroup.SymmetricGroup(6)
    end = datetime.datetime.now()
    print("launch_sudoku", end - start, "s")


def launch_sudoku(n):
    start = datetime.datetime.now()
    sudoku = SudokuGroup.SudokuGroup(2)
    end = datetime.datetime.now()
    print("Sudoku", end - start, "s")


if __name__ == '__main__':
    launch_SymmetryGroup()
    launch_SymmetricGroup(7)
    launch_sudoku(2)
