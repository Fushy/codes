from collections import defaultdict, OrderedDict
import copy
from datetime import datetime
import itertools
import json
import random
import re
import socket
from time import sleep
from typing import Callable, Optional, TypeVar, Iterable
import json as json_api
import argparse

from _pytest.capture import CaptureResult
from bs4 import BeautifulSoup
from colorama import Back, Fore, Style, init
import pytest
import requests
from pandas import DataFrame
from requests.exceptions import ChunkedEncodingError, SSLError
from requests_html import HTMLSession
from ruamel_yaml.compat import ordereddict
from urllib3.exceptions import NewConnectionError, MaxRetryError

from dataframe import from_excel_to_dataframe
from Util import reverse_dict
from collections import OrderedDict

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


# noinspection ProblematicWhitespace
class TestQuestionsAnswers:
    def test_constructor_with_empty_dictionary(self):
        test_questions_answers = {}
        with pytest.raises(AssertionError):
            # questions_answers is empty
            QuestionsAnswers(test_questions_answers)

    def test_constructor_with_valid_input(self):
        test_questions_answers = {"Question 1": ["Answer 1"]}
        qa = QuestionsAnswers(test_questions_answers)
        assert qa.questions_answers == test_questions_answers
        assert qa.questions_answers_origin == {"Question 1": ["Answer 1"]}

    def test_constructor_with_invalid_input(self):
        test_questions_answers = {"Question 1": [1]}
        with pytest.raises(AssertionError):
            # noinspection PyTypeChecker
            QuestionsAnswers(test_questions_answers)  # questions_answers doesn't match a type of dict[str, list[str]]

    def test_question_with_non_empty_dictionary(self, mocker):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        mocker.patch('random.choice', return_value="Question 1")
        assert qa._question() == "Question 1"

    def test_answer_with_contain_to_validate_false_is_true(self):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        assert qa._answer("Question 1", "Answer 1") is True
        assert qa.questions_answers == {'Question 1': ['Answer 2'], 'Question 2': ['Answer 3', 'Answer 4']}
        assert qa._answer("Question 1", "Answer 2") is True
        assert qa.questions_answers == {'Question 1': [], 'Question 2': ['Answer 3', 'Answer 4']}
        assert qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}

    def test_answer_with_contain_to_validate_true_is_true(self):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        assert qa._answer("Question 1", "Answer", contain_to_validate=True) is True
        assert qa.questions_answers == {"Question 1": ["Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        assert qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}

    def test_answer_with_contain_to_validate_false_is_false(self):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        assert qa._answer("Question 1", "Wrong Answer") is False
        assert qa.questions_answers == qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"],
                                                                       "Question 2": ["Answer 3", "Answer 4"]}

    def test_answer_with_contain_to_validate_true_is_false(self):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        assert qa._answer("Question 1", "Anss", contain_to_validate=True) is False
        assert qa.questions_answers == qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"],
                                                                       "Question 2": ["Answer 3", "Answer 4"]}

    def test_answer_with_contain_to_validate_true_with_empty_text(self):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        assert qa._answer("Question 1", "", contain_to_validate=True) is False
        assert qa.questions_answers == qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"],
                                                                       "Question 2": ["Answer 3", "Answer 4"]}

    def test_reverse_dict(self):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        qa.reverse_dict()
        assert qa.questions_answers == {"Answer 1": ["Question 1"], "Answer 2": ["Question 1"],
                                        "Answer 3": ["Question 2"], "Answer 4": ["Question 2"]}
        assert qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}

    def test_training(self, mocker, capsys):
        test_questions_answers = {"Question 1": ["Answer 1"],
                                  "Question 2": ["Answer 2", "Answer 3"],
                                  "Question 3": ["Answer 4", "Answer 5", "Answer 6"],
                                  "Question 4": ["Answer 7", "Answer 8", "Answer 9", "Answer 10"],
                                  "Question 5": ["Answer 11", "Answer 12", "Answer 13", "Answer 14", "Answer 15"]}
        qa = QuestionsAnswers(test_questions_answers)
        mocker.patch('random.choice', side_effect=[f"Question {i}" for i in range(6) for _ in range(i)])
        mocker.patch('builtins.input', side_effect=[f"Answer {i}" for i in range(1, 15)] + ["q"])
        qa.training()
        assert capsys.readouterr() == CaptureResult(out='Question 1 |1|\n\tok\nQuestion 2 |2|\n\tok\n\tok\nQuestion 2 |2|\nAnswer'
                                                        ' 2   Answer 3   \n\nQuestion 3 |3|\n\tok\n\tok\nAnswer 4   Answer 5   An'
                                                        'swer 6   \n\nQuestion 3 |3|\nAnswer 4   Answer 5   Answer 6   \n\nQuesti'
                                                        'on 3 |3|\nAnswer 4   Answer 5   Answer 6   \n\nQuestion 4 |4|\n\tok\nAns'
                                                        'wer 10   Answer 7   Answer 8   Answer 9   \n\nQuestion 4 |4|\nAnswer 10 '
                                                        '  Answer 7   Answer 8   Answer 9   \n\nQuestion 4 |4|\nAnswer 10   Answe'
                                                        'r 7   Answer 8   Answer 9   \n\nQuestion 4 |4|\nAnswer 10   Answer 7   A'
                                                        'nswer 8   Answer 9   \n\nQuestion 5 |5|\nEnd training\n', err='')

    def test_reverse_dict_on_training(self, mocker, capsys):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"]}
        qa = QuestionsAnswers(test_questions_answers)
        mocker.patch('random.choice', side_effect=["Question 1", "Answer 1", "Question 1"])
        mocker.patch('builtins.input', side_effect=[".", "+", ".", "+", ".", "q"])
        qa.training()
        assert qa.questions_answers == qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"]}
        captured = capsys.readouterr()
        assert captured.out == """Question 1 |2|
Question 1
Answer 1
Answer 2
Answer 1 |1|
Answer 1
Question 1
Answer 2
Question 1
Question 1 |2|
Question 1
Answer 1
Answer 2
End training
"""

    def test_filter_with_filter_function_returning_true(self):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        qa.filter(lambda question, answers: True)
        assert qa.questions_answers == qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"],
                                                                       "Question 2": ["Answer 3", "Answer 4"]}

    def test_filter_with_filter_function_filtering_question(self):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        qa.filter(lambda question, answers: "1" in question)
        assert qa.questions_answers == {"Question 1": ["Answer 1", "Answer 2"]}
        assert qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}

    def test_filter_with_filter_function_filtering_answer(self):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        qa.filter(lambda question, answers: any(["3" in a for a in answers]))
        assert qa.questions_answers == {"Question 2": ["Answer 3", "Answer 4"]}
        assert qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}

    def test_training_with_correct_answers(self, mocker, capsys):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        mocker.patch('random.choice', side_effect=["Question 1", "Question 2", "Question 1"])
        mocker.patch('builtins.input', side_effect=["Answer 1", "Answer 2", "Answer 3", "Answer 4", "q"])
        qa.training()
        assert qa.questions_answers == qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"],
                                                                       "Question 2": ["Answer 3", "Answer 4"]}
        captured = capsys.readouterr()
        assert captured.out == """Question 1 |2|
ok
ok
Question 2 |2|
ok
ok
Question 1 |2|
End training
"""

    def test_training_with_uncorrect_answers(self, mocker, capsys):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"], "Question 2": ["Answer 3", "Answer 4"]}
        qa = QuestionsAnswers(test_questions_answers)
        mocker.patch('random.choice', side_effect=["Question 1", "Question 2", "Question 1"])
        mocker.patch('builtins.input', side_effect=["Answer 1", "Answer 3", "Answer 1", "q"])
        qa.training()
        assert qa.questions_answers == qa.questions_answers_origin == {"Question 1": ["Answer 1", "Answer 2"],
                                                                       "Question 2": ["Answer 3", "Answer 4"]}
        captured = capsys.readouterr()
        assert captured.out == """Question 1 |2|
ok
Answer 1   Answer 2   

Question 2 |2|
Answer 3   Answer 4   

Question 1 |2|
End training
"""

    def test_questions_answers_after_answering_and_printing(self, mocker, capsys):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"]}
        qa = QuestionsAnswers(test_questions_answers)
        mocker.patch('random.choice', return_value="Question 1")
        mocker.patch('builtins.input', side_effect=["Answer 1", ".", "q"])
        qa.training()
        assert qa.questions_answers == {"Question 1": ["Answer 1", "Answer 2"]}
        captured = capsys.readouterr()
        assert captured.out == """Question 1 |2|
ok
Question 1
Answer 1
Answer 2
End training
"""

    def test_questions_answers_after_answering_and_reversing(self, mocker, capsys):
        test_questions_answers = {"Question 1": ["Answer 1", "Answer 2"]}
        qa = QuestionsAnswers(test_questions_answers)
        mocker.patch('random.choice', side_effect=["Question 1", "Answer 1"])
        mocker.patch('builtins.input', side_effect=["Answer 1", "+", "q"])
        qa.training()
        assert qa.questions_answers == {"Answer 1": ["Question 1"], "Answer 2": ["Question 1"]}
        captured = capsys.readouterr()
        assert captured.out == """Question 1 |2|
ok
Answer 1 |1|
End training
"""


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


def lyrics_to_questions_answers(lyrics: str, next_line=False, next_part=False, duplicate_line=True) -> QuestionsAnswers:
    """
    @param lyrics: text lyrics (https://genius.com)
    @param next_line: Answer will be the following line
    @param next_part: Answer will be a part of the current line (second half)
    @param duplicate_line: keep duplicate lines
    """
    assert next_line ^ next_part, "Choose just one from next_line and next_part"
    lyrics = [line for line in lyrics.strip().split("\n") if line != "" and (line[0] != "[" and line[-1] != "]")]
    if not duplicate_line:
        seen = set()
        lyrics = [line for line in lyrics if line not in seen and not seen.add(line)]
    qa_dict = {}
    for i in range(len(lyrics)):
        line = lyrics[i]
        if next_part:
            split_index = closest_space_index(line)
            # split_index = len(line) // 2
            qa_dict[f"{i} {line[:split_index]} ..."] = [f"{i} {line[split_index:]}"]
            # qa_dict[f"... {i} {line[:split_index]}"] = [line[:split_index]]
        if next_line and i + 1 < len(lyrics):
            qa_dict[f"{i} {line}"] = [f"{i + 1} {lyrics[i + 1]}"]
    return QuestionsAnswers(qa_dict)


##### START LIB #####


T = TypeVar("T")
E = TypeVar("E")
json_base = list[dict[T, E]]
json_T = dict[T, E]


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


def is_iter_but_not_str(element):
    """ If iterable object and not str"""
    if isinstance(element, Iterable) and not isinstance(element, str):
        return True
    return False


def url_to_json(url: str, timelimit=1) -> Optional[json_T]:
    html_session = HTMLSession()
    try:
        start = datetime.now()
        json_value = None
        while True:
            try:
                if (datetime.now() - start).total_seconds() / 60 >= timelimit:
                    return None
                html_result_text = html_session.get(url)
                html_result_text = html_result_text.text
                if "503 Service Unavailable" in html_result_text or "<Response [403]>" in html_result_text:
                    print("url_to_json error: err Response in html_result_text")
                    sleep(5)
                    continue
                json_value = json_api.loads(html_result_text)
                break
            except (ChunkedEncodingError, ConnectionError, NewConnectionError, socket.gaierror, json.decoder.JSONDecodeError,
                    requests.exceptions.ConnectTimeout):
                printc("url_to_json ChunkedEncodingError", background_color="red")
                sleep(2)
                return url_to_json(url)
        return json_value
    except MaxRetryError or SSLError:
        return None


def json_base_to_json_ok(dictionaries: json_base | dict,
                         keys_aim: list[T],
                         keys_path_to_start: list[T] = None,
                         condition: Callable[[json_T], bool] = None,
                         doublons=True) -> json_T:
    """
    On remplace les indices de la liste de base en la transformant en un dictionnaire où
    les clefs seront les valeurs associées à la clef donnée en paramètre des dictionnaires de la liste.
    S'il y a plusieurs keys, tous les champs doivent avoir le même pattern
    """
    result = {}
    if keys_path_to_start is not None:
        for key in keys_path_to_start:
            dictionaries = dictionaries[key]
    if type(dictionaries) is dict:
        dictionaries = [dictionaries]
    for dictionary in dictionaries:
        key_cursor = dictionary
        for k in keys_aim[:-1]:
            key_cursor = key_cursor[k]
        key = key_cursor[keys_aim[-1]]
        if condition is not None and not condition(dictionary):
            continue
        if doublons and key in result:
            if type(result[key]) is not list:
                result[key] = [result[key]]
            result[key].append(dictionary)
        else:
            result[key] = dictionary
    return result


##### END LIB #####


song_lyrics = """
I know it's past visiting hours
But can I please give her these flowers?
The doctor don't wanna take procedures
He claim her heart can't take the anaesthesia
It'll send her body into a seizure
That lil' thing by the hospital bed, it'll stop beepin'
Hey, chick, I'm at a loss for words
What do you say at this time? Remember when I was 9?
Tell her everything gon' be fine, but I be lyin'
Her family cryin', they want her to live, and she tryin'
I'm arguin' like what kind of doctor can we fly in?
You know the best medicine go to people that's paid
If Magic Johnson got a cure for AIDS
And all the broke - passed away
You telling me if my grandma's in the NBA
Right now she'd be okay? But since she
Was just a secretary, worked for the church for 35 years
Things s'posed to stop right here?
My grandfather tryin to pull it together, he strong
That's where I get my confidence from
I asked the nurse "Did you do the research?"
She asked me, "Can you sign some t-shirts?"
-, is you smokin -?
You don't see that we hurt? But still
I smile, when Rosie comes to see me
And I can't wait for a sunny day (seeing it through your eyes)
Can't wait for the clouds to break
They outside of the emergency room, room
You can feel my heart beat, beat, beat
If she gon' pull through, we gon' find out soon
But right now she 'sleep, 'sleep, 'sleep
My momma say they say she could pass away any day
Hey chick, what these doctors know anyway?
Let me see the X-rays, I ain't no expert, I'm just hurt
Cousin Kim took off of work
Plus my Aunt Shirley, Aunt Beverly, Aunt Clay and Aunt Jean
So many Aunties we could have an Auntie Team
Feel like Amerie, it's just "One Thing"
When they said that she made it you see they eyes gleam
I think we at a all-time high
To get there, we run, we fly, we drive
'Cause with my family we know where home is
So instead of sending flowers, we the roses
I smile, when Rosie comes to see me
And I can't wait for a sunny day (seeing it through your eyes)
Can't wait for the clouds to break
Oh, Rosie brings the sunshine
I smile, when Rosie comes to see me
And I can't wait for a sunny day (seeing it through your eyes)
Can't wait for the clouds to break
I smile, when Rosie come to see me
And I'm sad, when Rosie goes away
Oh, Rosie brings the sunshine (say)
Can't wait, I can't wait, no
Can't wait, I can't wait, no
Can't wait, I can't wait
No, can't wait, for, for a sunny day
Momma can't wait, for the clouds to break
Mm, mmm, mm, mm-mm, mm-mm
Oh, oh, oh, oh, no, no, say
Tellin' you the truth now
Said I can't wait, uh-uh
I won't wait, no
"""


def tft_to_questions_answers(langage="en_us", version=None, pbe=False) -> dict | list:
    live = "pbe" if pbe else "latest"
    response = requests.get(f"https://raw.communitydragon.org/{live}/cdragon/tft/")
    soup = BeautifulSoup(response.text, 'html.parser')
    available_langages = [tr.text[:tr.text.find(".json")] for tr in soup.body.find_all('tr') if ".json" in tr.text]
    if langage not in available_langages:
        return available_langages
    tft_db = url_to_json(f"https://raw.communitydragon.org/{live}/cdragon/tft/{langage}.json")
    available_version = list(tft_db["sets"])
    if version is None:
        version = str(max(map(int, tft_db["sets"])))
    elif version not in available_version:
        return available_version
    champions = json_base_to_json_ok(tft_db, ["name"], ["sets", version, "champions"])
    tft_champions = defaultdict(list)
    for champion, values in champions.items():
        if "_" in champion:
            champion = champion.split("_")[-1]
        if "traits" in values:
            for trait in values["traits"]:
                if "_" in trait:
                    trait = trait.split("_")[-1]
                tft_champions[champion].append(trait)
    print("TFT set", version)
    return tft_champions


def main():
    parser = argparse.ArgumentParser(description="""A questions/answers training
    On training mode:
        Press "." to show all questions and answers
        Press "+" to swap Q/A to A/Q
        Press "q" to quit""")
    parser.add_argument('--train', required=False, action='store_true', help='Train mode')
    parser.add_argument('--exam', required=False, action='store_true', help='Exam mode')
    parser.add_argument('--tft', action='store_true', help='TFT mode')
    parser.add_argument('--lyrics', action='store_true', help='Kanye ghost town')
    parser.add_argument('--trad', action='store_true', help='English-French')
    parser.add_argument('-k', '--keys', required=False, type=int, help='Amount of keys to pick up (default: all keys)')
    parser.add_argument('--one_to_validate', required=False, action='store_true', help='One answer is enough to validate the'
                                                                                       'question')
    parser.add_argument('--contain_to_validate', required=False, action='store_true', help='A containing text into the answer is '
                                                                                           'enough to validate the answer')
    tft_group = parser.add_argument_group('TFT Options')
    tft_group.add_argument('-l', '--language', required=False, type=str, default="en_us",
                           help='Language setting (default: en_us)')
    tft_group.add_argument('-v', '--version', required=False, type=str, help='TFT version (default: latest)')
    tft_group.add_argument('--pbe', required=False, action='store_true', help='PBE setting')
    args = parser.parse_args()
    mode = "train" if (args.train or not args.exam) else "exam"
    if not (args.tft or args.lyrics or args.trad):
        print("Error: You must provide at least one of the options: --tft, --lyrics, or --trad")
        parser.print_help()
        exit(1)
    qa = None
    if args.tft:
        answer = tft_to_questions_answers(args.language, args.version, args.pbe)
        if type(answer) is list:
            print("Wrong option argument, choose from ", answer)
            exit(1)
        qa = QuestionsAnswers(answer)
    elif args.lyrics:
        qa = lyrics_to_questions_answers(song_lyrics, next_line=True, duplicate_line=False)
    elif args.trad:
        qa = file_to_questions_answers("anglais.txt")
    (qa.training(keys_to_pickup=args.keys, one_to_validate=args.one_to_validate,
                 contain_to_validate=args.contain_to_validate) if mode == "train" else qa.exam())
    qa.exam()
    exit(1)


def dataframe_to_questions_answers(dataframe: DataFrame, column_name_questions, column_name_answers) -> QuestionsAnswers:
    dataframe = dataframe[[column_name_questions.capitalize(), column_name_answers.capitalize()]]
    dataframe = dataframe.rename(columns={column_name_questions: 'questions', column_name_answers: 'answers'})
    qa = OrderedDict(dataframe.groupby('questions', sort=False)['answers'].agg(list))
    return QuestionsAnswers(qa)


def excel_to_questions_answers(file_name: str, column_name_questions, column_name_answers) -> QuestionsAnswers:
    dataframe = from_excel_to_dataframe(file_name)
    return dataframe_to_questions_answers(dataframe, column_name_questions, column_name_answers)


if __name__ == '__main__':
    main()
    # qa = lyrics_to_questions_answers(song_lyrics, next_line=True, next_part=False, duplicate_line=True)
    # qa.training(ordered=True)
    # qa_tft = QuestionsAnswers(tft_to_questions_answers(pbe=True))
    # qa_tft.reverse_dict()
    # # qa_tft.filter(items_filter=lambda keys, values: "R" in keys)
    # qa_tft.training(one_to_validate=False, contain_to_validate=False)
    # qa_tft.training(one_to_validate=False, contain_to_validate=False, keys_to_pickup=3)
    # qa_tft.exam(reset_if_wrong=True)
    # qa_tft.exam(reset_if_wrong=False, keys_to_pickup=5)
    # qa_english = file_to_questions_answers("anglais.txt")
    # while True:
    # qa = excel_to_questions_answers("english-french-tagalog.xlsx", "English", "French")
    # qa.training(normal_and_reverse=True, keys_to_pickup=5)
    # qa_english = file_to_questions_answers("anglais.txt")
    # qa_english.training(keys_to_pickup=3)

    # test_questions_answers = {"Question 1": ["Answer 1"],
    #                           "Question 2": ["Answer 2", "Answer 3"],
    #                           "Question 3": ["Answer 4", "Answer 5", "Answer 6"],
    #                           "Question 4": ["Answer 7"]}
    # qa = QuestionsAnswers(test_questions_answers)
    # qa.reverse_dict()
    # qa.training()
    # qa.exam()
