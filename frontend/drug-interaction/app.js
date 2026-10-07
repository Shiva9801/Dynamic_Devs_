// =====================================================
// DRUG INTERACTION CHECKER
// English + Hindi + Bengali + Marathi
// OCR + interaction checking + multilingual TTS
// + Voice Assistant
// =====================================================

// Member 2's server (same Wi-Fi). If their IP changes,
// update this line.
const API_URL = "http://10.0.3.58:8000/check";

// Page starts with this file.
const MOCK_URL = "real_response.json";

// Browser TTS languages
const VOICE = {
  en: "en-IN",
  hi: "hi-IN",
  bn: "bn-IN",
  mr: "mr-IN"
};

// Speech recognition languages
const SPEECH_LANG = {
  en: "en-IN",
  hi: "hi-IN",
  bn: "bn-IN",
  mr: "mr-IN"
};

let data;
let tr;
let lang = "en";

// Speech recognition object
let recognition = null;
let isListening = false;

const order = {
  contraindicated: 0,
  major: 1,
  moderate: 2,
  minor: 3
};


// =====================================================
// INITIALIZE
// =====================================================

async function init() {
  try {
    tr = await (await fetch("translations.json")).json();
    data = await (await fetch(MOCK_URL)).json();

    createVoiceAssistant();
    setupVoiceRecognition();

    render();

  } catch (err) {

    document.body.insertAdjacentHTML(
      "afterbegin",
      `<p style="color:red;padding:10px">
        ERROR: ${err.message}
      </p>`
    );

    console.error(err);
  }
}


// =====================================================
// TRANSLATION / DRUG NAME HELPERS
// =====================================================

function toEnglish(name) {

  const n = name.trim();
  const lower = n.toLowerCase();

  for (const key in tr.drugNames) {

    const d = tr.drugNames[key];

    if (
      key === lower ||
      d.en.toLowerCase() === lower ||
      d.hi === n ||
      d.bn === n ||
      d.mr === n
    ) {
      return key;
    }
  }

  return lower;
}


function t(key) {

  return (
    (tr[lang] && tr[lang][key]) ||
    tr.en[key] ||
    key
  );
}


function dn(name) {

  const d = tr.drugNames[name];

  return d
    ? (d[lang] || d.en)
    : name;
}


// =====================================================
// RUN INTERACTION CHECK
// =====================================================

async function runCheck() {

  const split = id =>
    document
      .getElementById(id)
      .value
      .split(",")
      .map(s => s.trim())
      .filter(Boolean)
      .map(toEnglish);

  const names = split("drugsInput");
  const foods = split("foodsInput");

  const status =
    document.getElementById("apiStatus");

  if (names.length === 0) {

    status.textContent =
      "Type or speak at least one medicine.";

    return;
  }

  status.textContent = "Checking...";

  const body = {

    patient_id: "demo1",

    drugs: names.map(n => ({
      name: n,
      generic: n,
      code: "",
      dose: "",
      confidence: 1
    })),

    foods: foods
  };


  try {

    const res = await fetch(
      API_URL,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify(body)
      }
    );


    if (!res.ok) {

      const detail =
        await res.text();

      throw new Error(
        "Server replied " +
        res.status +
        ": " +
        detail.slice(0, 300)
      );
    }


    data = await res.json();


    const count =
      (data.interactions || []).length;


    status.textContent =
      "✅ " +
      count +
      " interaction(s) found.";


    render();


    // After checking, speak a short result
    speakAssistantResult(names);


  } catch (err) {

    status.textContent =
      t("apiError") +
      " (" +
      err.message +
      ")";

    console.error(err);
  }
}


// =====================================================
// SORT INTERACTIONS
// =====================================================

function sortedInteractions() {

  return [...(data.interactions || [])]
    .sort(
      (a, b) =>
        order[a.severity] -
        order[b.severity]
    );
}


// =====================================================
// EXPLANATION
// =====================================================

function explanation(i) {

  const e =
    tr.explanations[
      i.drug_a + "+" + i.drug_b
    ] ||
    tr.explanations[
      i.drug_b + "+" + i.drug_a
    ];

  return e
    ? (e[lang] || e.en)
    : i.mechanism;
}


// =====================================================
// CONFIRMATION COUNT
// =====================================================

function pendingCount() {

  const low =
    data.low_confidence_drugs ||
    data.low_confidence ||
    [];


  return (
    low.filter(
      x => !x.confirmed
    ).length +

    (data.unresolved_drugs || [])
      .length
  );
}


// =====================================================
// MAIN RENDER
// =====================================================

function render() {

  document
    .querySelectorAll("[data-i18n]")
    .forEach(el => {

      el.textContent =
        t(el.dataset.i18n);

    });


  renderBanner();
  renderConfirm();
  renderPatient();
  renderDoctor();

  updateVoiceAssistantLanguage();
}


// =====================================================
// BANNER
// =====================================================

function renderBanner() {

  const b =
    document.getElementById("banner");

  b.innerHTML =
    pendingCount() > 0

      ? `
        <p
          style="
            background:#fff3cd;
            border-left:6px solid orange;
            padding:10px 14px;
            border-radius:6px;
          "
        >
          ${t("confirmFirst")}
        </p>
      `

      : "";
}


// =====================================================
// CONFIRM MEDICINES
// =====================================================

function renderConfirm() {

  const box =
    document.getElementById("confirm");

  box.innerHTML = "";


  const lowList =
    data.low_confidence_drugs ||
    data.low_confidence ||
    [];


  const unresolved =
    data.unresolved_drugs || [];


  if (
    lowList.length === 0 &&
    unresolved.length === 0
  ) {

    box.textContent =
      t("allClear");

    return;
  }


  lowList.forEach(item => {

    const raw =
      typeof item === "string"
        ? item
        : (
            item.raw_text ||
            item.name ||
            ""
          );


    const sug =
      typeof item === "string"
        ? item
        : (
            item.suggested ||
            item.generic ||
            item.name ||
            raw
          );


    const pct =
      item.confidence
        ? ` (${Math.round(
            item.confidence * 100
          )}%)`
        : "";


    const div =
      document.createElement("div");

    div.className =
      "confirm-item";


    if (item.confirmed) {

      div.textContent =
        `${dn(sug)} ${t("confirmed")}`;

    } else {

      div.innerHTML =
        `"${raw}" → <b>${dn(sug)}</b>${pct} `;


      const yes =
        document.createElement("button");

      yes.textContent =
        t("yes");


      yes.onclick = () => {

        item.confirmed = true;

        renderBanner();
        renderConfirm();

      };


      const edit =
        document.createElement("button");

      edit.textContent =
        t("edit");


      edit.onclick = () => {

        const name =
          prompt(
            "Medicine name:",
            sug
          );


        if (name) {

          item.suggested =
            toEnglish(name);

          item.confirmed = true;

          renderBanner();
          renderConfirm();

        }
      };


      div.append(
        yes,
        edit
      );
    }


    box.appendChild(div);

  });


  unresolved.forEach(item => {

    const label =
      typeof item === "string"
        ? item
        : (
            item.name ||
            item.raw_text ||
            JSON.stringify(item)
          );


    const div =
      document.createElement("div");

    div.className =
      "confirm-item";


    div.textContent =
      `${t("unresolved")}: ${label}`;


    box.appendChild(div);

  });
}


// =====================================================
// PATIENT VIEW
// =====================================================

function renderPatient() {

  const box =
    document.getElementById("patient");

  box.innerHTML = "";


  const list =
    sortedInteractions();


  if (list.length === 0) {

    box.textContent =
      t("noResults");

    return;
  }


  list.forEach(i => {

    const div =
      document.createElement("div");

    div.className =
      "alert " + i.severity;


    const text =
      `${dn(i.drug_a)} + ${dn(i.drug_b)}. ` +
      `${explanation(i)}`;


    div.innerHTML =
      `<b>${t(i.severity)}</b>: ` +
      `${dn(i.drug_a)} + ${dn(i.drug_b)}` +
      `<br>` +
      `${explanation(i)}` +
      `<br>`;


    const btn =
      document.createElement("button");

    btn.textContent =
      t("speak");


    btn.onclick = () =>
      speak(text);


    div.appendChild(btn);

    box.appendChild(div);

  });
}


// =====================================================
// DOCTOR VIEW
// =====================================================

function renderDoctor() {

  const list =
    sortedInteractions();


  if (list.length === 0) {

    document
      .getElementById("doctor")
      .textContent =
        t("noResults");

    return;
  }


  let rows = "";


  list.forEach(i => {

    const alts =
      (
        i.alternatives &&
        i.alternatives.length
      )

        ? i.alternatives
            .map(dn)
            .join(", ")

        : t("none");


    rows +=
      `<tr class="${i.severity}">
        <td>
          ${dn(i.drug_a)}
          +
          ${dn(i.drug_b)}
        </td>

        <td>
          ${t(i.type || "drug-drug")}
        </td>

        <td>
          ${t(i.severity)}
        </td>

        <td>
          ${i.mechanism}
        </td>

        <td>
          ${i.source}
        </td>

        <td>
          ${alts}
        </td>
      </tr>`;
  });


  document
    .getElementById("doctor")
    .innerHTML =
      `<table>
        <tr>
          <th>${t("drugs")}</th>
          <th>${t("type")}</th>
          <th>${t("severity")}</th>
          <th>${t("mechanism")}</th>
          <th>${t("source")}</th>
          <th>${t("alternatives")}</th>
        </tr>

        ${rows}

      </table>`;
}


// =====================================================
// TTS
// Bengali + Marathi = FastAPI TTS
// English + Hindi = Browser TTS
// =====================================================

async function speak(text) {

  if (!text) return;


  // -----------------------------------------------
  // BENGALI + MARATHI
  // -----------------------------------------------

  if (
    lang === "bn" ||
    lang === "mr"
  ) {

    try {

      const response =
        await fetch(
          "http://localhost:8001/speak",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body: JSON.stringify({
              text: text,
              language: lang
            })
          }
        );


      if (!response.ok) {

        throw new Error(
          "TTS server returned " +
          response.status
        );
      }


      const audioBlob =
        await response.blob();


      const audioUrl =
        URL.createObjectURL(
          audioBlob
        );


      const audio =
        new Audio(audioUrl);


      audio.onended = () => {

        URL.revokeObjectURL(
          audioUrl
        );

      };


      await audio.play();


    } catch (error) {

      console.error(
        "Regional voice error:",
        error
      );


      alert(
        "Voice could not be played."
      );

    }


    return;
  }


  // -----------------------------------------------
  // ENGLISH + HINDI
  // -----------------------------------------------

  speechSynthesis.cancel();


  const u =
    new SpeechSynthesisUtterance(
      text
    );


  u.lang =
    VOICE[lang] ||
    "en-IN";


  speechSynthesis.speak(u);
}


// =====================================================
// VOICE ASSISTANT UI
// Created automatically — no HTML change needed
// =====================================================

function createVoiceAssistant() {

  if (
    document.getElementById(
      "voiceAssistant"
    )
  ) {
    return;
  }


  const section =
    document.createElement("section");

  section.id =
    "voiceAssistant";


  section.style.cssText = `
    margin: 20px 0;
    padding: 18px;
    border: 1px solid #ddd;
    border-radius: 12px;
    background: #f8f9fa;
  `;


  section.innerHTML = `
    <h2 id="voiceTitle">
      🎤 Voice Assistant
    </h2>

    <p id="voiceHint">
      Tap the microphone and speak the medicine names.
    </p>

    <button
      id="voiceButton"
      type="button"
      style="
        font-size:18px;
        padding:12px 20px;
        cursor:pointer;
      "
    >
      🎙️ Speak
    </button>

    <button
      id="voiceStopButton"
      type="button"
      style="
        font-size:16px;
        padding:10px 16px;
        cursor:pointer;
        margin-left:8px;
        display:none;
      "
    >
      ⏹ Stop
    </button>

    <p
      id="voiceStatus"
      style="margin-top:12px;font-weight:bold;"
    >
      Ready
    </p>

    <div
      id="voiceTranscript"
      style="
        margin-top:10px;
        padding:10px;
        background:white;
        border-radius:8px;
        min-height:25px;
      "
    >
    </div>
  `;


  const banner =
    document.getElementById("banner");


  if (banner) {

    banner.parentNode.insertBefore(
      section,
      banner
    );

  } else {

    document.body.prepend(
      section
    );

  }


  document
    .getElementById("voiceButton")
    .addEventListener(
      "click",
      startListening
    );


  document
    .getElementById(
      "voiceStopButton"
    )
    .addEventListener(
      "click",
      stopListening
    );
}


// =====================================================
// SPEECH RECOGNITION SETUP
// =====================================================

function setupVoiceRecognition() {

  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


  if (!SpeechRecognition) {

    console.warn(
      "Speech Recognition is not supported."
    );

    return;
  }


  recognition =
    new SpeechRecognition();


  recognition.continuous =
    false;


  recognition.interimResults =
    false;


  recognition.maxAlternatives =
    1;


  recognition.onstart = () => {

    isListening = true;

    const status =
      document.getElementById(
        "voiceStatus"
      );


    const button =
      document.getElementById(
        "voiceButton"
      );


    const stopButton =
      document.getElementById(
        "voiceStopButton"
      );


    if (status) {

      status.textContent =
        getVoiceText(
          "listening"
        );

    }


    if (button) {

      button.style.display =
        "none";

    }


    if (stopButton) {

      stopButton.style.display =
        "inline-block";

    }
  };


  recognition.onresult =
    async (event) => {

      const transcript =
        event.results[0][0]
          .transcript
          .trim();


      console.log(
        "Patient said:",
        transcript
      );


      const output =
        document.getElementById(
          "voiceTranscript"
        );


      if (output) {

        output.textContent =
          `🗣️ ${transcript}`;

      }


      await processVoiceCommand(
        transcript
      );
    };


  recognition.onerror =
    (event) => {

      console.error(
        "Speech recognition error:",
        event.error
      );


      const status =
        document.getElementById(
          "voiceStatus"
        );


      if (status) {

        status.textContent =
          "❌ " +
          getSpeechErrorText(
            event.error
          );

      }
    };


  recognition.onend = () => {

    isListening = false;


    const button =
      document.getElementById(
        "voiceButton"
      );


    const stopButton =
      document.getElementById(
        "voiceStopButton"
      );


    if (button) {

      button.style.display =
        "inline-block";

    }


    if (stopButton) {

      stopButton.style.display =
        "none";

    }
  };
}


// =====================================================
// START LISTENING
// =====================================================

function startListening() {

  if (!recognition) {

    alert(
      "Speech recognition is not available in this browser."
    );

    return;
  }


  try {

    // Use the currently selected language.
    recognition.lang =
      SPEECH_LANG[lang] ||
      "en-IN";


    recognition.start();


  } catch (error) {

    console.error(
      "Could not start recognition:",
      error
    );

  }
}


// =====================================================
// STOP LISTENING
// =====================================================

function stopListening() {

  if (
    recognition &&
    isListening
  ) {

    recognition.stop();

  }
}


// =====================================================
// PROCESS SPOKEN COMMAND
// =====================================================

async function processVoiceCommand(
  transcript
) {

  const medicines =
    extractMedicinesFromSpeech(
      transcript
    );


  const status =
    document.getElementById(
      "voiceStatus"
    );


  if (medicines.length === 0) {

    if (status) {

      status.textContent =
        getVoiceText(
          "noMedicine"
        );

    }


    speak(
      getVoiceText(
        "noMedicineSpeak"
      )
    );


    return;
  }


  // Remove duplicates
  const uniqueMedicines =
    [...new Set(medicines)];


  // Put medicines into input
  const input =
    document.getElementById(
      "drugsInput"
    );


  if (input) {

    input.value =
      uniqueMedicines.join(", ");

  }


  if (status) {

    status.textContent =
      getVoiceText(
        "foundMedicine"
      ) +
      ": " +
      uniqueMedicines
        .map(dn)
        .join(", ");

  }


  // Automatically check
  await runCheck();
}


// =====================================================
// MEDICINE EXTRACTION FROM SPEECH
// =====================================================

function extractMedicinesFromSpeech(
  transcript
) {

  const text =
    transcript.trim();


  const lower =
    text.toLowerCase();


  const found = [];


  for (
    const key in tr.drugNames
  ) {

    const drug =
      tr.drugNames[key];


    const names = [
      drug.en,
      drug.hi,
      drug.bn,
      drug.mr,
      key
    ];


    for (
      const name of names
    ) {

      if (!name) continue;


      const candidate =
        name.toLowerCase();


      if (
        lower.includes(candidate)
      ) {

        found.push(key);

        break;
      }
    }
  }


  return found;
}


// =====================================================
// SPOKEN RESULT
// =====================================================

function speakAssistantResult(
  medicines
) {

  const interactions =
    sortedInteractions();


  if (
    interactions.length === 0
  ) {

    speak(
      getVoiceText(
        "noInteraction"
      )
    );

    return;
  }


  // Speak the most serious interaction
  const first =
    interactions[0];


  const resultText =
    `${dn(first.drug_a)} ` +
    `and ` +
    `${dn(first.drug_b)}. ` +
    `${explanation(first)}`;


  speak(resultText);
}


// =====================================================
// VOICE ASSISTANT TEXT
// =====================================================

function getVoiceText(
  type
) {

  const text = {

    en: {
      listening:
        "🎤 Listening... Speak now.",

      noMedicine:
        "No known medicine was detected.",

      noMedicineSpeak:
        "I could not identify a medicine. Please say the medicine name clearly.",

      foundMedicine:
        "Medicines detected",

      noInteraction:
        "No interaction was found in the current medicine list."
    },


    hi: {
      listening:
        "🎤 सुन रहा हूँ... अब बोलिए।",

      noMedicine:
        "कोई पहचानी गई दवा नहीं मिली।",

      noMedicineSpeak:
        "मैं दवा पहचान नहीं सका। कृपया दवा का नाम साफ़ बोलें।",

      foundMedicine:
        "पहचानी गई दवाएं",

      noInteraction:
        "दवाओं की वर्तमान सूची में कोई इंटरैक्शन नहीं मिला।"
    },


    bn: {
      listening:
        "🎤 শুনছি... এখন বলুন।",

      noMedicine:
        "কোনো পরিচিত ওষুধ শনাক্ত করা যায়নি।",

      noMedicineSpeak:
        "আমি কোনো ওষুধ শনাক্ত করতে পারিনি। অনুগ্রহ করে ওষুধের নাম পরিষ্কারভাবে বলুন।",

      foundMedicine:
        "শনাক্ত করা ওষুধ",

      noInteraction:
        "বর্তমান ওষুধের তালিকায় কোনো ইন্টারঅ্যাকশন পাওয়া যায়নি।"
    },


    mr: {
      listening:
        "🎤 ऐकत आहे... आता बोला.",

      noMedicine:
        "कोणतेही ओळखलेले औषध सापडले नाही.",

      noMedicineSpeak:
        "मला कोणतेही औषध ओळखता आले नाही. कृपया औषधाचे नाव स्पष्टपणे बोला.",

      foundMedicine:
        "ओळखलेली औषधे",

      noInteraction:
        "सध्याच्या औषधांच्या यादीमध्ये कोणताही इंटरॅक्शन आढळला नाही."
    }

  };


  return (
    text[lang] &&
    text[lang][type]
  )
    ? text[lang][type]
    : text.en[type];
}


// =====================================================
// SPEECH ERROR TEXT
// =====================================================

function getSpeechErrorText(
  error
) {

  const messages = {

    "not-allowed":
      "Microphone permission was denied.",

    "no-speech":
      "No speech was detected.",

    "audio-capture":
      "Microphone could not be accessed.",

    "language-not-supported":
      "This speech language is not supported.",

    "network":
      "Speech recognition network error.",

    "aborted":
      "Speech recognition stopped."
  };


  return (
    messages[error] ||
    "Speech recognition error."
  );
}


// =====================================================
// UPDATE VOICE ASSISTANT LANGUAGE
// =====================================================

function updateVoiceAssistantLanguage() {

  const title =
    document.getElementById(
      "voiceTitle"
    );


  const hint =
    document.getElementById(
      "voiceHint"
    );


  const button =
    document.getElementById(
      "voiceButton"
    );


  const stopButton =
    document.getElementById(
      "voiceStopButton"
    );


  if (!title) return;


  const ui = {

    en: {
      title:
        "🎤 Voice Assistant",

      hint:
        "Tap the microphone and speak the medicine names.",

      speak:
        "🎙️ Speak",

      stop:
        "⏹ Stop"
    },


    hi: {
      title:
        "🎤 वॉइस असिस्टेंट",

      hint:
        "माइक्रोफोन दबाएं और दवा के नाम बोलें।",

      speak:
        "🎙️ बोलें",

      stop:
        "⏹ रोकें"
    },


    bn: {
      title:
        "🎤 ভয়েস অ্যাসিস্ট্যান্ট",

      hint:
        "মাইক্রোফোনে চাপ দিন এবং ওষুধের নাম বলুন।",

      speak:
        "🎙️ বলুন",

      stop:
        "⏹ থামুন"
    },


    mr: {
      title:
        "🎤 व्हॉइस असिस्टंट",

      hint:
        "मायक्रोफोन दाबा आणि औषधांची नावे बोला.",

      speak:
        "🎙️ बोला",

      stop:
        "⏹ थांबा"
    }

  };


  const current =
    ui[lang] || ui.en;


  title.textContent =
    current.title;


  hint.textContent =
    current.hint;


  button.textContent =
    current.speak;


  stopButton.textContent =
    current.stop;
}


// =====================================================
// LANGUAGE BUTTONS
// =====================================================

["en", "hi", "bn", "mr"]
  .forEach(code => {

    const button =
      document.getElementById(
        "btn-" + code
      );


    if (button) {

      button.onclick = () => {

        lang = code;

        render();

      };
    }
  });


// =====================================================
// CHECK BUTTON
// =====================================================

const checkButton =
  document.getElementById(
    "checkBtn"
  );


if (checkButton) {

  checkButton.onclick =
    runCheck;
}


// =====================================================
// IMAGE UPLOAD
// =====================================================

const upload =
  document.getElementById(
    "upload"
  );


if (upload) {

  upload.addEventListener(
    "change",
    e => {

      const file =
        e.target.files[0];


      if (!file) return;


      document
        .getElementById(
          "preview"
        )
        .src =
        URL.createObjectURL(
          file
        );
    }
  );
}


// =====================================================
// START APPLICATION
// =====================================================

init();
