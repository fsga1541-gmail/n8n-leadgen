const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const fileMeta = document.getElementById("fileMeta");
const fileNameEl = document.getElementById("fileName");
const fileSizeEl = document.getElementById("fileSize");
const fileTypeEl = document.getElementById("fileType");
const filePreview = document.getElementById("filePreview");
const submitBtn = document.getElementById("submitBtn");
const clearBtn = document.getElementById("clearBtn");
const statusEl = document.getElementById("status");
const webhookUrlEl = document.getElementById("webhookUrl");

const STORAGE_KEY = "lq_webhook_url";
const savedUrl = localStorage.getItem(STORAGE_KEY);
if (savedUrl) webhookUrlEl.value = savedUrl;
webhookUrlEl.addEventListener("change", () => {
  localStorage.setItem(STORAGE_KEY, webhookUrlEl.value.trim());
});

let parsed = null;

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files?.[0];
  if (file) handleFile(file);
});

fileInput.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (file) handleFile(file);
});

clearBtn.addEventListener("click", reset);
submitBtn.addEventListener("click", submit);

function reset() {
  parsed = null;
  fileInput.value = "";
  fileMeta.classList.add("hidden");
  submitBtn.disabled = true;
  hideStatus();
}

function setStatus(message, kind = "info") {
  statusEl.textContent = message;
  statusEl.className = `status show ${kind}`;
}

function hideStatus() {
  statusEl.className = "status";
  statusEl.textContent = "";
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function getKind(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith(".xlsx") || name.endsWith(".xls")) return "excel";
  if (name.endsWith(".csv")) return "csv";
  if (name.endsWith(".tsv")) return "tsv";
  if (name.endsWith(".txt")) return "text";
  if (file.type.startsWith("text/")) return "text";
  return null;
}

async function readAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

async function readAsArrayBuffer(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(file);
  });
}

async function parseExcel(file) {
  const buffer = await readAsArrayBuffer(file);
  const workbook = XLSX.read(buffer, { type: "array" });
  const sections = workbook.SheetNames.map((name) => {
    const csv = XLSX.utils.sheet_to_csv(workbook.Sheets[name]);
    return `# Sheet: ${name}\n${csv}`;
  });
  return sections.join("\n\n");
}

async function handleFile(file) {
  hideStatus();
  const kind = getKind(file);
  if (!kind) {
    setStatus(
      `Unsupported file type: ${file.name}. Use .csv, .tsv, .txt, .xlsx, or .xls.`,
      "error"
    );
    return;
  }

  try {
    setStatus(`Parsing ${file.name}...`, "info");
    let content = "";
    if (kind === "excel") {
      content = await parseExcel(file);
    } else {
      content = await readAsText(file);
    }
    content = content.trim();

    if (!content) {
      setStatus("File appears to be empty.", "warn");
      submitBtn.disabled = true;
      return;
    }

    parsed = { filename: file.name, kind, content };

    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = formatBytes(file.size);
    fileTypeEl.textContent = kind;
    filePreview.textContent =
      content.slice(0, 1500) + (content.length > 1500 ? "\n...[truncated]" : "");
    fileMeta.classList.remove("hidden");
    submitBtn.disabled = false;

    // n8n's default webhook payload limit is 16 MB. Warn (not block) so the
    // user knows large files may 413 on the server side.
    const SOFT_WARN_BYTES = 8 * 1024 * 1024;
    const charBytes = new Blob([content]).size;
    if (charBytes > SOFT_WARN_BYTES) {
      setStatus(
        `Ready to upload — ${content.length.toLocaleString()} characters parsed (~${formatBytes(charBytes)}). Large payload: n8n's default webhook body limit is 16 MB, so this may 413. Consider splitting the file.`,
        "warn"
      );
    } else {
      setStatus(
        `Ready to upload — ${content.length.toLocaleString()} characters parsed.`,
        "success"
      );
    }
  } catch (err) {
    console.error(err);
    setStatus(`Failed to parse file: ${err.message || err}`, "error");
    submitBtn.disabled = true;
  }
}

async function submit() {
  if (!parsed) return;
  const url = webhookUrlEl.value.trim();
  if (!url) {
    setStatus("Please enter the n8n webhook URL.", "error");
    return;
  }
  let parsedUrl;
  try {
    parsedUrl = new URL(url);
  } catch {
    setStatus("Webhook URL is not a valid URL.", "error");
    return;
  }
  if (
    parsedUrl.protocol !== "https:" &&
    !(parsedUrl.protocol === "http:" && /^(localhost|127\.0\.0\.1|\[::1\])$/.test(parsedUrl.hostname))
  ) {
    setStatus("Webhook URL must use HTTPS (or http://localhost for dev).", "error");
    return;
  }

  submitBtn.disabled = true;
  setStatus("Uploading to n8n...", "info");

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: parsed.filename,
        kind: parsed.kind,
        content: parsed.content,
      }),
    });

    const text = await res.text();
    let payload;
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { raw: text };
    }

    if (!res.ok) {
      setStatus(
        `Upload failed (${res.status}): ${payload.message || text || res.statusText}`,
        "error"
      );
      submitBtn.disabled = false;
      return;
    }

    setStatus(
      `Uploaded "${parsed.filename}" successfully. Now message your Telegram bot to query the knowledge base.`,
      "success"
    );
  } catch (err) {
    console.error(err);
    setStatus(
      `Network error: ${err.message || err}. If running n8n locally, make sure the workflow is active and CORS is allowed.`,
      "error"
    );
    submitBtn.disabled = false;
  }
}
