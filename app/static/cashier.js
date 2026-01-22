const API = ""; // same origin
const TERMINAL_TOKEN = "PUT_TERMINAL_TOKEN_HERE";

let sessionId = null;
let livenessToken = null;
let frameTimer = null;

function log(msg) {
  const el = document.getElementById("log");
  el.textContent = msg + "\n" + el.textContent;
}

async function initCamera() {
  const video = document.getElementById("video");
  const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
  video.srcObject = stream;
}
initCamera().catch(e => log("Camera error: " + e));

async function loadEmployee() {
  const uid = document.getElementById("cardUid").value.trim();
  const r = await fetch(`${API}/api/employee_info?card_uid=${encodeURIComponent(uid)}`, {
    headers: { "X-Terminal-Token": TERMINAL_TOKEN }
  });
  const j = await r.json();
  if (!j.ok) { log(JSON.stringify(j)); return; }
  const d = j.data;
  document.getElementById("fio").textContent = d.full_name;
  document.getElementById("subsidy").textContent = (d.subsidy_today_left_cents/100).toFixed(2);
  document.getElementById("monthly").textContent = (d.monthly_left_cents/100).toFixed(2);
  document.getElementById("refPhoto").src = d.photo_base64 ? `data:image/jpeg;base64,${d.photo_base64}` : "";
  document.getElementById("hint").textContent = d.needs_face_enrollment ? "Нужно зарегистрировать лицо" : "—";
  log("Employee loaded");
}

async function startLiveness() {
  const uid = document.getElementById("cardUid").value.trim();
  const r = await fetch(`${API}/api/start_liveness`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Terminal-Token": TERMINAL_TOKEN },
    body: JSON.stringify({ card_uid: uid })
  });
  const j = await r.json();
  if (!j.ok) { log(JSON.stringify(j)); return; }
  sessionId = j.data.session_id;
  livenessToken = null;
  document.getElementById("hint").textContent = j.data.commands[0].text;
  log("Liveness started: " + sessionId);

  if (frameTimer) clearInterval(frameTimer);
  frameTimer = setInterval(sendFrame, j.data.frame_interval_ms || 150);
}

async function sendFrame() {
  if (!sessionId) return;

  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.7));
  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("image", blob, "frame.jpg");

  const r = await fetch(`${API}/api/liveness_frame`, {
    method: "POST",
    headers: { "X-Terminal-Token": TERMINAL_TOKEN },
    body: fd
  });
  const j = await r.json();
  if (!j.ok) {
    document.getElementById("hint").textContent = j.message || "Ошибка";
    log(JSON.stringify(j));
    stopFrames();
    return;
  }

  document.getElementById("hint").textContent = j.data.hint;
  if (j.data.status !== "IN_PROGRESS") {
    log("Liveness status: " + j.data.status);
    stopFrames();
  }
}

function stopFrames() {
  if (frameTimer) clearInterval(frameTimer);
  frameTimer = null;
}

async function finishLiveness() {
  if (!sessionId) return;
  const r = await fetch(`${API}/api/finish_liveness`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Terminal-Token": TERMINAL_TOKEN },
    body: JSON.stringify({ session_id: sessionId })
  });
  const j = await r.json();
  if (!j.ok) { log(JSON.stringify(j)); return; }
  if (j.data.result === "PASSED") {
    livenessToken = j.data.liveness_token;
    log("Liveness PASSED");
  } else {
    log("Liveness result: " + j.data.result + " reason=" + (j.data.reason_code || ""));
  }
}

async function pay() {
  const uid = document.getElementById("cardUid").value.trim();
  const rub = parseFloat(document.getElementById("amountRub").value || "0");
  const amount_cents = Math.round(rub * 100);

  const r = await fetch(`${API}/api/pay`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Terminal-Token": TERMINAL_TOKEN },
    body: JSON.stringify({ card_uid: uid, amount_cents, liveness_token: livenessToken })
  });
  const j = await r.json();
  log(JSON.stringify(j, null, 2));
}
