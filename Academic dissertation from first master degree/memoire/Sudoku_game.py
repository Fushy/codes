class SudokuGame(object):
    """
    Classe représentant un Sudoku_game
    Un sudoku classique contient neuf lignes et neuf colonnes, 81 cases au total.
    Le but du jeu est de remplir ces cases avec des chiffres allant de 1 à 9 en veillant
    toujours à ce qu'un même chiffre ne figure qu'une seule fois par colonne,
    une seule fois par ligne, et une seule fois par carré de neuf cases.
    """

    def __init__(self, taille: int):
        """
        On initialise un sudoku_game en indiquant la taille correspondant à
        la longueur d'un groupe, la grille est initialisé à une liste vide
        On rempli la grille en utilisant la méthode ajoute_ligne
        """
        self.taille = taille
        self.grille = []

    def __repr__(self):
        return_value = ""
        for i in range(len(self.grille)):
            ligne = self.grille[i]
            for j in range(len(ligne)):
                nombre = ligne[j]
                if nombre is None:
                    nombre = "."
                return_value += '{: ^5}'.format(nombre)
                if j < len(ligne) - 1:
                    return_value += "|"
                    if (j % self.taille) == self.taille - 1:
                        return_value += "||"
                j += 1
            return_value += " \n"
            for _ in range(6 * self.taille ** 2 + (self.taille - 1)):
                # 6 est la taille sur laquelle une case est représenté,
                # on ne peut pas générifier l'affichage sur le stdout
                # au caractère près car chaque caractère de ne possède
                # pas la même longueur d'affichage (9 != |)
                return_value += "-"
            return_value += "\n"
            if i % self.taille == self.taille - 1 and i != len(ligne) - 1:
                for _ in range(2):
                    for _ in range(6 * self.taille ** 2 + (self.taille - 1)):
                        return_value += "-"
                    return_value += "\n"
            i += 1
        return return_value

    def ajoute_ligne(self, *ligne):
        """
        Ajoute une ligne à la grille du sudoku_game.
        :param ligne: Peut être une liste de longeur (self.taille ** 2) ou une succession de (self.taille ** 2) nombres.
        """
        assert len(self.grille) < (self.taille ** 2), "La grille est déjà rempli"
        if len(ligne) > 1:
            assert len(ligne) == (self.taille ** 2), "La taille de la ligne ajouté n'est pas valide"
            self.grille.append(list(ligne))
        else:
            assert len(ligne[0]) == (self.taille ** 2), "La taille de la ligne ajouté n'est pas valide"
            self.grille.append(list(ligne[0]))

    def change_ligne(self, n1: int, n2: int):
        """
        Effectue une permutation de ligne. La ligne de la grille d'indice (n1 - 1) est échangé avec la ligne de la grille d'indice (n2 - 1)
        :param n1: min 1, max (self.taille ** 2)
        :param n2: min 1, max (self.taille ** 2)
        """
        assert 0 < n1 <= (self.taille ** 2) and 0 < n2 <= (self.taille ** 2), "Mauvais indice entré"
        self.grille[n1 - 1], self.grille[n2 - 1] = self.grille[n2 - 1], self.grille[n1 - 1]

    def change_colonne(self, n1: int, n2: int):
        """
        Effectue une permutation de colonne.
        :param n1: min 1, max (self.taille ** 2)
        :param n2: min 1, max (self.taille ** 2)
        """
        assert 0 < n1 <= (self.taille ** 2) and 0 < n2 <= (self.taille ** 2), "Mauvais indice entré"
        for i in range(self.taille ** 2):
            self.grille[i][n1 - 1], self.grille[i][n2 - 1] = self.grille[i][n2 - 1], self.grille[i][n1 - 1]

    def change_case(self, x: int, y: int, valeur: int):
        """
        Effectue une modification sur la grille.
        :param x: min 1, max (self.taille ** 2)
        :param y: min 1, max (self.taille ** 2)
        :param valeur: nouvelle valeur de la case
        """
        assert 0 < x <= (self.taille ** 2) and 0 < y <= (self.taille ** 2), "Mauvais indice entré"
        self.grille[y - 1][x - 1] = valeur

    def est_resolu(self):
        """
        Vérifie si le sudoku_game est résolu.
        Utilise un algorithme qui vérifie si tous les différents ensemble (ligne, colonne, groupe) sont égaux.
        """
        if len(self.grille) < (self.taille ** 2):
            return False
        ensemble = set(self.grille[0])
        if len(ensemble) != (self.taille ** 2):
            return False
        ii = 0
        for i in range(len(self.grille)):
            ligne = set()
            colonne = set()
            groupe = set()
            jj = 0
            for j in range(len(self.grille)):
                ligne.add(self.grille[i][j])
                colonne.add(self.grille[j][i])
                groupe.add(self.grille[(jj + ii * self.taille) % (self.taille ** 2)][
                               (j % self.taille + i * self.taille) % (self.taille ** 2)])
                if (j % self.taille) == self.taille - 1:
                    jj += 1
            if ligne != ensemble or colonne != ensemble or groupe != ensemble:
                return False
            if (i % self.taille) == self.taille - 1:
                ii += 1
        return True


###################
if __name__ == '__main__':
    # Taille 2
    jeu = SudokuGame(2)
    print(jeu.est_resolu())
    jeu.ajoute_ligne(1, 2, 3, 4)
    jeu.ajoute_ligne(3, 4, 1, 2)
    jeu.ajoute_ligne(2, 1, 4, 3)
    jeu.ajoute_ligne(4, 3, 2, 1)
    print(jeu.grille)
    print(jeu)
    print(jeu.est_resolu())
    jeu.change_ligne(1, 2)
    print(jeu.est_resolu())

    # ## Taille 3
    # jeu = Sudoku_game(3)
    # print(jeu.est_resolu())
    #
    # # Non résolu
    # # jeu.ajoute_ligne([5, 3, None, None, 7, None, None, None, None])
    # # jeu.ajoute_ligne((6, None, None, 1, 9, 5, None, None, None))
    # # jeu.ajoute_ligne(None, 9, 8, None, None, None, None, 6, None)
    # # jeu.ajoute_ligne(8, None, None, None, 6, None, None, None, 3)
    # # jeu.ajoute_ligne(4, None, None, 8, None, 3, None, None, 1)
    # # jeu.ajoute_ligne(7, None, None, None, 2, None, None, None, 6)
    # # jeu.ajoute_ligne(None, 6, None, None, None, None, 2, 8, None)
    # # jeu.ajoute_ligne(None, None, None, 4, 1, 9, None, None, 5)
    # # jeu.ajoute_ligne(None, None, None, None, 8, None, None, 7, 9)
    #
    # # Résolu
    # jeu.ajoute_ligne([5, 3, 4, 6, 7, 8, 9, 1, 2])
    # jeu.ajoute_ligne((6, 7, 2, 1, 9, 5, 3, 4, 8))
    # jeu.ajoute_ligne(1, 9, 8, 3, 4, 2, 5, 6, 7)
    # jeu.ajoute_ligne(8, 5, 9, 7, 6, 1, 4, 2, 3)
    # jeu.ajoute_ligne(4, 2, 6, 8, 5, 3, 7, 9, 1)
    # jeu.ajoute_ligne(7, 1, 3, 9, 2, 4, 8, 5, 6)
    # jeu.ajoute_ligne(9, 6, 1, 5, 3, 7, 2, 8, 4)
    # jeu.ajoute_ligne(2, 8, 7, 4, 1, 9, 6, 3, 5)
    # jeu.ajoute_ligne(3, 4, 5, 2, 8, 6, 1, 7, 9)
    # # jeu.ajoute_ligne(3, 4, 5, 2, 8, 6, 1, 7, 9)
    #
    # print(jeu)
    # jeu.change_colonne(1, 2)
    # print(jeu.est_resolu())
    # jeu.change_case(1, 2, 9)
    # print(jeu.est_resolu())
