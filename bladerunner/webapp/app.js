const chatPanel = document.getElementById("chat-panel");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const userIdInput = document.getElementById("user-id");
const apiKeyRow = document.getElementById("api-key-row");
const apiKeyInput = document.getElementById("api-key");
const engineSelect = document.getElementById("engine");
const modelInput = document.getElementById("model");
const modelList = document.getElementById("model-list");
const permissionProfileSelect = document.getElementById("permission-profile");
const skillSelect = document.getElementById("skill");
const enableWebSearchCheckbox = document.getElementById("enable-web-search");
const enableRagCheckbox = document.getElementById("enable-rag");
const autoMatchSkillCheckbox = document.getElementById("auto-match-skill");
const googleSearchGroundingCheckbox = document.getElementById("google-search-grounding");
const enablePlanningCheckbox = document.getElementById("enable-planning");
const enableReflectionCheckbox = document.getElementById("enable-reflection");
const enableRetryCheckbox = document.getElementById("enable-retry");
const enableStreamingCheckbox = document.getElementById("enable-streaming");
const streamingLabelText = document.getElementById("streaming-label-text");
const imageFileInput = document.getElementById("image-file");
const newSessionButton = document.getElementById("new-session");
const interruptBtn = document.getElementById("interrupt-btn");
const healthPill = document.getElementById("health-pill");
const sessionPill = document.getElementById("session-pill");
const runStatePill = document.getElementById("run-state-pill");
const contextToggleBtn = document.getElementById("context-toggle");
const sessionFlags = document.getElementById("session-flags");
const telemetrySession = document.getElementById("telemetry-session");
const telemetryEngine = document.getElementById("telemetry-engine");
const telemetryModel = document.getElementById("telemetry-model");
const telemetryPermission = document.getElementById("telemetry-permission");
const telemetryRetrieval = document.getElementById("telemetry-retrieval");
const telemetryTurns = document.getElementById("telemetry-turns");
const telemetryLatency = document.getElementById("telemetry-latency");
const telemetryWebUsed = document.getElementById("telemetry-web-used");
const qaFocus = document.getElementById("qa-focus");
const qaClearChat = document.getElementById("qa-clear-chat");
const qaCopySession = document.getElementById("qa-copy-session");
const qaResearchMode = document.getElementById("qa-research-mode");
const focusExitBtn = document.getElementById("focus-exit");

let sessionId = null;
let activeWebSocket = null;  // Track active WebSocket connection for interruption
let userTurns = 0;
let assistantTurns = 0;
let webSearchHits = 0;
let lastLatencyMs = null;

const FALLBACK_MODEL_HINTS = [
  "haiku",
  "sonnet",
  "opus",
  "llama",
  "gemini",
  "mistral",
  "groq-llama",
  "groq-mixtral",
  "gemini-2.0-flash",
];

function updateSessionPill() {
  if (!sessionPill) {
    return;
  }
  sessionPill.textContent = sessionId ? `Session ${sessionId.slice(0, 8)}` : "Session idle";
}

function setRunState(text) {
  if (!runStatePill) {
    return;
  }
  runStatePill.textContent = text;
}

function setDrawerCollapsed(collapsed) {
  document.body.classList.toggle("drawer-collapsed", collapsed);
  if (contextToggleBtn) {
    contextToggleBtn.textContent = collapsed ? "Configure" : "Hide Config";
    contextToggleBtn.setAttribute("aria-expanded", collapsed ? "false" : "true");
  }
}

function setFocusMode(enabled) {
  document.body.classList.toggle("focus-mode", enabled);
  if (qaFocus) {
    qaFocus.textContent = enabled ? "Focus: On" : "Focus";
    qaFocus.setAttribute("aria-pressed", enabled ? "true" : "false");
  }
}

function updateTelemetry() {
  if (telemetrySession) {
    telemetrySession.textContent = sessionId ? sessionId.slice(0, 8) : "idle";
  }
  if (telemetryEngine) {
    telemetryEngine.textContent = engineSelect.value;
  }
  if (telemetryModel) {
    telemetryModel.textContent = modelInput.value.trim() || "(default)";
  }
  if (telemetryPermission) {
    telemetryPermission.textContent = permissionProfileSelect.value;
  }
  if (telemetryRetrieval) {
    telemetryRetrieval.textContent = `${enableWebSearchCheckbox.checked ? "on" : "off"}/${enableRagCheckbox.checked ? "on" : "off"}`;
  }
  if (telemetryTurns) {
    telemetryTurns.textContent = `${userTurns}/${assistantTurns}`;
  }
  if (telemetryLatency) {
    telemetryLatency.textContent = Number.isFinite(lastLatencyMs) ? `${lastLatencyMs}ms` : "--";
  }
  if (telemetryWebUsed) {
    telemetryWebUsed.textContent = String(webSearchHits);
  }
}

function syncStreamingAvailability() {
  const isBladeRunner = engineSelect.value === "bladerunner";
  if (!isBladeRunner) {
    enableStreamingCheckbox.checked = false;
  }
  enableStreamingCheckbox.disabled = !isBladeRunner;
  streamingLabelText.textContent = isBladeRunner
    ? "Streaming (BladeRunner only)"
    : "Streaming unavailable for Google ADK";
  renderSessionFlags();
  updateTelemetry();
}

function renderSessionFlags() {
  if (!sessionFlags) {
    return;
  }

  const items = [
    { label: `Engine: ${engineSelect.value}` },
    { label: `Model: ${modelInput.value.trim() || "(default)"}` },
    { label: `Web: ${enableWebSearchCheckbox.checked ? "on" : "off"}`, enabled: enableWebSearchCheckbox.checked },
    { label: `RAG: ${enableRagCheckbox.checked ? "on" : "off"}`, enabled: enableRagCheckbox.checked },
    { label: `Skill: ${skillSelect.value || "none"}`, enabled: Boolean(skillSelect.value) },
    { label: `Auto Skill Match: ${autoMatchSkillCheckbox.checked ? "on" : "off"}`, enabled: autoMatchSkillCheckbox.checked },
    { label: `Permission: ${permissionProfileSelect.value}` },
    { label: `Streaming: ${enableStreamingCheckbox.checked ? "on" : "off"}`, enabled: enableStreamingCheckbox.checked },
  ];

  sessionFlags.innerHTML = "";
  for (const item of items) {
    const node = document.createElement("span");
    node.className = item.enabled ? "session-flag enabled" : "session-flag";
    node.textContent = item.label;
    sessionFlags.appendChild(node);
  }

  updateTelemetry();
}

function populateModelHints(models) {
  const merged = new Set(models || []);

  // If config exposes only one model, keep UX helpful with common aliases.
  if (merged.size <= 1) {
    for (const fallback of FALLBACK_MODEL_HINTS) {
      merged.add(fallback);
    }
  }

  modelList.innerHTML = "";
  for (const model of merged) {
    const option = document.createElement("option");
    option.value = model;
    modelList.appendChild(option);
  }
}

function appendBubble(
  role,
  text,
  meta,
  sources = [],
  webSearchUsed = false,
  webSearchRequested = false,
  ragRequested = false,
  ragAvailable = false,
  appliedSkill = null,
  warnings = []
) {
  const bubble = document.createElement("article");
  bubble.className = `bubble ${role}`;

  const metaNode = document.createElement("div");
  metaNode.className = "meta";
  let metaText = meta;
  const isSystemMeta = typeof meta === "string" && meta.startsWith("system");
  if (role === "user") {
    userTurns += 1;
  } else if (role === "assistant" && !isSystemMeta) {
    assistantTurns += 1;
  }

  if (role === "assistant" && !isSystemMeta) {
    if (webSearchUsed) {
      metaText += " | Web: used";
      bubble.classList.add("web-search-used");
      webSearchHits += 1;
    } else if (webSearchRequested) {
      metaText += " | Web: on (not used)";
      bubble.classList.add("web-search-requested");
    } else {
      metaText += " | Web: off";
    }

    if (ragRequested) {
      metaText += ragAvailable ? " | RAG: on" : " | RAG: unavailable";
    }

    if (appliedSkill) {
      metaText += ` | Skill: ${appliedSkill}`;
    }
  }
  metaNode.textContent = metaText;
  bubble.appendChild(metaNode);

  const textNode = document.createElement("div");
  textNode.textContent = text;
  bubble.appendChild(textNode);

  if (sources.length > 0) {
    const srcWrap = document.createElement("div");
    srcWrap.className = "sources";
    for (const src of sources) {
      const a = document.createElement("a");
      a.href = src.url;
      a.target = "_blank";
      a.rel = "noreferrer";
      a.textContent = src.title;
      srcWrap.appendChild(a);
    }
    bubble.appendChild(srcWrap);
  }

  if (warnings.length > 0) {
    const warnWrap = document.createElement("div");
    warnWrap.className = "sources";
    for (const warning of warnings) {
      const line = document.createElement("div");
      line.textContent = `Warning: ${warning}`;
      warnWrap.appendChild(line);
    }
    bubble.appendChild(warnWrap);
  }

  chatPanel.appendChild(bubble);
  chatPanel.scrollTop = chatPanel.scrollHeight;
  updateTelemetry();
}

function getAuthHeaders(extra = {}) {
  const key = apiKeyInput.value.trim();
  return {
    ...extra,
    ...(key ? { "X-API-Key": key } : {}),
  };
}

async function checkHealth() {
  try {
    const res = await fetch("/api/health", {
      headers: getAuthHeaders(),
    });

    if (res.status === 401) {
      healthPill.textContent = "Auth required | provide API key";
      return;
    }

    const payload = await res.json();
    if (payload.ok) {
      healthPill.classList.add("ok");
      healthPill.textContent = payload.google_adk_available
        ? "Core online | ADK detected"
        : "Core online | ADK optional";
    }
  } catch (_) {
    healthPill.textContent = "Core unreachable";
  }
}

async function loadMeta() {
  try {
    const res = await fetch("/api/meta", {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      return;
    }

    const payload = await res.json();
    const models = payload.models || [];
    const skills = payload.skills || [];
    populateModelHints(models);

    // Keep API key field visible only when auth is enabled.
    if (apiKeyRow) {
      apiKeyRow.style.display = payload.auth_enabled ? "grid" : "none";
    }

    if (!modelInput.value && payload.default_model) {
      modelInput.value = payload.default_model;
    }

    skillSelect.innerHTML = '<option value="">none</option>';
    for (const skill of skills) {
      const option = document.createElement("option");
      option.value = skill.name;
      option.textContent = `${skill.name} - ${skill.description}`;
      skillSelect.appendChild(option);
    }
  } catch (_) {
    // Keep UI usable even if metadata endpoint is unavailable.
  }
}

async function createSession() {
  const user_id = userIdInput.value.trim();
  if (!user_id) {
    alert("Enter a user id first.");
    return;
  }

  const res = await fetch("/api/sessions", {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ user_id, title: "Web Console Session" }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to create session");
  }

  const data = await res.json();
  sessionId = data.session_id;
  updateSessionPill();
  updateTelemetry();
  appendBubble("assistant", `Session ready: ${sessionId}`, "system");
}

newSessionButton.addEventListener("click", async () => {
  try {
    await createSession();
    renderSessionFlags();
  } catch (error) {
    appendBubble("assistant", error.message, "system/error");
  }
});

async function uploadImage(user_id) {
  const file = imageFileInput.files[0];
  if (!file) {
    return null;
  }

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`/api/uploads/image?user_id=${encodeURIComponent(user_id)}`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });

  const payload = await res.json();
  if (!res.ok) {
    throw new Error(payload.detail || "Image upload failed");
  }

  return payload.file_path;
}

async function sendViaWebSocket(payload) {
  return new Promise((resolve, reject) => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const key = apiKeyInput.value.trim();
    const keyQuery = key ? `?api_key=${encodeURIComponent(key)}` : "";
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/chat${keyQuery}`);
    activeWebSocket = ws;

    let streamed = "";

    ws.onopen = () => {
      ws.send(JSON.stringify(payload));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "status") {
        // Status update (executing, interrupting, etc.)
        console.log("Status:", msg.status);
        if (msg.status === "executing") {
          setRunState("Streaming");
        } else if (msg.status === "interrupting") {
          setRunState("Interrupting");
        }
      } else if (msg.type === "chunk") {
        streamed += msg.delta;
      } else if (msg.type === "final") {
        if (!msg.answer && streamed) {
          msg.answer = streamed;
        }
        activeWebSocket = null;
        resolve(msg);
      } else if (msg.type === "error") {
        activeWebSocket = null;
        reject(new Error(msg.message || "WebSocket error"));
      } else if (msg.type === "pong") {
        // Heartbeat response
        console.log("Pong received");
      }
    };

    ws.onerror = () => {
      activeWebSocket = null;
      reject(new Error("WebSocket connection failed"));
    };

    ws.onclose = () => {
      activeWebSocket = null;
    };
  });
}

function interruptStream() {
  if (activeWebSocket && activeWebSocket.readyState === WebSocket.OPEN) {
    activeWebSocket.send(JSON.stringify({ type: "interrupt" }));
    console.log("Interrupt signal sent");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const requestStartedAt = performance.now();
  setRunState("Executing");

  const message = messageInput.value.trim();
  const user_id = userIdInput.value.trim();
  const engine = engineSelect.value;
  const enable_web_search = enableWebSearchCheckbox.checked;
  const enable_rag = enableRagCheckbox.checked;
  const auto_match_skill = autoMatchSkillCheckbox.checked;
  const google_search_grounding = googleSearchGroundingCheckbox.checked;
  const enable_planning = enablePlanningCheckbox.checked;
  const enable_reflection = enableReflectionCheckbox.checked;
  const enable_retry = enableRetryCheckbox.checked;
  const enable_streaming = enableStreamingCheckbox.checked;
  const permission_profile = permissionProfileSelect.value;
  const skill = skillSelect.value || null;
  const model = modelInput.value.trim() || null;

  if (!message || !user_id) {
    return;
  }

  appendBubble("user", message, `${user_id} | ${engine}`);
  messageInput.value = "";

  try {
    if (!sessionId) {
      await createSession();
    }

    const uploadedImagePath = await uploadImage(user_id);
    const image_paths = uploadedImagePath ? [uploadedImagePath] : [];

    const requestPayload = {
      user_id,
      message,
      session_id: sessionId,
      engine,
      enable_web_search,
      enable_rag,
      image_paths,
      auto_match_skill,
      google_search_grounding,
      enable_planning,
      enable_reflection,
      enable_retry,
      enable_streaming,
      permission_profile,
      skill,
      model,
    };

    // Show interrupt button if streaming
    if (enable_streaming && engine === "bladerunner") {
      interruptBtn.style.display = "inline-block";
    }

    const payload =
      enable_streaming && engine === "bladerunner"
        ? await sendViaWebSocket(requestPayload)
        : await (async () => {
            const res = await fetch("/api/chat", {
              method: "POST",
              headers: getAuthHeaders({ "Content-Type": "application/json" }),
              body: JSON.stringify(requestPayload),
            });
            const body = await res.json();
            if (!res.ok) {
              throw new Error(body.detail || "Chat request failed");
            }
            return body;
          })();

    // Hide interrupt button
    interruptBtn.style.display = "none";

    appendBubble(
      "assistant",
      payload.answer,
      `${payload.engine} | ${payload.model}`,
      payload.sources || [],
      payload.web_search_used,
      payload.web_search_requested,
      payload.rag_requested,
      payload.rag_available,
      payload.applied_skill,
      payload.warnings || []
    );

    lastLatencyMs = Math.round(performance.now() - requestStartedAt);
    updateTelemetry();

    if (payload.session_id && payload.session_id !== sessionId) {
      sessionId = payload.session_id;
      updateSessionPill();
      updateTelemetry();
    }
  } catch (error) {
    setRunState("Error");
    appendBubble("assistant", error.message, "system/error");
  } finally {
    setRunState("Ready");
    interruptBtn.style.display = "none";
    imageFileInput.value = "";
  }
});

// Wire up interrupt button
interruptBtn.addEventListener("click", () => {
  interruptStream();
});

engineSelect.addEventListener("change", () => {
  syncStreamingAvailability();
});

for (const input of [
  modelInput,
  permissionProfileSelect,
  skillSelect,
  enableWebSearchCheckbox,
  enableRagCheckbox,
  autoMatchSkillCheckbox,
  enableStreamingCheckbox,
]) {
  input.addEventListener("change", renderSessionFlags);
}

modelInput.addEventListener("input", renderSessionFlags);

qaFocus?.addEventListener("click", () => {
  const focused = !document.body.classList.contains("focus-mode");
  setFocusMode(focused);
});

focusExitBtn?.addEventListener("click", () => {
  setFocusMode(false);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && document.body.classList.contains("focus-mode")) {
    setFocusMode(false);
  }
});

qaClearChat?.addEventListener("click", () => {
  chatPanel.innerHTML = "";
  userTurns = 0;
  assistantTurns = 0;
  webSearchHits = 0;
  lastLatencyMs = null;
  updateTelemetry();
});

qaCopySession?.addEventListener("click", async () => {
  if (!sessionId) {
    return;
  }
  try {
    await navigator.clipboard.writeText(sessionId);
    sessionPill.textContent = "Session copied";
    setTimeout(updateSessionPill, 900);
  } catch (_) {
    appendBubble("assistant", "Clipboard access denied by browser.", "system/error");
  }
});

qaResearchMode?.addEventListener("click", () => {
  enableWebSearchCheckbox.checked = true;
  enableRagCheckbox.checked = true;
  autoMatchSkillCheckbox.checked = true;
  enablePlanningCheckbox.checked = true;
  enableReflectionCheckbox.checked = true;
  enableRetryCheckbox.checked = true;
  renderSessionFlags();
});

contextToggleBtn?.addEventListener("click", () => {
  const collapsed = !document.body.classList.contains("drawer-collapsed");
  setDrawerCollapsed(collapsed);
});

checkHealth();
loadMeta();
syncStreamingAvailability();
renderSessionFlags();
updateSessionPill();
updateTelemetry();
setRunState("Ready");
setDrawerCollapsed(false);
appendBubble(
  "assistant",
  "Console initialized. Create a session and transmit your first query.",
  "system",
  [],
  false
);
