import copy
import itertools
import random
import re
from collections import OrderedDict
from typing import Callable, Iterable, Optional, TypeVar

import pandas as pd
from colorama import Back, Fore, init, Style
from openpyxl.reader.excel import load_workbook
from pandas import DataFrame

# colors = ["WHITE", "BLACK", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN"]
colors = ["WHITE", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN"]


class QuestionsAnswers:
    """ A class that able to train question and answer
    The constructor takes a dict[str, list[str]] as argument where keys represent questions, and the corresponding values
    represent their respective answers
    Questions & Answers are colored to faster memoize them. Given a same questions_answers sample, they always have the same
    color """

    def __init__(self, questions_answers: dict[str, list[str]]):
        assert len(questions_answers) > 0, "questions_answers is empty"
        assert (isinstance(questions_answers, dict) and
                all(bool(isinstance(k, str) and isinstance(v, list) and all(isinstance(item, str) for item in v))
                    for k, v in questions_answers.items())), "questions_answers doesn't match a type of dict[str, list[str]]"
        self.questions_answers_origin: dict[str, list[str]] = copy.deepcopy(questions_answers)
        self.questions_answers: dict[str, list[str]] = questions_answers

    def filter(self, items_filter: Callable[[str, list[str]], bool]):
        """ Given a filter function that acts on question or answers, filter the questions_answers """
        self.questions_answers = {k: v for (k, v) in self.questions_answers.items() if items_filter(k, v)}

    def question(self) -> str:
        """ Return randomly a question from questions_answers """
        return random.choice(list(self.questions_answers.keys()))

    def question_index(self, index) -> str:
        """ Return a question corresponding to a given index """
        return list(self.questions_answers.keys())[index]

    def _answer(self, question: str, response: str, contain_to_validate=False) -> bool:
        """ Pop the answer if the response is correct. Response are case-insensitive
            If not contain_to_validate
                The response has to be exactly an answer into the answer list corresponding to the question
            If contain_to_validate
                The response has to be a subset from an answer into the answer list corresponding to the question
                Min 3 letters are accepted if the response has more or equal than 3 letters """
        answers = self.questions_answers[question]
        try:
            if contain_to_validate:
                # Can throw StopIteration blocks
                if len(response) <= 3 <= len(question):
                    # index = next(index for (index, answer) in enumerate(answers) if response.lower() == answer.lower())
                    return False
                else:
                    index = next(index for (index, answer) in enumerate(answers) if response.lower() == answer.lower())
            else:
                # Can throw ValueError
                index = list(map(lambda x: x.lower(), answers)).index(response.lower())
            self.questions_answers[question].pop(index)
            return True
        except (ValueError, StopIteration):
            return False

    def delete_line_return(self):
        self.questions_answers = {k.replace("\n", ""): v for (k, v) in self.questions_answers.items()}

    def reverse_dict(self):
        """ Reverse the self.questions_answers dictionary. Keys become values, and values become keys """
        self.questions_answers = reverse_dict(self.questions_answers)
        self.delete_line_return()

    def training(self, one_to_validate: bool = False, keys_to_pickup: Optional[int] = None, contain_to_validate=False,
                 ordered=False, normal_and_reverse=False):
        """ Train for the Q/A
            Press "." to show all questions and answers with corresponding colors
            Press "+" to swap Q/A to A/Q
            Press "-" to set questions_answers to its origin
            Press "q" to quit
            one_to_validate: One answer from all answer is enough to be considered as correct
            keys_to_pickup: Choose a given numbers of keys that will be the sample, questions will be selected randomly
        """
        if keys_to_pickup is not None:
            pickup_keys = random.sample(list(self.questions_answers.keys()),
                                        min(len(self.questions_answers), keys_to_pickup))
            self.questions_answers = {k: self.questions_answers[k] for k in pickup_keys}
        if normal_and_reverse:
            self.questions_answers.update(reverse_dict(self.questions_answers))
            self.delete_line_return()
        # Questions are sorted to obtain the same color for a same given questions_answers dict
        sorted_questions = sorted(self.questions_answers)
        questions_answers_training = copy.deepcopy(self.questions_answers)
        index = 0
        while True:
            question = self.question_index(index) if ordered else self.question()
            index = (index + 1) % len(self.questions_answers)
            answer = self.questions_answers[question]
            answer_recovery = sorted(answer)
            answers_color = colors[sorted_questions.index(question) % len(colors)]
            response = ""
            printc("{} |{}|".format(question, len(answer)), color=answers_color)
            i = 0
            while i < len(answer_recovery):
                response = input("\t")
                i += 1
                if response == ".":
                    for (q, answers) in sorted(questions_answers_training.items()):
                        color = colors[sorted_questions.index(q) % len(colors)]
                        printc("{} |{}|".format(q, len(answers)), color=color)
                        for a in answers:
                            printc("\t{}".format(a), color=color)
                    i -= 1
                    continue
                elif response == "q":
                    self.questions_answers[question] = answer_recovery
                    print("End training")
                    return
                elif response == "+":
                    self.questions_answers = questions_answers_training
                    self.reverse_dict()
                    sorted_questions = sorted(self.questions_answers)
                    questions_answers_training = copy.deepcopy(self.questions_answers)
                    break
                    # return self.training(one_to_validate, keys_to_pickup, contain_to_validate)
                elif response == "-":
                    self.questions_answers = copy.deepcopy(self.questions_answers_origin)
                correct = self._answer(question, response, contain_to_validate)
                if correct:
                    print("\tok")
                    if one_to_validate:
                        [printc(a.replace("\n", ""), color=answers_color, end="   ") for a in sorted(answer_recovery)]
                        print("\n")
                        break
                else:
                    [printc(a.replace("\n", ""), color=answers_color, end="   ") for a in sorted(answer_recovery)]
                    print("\n")
                    break
            """ Recovery the question's answers after they have been pop. """
            if all(r != char for r in response for char in "q+."):
                self.questions_answers[question] = answer_recovery

    def exam(self, reset_if_wrong=False, keys_to_pickup: Optional[int] = None, one_to_validate=False, contain_to_validate=False):
        """ Knowledge evaluation on the Q/A """
        if keys_to_pickup is not None:
            pickup_keys = random.sample(list(self.questions_answers.keys()),
                                        min(len(self.questions_answers), keys_to_pickup))
            self.questions_answers = {k: self.questions_answers[k] for k in pickup_keys}
        out_of = len(self.questions_answers) if one_to_validate else sum(map(len, self.questions_answers.values()))
        score = 0
        for _ in range(len(self.questions_answers)):
            question = self.question()
            answer = self.questions_answers[question]
            answer_recovery = sorted(answer)
            print(question)
            for _ in range(len(answer)):
                response = input("\t")
                correct = self._answer(question, response, contain_to_validate)
                if correct:
                    score += 1
                    printc("{:>20}/{}".format(score, out_of), "GREEN")
                    if one_to_validate:
                        break
                else:
                    [print(a, end="   ") for a in sorted(answer_recovery)]
                    if reset_if_wrong:
                        print("RESTART {}/{}\n".format(score, out_of), "RED")
                        self.questions_answers = copy.deepcopy(self.questions_answers_origin)
                        return self.exam(reset_if_wrong, one_to_validate, contain_to_validate)
                    else:
                        printc("WRONG {}/{}\n".format(score, out_of), "RED")
                        break
            del self.questions_answers[question]
            print()
        print("SUCCESS {}/{}".format(score, out_of))
        self.questions_answers = copy.deepcopy(self.questions_answers_origin)


##### START LIB #####


T = TypeVar("T")
E = TypeVar("E")
json_base = list[dict[T, E]]
json_T = dict[T, E]


def is_correct_lines(lines: list[str], debug=True) -> bool:
    questions_answers_pattern = r"[^\t\n\r]+\t[^\t\n\r]+[\n\r]"
    incorrect_lines = [(i + 1, lines[i]) for i in range(len(lines)) if re.fullmatch(questions_answers_pattern, lines[i]) is None]
    if debug and len(incorrect_lines) > 0:
        printc(str(incorrect_lines), color="red")
    return len(incorrect_lines) == 0


def file_to_questions_answers(file_name: str) -> QuestionsAnswers:
    lines = get_lines(file_name)
    assert (is_correct_lines(lines))
    qa = {question: answers.split("/") for (question, answers) in
          [(line.split("\t")[0], line.split("\t")[1]) for line in lines]}
    return QuestionsAnswers(qa)


def closest_space_index(text: str) -> int:
    if " " not in text:
        return -1
    midpoint = len(text) // 2
    left_move, right_move = 0, 0
    while True:
        if 0 <= midpoint - left_move and text[midpoint - left_move] == ' ':
            return midpoint - left_move
        if midpoint + right_move < len(text) and text[midpoint + right_move] == ' ':
            return midpoint + right_move
        left_move += 1
        right_move += 1

def get_lines(file_name: str, encoding="utf-8") -> Optional[list[str]]:
    try:
        with open(file_name, 'r', encoding=encoding) as file:
            return file.readlines()
    except FileNotFoundError:
        return None


def printc(text: str, color="green", background_color=None, attributes: Iterable[str] = ("NORMAL",), end="\n") -> None:
    init()
    style = getattr(Fore, color.upper()) if color != "" else ""
    if background_color:
        style += getattr(Back, background_color.upper())
    if attributes:
        " ".join([getattr(Style, attribute.upper()) for attribute in attributes])
    print("{}{}{}".format(style, text, Style.RESET_ALL), end=end)




def from_excel_to_dataframe(file_name: str, sheet_name=None) -> DataFrame:
    workbook = load_workbook(file_name)
    data = workbook.get_sheet_by_name(sheet_name) if sheet_name else workbook.active
    data = data.values
    headers = next(data)
    return pd.DataFrame(data, columns=headers)


def reverse_dict(dict_: dict) -> dict:
    """ Reverse the self.questions_answers dictionary. Keys become values, and values become keys """
    new_keys = sorted(set(itertools.chain.from_iterable(dict_.values())))
    return {new_key: [key for (key, values) in dict_.items() if new_key in values] for new_key in new_keys}


def dataframe_to_questions_answers(dataframe: DataFrame, column_name_questions, column_name_answers) -> QuestionsAnswers:
    dataframe = dataframe[[column_name_questions.capitalize(), column_name_answers.capitalize()]]
    dataframe = dataframe.rename(columns={column_name_questions: 'questions', column_name_answers: 'answers'})
    qa = OrderedDict(dataframe.groupby('questions', sort=False)['answers'].agg(list))
    return QuestionsAnswers(qa)


def excel_to_questions_answers(file_name: str, column_name_questions, column_name_answers, sheet_name=None) -> QuestionsAnswers:
    dataframe = from_excel_to_dataframe(file_name, sheet_name)
    return dataframe_to_questions_answers(dataframe, column_name_questions, column_name_answers)


##### END LIB #####


if __name__ == '__main__':
    while True:
        # qa = excel_to_questions_answers("english-french-tagalog.xlsx", "English", "French", sheet_name="Train")
        # qa = excel_to_questions_answers("english-french-tagalog.xlsx", "French", "Tagalog", sheet_name="Train")
        qa = excel_to_questions_answers("english-french-tagalog.xlsx", "English", "Tagalog", sheet_name="Train")
        qa.training(normal_and_reverse=True)
