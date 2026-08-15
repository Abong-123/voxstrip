// main.js
// Alur: pilih/drop file -> tombol "Upload track" muncul -> upload ->
// tombol "Strip vocals" muncul -> jalankan filter -> poll status ->
// selesai -> tombol download muncul.

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const fileInfo = document.getElementById("fileInfo");
const fileNameEl = document.getElementById("fileName");
const fileIdEl = document.getElementById("fileId");
const eq = document.getElementById("eq");

const uploadBtn = document.getElementById("uploadBtn");
const filterBtn = document.getElementById("filterBtn");
const downloadBtn = document.getElementById("downloadBtn");
const resetBtn = document.getElementById("resetBtn");
const statusLine = document.getElementById("statusLine");

const chainSteps = {
  input: document.querySelector('.chain__step[data-step="input"]'),
  separate: document.querySelector('.chain__step[data-step="separate"]'),
  output: document.querySelector('.chain__step[data-step="output"]'),
};

let selectedFile = null;
let currentFileId = null;
let pollTimer = null;

// ---------- Dropzone interactions ----------

dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelected(file);
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (file) handleFileSelected(file);
});

function handleFileSelected(file) {
  selectedFile = file;
  fileNameEl.textContent = file.name;
  fileIdEl.textContent = "not uploaded yet";
  fileInfo.classList.remove("hidden");
  uploadBtn.classList.remove("hidden");
  filterBtn.classList.add("hidden");
  downloadBtn.classList.add("hidden");
  resetBtn.classList.remove("hidden");
  setStatus("");
  setChainStep("input", "active");
}

// ---------- Upload ----------

uploadBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Uploading…";
  setStatus("Uploading file to server…");

  try {
    const formData = new FormData();
    formData.append("file", selectedFile);

    const res = await fetch("/upload", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed.");
    }

    const data = await res.json();
    currentFileId = data.file_id;
    fileIdEl.textContent = `id: ${currentFileId}`;

    setChainStep("input", "done");
    uploadBtn.classList.add("hidden");
    filterBtn.classList.remove("hidden");
    setStatus("Uploaded. Ready to strip vocals.");
  } catch (err) {
    setStatus(err.message, "error");
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Upload track";
  }
});

// ---------- Filter (vocal separation) ----------

filterBtn.addEventListener("click", async () => {
  if (!currentFileId) return;

  filterBtn.disabled = true;
  filterBtn.textContent = "Processing…";
  eq.classList.add("playing");
  setChainStep("separate", "active");
  setStatus("Separating vocals from instrumental — this can take 1–3 minutes on CPU…");

  try {
    const res = await fetch(`/filter/${currentFileId}`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to start processing.");
    }
    startPolling();
  } catch (err) {
    eq.classList.remove("playing");
    setStatus(err.message, "error");
    filterBtn.disabled = false;
    filterBtn.textContent = "Strip vocals";
  }
});

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/status/${currentFileId}`);
      if (!res.ok) throw new Error("Failed to check status.");
      const data = await res.json();

      if (data.status === "done") {
        clearInterval(pollTimer);
        eq.classList.remove("playing");
        setChainStep("separate", "done");
        setChainStep("output", "done");
        filterBtn.classList.add("hidden");
        downloadBtn.classList.remove("hidden");
        downloadBtn.href = `/download/${currentFileId}`;
        setStatus("Done. Instrumental is ready.", "done");
      } else if (data.status === "error") {
        clearInterval(pollTimer);
        eq.classList.remove("playing");
        filterBtn.disabled = false;
        filterBtn.textContent = "Strip vocals";
        setStatus(`Processing failed: ${data.error}`, "error");
      }
      // "queued" / "processing" -> keep polling, keep current message
    } catch (err) {
      clearInterval(pollTimer);
      eq.classList.remove("playing");
      setStatus(err.message, "error");
    }
  }, 2500);
}

// ---------- Reset ----------

resetBtn.addEventListener("click", () => {
  if (pollTimer) clearInterval(pollTimer);
  selectedFile = null;
  currentFileId = null;
  fileInput.value = "";

  fileInfo.classList.add("hidden");
  uploadBtn.classList.add("hidden");
  filterBtn.classList.add("hidden");
  downloadBtn.classList.add("hidden");
  resetBtn.classList.add("hidden");
  eq.classList.remove("playing");

  uploadBtn.disabled = false;
  uploadBtn.textContent = "Upload track";
  filterBtn.disabled = false;
  filterBtn.textContent = "Strip vocals";

  setStatus("");
  Object.values(chainSteps).forEach((el) => el.classList.remove("active", "done"));
});

// ---------- Helpers ----------

function setStatus(message, kind) {
  statusLine.textContent = message;
  statusLine.classList.toggle("hidden", !message);
  statusLine.classList.remove("status-line--error", "status-line--done");
  if (kind === "error") statusLine.classList.add("status-line--error");
  if (kind === "done") statusLine.classList.add("status-line--done");
}

function setChainStep(step, state) {
  const el = chainSteps[step];
  if (!el) return;
  if (state === "active") {
    el.classList.add("active");
    el.classList.remove("done");
  } else if (state === "done") {
    el.classList.remove("active");
    el.classList.add("done");
  }
}