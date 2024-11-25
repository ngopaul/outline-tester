import math
import os
from enum import Enum
import re

from flask import Flask, render_template, request, redirect, url_for, session

from test import generate_initial_outline, Occlusion, serialize_outline, deserialize_outline, calculate_new_dropout_rate

APP_VERSION = "1.0.0"

app = Flask(__name__)

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

@app.route('/', methods=['GET', 'POST'])
def index():
    output = ""
    setup_session_if_necessary()
    session["possible_files"] = os.listdir("./")
    session["possible_files"] = list(
        map(lambda f: f[:-4], filter(lambda f: os.path.isfile(f) and f.endswith(".txt") and f != "1000words.txt",
                                     session["possible_files"])))
    session["possible_files"] = sort_names(session["possible_files"])
    if request.method == 'POST':
        user_input = request.form['user_input']
        interpret(user_input)
    else:
        interpret(None)
    output_text = get_displayed_text()
    return render_template('index.html', output_text=output_text)


def setup_session_if_necessary():
    # app.logger.info("Setting up session")
    # handle old cookies to prevent errors
    if "version" not in session:
        app.logger.info(f"Clearing session because version not found")
        session.clear()
        session["version"] = APP_VERSION
    elif session["version"] != APP_VERSION:
        app.logger.info(f"Clearing session because version changed from {session['version']} to {APP_VERSION}")
        session.clear()
        session["version"] = APP_VERSION
    # set up session cookie
    if "occluded_outline" not in session:
        session['occluded_outline'] = None
    if "current_outline" not in session:
        session['current_outline'] = None
    if "current_difficulty" not in session:
        session['current_difficulty'] = None
    if "current_state" not in session:
        session['current_state'] = "CHOOSING_OUTLINE"
    if "occlusion_currently_guessing" not in session:
        session['occlusion_currently_guessing'] = None
    if "status" not in session:
        session['status'] = ""
    if "possible_files" not in session:
        session['possible_files'] = []
    if "response_message" not in session:
        session['response_message'] = ""


def get_repr_occluded_outline(temp_outline):
    output = ""
    printed_first_occlusion = False
    for i in range(len(temp_outline.outline)):
        if type(temp_outline.outline[i]) == Occlusion:
            if temp_outline.outline[i].guessed_correctly:
                output += "<span style='color: green'>"  # ("\033[92m")
            elif temp_outline.outline[i].skipped:
                output += "<span style='color: grey; font-style:italic'>"  # ("\033[93m")
            elif not printed_first_occlusion and temp_outline.outline[i].use_as_blank:
                output += "<span style='color: red'>"  #("\033[91m")
            output += (temp_outline.outline[i].get_display_value())
            if temp_outline.outline[i].guessed_correctly or temp_outline.outline[i].skipped or \
                    not (temp_outline.outline[i].guessed_correctly or temp_outline.outline[i].skipped) and \
                    not printed_first_occlusion and temp_outline.outline[i].use_as_blank:
                output += "</span>"  # ("\033[0m")
            if not (temp_outline.outline[i].guessed_correctly or temp_outline.outline[i].skipped) and \
                    not printed_first_occlusion and temp_outline.outline[i].use_as_blank:
                printed_first_occlusion = True
        else:
            output += (temp_outline.outline[i])
    output += "\n"
    return output

def get_outline_testing_links():
    """
    Instead of directly giving the strings, give <a> tags that submit the form immediately
    :return:
    """
    possible_files = session["possible_files"]
    output = ""
    for file in possible_files:
        output += f"<a href='javascript:submit_form_with_data(\"{file}\")'>{file}</a>, \n"
    return output[:-2]


def get_retry_difficulty_links():
    """
    Instead of directly giving the strings, give <a> tags that submit the form immediately
    :return:
    """
    possible_difficulties = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1000]
    difficulty_strings = ["No blanks", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "All blanks"]
    output = ""
    for i in range(len(possible_difficulties)):
        output += f"<a href='javascript:submit_form_with_data(\"RETRY!{possible_difficulties[i]}\")'>{difficulty_strings[i]}</a>, "
    return output[:-2]


def get_quit_hint_skip_links():
    output = ""
    output += "<a href='javascript:submit_form_with_data(\"quit\")'>quit</a>, "
    output += "<a href='javascript:submit_form_with_data(\"hint\")'>hint</a>, "
    output += "<a href='javascript:submit_form_with_data(\"skip\")'>skip</a>"
    return output


def get_difficulty_testing_links():
    """
    Instead of directly giving the strings, give <a> tags that submit the form immediately
    :return:
    """
    possible_difficulties = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1000]
    difficulty_strings = ["No blanks", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "All blanks"]
    output = ""
    for i in range(len(possible_difficulties)):
        output += f"<a href='javascript:submit_form_with_data(\"{possible_difficulties[i]}\")'>{difficulty_strings[i]}</a>, "
    return output[:-2]


def get_displayed_text():
    output = session['response_message'] + " " + "\n"
    # output += session['current_state'] + "\n"
    if session['current_state'] == "CHOOSING_OUTLINE":
        # if currently validating outline, or currently validating difficulty on page load
        output += "<h3>Welcome to the Memorization Practice Tool!</h3>" + "\n"
        output += "For longer outlines, it is recommended that you first <b>study/PSRP the material before</b> using this tool." + "\n"
        output += "There are 10 difficulties, 1 being the easiest and 10 being the hardest." + "\n"
        output += "(by the way, 0 means no blanks and 1000 means all blanks)" + "\n\n"
        output += "You can type hint, quit, or skip while testing an outline." + "\n"
        output += "This tool works best on a laptop with a keyboard. It is easier to read at zoom = 150%. " + "\n\n"
        output += "Type/click an outline to study:" + "\n"
        # output += "Possible outlines: " + ", ".join(session['possible_files']) + "\n"
        output += "Possible outlines: \n" + get_outline_testing_links() + "\n"
    elif session['current_state'] == "CHOOSING_DIFFICULTY":
        output += (f"Selected {session['current_outline']}. Enter/click desired difficulty (1-10)\n" +
                   get_difficulty_testing_links() + "\n")
    elif session['current_state'] == "ANSWERING_OUTLINE":
        temp_outline, _ = deserialize_outline(session['occluded_outline'], session['current_difficulty'] / 10)
        output += "Guess the blank. " + get_quit_hint_skip_links() + " otherwise.\n"
        output += f"Testing {session['current_outline']}, difficulty {session['current_difficulty']}. {session['status']}" + "\n"
        output += get_repr_occluded_outline(temp_outline)
    elif session['current_state'] == "FINISHED_OUTLINE":
        temp_outline, _ = deserialize_outline(session['occluded_outline'], session['current_difficulty'] / 10)
        occlusions_to_guess = [x for x in temp_outline.outline if type(x) == Occlusion and x.use_as_blank]

        output += get_repr_occluded_outline(temp_outline)
        num_blanks = len(occlusions_to_guess)
        num_attempts = sum([x.attempts for x in occlusions_to_guess])
        num_skipped = sum([x.skipped for x in occlusions_to_guess])
        num_hints = sum([x.hint_counter + 1 for x in occlusions_to_guess])
        output += "<span style='color: green'>" + "\n"
        output += f"Finished testing {session['current_outline']}, level {session['current_difficulty']}." + "\n"
        output += f"Filled {num_blanks} blanks." + "\n"
        output += f"Finished in {num_attempts} attempts, with {num_skipped} skipped, and {num_hints} hints given." + "\n"
        output += "</span>" + "\n"

        suggested_dropout_rate = calculate_new_dropout_rate(session['current_difficulty'] / 10, num_attempts,
                                                            num_skipped, num_blanks,
                                                            num_hints)
        if suggested_dropout_rate > 1:
            suggested_dropout_rate = 1
        suggested_dropout_rate = round(suggested_dropout_rate, 1)
        output += f"New suggested difficulty: {int(suggested_dropout_rate * 10)}" + "\n"
        session['current_state'] = "CHOOSING_OUTLINE"
        output += "Type/click an outline to study:" + "\n"
        output += "Possible outlines: \n" + get_outline_testing_links() + "\n"
        output += "Or retry with difficulty: " + "\n"
        output += "Difficulty: " + get_retry_difficulty_links() + "\n"

    return output


def interpret(input_text):
    """
    Change state based on input text and current state
    :param input_text:
    :return:
    """
    # replace all single apostrophes with a standard apostrophe
    if input_text is not None:
        input_text = input_text.replace("'", "'").replace("’", "'").replace("‘", "'").replace("’", "'").replace("‘", "'")
    # replace all non breaking spaces with regular spaces
    if input_text is not None:
        input_text = input_text.replace("\xa0", " ").replace("\u200b", " ").replace("\u200c", " ").replace(
            "\u200d"," ").replace("\uFEFF", " ")
    output = ""
    if session['current_state'] == "CHOOSING_OUTLINE":
        # if currently validating outline, or currently validating difficulty on page load
        # also occurs when you have finished an outline
        print(session['current_outline'])
        if input_text is None:
            session['response_message'] = ""
        elif input_text.startswith("RETRY!"):
            try:
                session['current_difficulty'] = int(input_text.replace("RETRY!", ""))
                assert session['current_difficulty'] >= 0
            except:
                session['response_message'] = "Not a valid difficulty, try again."
                session['current_state'] = "CHOOSING_DIFFICULTY"
                return
            session['response_message'] = ""
            temp_outline = generate_initial_outline(session['current_outline'] + ".txt", session['current_difficulty'] / 10)
            session['occluded_outline'] = serialize_outline(temp_outline)
            session['occlusion_currently_guessing'] = 0
            session['current_state'] = "ANSWERING_OUTLINE"
        elif input_text in session['possible_files']:
            session['response_message'] = ""
            session['current_outline'] = input_text
            session['current_state'] = "CHOOSING_DIFFICULTY"
        else:
            session['response_message'] = "Not a valid outline."
    elif session['current_state'] == "CHOOSING_DIFFICULTY":
        # if currently validating difficulty, or currently answering outline on page load
        if input_text is None:
            session['response_message'] = ""
        elif input_text in ["quit", "exit"]:
            session['response_message'] = ""
            session['current_state'] = "CHOOSING_OUTLINE"
        else:
            try:
                session['current_difficulty'] = int(input_text)
                assert 0 <= session['current_difficulty']
            except:
                session['response_message'] = "Not a valid difficulty, try again."
            else:
                session['response_message'] = ""
                temp_outline = generate_initial_outline(session['current_outline'] + ".txt", session['current_difficulty'] / 10)
                session['occluded_outline'] = serialize_outline(temp_outline)
                session['occlusion_currently_guessing'] = 0
                session['current_state'] = "ANSWERING_OUTLINE"
    elif session['current_state'] == "ANSWERING_OUTLINE":
        temp_outline, error = deserialize_outline(session['occluded_outline'], session['current_difficulty'] / 10)
        if error:
            session['response_message'] = "Error: " + error
            session['current_state'] = "CHOOSING_OUTLINE"
            return
        occlusions_to_guess = [x for x in temp_outline.outline if type(x) == Occlusion and x.use_as_blank]
        if not occlusions_to_guess:
            session['current_state'] = "FINISHED_OUTLINE"
            return
        if input_text is None:
            session['response_message'] = ""
        elif input_text.lower().strip() in ["quit", "exit"]:
            session['response_message'] = ""
            session['current_state'] = "CHOOSING_OUTLINE"
        elif input_text.lower().strip() == "hint":
            if occlusions_to_guess[session['occlusion_currently_guessing']].increase_hint():
                session['response_message'] = "Hint: " + occlusions_to_guess[
                    session['occlusion_currently_guessing']].get_display_value()
            else:
                session['response_message'] = "No more hints."
        elif input_text.lower().strip() == "skip":
            occlusions_to_guess[session['occlusion_currently_guessing']].skip()
            session['occlusion_currently_guessing'] += 1
            session['response_message'] = "Skipped. "
        else:
            if occlusions_to_guess[session['occlusion_currently_guessing']].guess(input_text, ignore_case=True,
                                                                                  ignore_whitespace=True):
                session['occlusion_currently_guessing'] += 1
                session['response_message'] = "Correct."
            else:
                session['response_message'] = f"'{input_text}' is incorrect."

        if (session['occlusion_currently_guessing'] >= len(occlusions_to_guess) or
                all([x.guessed_correctly or x.skipped for x in occlusions_to_guess])):
            session['current_state'] = "FINISHED_OUTLINE"
        session['occluded_outline'] = serialize_outline(temp_outline)
    elif session['current_state'] == "FINISHED_OUTLINE":
        if input_text is None:
            session['response_message'] = ""
        else:
            session['response_message'] = ""

app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

if __name__ == "__main__":
    app.run(debug=True)