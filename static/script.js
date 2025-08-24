// --- tiny helpers ---
const $ = (q) => document.querySelector(q);
const show = (el, on = true) => el && (el.style.display = on ? "" : "none");
const setText = (el, txt) => el && (el.textContent = txt ?? "");

// UI elems
const authSection = $("#authSection");
const chatSection = $("#chatSection");
const whoami = $("#whoami");
const logoutBtn = $("#logoutBtn");
const authOut = $("#authOut");

// tabs (if present in your HTML)
const tabLogin = $("#tabLogin");
const tabRegister = $("#tabRegister");
const tabReset = $("#tabReset");
const loginForm = $("#loginForm");
const registerForm = $("#registerForm");
const resetForm = $("#resetForm");

// auth forms
const loginEmail = $("#loginEmail");
const loginPassword = $("#loginPassword");
const regEmail = $("#regEmail");
const regPassword = $("#regPassword");

const resetEmail = $("#resetEmail");
const resetToken = $("#resetToken");
const newPassword = $("#newPassword");

// chat elems
const chatBox = $("#chat-box");
const userInput = $("#user-input");
const sendBtn = $("#send-button");
const out = $("#out");
const spinner = $("#spinner");

const dz = $("#dz");
const thumbs = $("#thumbs");
const listBtn = $("#list");
const clearThumbsBtn = $("#clearThumbs");

// state
let currentUser = null;
let pendingFiles = []; // local (unsent) files

// ---- view switching ----
function setAuthed(user) {
  currentUser = user;
  document.title = user ? "WarriorChat — Chat" : "WarriorChat — Sign in to start chatting";

  if (user) {
    setText(whoami, `${user.email}`);
    show(logoutBtn, true);
    show(authSection, false);
    show(chatSection, true);
    userInput?.focus();
  } else {
    setText(whoami, "Not signed in");
    show(logoutBtn, false);
    show(chatSection, false);
    show(authSection, true);
    selectTab("login");
  }
}

function selectTab(which) {
  // button styles
  tabLogin?.classList.toggle("primary", which === "login");
  tabRegister?.classList.toggle("primary", which === "register");
  tabReset?.classList.toggle("primary", which === "reset");
  // panes
  show(loginForm, which === "login");
  show(registerForm, which === "register");
  show(resetForm, which === "reset");
  // clear messages
  setText(authOut, "");
}

tabLogin?.addEventListener("click", () => selectTab("login"));
tabRegister?.addEventListener("click", () => selectTab("register"));
tabReset?.addEventListener("click", () => selectTab("reset"));

// ---- auth api ----
async function fetchMe() {
  try {
    const r = await fetch("/me", { credentials: "include" });
    if (!r.ok) throw 0;
    const j = await r.json();
    return j.user;
  } catch {
    return null;
  }
}

async function register() {
  setText(authOut, "Creating account…");
  try {
    const r = await fetch("/auth/register", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: regEmail.value.trim(), password: regPassword.value }),
      credentials: "include",
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || "Registration failed");
    setText(authOut, "Account created. You can now sign in.");
    selectTab("login");
    loginEmail.value = regEmail.value.trim();
  } catch (e) {
    setText(authOut, String(e.message || e));
  }
}

async function login() {
  setText(authOut, "Signing in…");
  try {
    // FastAPI OAuth2PasswordRequestForm expects x-www-form-urlencoded with username,password
    const body = new URLSearchParams();
    body.set("username", loginEmail.value.trim());
    body.set("password", loginPassword.value);

    const r = await fetch("/auth/login", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body,
      credentials: "include",
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || "Invalid credentials");
    setText(authOut, "");
    const u = await fetchMe();
    setAuthed(u);
  } catch (e) {
    setText(authOut, String(e.message || e));
  }
}

async function logout() {
  await fetch("/auth/logout", { method: "POST", credentials: "include" });
  setAuthed(null);
  // clear chat UI
  chatBox.innerHTML = "";
  out.textContent = "";
  thumbs.innerHTML = "";
  dz && (dz.innerHTML = "");
  pendingFiles = [];
}

// Password reset
async function requestReset() {
  setText(authOut, "Requesting reset token…");
  try {
    const r = await fetch("/auth/request_password_reset", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: resetEmail.value.trim() }),
      credentials: "include",
    });
    const j = await r.json();
    // In dev, backend may include token; in prod you’d email it.
    setText(authOut, j.reset_token ? `Token (dev only): ${j.reset_token}` : "If that account exists, a reset email was sent.");
  } catch {
    setText(authOut, "Reset request failed.");
  }
}

async function doReset() {
  setText(authOut, "Resetting password…");
  try {
    const r = await fetch("/auth/reset_password", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ token: resetToken.value.trim(), new_password: newPassword.value }),
      credentials: "include",
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || "Reset failed");
    setText(authOut, "Password reset. You can log in now.");
    selectTab("login");
  } catch (e) {
    setText(authOut, String(e.message || e));
  }
}

// wire auth buttons
$("#registerBtn")?.addEventListener("click", register);
$("#loginBtn")?.addEventListener("click", login);
logoutBtn?.addEventListener("click", logout);
$("#requestResetBtn")?.addEventListener("click", requestReset);
$("#doResetBtn")?.addEventListener("click", doReset);

// ---- chat rendering ----
function appendMsg(role, text) {
  const wrap = document.createElement("div");
  wrap.className = "msg-block";
  const label = document.createElement("span");
  label.className = role === "user" ? "user-label" : "bot-label";
  label.textContent = role === "user" ? "You:" : "Bot:";
  const msg = document.createElement("span");
  msg.className = role === "user" ? "user-msg" : "bot-msg";
  msg.textContent = text;
  wrap.appendChild(label);
  wrap.appendChild(msg);
  chatBox.appendChild(wrap);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// ---- attachments UI (thumbs/chips with remove) ----
function addThumb({ url, fileName, localIndex = null, fileId = null }) {
  const wrap = document.createElement("div");
  wrap.className = "thumb";

  if (url) {
    const img = new Image();
    img.src = url;
    img.loading = "lazy";
    img.onload = () => URL.revokeObjectURL(img.src);
    wrap.appendChild(img);
  } else {
    const chip = document.createElement("div");
    chip.className = "file";
    chip.textContent = fileName || "file";
    wrap.appendChild(chip);
  }

  const x = document.createElement("button");
  x.type = "button";
  x.className = "remove";
  x.textContent = "×";
  wrap.appendChild(x);

  if (localIndex !== null) wrap.dataset.localIndex = String(localIndex);
  if (fileId) wrap.dataset.fileId = fileId;

  thumbs.appendChild(wrap);
}

// Remove a local (unsent) file by index, keeping indices consistent
function rebuildLocalThumbs() {
  thumbs.innerHTML = "";
  pendingFiles.forEach((f, i) => {
    if (f.type?.startsWith?.("image/")) addThumb({ url: URL.createObjectURL(f), localIndex: i });
    else addThumb({ fileName: f.name, localIndex: i });
  });
}
function removeLocal(index) {
  pendingFiles.splice(index, 1);
  rebuildLocalThumbs();
}

// Event delegation for the little × on each thumb
thumbs?.addEventListener("click", async (e) => {
  const btn = e.target.closest(".remove");
  if (!btn) return;
  const card = btn.closest(".thumb");
  if (!card) return;

  // Local pending file?
  if (card.dataset.localIndex !== undefined) {
    removeLocal(Number(card.dataset.localIndex));
    return;
  }

  // Already uploaded? Delete from session
  const fileId = card.dataset.fileId;
  if (fileId) {
    try {
      await fetch(`/files/session/${fileId}`, { method: "DELETE", credentials: "include" });
      card.remove();
    } catch {
      out.textContent = "Failed to delete file from session.";
    }
  }
});

// ---- paste / drop handlers ----
dz?.addEventListener("paste", (e) => {
  const items = [...(e.clipboardData?.items || [])];
  const files = items.map((it) => (it.kind === "file" ? it.getAsFile() : null)).filter(Boolean);

  if (files.length) {
    e.preventDefault(); // stop inline paste
    dz.innerHTML = "";
    files.forEach((f) => {
      const idx = pendingFiles.push(f) - 1; // capture index
      if (f.type.startsWith("image/")) addThumb({ url: URL.createObjectURL(f), localIndex: idx });
      else addThumb({ fileName: f.name, localIndex: idx });
    });
    return;
  }

  // allow plain text, strip formatting
  const text = e.clipboardData.getData("text/plain");
  if (text) {
    e.preventDefault();
    document.execCommand("insertText", false, text);
  }
});

dz?.addEventListener("dragover", (e) => {
  e.preventDefault();
  dz.classList.add("focus");
});
dz?.addEventListener("dragleave", () => dz.classList.remove("focus"));
dz?.addEventListener("drop", (e) => {
  e.preventDefault();
  dz.classList.remove("focus");
  const files = [...(e.dataTransfer?.files || [])];
  if (!files.length) return;

  dz.innerHTML = "";
  files.forEach((f) => {
    const idx = pendingFiles.push(f) - 1;
    if (f.type.startsWith("image/")) addThumb({ url: URL.createObjectURL(f), localIndex: idx });
    else addThumb({ fileName: f.name, localIndex: idx });
  });
});

// ---- send: upload + message, then clear tray ----
async function send() {
  const prompt = userInput.value.trim();
  if (!prompt && !pendingFiles.length) return;

  if (prompt) appendMsg("user", prompt);
  userInput.value = "";

  // Upload pending files first (if any)
  let attachmentsMeta = [];
  if (pendingFiles.length) {
    const form = new FormData();
    pendingFiles.forEach((f) => form.append("files", f, f.name || "attachment"));
    form.append("message", prompt || "");

    try {
      const r = await fetch("/files/upload", { method: "POST", body: form, credentials: "include" });
      const j = await r.json();
      if (r.ok && j.ok) attachmentsMeta = j.files || [];
      else out.textContent = JSON.stringify(j, null, 2);
    } catch {
      out.textContent = "Upload failed.";
    }
  }

  // Now ask the model
  show(spinner, true);
  appendMsg("bot", "");
  const last = chatBox.lastChild.querySelector(".bot-msg");

  try {
    const r = await fetch("/api/generate", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt, attachments: attachmentsMeta }),
      credentials: "include",
    });

    if (!r.ok || !r.body) {
      last.textContent = "Error";
      return;
    }

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      last.textContent += decoder.decode(value);
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  } catch {
    last.textContent = "Error generating response.";
  } finally {
    show(spinner, false);
    // Clear the tray after a full send cycle
    pendingFiles = [];
    thumbs.innerHTML = "";
    dz && (dz.innerHTML = "");
  }
}

sendBtn?.addEventListener("click", send);
userInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});

// “List” -> fetch current session files and render chips with delete buttons
listBtn?.addEventListener("click", async () => {
  out.textContent = "Loading session files…";
  try {
    const r = await fetch("/files/session", { credentials: "include" });
    const j = await r.json();
    out.textContent = ""; // show chips instead

    thumbs.innerHTML = "";
    (j.files || []).forEach((f) => {
      // If you later expose a /files/download/{id} route, you can show real previews for images
      addThumb({ fileName: f.name, fileId: f.id });
    });
  } catch {
    out.textContent = "Failed to list session files.";
  }
});

// “Clear” -> clears local pending (unsent) files only
clearThumbsBtn?.addEventListener("click", () => {
  pendingFiles = [];
  thumbs.innerHTML = "";
});

// ---- boot ----
(async function init() {
  const user = await fetchMe();
  setAuthed(user);
  if (!user) show(authSection, true);
})();
