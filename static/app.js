let possibleFiles = [];
let occludedOutline = null;
let currentState = "CHOOSING_OUTLINE";
let currentDifficulty = null;
let currentOutline = null;
let occlusionCurrentlyGuessing = 0;
let responseMessage = "";
let session = {};

function handleFormSubmit() {
  const userInput = document.getElementById('user_input').value;
  interpret(userInput);
  updateDisplay();
}

function interpret(inputText) {
  if (currentState === "CHOOSING_OUTLINE") {
    if (possibleFiles.includes(inputText)) {
      currentOutline = inputText;
      currentState = "CHOOSING_DIFFICULTY";
    } else {
      responseMessage = "Not a valid outline.";
    }
  } else if (currentState === "CHOOSING_DIFFICULTY") {
    const difficulty = parseInt(inputText);
    if (difficulty >= 0 && difficulty <= 10) {
      currentDifficulty = difficulty;
      occludedOutline = generateInitialOutline(currentOutline + ".txt", currentDifficulty / 10);
      currentState = "ANSWERING_OUTLINE";
    } else {
      responseMessage = "Not a valid difficulty, try again.";
    }
  } else if (currentState === "ANSWERING_OUTLINE") {
    const tempOutline = deserializeOutline(occludedOutline, currentDifficulty / 10);
    const occlusionsToGuess = tempOutline.outline.filter(x => x instanceof Occlusion && x.useAsBlank);

    if (inputText.toLowerCase().trim() === "quit" || inputText.toLowerCase().trim() === "exit") {
      currentState = "CHOOSING_OUTLINE";
    } else if (inputText.toLowerCase().trim() === "hint") {
      if (occlusionsToGuess[occlusionCurrentlyGuessing].increaseHint()) {
        responseMessage = "Hint: " + occlusionsToGuess[occlusionCurrentlyGuessing].getDisplayValue();
      } else {
        responseMessage = "No more hints.";
      }
    } else if (inputText.toLowerCase().trim() === "skip") {
      occlusionsToGuess[occlusionCurrentlyGuessing].skip();
      occlusionCurrentlyGuessing++;
      responseMessage = "Skipped.";
    } else {
      if (occlusionsToGuess[occlusionCurrentlyGuessing].guess(inputText, true, true)) {
        occlusionCurrentlyGuessing++;
        responseMessage = "Correct.";
      } else {
        responseMessage = `'${inputText}' is incorrect.`;
      }
    }

    if (occlusionCurrentlyGuessing >= occlusionsToGuess.length || occlusionsToGuess.every(x => x.guessedCorrectly || x.skipped)) {
      currentState = "FINISHED_OUTLINE";
    }
    occludedOutline = serializeOutline(tempOutline);
  }
}

function updateDisplay() {
  let output = responseMessage + "\n";
  if (currentState === "CHOOSING_OUTLINE") {
    output += "<h3>Welcome to the FTTA Memorization Practice Tool!</h3>\n";
    output += "Possible outlines: " + possibleFiles.map(file => `<a href='javascript:submitFormWithData("${file}")'>${file}</a>`).join(", ") + "\n";
  } else if (currentState === "CHOOSING_DIFFICULTY") {
    output += `Selected ${currentOutline}. Enter/click desired difficulty (1-10)\n`;
    output += [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(difficulty => `<a href='javascript:submitFormWithData("${difficulty}")'>${difficulty}</a>`).join(", ") + "\n";
  } else if (currentState === "ANSWERING_OUTLINE") {
    const tempOutline = deserializeOutline(occludedOutline, currentDifficulty / 10);
    output += "Guess the blank. " + getQuitHintSkipLinks() + "\n";
    output += `Testing ${currentOutline}, difficulty ${currentDifficulty}. ${responseMessage}\n`;
    output += getReprOccludedOutline(tempOutline);
  } else if (currentState === "FINISHED_OUTLINE") {
    const tempOutline = deserializeOutline(occludedOutline, currentDifficulty / 10);
    output += getReprOccludedOutline(tempOutline);
    output += "Finished testing " + currentOutline + ", level " + currentDifficulty + ".\n";
    output += "Possible outlines: " + possibleFiles.map(file => `<a href='javascript:submitFormWithData("${file}")'>${file}</a>`).join(", ") + "\n";
  }
  document.getElementById('output').innerHTML = output;
}

function getQuitHintSkipLinks() {
  return "<a href='javascript:submitFormWithData(\"quit\")'>quit</a>, " +
    "<a href='javascript:submitFormWithData(\"hint\")'>hint</a>, " +
    "<a href='javascript:submitFormWithData(\"skip\")'>skip</a>";
}

function submitFormWithData(data) {
  document.getElementById("user_input").value = data;
  handleFormSubmit();
}

function fetchPossibleFiles() {
  fetch('/list_files')
    .then(response => response.json())
    .then(files => {
      possibleFiles = files;
      updateDisplay();
    })
    .catch(error => console.error('Error fetching file list:', error));
}

function init() {
  fetchPossibleFiles();
  document.getElementById('refresh_button').addEventListener('click', fetchPossibleFiles);
}

document.addEventListener('DOMContentLoaded', init);
