# launch file, install Cython and gcc then run main.py.

import pyximport
pyximport.install()

# import memoire_cython.SymmetricGroup
import memoire_cython.Sudoku
