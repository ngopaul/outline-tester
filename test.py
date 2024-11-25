import json
import math
import os
import random
import hashlib
import re

ignore_files = ["1000words.txt", "helpful-replacement-regexes.txt"]

class Occlusion:
    """
    An occlusion, an object containing the correct value, hints, and the number of attempts at answering an occlusion.
    """

    def __init__(self, answer, hints):
        """
        Initialize the occlusion.
        :param answer: str, the correct answer.
        :param hints: list of str, the hints.
        """
        self.answer = answer
        self.words_in_answer = self.answer.split(" ")
        self.hints = hints.split(',')
        if len(self.hints) == 1 and self.hints[0] == '':
            self.generated_hints = True
            self.hints = []
            words_completed = [False for _ in range(len(self.words_in_answer))]
            idx = 1
            adder = 1
            inc_adder_counter = 0
            while not all(words_completed):
                self.hints.append(" ".join([s[:idx] + "_" * (len(s)-idx) for s in self.words_in_answer]))
                words_completed = [idx >= len(s) for s in self.words_in_answer]
                idx += adder
                if inc_adder_counter:
                    adder += 1
                inc_adder_counter = 1 - inc_adder_counter
        else:
            self.generated_hints = False
        self.attempts = 0
        self.hint_counter = -1
        self.use_as_blank = True
        self.guessed_correctly = False
        self.skipped = False

    def guess(self, guess, ignore_case=False, ignore_whitespace=False):
        """
        Guess the answer.
        :param guess: str, the guess.
        :param ignore_case: ignore the capitalization of the guess or not.
        :return: bool, whether the guess is correct.
        """
        self.attempts += 1
        if ignore_case and ignore_whitespace:
            if guess.lower().strip() == self.answer.lower().strip():
                self.guessed_correctly = True
                return True
        elif ignore_whitespace:
            if guess.strip() == self.answer.strip():
                self.guessed_correctly = True
                return True
        elif ignore_case:
            if guess.lower() == self.answer.lower():
                self.guessed_correctly = True
                return True
        else:
            if guess == self.answer:
                self.guessed_correctly = True
                return True
        return False

    def skip(self):
        """
        Skip the occlusion.
        """
        self.skipped = True

    def increase_hint(self):
        """
        Increase the hint counter. Return whether there are more hints to give.
        """
        if self.hint_counter < len(self.hints) - 1:
            self.hint_counter += 1
            return True
        else:
            return False

    def get_display_value(self, with_number_of_words=False):
        """
        Get the value to display for the occlusion.
        :return: str, the value to display.
        """
        if not self.use_as_blank:
            return self.answer

        if self.guessed_correctly:
            return self.answer
        elif self.skipped:
            return self.answer
        else:
            word_hint_helper = f"({len(self.words_in_answer)})" if len(self.words_in_answer) > 1 else ""
            if self.hint_counter == -1:
                num_blanks = len(self.answer)
                return '_' * num_blanks + (word_hint_helper if with_number_of_words else "")
            else:
                length_of_hint = len(self.hints[self.hint_counter])
                num_blanks = (len(self.answer) - length_of_hint)//2
                num_blanks = max(1, num_blanks)
                return self.hints[self.hint_counter] + (word_hint_helper if with_number_of_words else "")
                # return '_' + self.hints[self.hint_counter] + '_' + (word_hint_helper if with_number_of_words else "")


def serialize_occlusion(occlusion):
    """
    Serialize an occlusion.
    :param occlusion: Occlusion, the occlusion to serialize.
    :return: dict, the serialized occlusion.
    """
    return (occlusion.answer, occlusion.hints if not occlusion.generated_hints else [],
            occlusion.attempts, occlusion.hint_counter, occlusion.guessed_correctly, occlusion.skipped,
            occlusion.use_as_blank)

def deserialize_occlusion(occlusion):
    """
    Deserialize an occlusion.
    :param occlusion: tuple, the serialized occlusion.
    :return: Occlusion, the deserialized occlusion.
    """
    new_occlusion = Occlusion(occlusion[0], ",".join(occlusion[1]))
    new_occlusion.attempts = occlusion[2]
    new_occlusion.hint_counter = occlusion[3]
    new_occlusion.guessed_correctly = occlusion[4]
    new_occlusion.skipped = occlusion[5]
    new_occlusion.use_as_blank = occlusion[6]
    return new_occlusion


class OccludedOutline:
    """
    The representation of an outline with occlusions.
    """

    def __init__(self, input_file):
        """
        Initialize the occluded outline.
        :param input_file: str, path to the input file. The outline has occlusions of the form:
            {{correct_word|hint_word_1,hint_word_2,...,hint_word_n}}
        """
        self.original_use_as_blanks = None
        self.input_file = input_file
        if input_file == "":
            # probably deserializing
            self.outline = []
            self.filehash = ""
            return

        with open(input_file, 'r') as f:
            raw_outline = f.read()

        self.filehash = hashlib.md5(raw_outline.encode()).hexdigest()

        if "# shuffle-points\n" in raw_outline:
            # shuffle all bullet points around
            raw_outline += "\n"  # in case the last line is not a newline
            before_text = raw_outline.split("# shuffle-points\n")[0]
            points_and_more = raw_outline.split("# shuffle-points\n")[1]
            points = points_and_more.split("# shuffle-points-end\n")[0]
            if len(points_and_more.split("# shuffle-points-end\n")) == 1:
                after_text = ""
            else:
                after_text = points_and_more.split("# shuffle-points-end\n")[1]
            points = points.split("\n")
            points = [x for x in points if x != '']
            random.shuffle(points)
            raw_outline = before_text + "\n".join(points) + after_text

        self.outline = []
        ## split the outline where there are occlusions
        # force spaces after new lines to be viewable
        split_by_newlines = raw_outline.split('\n')
        for i in range(len(split_by_newlines)):
            # replace the first few spaces in each line with &nbsp;, but not the spaces in the middle of the outline
            j = 0
            is_space = True
            while j < len(split_by_newlines[i]) and is_space:
                if split_by_newlines[i][j] == ' ':
                    split_by_newlines[i] = split_by_newlines[i][:j] + '&nbsp;' + split_by_newlines[i][j+1:]
                else:
                    is_space = False
                j += 1
        force_spaced_outline = '\n'.join(split_by_newlines)
        split_1 = force_spaced_outline.split('{{')
        for i in range(len(split_1)):
            split_2 = split_1[i].split('}}')
            if len(split_2) == 1:
                self.outline.append(split_2[0])
            else:
                split_3 = split_2[0].split('|')
                if len(split_3) == 1:
                    self.outline.append(Occlusion(split_3[0], ''))
                    self.outline.append(split_2[1])
                else:
                    self.outline.append(Occlusion(split_3[0], split_3[1]))
                    self.outline.append(split_2[1])
        self.outline = [x for x in self.outline if x != '']

    def set_blanks(self, dropout_rate, smart_dropout=True):
        """
        Set the blanks in the outline.
        TODO change the hardcoded way to avoid the words the, of, to, and, a
        :param dropout_rate:
        :param smart_dropout:
        :return:
        """
        avoid_words = ["the", "of", "to", "and", "a"]
        if smart_dropout:
            with open("1000words.txt") as f:
                words = f.read().split("\n")
            denom = 2
            word_mapping = {}
            for word in words:
                word_mapping[word] = 1/denom
                denom += 0.2
        for i in range(len(self.outline)):
            if type(self.outline[i]) == Occlusion:
                if self.outline[i].answer.lower() in avoid_words and dropout_rate < 1:
                    # TODO change this to a more general way to avoid easy words
                    self.outline[i].use_as_blank = False
                elif smart_dropout:
                    # get the lowest word_mapping value of the words in the occlusion
                    lowest_word_mapping = 1/2
                    for word in self.outline[i].answer.split(" "):
                        # clean up commas and other punctuation
                        word = re.sub("[,.\?!;:\(\)\[\]{}]", "", word).lower()
                        if word in word_mapping and word_mapping[word] < lowest_word_mapping:
                            lowest_word_mapping = word_mapping[word]
                        else:
                            lowest_word_mapping = 0
                            break
                    temp_dropout_rate = dropout_rate * (1 - lowest_word_mapping) ** 5
                    # weight by how close dropout_rate is to 1
                    temp_dropout_rate = dropout_rate * dropout_rate + temp_dropout_rate * (1 - dropout_rate)
                    if random.random() > temp_dropout_rate:
                        self.outline[i].use_as_blank = False
                        # TODO remove
                        # print(self.outline[i].answer, f"[{round(temp_dropout_rate, 2)}] ", end="")
                elif random.random() > dropout_rate:
                    self.outline[i].use_as_blank = False
            elif "\n" in self.outline[i]:
                # TODO remove
                # print("\n")
                pass
        self.original_use_as_blanks = [x.use_as_blank for x in self.outline if type(x) == Occlusion]
        self.combine_consecutive_occlusions()

    def has_consecutive_occlusions(self):
        for i in range(len(self.outline) - 2):
            if isinstance(self.outline[i], Occlusion) and self.outline[i + 1] == " " and \
                    isinstance(self.outline[i + 2], Occlusion) and self.outline[i].use_as_blank and \
                    self.outline[i + 2].use_as_blank:
                return True

    def combine_consecutive_occlusions(self):
        while self.has_consecutive_occlusions():
            idx = 0
            new_outline = []
            while idx < len(self.outline) - 2:
                if isinstance(self.outline[idx], Occlusion) and self.outline[idx + 1] == " " and \
                        isinstance(self.outline[idx + 2], Occlusion) and self.outline[idx].use_as_blank and \
                        self.outline[idx + 2].use_as_blank:
                    new_outline.append(
                        Occlusion(self.outline[idx].answer + " " + self.outline[idx + 2].answer, "")
                    )
                    idx += 3
                else:
                    new_outline.append(self.outline[idx])
                    idx += 1
            while idx < len(self.outline):
                new_outline.append(self.outline[idx])
                idx += 1
            self.outline = new_outline


def serialize_outline(outline):
    """
    Serialize an outline.
    :param outline: OccludedOutline, the outline to serialize.
    :return: dict, the serialized outline.
    """
    return {
        "input_file": outline.input_file,
        "filehash": outline.filehash,
        "original_use_as_blanks": outline.original_use_as_blanks,
        "combined_occlusions": [serialize_occlusion(x) for x in outline.outline if type(x) == Occlusion and
                                x.use_as_blank]
    }

def deserialize_outline(outline, dropout_rate):
    """
    Deserialize an outline.
    :param outline: dict, the serialized outline.
    :return: OccludedOutline, the deserialized outline.
    """
    try:
    	new_outline = OccludedOutline(outline["input_file"])
    except:
    	return None, "File not found, starting over."
    # check if filehash matches. Otherwise the outline is outdated and should be regenerated
    if new_outline.filehash != outline["filehash"]:
        new_outline = generate_initial_outline(outline["input_file"], dropout_rate)
        error = "Outline was outdated, starting over."
    else:
        occlusion_objects = [deserialize_occlusion(x) for x in outline["combined_occlusions"]]
        occlusion_idx = 0
        for item in new_outline.outline:
            if type(item) == Occlusion:
                item.use_as_blank = outline["original_use_as_blanks"][occlusion_idx]
                occlusion_idx += 1
        # combine occlusions and apply history of attempts
        new_outline.combine_consecutive_occlusions()
        combined_occlusion_idx = 0
        for item in new_outline.outline:
            if type(item) == Occlusion and item.use_as_blank:
                item.attempts = occlusion_objects[combined_occlusion_idx].attempts
                item.hint_counter = occlusion_objects[combined_occlusion_idx].hint_counter
                item.guessed_correctly = occlusion_objects[combined_occlusion_idx].guessed_correctly
                item.skipped = occlusion_objects[combined_occlusion_idx].skipped
                combined_occlusion_idx += 1
        new_outline.original_use_as_blanks = outline["original_use_as_blanks"]
        error = ""

    return new_outline, error

def clear_screen():
    print("\033[H\033[J", end='')


def sigmoid(x):
    return 1 / (1 + math.e ** (-x))


def calculate_new_dropout_rate(dropout_rate, num_attempts, num_skipped, num_blanks, num_hints):
    """
    Calculate a new dropout rate based on the performance of the user.
    :param dropout_rate: a float between 0 and 1
    :param num_attempts: number of attempts to fill the blanks
    :param num_skipped: number skipped
    :param num_blanks: number of blanks
    :param num_hints: number of hints given
    :return: a float between 0 and 1
    """
    if num_blanks == 0:
        num_blanks = 1
    denom_denom = num_blanks - num_skipped
    if denom_denom == 0:
        denominator = 0
    else:
        denominator = (num_attempts + num_skipped * num_attempts / (num_blanks - num_skipped) + num_hints)
    breakeven_point = 1 - 1/math.e
    if denominator == 0:
        overall_score = breakeven_point
    else:
        overall_score = num_blanks / denominator
    # overall_score is between 0 and 1, 1 being perfect and 0 being infinitely bad.
    scaling_factor = 1 / breakeven_point
    normalized_score = overall_score * scaling_factor
    additional_scaler = 0.75 + (1 - dropout_rate)
    dropout_rate = (dropout_rate * normalized_score - dropout_rate) * additional_scaler + dropout_rate
    dropout_rate = min(dropout_rate, 1)
    dropout_rate = max(dropout_rate, 0)
    return dropout_rate

def generate_initial_outline(input_file, dropout_rate):
    """
    Generate an occluded outline of the input file.
    :param input_file: str, path to the input file. The outline has occlusions of the form:
        {{correct_word|hint_word_1,hint_word_2,...,hint_word_n}}
    :param dropout_rate: float, the probability of dropping a word from the outline.
    :return: OccludedOutline, the occluded outline.
    """
    outline = OccludedOutline(input_file)
    outline.set_blanks(dropout_rate)
    outline.combine_consecutive_occlusions()

    return outline


def test_outline(input_file, dropout_rate):
    """
    Test the occluded outline by asking the user to guess the occlusions. Keep on asking for the occlusions until
    the user guesses all of them correctly.
    :param input_file: str, path to the input file. The outline has occlusions of the form:
        {{correct_word|hint_word_1,hint_word_2,...,hint_word_n}}
    :param dropout_rate: float, the probability of dropping a word from the outline.
    """
    outline = generate_initial_outline(input_file, dropout_rate)
    occlusions_to_guess = [x for x in outline.outline if type(x) == Occlusion and x.use_as_blank]
    occlusion_currently_guessing = 0
    status = "Guess the blanks. Type 'quit', 'hint', 'skip' otherwise."
    exited_early = False
    while True:
        # clear the screen
        clear_screen()
        print(f"Testing {input_file[:-4]}, difficulty {int(dropout_rate * 10)}. {status}")
        printed_first_occlusion = False
        for i in range(len(outline.outline)):
            if type(outline.outline[i]) == Occlusion:
                if outline.outline[i].guessed_correctly:
                    print("\033[92m", end='')
                elif outline.outline[i].skipped:
                    print("\033[93m", end='')
                elif not printed_first_occlusion and outline.outline[i].use_as_blank:
                    print("\033[91m", end='')
                print(outline.outline[i].get_display_value(), end='')
                if outline.outline[i].guessed_correctly or outline.outline[i].skipped or \
                        not (outline.outline[i].guessed_correctly or outline.outline[i].skipped) and \
                        not printed_first_occlusion and outline.outline[i].use_as_blank:
                    print("\033[0m", end='')
                if not (outline.outline[i].guessed_correctly or outline.outline[i].skipped) and \
                        not printed_first_occlusion and outline.outline[i].use_as_blank:
                    printed_first_occlusion = True
            else:
                print(outline.outline[i], end='')
        print()
        if all([x.guessed_correctly or x.skipped for x in occlusions_to_guess]):
            break
        guess = input('> ')
        if guess in ['quit', 'exit']:
            exited_early = True
            break
        if occlusions_to_guess[occlusion_currently_guessing].guess(guess, ignore_case=True, ignore_whitespace=True):
            occlusion_currently_guessing += 1
            status = "Correct. 'quit', 'hint', 'skip' otherwise."
        elif guess == 'hint':
            if occlusions_to_guess[occlusion_currently_guessing].increase_hint():
                status = "Hint: " + occlusions_to_guess[occlusion_currently_guessing].get_display_value()
            else:
                status = "No more hints. Try again. 'quit', 'skip' otherwise."
        elif guess == 'skip':
            occlusions_to_guess[occlusion_currently_guessing].skip()
            occlusion_currently_guessing += 1
            status = "Skipped. 'quit', 'hint', 'skip' otherwise."
        else:
            status = f"'{guess}' is incorrect, try again. 'quit', 'hint', 'skip' otherwise."
    num_blanks = len(occlusions_to_guess)
    num_attempts = sum([x.attempts for x in occlusions_to_guess])
    num_skipped = sum([x.skipped for x in occlusions_to_guess])
    num_hints = sum([x.hint_counter + 1 for x in occlusions_to_guess])
    print(f"Finished testing {input_file[:-4]}, level {int(dropout_rate * 10)}.")
    print(f"Filled {num_blanks} blanks.")
    print(f"Finished in {num_attempts} attempts, with {num_skipped} skipped, and {num_hints} hints given.")

    suggested_dropout_rate = calculate_new_dropout_rate(dropout_rate, num_attempts, num_skipped, num_blanks, num_hints)
    if suggested_dropout_rate > 1:
        suggested_dropout_rate = 1
    suggested_dropout_rate = round(suggested_dropout_rate, 1)
    print(f"New suggested difficulty: {int(suggested_dropout_rate * 10)}" +
          (" (probably ignore this - exited early)" if exited_early else ""))


def custom_key(name):
    # Extract all parts of the string
    parts = re.split(r'(\d+)', name)

    # Convert numeric parts to integers and keep string parts as is
    key = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part)

    return key


def sort_names(names):
    return sorted(names, key=lambda name: (len(custom_key(name)), custom_key(name)))


def main_loop():
    print("Started outline tester in directory: " + os.getcwd(), ", file " + __file__)
    while True:
        possible_files = os.listdir("./")
        possible_files = list(
            map(lambda f: f[:-4],
                filter(lambda f: os.path.isfile(f) and f.endswith(".txt") and f not in ignore_files,
                       possible_files)))
        possible_files = sort_names(possible_files)
        print("Type an outline to study:")
        print("Possible outlines: " + ", ".join(possible_files))
        outline_name = input("> ")
        if outline_name in ["quit", "exit"]:
            break
        if outline_name in possible_files:
            quitting = False
            selected_difficulty = False
            difficulty = None
            while not selected_difficulty:
                print(f"Selected {outline_name}. Enter desired difficulty (1-10)")
                difficulty = input("> ")
                if difficulty in ["quit", "exit"]:
                    quitting = True
                    break
                try:
                    difficulty = int(difficulty)
                    assert 0 <= difficulty
                    selected_difficulty = True
                except:
                    print("Not a valid difficulty. Try again.")
            if quitting:
                continue
            test_outline(outline_name + ".txt", difficulty / 10)
        else:
            print("Not a valid outline.")


if __name__ == '__main__':
    main_loop()
    # parser = ArgumentParser(prog="Outline Tester", description="Provide outlines in the local directory with occlusions to be tested!")
    # args = parser.parse_args()
