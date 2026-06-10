const form = document.getElementById("challenge-form");
const outputYaml = document.getElementById("output-yaml");
const outputCursor = document.getElementById("output-cursor");
const resultPath = document.getElementById("result-path");
const toast = document.getElementById("toast");

let activeTab = "yaml";

function escapeYamlString(s) {
  if (!s) return '""';
  if (s.includes("\n") || s.includes('"') || s.includes("'")) {
    return `"${s.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
  }
  return s.includes(":") || s.includes("#") ? `"${s}"` : s;
}

function blockYaml(text) {
  if (!text || !text.trim()) return '""';
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  return "|\n" + lines.map((l) => "  " + l).join("\n");
}

function collectData() {
  const hintsRaw = document.getElementById("hints").value.trim();
  const hints = hintsRaw
    ? hintsRaw.split("\n").map((h) => h.trim()).filter(Boolean)
    : [];

  return {
    name: document.getElementById("name").value.trim(),
    category: document.getElementById("category").value,
    flag_format: document.getElementById("flag_format").value.trim(),
    platform: document.getElementById("platform").value.trim(),
    connection_info: document.getElementById("connection_info").value.trim(),
    description: document.getElementById("description").value,
    hints,
    notes: document.getElementById("notes").value.trim(),
  };
}

function buildYaml(data) {
  let yaml = `name: ${escapeYamlString(data.name)}
category: ${data.category}
flag_format: ${escapeYamlString(data.flag_format)}
platform: ${escapeYamlString(data.platform)}
connection_info: ${escapeYamlString(data.connection_info)}

description: ${blockYaml(data.description)}
`;

  if (data.hints.length) {
    yaml += "hints:\n";
    for (const h of data.hints) {
      yaml += `  - ${escapeYamlString(h)}\n`;
    }
  } else {
    yaml += "hints: []\n";
  }

  yaml += `notes: ${escapeYamlString(data.notes)}\n`;
  return yaml;
}

function buildCursorTemplate(data, workspacePath) {
  const wsLine = workspacePath
    ? `\n워크스페이스: ${workspacePath}\n(@challenge.yaml @PROMPT.md @files/ 확인)`
    : "";

  const hintsBlock =
    data.hints.length > 0
      ? `\n힌트:\n${data.hints.map((h) => `- ${h}`).join("\n")}\n`
      : "";

  const conn = data.connection_info
    ? `\n연결 정보: ${data.connection_info}`
    : "";
  const plat = data.platform ? `\n플랫폼: ${data.platform}` : "";

  return `CTF 문제 풀어줘. ctf-solve skill 따라 진행해.

문제 이름: ${data.name}
분야: ${data.category}
플래그 형식: ${data.flag_format}${plat}${conn}
${hintsBlock}
문제 내용:
"""
${data.description.trim()}
"""${wsLine}

검증되면 마지막에 FLAG: <플래그> 한 줄로 답해줘.`;
}

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2200);
}

function updatePreview() {
  const data = collectData();
  if (!data.name || !data.description.trim()) {
    showToast("문제 이름과 내용을 입력하세요");
    return;
  }
  outputYaml.value = buildYaml(data);
  outputCursor.value = buildCursorTemplate(data, resultPath.dataset.path || "");
}

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.tab === tab);
  });
  outputYaml.hidden = tab !== "yaml";
  outputCursor.hidden = tab !== "cursor";
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

document.getElementById("btn-preview").addEventListener("click", updatePreview);

form.addEventListener("input", () => {
  if (outputYaml.value) updatePreview();
});

document.getElementById("btn-copy").addEventListener("click", async () => {
  const text = activeTab === "yaml" ? outputYaml.value : outputCursor.value;
  if (!text) {
    updatePreview();
  }
  await navigator.clipboard.writeText(
    activeTab === "yaml" ? outputYaml.value : outputCursor.value
  );
  showToast("클립보드에 복사됨");
});

document.getElementById("btn-copy-cursor").addEventListener("click", async () => {
  if (!outputCursor.value) updatePreview();
  await navigator.clipboard.writeText(outputCursor.value);
  showToast("Cursor 템플릿 복사됨");
});

document.getElementById("btn-download").addEventListener("click", () => {
  if (!outputYaml.value) updatePreview();
  const blob = new Blob([outputYaml.value], { type: "text/yaml" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "challenge.yaml";
  a.click();
  URL.revokeObjectURL(a.href);
  showToast("challenge.yaml 다운로드");
});

document.getElementById("btn-create").addEventListener("click", async () => {
  const data = collectData();
  if (!data.name || !data.description.trim() || !data.flag_format) {
    showToast("필수 항목을 채워주세요");
    return;
  }

  const fileInput = document.getElementById("files");
  const formData = new FormData();
  formData.append("payload", JSON.stringify(data));
  for (const file of fileInput.files) {
    formData.append("files", file, file.name);
  }

  const btn = document.getElementById("btn-create");
  btn.disabled = true;
  btn.textContent = "생성 중…";

  try {
    const resp = await fetch("/api/create", { method: "POST", body: formData });
    const json = await resp.json();
    if (!resp.ok || !json.ok) {
      throw new Error(json.error || "생성 실패");
    }
    resultPath.textContent = `생성됨: ${json.path}\n\nCursor에서:\n  @challenge.yaml @PROMPT.md 이 문제 풀어줘`;
    resultPath.classList.add("visible");
    resultPath.dataset.path = json.path;
    updatePreview();
    switchTab("cursor");
    showToast("워크스페이스 생성 완료");
  } catch (err) {
    showToast(err.message || "오류");
  } finally {
    btn.disabled = false;
    btn.textContent = "워크스페이스 생성";
  }
});

updatePreview();
