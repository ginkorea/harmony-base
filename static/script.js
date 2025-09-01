// script.js — WarriorGPT model-agnostic UI

// --- tiny helpers ---
const $ = (q) => document.querySelector(q);
const show = (el, on = true) => el && (el.style.display = on ? "" : "none");
const setText = (el, txt) => el && (el.textContent = txt ?? "");
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const authSection = $("#authSection");
const chatSection = $("#chatSection");
const whoami = $("#whoami");
const logoutBtn = $("#logoutBtn");
const authOut = $("#authOut");
const modelSelect = $("#modelSelect");

const tabLogin = $("#tabLogin");
const tabRegister = $("#tabRegister");
const tabReset = $("#tabReset");
const loginForm = $("#loginForm");
const registerForm = $("#registerForm");
const resetForm = $("#resetForm");

const loginEmail = $("#loginEmail");
const loginPassword = $("#loginPassword");
const regEmail = $("#regEmail");
const regPassword = $("#regPassword");
const resetEmail = $("#resetEmail");
const resetToken = $("#resetToken");
const newPassword = $("#newPassword");

const chatBox = $("#chat-box");
const spinner = $("#spinner");
const dz = $("#dz");           // paste/drop zone for content, not required to send
const thumbs = $("#thumbs");
const out = $("#out");
const userInput = $("#user-input");
const sendBtn = $("#send-button");
const listBtn = $("#list");
const clearThumbsBtn = $("#clearThumbs");
const systemPrompt = $("#systemPrompt");

// session-local preview cache
let localThumbs = []; // [{id,name,url,isImage}]
let streaming = false;

// --- auth state dance ---
async function me() {
  try {
    const r = await fetch("/me");
    if (!r.ok) throw 0;
    const j = await r.json();
    return j.user || null;
  } catch { return null; }
}
function setAuthed(u) {
  if (u) {
    setText(whoami, u.email || u.display_name || "Signed in");
    show(logoutBtn, true);
    show(modelSelect, true);
    show(authSection, false);
    show(chatSection, true);
  } else {
    setText(whoami, "Not signed in");
    show(logoutBtn, false);
    show(modelSelect, false);
    show(chatSection, false);
    show(authSection, true);
  }
}

// --- tabs ---
tabLogin.onclick = () => {
  show(loginForm, true); show(registerForm, false); show(resetForm, false);
  tabLogin.classList.add("primary"); tabRegister.classList.remove("primary"); tabReset.classList.remove("primary");
};
tabRegister.onclick = () => {
  show(loginForm, false); show(registerForm, true); show(resetForm, false);
  tabLogin.classList.remove("primary"); tabRegister.classList.add("primary"); tabReset.classList.remove("primary");
};
tabReset.onclick = () => {
  show(loginForm, false); show(registerForm, false); show(resetForm, true);
  tabLogin.classList.remove("primary"); tabRegister.classList.remove("primary"); tabReset.classList.add("primary");
};

// --- auth actions ---
$("#loginBtn").onclick = async () => {
  authOut.textContent = "";
  const fd = new FormData();
  // FastAPI OAuth2 style expects "username"/"password"
  fd.append("username", loginEmail.value.trim());
  fd.append("password", loginPassword.value);
  const r = await fetch("/auth/login", { method: "POST", body: fd });
  authOut.textContent = (await r.text());
  setTimeout(init, 150);
};
$("#registerBtn").onclick = async () => {
  authOut.textContent = "";
  const b = { email: regEmail.value.trim(), password: regPassword.value };
  const r = await fetch("/auth/register", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(b) });
  authOut.textContent = (await r.text());
};
$("#requestResetBtn").onclick = async () => {
  const r = await fetch("/auth/request_password_reset", {
    method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ email: resetEmail.value.trim() })
  });
  authOut.textContent = (await r.text());
};
$("#doResetBtn").onclick = async () => {
  const r = await fetch("/auth/reset_password", {
    method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ token: resetToken.value.trim(), new_password: newPassword.value })
  });
  authOut.textContent = (await r.text());
};
logoutBtn.onclick = async () => {
  await fetch("/auth/logout", {method:"POST"});
  await init();
};

// --- models ---
async function loadModels() {
  // If you add a /models endpoint later, we’ll populate from it.
  // Fallback stays usable today with a single default value.
  modelSelect.innerHTML = `<option value="scout17b">Llama 4 Scout 17B (Q4_K)</option>`;
  try {
    const r = await fetch("/models");
    if (!r.ok) return; // endpoint not present is fine
    const j = await r.json(); // expect [{name, display_name}]
    if (Array.isArray(j) && j.length) {
      modelSelect.innerHTML = "";
      for (const m of j) {
        const opt = document.createElement("option");
        opt.value = m.name;
        opt.textContent = m.display_name || m.name;
        modelSelect.appendChild(opt);
      }
    }
  } catch {}
}

// --- chat helpers ---
function addMsg(role, text) {
  const block = document.createElement("div");
  block.className = "msg-block";
  const label = document.createElement("span");
  label.className = role === "user" ? "user-label" : "bot-label";
  label.textContent = role === "user" ? "You: " : "Bot: ";
  const msg = document.createElement("span");
  msg.className = role === "user" ? "user-msg" : "bot-msg";
  msg.textContent = text;
  block.appendChild(label);
  block.appendChild(msg);
  chatBox.appendChild(block);
  chatBox.scrollTop = chatBox.scrollHeight;
}
function setSpinner(on) { show(spinner, on); }
function clearOutput() { out.textContent = ""; }

async function streamGenerate(prompt) {
  const model = modelSelect.value || "scout17b";
  const system = (systemPrompt && systemPrompt.value.trim()) || null;

  setSpinner(true);
  streaming = true;
  addMsg("user", prompt);
  addMsg("bot", ""); // create an empty bot block we will fill:
  const botSpan = chatBox.lastChild.querySelector(".bot-msg");

  try {
    const r = await fetch(`/api/generate?model=${encodeURIComponent(model)}`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        prompt,
        system,
        llm_params: {} // extend with UI dials later (temperature, max_tokens, etc.)
      })
    });
    if (!r.ok || !r.body) {
      const t = await r.text();
      botSpan.textContent = `Error: ${t || r.status}`;
      return;
    }
    const reader = r.body.getReader();
    const dec = new TextDecoder();
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      const chunk = dec.decode(value);
      botSpan.textContent += chunk;
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  } catch (e) {
    botSpan.textContent += `\n[Network error: ${e}]`;
  } finally {
    setSpinner(false);
    streaming = false;
  }
}

// --- paste/drag uploads ---
dz.addEventListener("paste", async (e) => {
  const items = e.clipboardData?.items || [];
  const files = [];
  for (const it of items) {
    if (it.kind === "file") {
      const f = it.getAsFile();
      if (f) files.push(f);
    }
  }
  if (files.length) await uploadFiles(files);
});

dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.style.borderColor = "#08f"; });
dz.addEventListener("dragleave", (e) => { dz.style.borderColor = "#2a2a2a"; });
dz.addEventListener("drop", async (e) => {
  e.preventDefault(); dz.style.borderColor = "#2a2a2a";
  const files = Array.from(e.dataTransfer?.files || []);
  if (files.length) await uploadFiles(files);
});

async function uploadFiles(files) {
  const fd = new FormData();
  for (const f of files) fd.append("files", f, f.name);
  const r = await fetch("/files/upload", { method: "POST", body: fd });
  const j = await r.json().catch(() => null);
  // Expecting payload with file infos; fallback to show just names if unknown
  if (j && Array.isArray(j.files)) {
    for (const f of j.files) addThumb(f);
  } else {
    for (const f of files) addThumb({ id: `local:${Date.now()}-${f.name}`, name: f.name, url: "", is_image: f.type.startsWith("image/") });
  }
}

function addThumb(f) {
  const id = f.id || f.file_id || `local:${Math.random()}`;
  const name = f.name || f.filename || "file";
  const url = f.url || (f.is_image ? f.preview_url : "");
  const isImage = !!(f.is_image || (url && !name.toLowerCase().endsWith(".pdf")));
  localThumbs.push({ id, name, url, isImage });

  const el = document.createElement("div");
  el.className = "thumb";
  el.dataset.id = id;

  const btn = document.createElement("button");
  btn.className = "remove";
  btn.textContent = "×";
  btn.title = "Remove";
  btn.onclick = () => { thumbs.removeChild(el); localThumbs = localThumbs.filter(t => t.id !== id); };

  el.appendChild(btn);

  if (isImage && url) {
    const img = document.createElement("img");
    img.src = url;
    el.appendChild(img);
  } else {
    const div = document.createElement("div");
    div.className = "file";
    div.textContent = name;
    el.appendChild(div);
  }
  thumbs.appendChild(el);
}

listBtn.onclick = async () => {
  const r = await fetch("/files/session");
  out.textContent = await r.text();
};
clearThumbsBtn.onclick = () => {
  thumbs.innerHTML = "";
  localThumbs = [];
};

// --- send ---
sendBtn.onclick = async () => {
  const prompt = userInput.value.trim() || dz.textContent.trim();
  if (!prompt || streaming) return;
  userInput.value = "";
  await streamGenerate(prompt);
};
userInput.addEventListener("keydown", async (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendBtn.click();
  }
});

// --- bootstrap ---
async function init() {
  const u = await me();
  setAuthed(u);
  if (u) await loadModels();
}
init();
