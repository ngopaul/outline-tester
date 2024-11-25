class Occlusion {
  constructor(answer, hints) {
    this.answer = answer;
    this.wordsInAnswer = this.answer.split(" ");
    this.hints = hints.split(',');
    if (this.hints.length === 1 && this.hints[0] === '') {
      this.generatedHints = true;
      this.hints = [];
      let wordsCompleted = Array(this.wordsInAnswer.length).fill(false);
      let idx = 1, adder = 1, incAdderCounter = 0;
      while (!wordsCompleted.every(Boolean)) {
        this.hints.push(this.wordsInAnswer.map(word => word.slice(0, idx)).join(" "));
        wordsCompleted = this.wordsInAnswer.map(word => idx >= word.length);
        idx += adder;
        if (incAdderCounter) {
          adder += 1;
        }
        incAdderCounter = 1 - incAdderCounter;
      }
    } else {
      this.generatedHints = false;
    }
    this.attempts = 0;
    this.hintCounter = -1;
    this.useAsBlank = true;
    this.guessedCorrectly = false;
    this.skipped = false;
  }

  guess(guess, ignoreCase = false, ignoreWhitespace = false) {
    this.attempts += 1;
    if (ignoreCase && ignoreWhitespace) {
      if (guess.toLowerCase().trim() === this.answer.toLowerCase().trim()) {
        this.guessedCorrectly = true;
        return true;
      }
    } else if (ignoreWhitespace) {
      if (guess.trim() === this.answer.trim()) {
        this.guessedCorrectly = true;
        return true;
      }
    } else if (ignoreCase) {
      if (guess.toLowerCase() === this.answer.toLowerCase()) {
        this.guessedCorrectly = true;
        return true;
      }
    } else {
      if (guess === this.answer) {
        this.guessedCorrectly = true;
        return true;
      }
    }
    return false;
  }

  skip() {
    this.skipped = true;
  }

  increaseHint() {
    if (this.hintCounter < this.hints.length - 1) {
      this.hintCounter += 1;
      return true;
    } else {
      return false;
    }
  }

  getDisplayValue(withNumberOfWords = false) {
    if (!this.useAsBlank) {
      return this.answer;
    }
    if (this.guessedCorrectly) {
      return this.answer;
    } else if (this.skipped) {
      return this.answer;
    } else {
      let wordHintHelper = (this.wordsInAnswer.length > 1) ? `(${this.wordsInAnswer.length})` : "";
      if (this.hintCounter === -1) {
        let numBlanks = this.answer.length;
        return '_'.repeat(numBlanks) + (withNumberOfWords ? wordHintHelper : "");
      } else {
        let lengthOfHint = this.hints[this.hintCounter].length;
        let numBlanks = Math.max(1, (this.answer.length - lengthOfHint) / 2);
        return '_'.repeat(numBlanks) + this.hints[this.hintCounter] + '_'.repeat(numBlanks) + (withNumberOfWords ? wordHintHelper : "");
      }
    }
  }
}

function fetchFileContent(fileName) {
  return fetch(`../${fileName}`)
    .then(response => response.text())
    .then(data => data)
    .catch(error => console.error('Error fetching file:', error));
}

class OccludedOutline {
  constructor(inputFile) {
    this.originalUseAsBlanks = null;
    this.inputFile = inputFile;
    if (inputFile === "") {
      this.outline = [];
      this.filehash = "";
      return;
    }

    let rawOutline = fetchFileContent(inputFile);

    // wait for the file to be fetched
    rawOutline.then(data => {
      this.filehash = inputFile;
      if (data.includes("# shuffle-points\n")) {
        data += "\n"; // in case the last line is not a newline
        let [beforeText, pointsAndMore] = data.split("# shuffle-points\n");
        let [points, afterText] = pointsAndMore.split("# shuffle-points-end\n");
        points = points.split("\n").filter(x => x !== '');
        points = this.shuffleArray(points);
        data = beforeText + points.join("\n") + afterText;
      }

      this.outline = this.splitOutline(data);
      console.log(this.outline);
      this.combineConsecutiveOcclusions();
    });
  }

  shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }

  splitOutline(rawOutline) {
    let split1 = rawOutline.split('{{');
    let outline = [];
    for (let part1 of split1) {
      let split2 = part1.split('}}');
      if (split2.length === 1) {
        outline.push(split2[0]);
      } else {
        let split3 = split2[0].split('|');
        if (split3.length === 1) {
          outline.push(new Occlusion(split3[0], ''));
          outline.push(split2[1]);
        } else {
          outline.push(new Occlusion(split3[0], split3[1]));
          outline.push(split2[1]);
        }
      }
    }
    return outline.filter(x => x !== '');
  }

  setBlanks(dropoutRate, smartDropout = true) {
    const avoidWords = ["the", "of", "to", "and", "a"];
    let wordMapping = {};

    if (smartDropout) {
      // Implement reading from "1000words.txt"
      let words = []; // Placeholder
      let denom = 2;
      for (let word of words) {
        wordMapping[word] = 1 / denom;
        denom += 0.2;
      }
    }

    for (let item of this.outline) {
      if (item instanceof Occlusion) {
        if (avoidWords.includes(item.answer.toLowerCase()) && dropoutRate < 1) {
          item.useAsBlank = false;
        } else if (smartDropout) {
          let lowestWordMapping = 1 / 2;
          for (let word of item.answer.split(" ")) {
            word = word.replace(/[,\.\?!;:\(\)\[\]{}]/g, "").toLowerCase();
            if (word in wordMapping && wordMapping[word] < lowestWordMapping) {
              lowestWordMapping = wordMapping[word];
            } else {
              lowestWordMapping = 0;
              break;
            }
          }
          let tempDropoutRate = dropoutRate * Math.pow((1 - lowestWordMapping), 5);
          tempDropoutRate = dropoutRate * dropoutRate + tempDropoutRate * (1 - dropoutRate);
          if (Math.random() > tempDropoutRate) {
            item.useAsBlank = false;
          }
        } else if (Math.random() > dropoutRate) {
          item.useAsBlank = false;
        }
      }
    }
    this.originalUseAsBlanks = this.outline.filter(item => item instanceof Occlusion).map(item => item.useAsBlank);
    this.combineConsecutiveOcclusions();
  }

  hasConsecutiveOcclusions() {
    for (let i = 0; i < this.outline.length - 2; i++) {
      if (this.outline[i] instanceof Occlusion && this.outline[i + 1] === " " && this.outline[i + 2] instanceof Occlusion && this.outline[i].useAsBlank && this.outline[i + 2].useAsBlank) {
        return true;
      }
    }
    return false;
  }

  combineConsecutiveOcclusions() {
    while (this.hasConsecutiveOcclusions()) {
      let idx = 0;
      let newOutline = [];
      while (idx < this.outline.length - 2) {
        if (this.outline[idx] instanceof Occlusion && this.outline[idx + 1] === " " && this.outline[idx + 2] instanceof Occlusion && this.outline[idx].useAsBlank && this.outline[idx + 2].useAsBlank) {
          newOutline.push(
            new Occlusion(this.outline[idx].answer + " " + this.outline[idx + 2].answer, "")
          );
          idx += 3;
        } else {
          newOutline.push(this.outline[idx]);
          idx += 1;
        }
      }
      while (idx < this.outline.length) {
        newOutline.push(this.outline[idx]);
        idx += 1;
      }
      this.outline = newOutline;
    }
  }
}

function serializeOcclusion(occlusion) {
  return [occlusion.answer, occlusion.hints.length ? occlusion.hints : [], occlusion.attempts, occlusion.hintCounter, occlusion.guessedCorrectly, occlusion.skipped, occlusion.useAsBlank];
}

function deserializeOcclusion(occlusion) {
  let newOcclusion = new Occlusion(occlusion[0], occlusion[1].join(','));
  newOcclusion.attempts = occlusion[2];
  newOcclusion.hintCounter = occlusion[3];
  newOcclusion.guessedCorrectly = occlusion[4];
  newOcclusion.skipped = occlusion[5];
  newOcclusion.useAsBlank = occlusion[6];
  return newOcclusion;
}

function serializeOutline(outline) {
  return {
    inputFile: outline.inputFile,
    filehash: outline.filehash,
    originalUseAsBlanks: outline.originalUseAsBlanks,
    combinedOcclusions: outline.outline.filter(item => item instanceof Occlusion && item.useAsBlank).map(serializeOcclusion)
  };
}

function deserializeOutline(outline, dropoutRate) {
  let newOutline;
  try {
    newOutline = new OccludedOutline(outline.inputFile);
  } catch {
    return [null, "File not found, starting over."];
  }

  if (newOutline.filehash !== outline.filehash) {
    newOutline = generateInitialOutline(outline.inputFile, dropoutRate);
    return [newOutline, "Outline was outdated, starting over."];
  } else {
    let occlusionObjects = outline.combinedOcclusions.map(deserializeOcclusion);
    let occlusionIdx = 0;
    for (let item of newOutline.outline) {
      if (item instanceof Occlusion) {
        item.useAsBlank = outline.originalUseAsBlanks[occlusionIdx];
        occlusionIdx += 1;
      }
    }
    newOutline.combineConsecutiveOcclusions();
    let combinedOcclusionIdx = 0;
    for (let item of newOutline.outline) {
      if (item instanceof Occlusion && item.useAsBlank) {
        item.attempts = occlusionObjects[combinedOcclusionIdx].attempts;
        item.hintCounter = occlusionObjects[combinedOcclusionIdx].hintCounter;
        item.guessedCorrectly = occlusionObjects[combinedOcclusionIdx].guessedCorrectly;
        item.skipped = occlusionObjects[combinedOcclusionIdx].skipped;
        combinedOcclusionIdx += 1;
      }
    }
    newOutline.originalUseAsBlanks = outline.originalUseAsBlanks;
    return [newOutline, ""];
  }
}

function generateInitialOutline(inputFile, dropoutRate) {
  let outline = new OccludedOutline(inputFile);
  outline.setBlanks(dropoutRate);
  outline.combineConsecutiveOcclusions();
  return outline;
}

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
  if (inputText) {
    inputText = inputText.replace("'", "'").replace("’", "'").replace("‘", "'").replace("’", "'").replace("‘", "'");
  }
  if (inputText) {
    inputText = inputText.replace("\xa0", " ").replace("\u200b", " ").replace("\u200c", " ").replace(
      "\u200d"," ").replace("\uFEFF", " ");
  }
  let output = "";

  if (currentState === "CHOOSING_OUTLINE") {
    // if currently validating outline, or currently validating difficulty on page load
    // also occurs when you have finished an outline
    console.log(possibleFiles.toString() + inputText);
    if (!inputText) {
      responseMessage = "";
    } else if (inputText.startsWith("RETRY!")) {
      try {
        currentDifficulty = parseInt(inputText.replace("RETRY!", ""));
        if (currentDifficulty < 0 || isNaN(currentDifficulty)) {
          throw Error();
        }
      } catch {
        responseMessage = "Not a valid difficulty, try again."
        currentState = "CHOOSING_DIFFICULTY"
        return;
      }
      responseMessage = "";
      let tempOutline = generateInitialOutline(currentOutline + ".txt", currentDifficulty / 10);
      occludedOutline = serializeOutline(tempOutline);
      occlusionCurrentlyGuessing = 0;
      currentState = "ANSWERING_OUTLINE";
    } else if (possibleFiles.includes(inputText)) {
      responseMessage = "";
      currentOutline = inputText;
      currentState = "CHOOSING_DIFFICULTY"
    } else {
      responseMessage = "Not a valid outline."
    }
  } else if (currentState === "CHOOSING_DIFFICULTY") {
    if (!inputText) {
      responseMessage = ""
    } else if (responseMessage.toLowerCase().trim() == "quit" || responseMessage.toLowerCase().trim() == "exit") {
      responseMessage = "";
      currentState = "CHOOSING_OUTLINE"
    } else {
      try {
        currentDifficulty = parseInt(inputText.replace("RETRY!", ""));
        if (currentDifficulty < 0 || isNaN(currentDifficulty)) {
          throw Error();
        }
      } catch {
        responseMessage = "Not a valid difficulty, try again."
        currentState = "CHOOSING_DIFFICULTY"
        return;
      }
      responseMessage = "";
      tempOutline = generateInitialOutline(currentOutline + ".txt", currentDifficulty / 10);
      occludedOutline = serializeOutline(tempOutline);
      occlusionCurrentlyGuessing = 0;
      currentState = "ANSWERING_OUTLINE";
    }
  } else if (currentState === "ANSWERING_OUTLINE") {
    const [tempOutline, error] = deserializeOutline(occludedOutline, currentDifficulty / 10);
    if (error) {
      responseMessage = error;
      currentState = "CHOOSING_OUTLINE";
      return;
    }
    const occlusionsToGuess = tempOutline.outline.filter(x => x instanceof Occlusion && x.useAsBlank);
    if (!occlusionsToGuess) {
      currentState = "FINISHED_OUTLINE";
      return;
    }
    if (!inputText) {
      responseMessage = ""
    } else if (inputText.toLowerCase().trim() === "quit" || inputText.toLowerCase().trim() === "exit") {
      responseMessage = "";
      currentState = "CHOOSING_OUTLINE";
    } else if (inputText.toLowerCase().trim() === "hint") {
      if (occlusionCurrentlyGuessing < occlusionsToGuess.length && occlusionsToGuess[occlusionCurrentlyGuessing].increaseHint()) {
        responseMessage = "Hint: " + occlusionsToGuess[occlusionCurrentlyGuessing].getDisplayValue();
      } else {
        responseMessage = "No more hints.";
      }
    } else if (inputText.toLowerCase().trim() === "skip") {
      if (occlusionCurrentlyGuessing < occlusionsToGuess.length) {
        occlusionsToGuess[occlusionCurrentlyGuessing].skip();
        occlusionCurrentlyGuessing++;
        responseMessage = "Skipped.";
      }
    } else {
      if (occlusionCurrentlyGuessing < occlusionsToGuess.length && occlusionsToGuess[occlusionCurrentlyGuessing].guess(inputText, true, true)) {
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
  } else if (currentState == "FINISHED_OUTLINE") {
    responseMessage = "";
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
    const [tempOutline, _] = deserializeOutline(occludedOutline, currentDifficulty / 10);
    output += "Guess the blank. " + getQuitHintSkipLinks() + "\n";
    output += `Testing ${currentOutline}, difficulty ${currentDifficulty}. ${responseMessage}\n`;
    output += getReprOccludedOutline(tempOutline);
  } else if (currentState === "FINISHED_OUTLINE") {
    const [tempOutline, _] = deserializeOutline(occludedOutline, currentDifficulty / 10);
    output += getReprOccludedOutline(tempOutline);
    output += "Finished testing " + currentOutline + ", level " + currentDifficulty + ".\n";
    output += "Possible outlines: " + possibleFiles.map(file => `<a href='javascript:submitFormWithData("${file}")'>${file}</a>`).join(", ") + "\n";
  }
  document.getElementById('output').innerHTML = output;
}

function getReprOccludedOutline(tempOutline) {
  console.log("temp outline: \n" + tempOutline.toString());
  let output = "";
  let printedFirstOcclusion = false;
  for (let i = 0; i < tempOutline.outline.length; i++) {
    console.log("i: " + i);
    if (tempOutline.outline[i] instanceof Occlusion) {
      console.log("got occlusion: " + tempOutline.outline[i].getDisplayValue());
      if (tempOutline.outline[i].guessedCorrectly) {
        output += "<span style='color: green'>";
      } else if (tempOutline.outline[i].skipped) {
        output += "<span style='color: grey; font-style:italic'>";
      } else if (!printedFirstOcclusion && tempOutline.outline[i].useAsBlank) {
        output += "<span style='color: red'>";
      }
      output += tempOutline.outline[i].getDisplayValue();
      if (tempOutline.outline[i].guessedCorrectly || tempOutline.outline[i].skipped || !printedFirstOcclusion && tempOutline.outline[i].useAsBlank) {
        output += "</span>";
      }
      if (!tempOutline.outline[i].guessedCorrectly && !tempOutline.outline[i].skipped && !printedFirstOcclusion && tempOutline.outline[i].useAsBlank) {
        printedFirstOcclusion = true;
      }
    } else {
      console.log("got text: " + tempOutline.outline[i]);
      output += tempOutline.outline[i];
    }
  }
  return output + "\n";
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
