const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const alarm = document.getElementById("alarm");
const simulateBtn = document.getElementById("simulateBtn");
const pauseBtn = document.getElementById("pauseBtn");
const resetBtn = document.getElementById("resetBtn");
const timeEl = document.getElementById("time");
const escapedEl = document.getElementById("escaped");
const trappedEl = document.getElementById("trapped");

let frames = []; 
let tickMs = 1100;   // ⭐ SLOWER HUMANS
let currentFrame = 0;
let playing = false;
let intervalId = null;
let rows = 30, cols = 30;
let cellSize = Math.min(canvas.width / cols, canvas.height / rows);

// fetch initial map
async function initMap() {
  const res = await fetch("/init");
  const json = await res.json();
  rows = json.rows;
  cols = json.cols;
  cellSize = Math.floor(Math.min(canvas.width / cols, canvas.height / rows));
  drawStatic(json);
}

// draw static map
function drawStatic(state) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const offsetX = Math.floor((canvas.width - cellSize * cols) / 2);
  const offsetY = Math.floor((canvas.height - cellSize * rows) / 2);

  ctx.fillStyle = "rgba(8,10,12,0.85)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const x = offsetX + c * cellSize;
      const y = offsetY + r * cellSize;
      ctx.fillStyle = "#16202b";
      ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
    }
  }

  (state.walls || []).forEach(([r, c]) => {
    const x = offsetX + c * cellSize,
      y = offsetY + r * cellSize;
    ctx.fillStyle = "#000";
    ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
  });

  (state.exits || []).forEach(([r, c]) => {
    const x = offsetX + c * cellSize,
      y = offsetY + r * cellSize;
    ctx.fillStyle = "#20d06a";
    ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
  });

  (state.fires || []).forEach(([r, c]) => {
    const x = offsetX + c * cellSize,
      y = offsetY + r * cellSize;
    ctx.fillStyle = "orange";
    ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
    ctx.globalAlpha = 0.12;
    ctx.fillStyle = "orange";
    ctx.fillRect(x - 3, y - 3, cellSize + 6, cellSize + 6);
    ctx.globalAlpha = 1;
  });

  (state.humans || []).forEach((h) => {
    const x = offsetX + h.c * cellSize + cellSize / 2;
    const y = offsetY + h.r * cellSize + cellSize / 2;
    drawHuman(x, y);
  });
}

function drawHuman(cx, cy) {
  ctx.beginPath();
  ctx.fillStyle = "#2aa0ff";
  ctx.arc(cx, cy, Math.max(3, cellSize * 0.28), 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(0,0,0,0.4)";
  ctx.stroke();
}

function drawFrame(frame) {
  const offsetX = Math.floor((canvas.width - cellSize * cols) / 2);
  const offsetY = Math.floor((canvas.height - cellSize * rows) / 2);

  ctx.fillStyle = "rgba(8,10,12,0.9)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const x = offsetX + c * cellSize,
        y = offsetY + r * cellSize;
      ctx.fillStyle = "#11151a";
      ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
    }
  }

  frame.walls.forEach(([r, c]) => {
    const x = offsetX + c * cellSize,
      y = offsetY + r * cellSize;
    ctx.fillStyle = "#000";
    ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
  });

  frame.exits.forEach(([r, c]) => {
    const x = offsetX + c * cellSize,
      y = offsetY + r * cellSize;
    ctx.fillStyle = "#20d06a";
    ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
  });

  frame.fires.forEach(([r, c]) => {
    const x = offsetX + c * cellSize,
      y = offsetY + r * cellSize;
    const g = Math.floor(60 + Math.random() * 140);
    ctx.fillStyle = `rgb(255,${g},0)`;
    ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
    ctx.globalAlpha = 0.12;
    ctx.fillStyle = "orange";
    ctx.fillRect(x - 3, y - 3, cellSize + 6, cellSize + 6);
    ctx.globalAlpha = 1;
  });

  frame.humans.forEach((h) => {
    const x = offsetX + h.c * cellSize + cellSize / 2;
    const y = offsetY + h.r * cellSize + cellSize / 2;
    ctx.beginPath();
    ctx.fillStyle = h.escaped ? "#9efc9e" : h.trapped ? "#444344" : "#2aa0ff";
    ctx.arc(x, y, Math.max(3, cellSize * 0.28), 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(0,0,0,0.4)";
    ctx.stroke();
  });

  timeEl.textContent = frame.tick;
  const escaped = frame.humans.filter((h) => h.escaped).length;
  const trapped = frame.humans.filter((h) => h.trapped).length;
  escapedEl.textContent = escaped;
  trappedEl.textContent = trapped;
}

async function startSimulation() {
  if (playing) return;

  const res = await fetch("/simulate");
  const data = await res.json();
  frames = data.frames;
  tickMs = 1100;

  if (!frames || frames.length === 0) return;

  try {
    alarm.currentTime = 0;
    alarm.volume = 1.0;
    alarm.play();
  } catch (e) {}

  setTimeout(() => {
    try {
      alarm.pause();
      alarm.currentTime = 0;
    } catch (e) {}

    speak("Fire is spreading.");

    playing = true;
    currentFrame = 0;
    intervalId = setInterval(() => {
      if (!playing) return;
      if (currentFrame >= frames.length) {
        clearInterval(intervalId);
        playing = false;
        speak("Simulation complete.");
        return;
      }
      drawFrame(frames[currentFrame]);
      currentFrame++;
    }, tickMs);
  }, 5000);
}

function pauseSimulation() {
  playing = false;
  if (intervalId) clearInterval(intervalId);

  alarm.pause();
  alarm.currentTime = 0;
  window.speechSynthesis.cancel();
}

async function resetSimulation() {
  if (intervalId) clearInterval(intervalId);

  playing = false;
  window.speechSynthesis.cancel();
  alarm.pause();
  alarm.currentTime = 0;

  currentFrame = 0;
  frames = [];
  await initMap();

  timeEl.textContent = 0;
  escapedEl.textContent = 0;
  trappedEl.textContent = 0;
}

function speak(text) {
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  u.rate = 1.0;
  u.pitch = 1.0;
  window.speechSynthesis.speak(u);
}

simulateBtn.addEventListener("click", startSimulation);
pauseBtn.addEventListener("click", pauseSimulation);
resetBtn.addEventListener("click", resetSimulation);

initMap();
