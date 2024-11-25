# outline-tester

This repository contains a python script, `test.py`, which 
can be used to help memorize long-form text. This runs in 
the command-line.

Using `app.py` will start a local server that does the same 
thing. This runs in your browser.

By placing `.txt` files in the local directory, and running
`python test.py`, the script will be able to read the files
and test the user on them by displaying blanks.

The user will have to first choose a file, then a 
difficulty (1-10). The script will then create a test with
blanks according to the difficulty. A difficulty of 0 will 
display no blanks and a difficulty of >100 will display
all blanks. 

## Format of testable files

A testable file is a `.txt` plaintext UTF-8 encoded file.
In order to make a word something that will be tested,
it must be in the following format: `{{word}}`. 

To supply hints, you may include something like:
`{{cat|meow,animal}}`, which will display `meow` as the 
first hint and `animal` as the second hint. Otherwise, 
hints will default to the word spelled out with increasing
numbers of letters (i.e. `c`, `ca`, `cat` if supplied with
`{{cat}}`). 

It may often be the case that you would like to test all
of the text in an outline. To do this, use the regex 
replacement in helpful-replacement-regexes.txt to replace
all words `word` with `{{word}}`.

### Examples

Examples provided: `gospel.txt` in `templates/`

Use by running `python test.py` in the console, or for a local server, run `python app.py`

## Additional features

Place `# shuffle-points` on its own line before a block
followed by `# shuffle-points-end` in order to shuffle
all the lines within when generating the test.

## Limitations and To-Dos

1. Handle different terminal sizes and text with many 
lines (beyond the terminal height)
