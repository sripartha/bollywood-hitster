// Bollywood Hitster — Party Edition (iPhone Web App)
// Supports:
// 1. Physical Cards Mode (In-App Camera QR Scanner + Card # Keypad + URL ?card=A001 deep link)
// 2. No-Card Mode (Spontaneous Digital Mystery Draw + Interactive 2-Team Digital Timeline with Year Window check)
// 3. Official House Rules:
//    - Film Songs: Name Film + Song Title -> Qualifies to guess Year Window
//    - No-Film (Indipop): Say "No Film" + Artist Name + Song Title -> Qualifies to guess Year Window
// 4. Zero-spoiler iOS Lock Screen / Dynamic Island metadata + Screen Wake Lock + DND Host Checklist

const state = {
  catalog: [],
  byId: {},
  selectedDeck: "A",
  currentCard: null,
  blindMode: true, // Default: hide song details on screen until "Tap to Reveal" (since opposing team holds physical card)
  isPlaying: false,
  // No-Card Mode state
  noCardPoolFilter: "ALL",
  playedIds: new Set(JSON.parse(localStorage.getItem("bh_played_ids") || "[]")),
  activeTeam: 0, // 0 = Team A, 1 = Team B
  selectedSlotIndex: null,
  timelines: JSON.parse(localStorage.getItem("bh_timelines") || "null") || [[], []],
  // Scoreboard state
  teams: JSON.parse(localStorage.getItem("bh_teams") || "null") || [
    { name: "Team A (Sholay)", cards: 1, tokens: 2 },
    { name: "Team B (DDLJ)", cards: 1, tokens: 2 }
  ],
  // Camera scanner state
  cameraStream: null,
  scanRaf: null,
  wakeLock: null
};

const audioEl = document.getElementById("hitster-audio");

// ==================== INITIALIZATION ====================
document.addEventListener("DOMContentLoaded", async () => {
  initTabs();
  initHostBannerAndWakeLock();
  initScoreboard();
  initKeypadAndScanner();
  initPlayerControls();
  initNoCardMode();
  initCatalogInspector();

  await loadCatalog();
  checkUrlForCardParam();
});

async function loadCatalog() {
  try {
    const res = await fetch("catalog.json");
    const data = await res.json();
    state.catalog = data;
    state.byId = {};
    data.forEach((item) => {
      state.byId[item.card_id.toUpperCase()] = item;
      state.byId[item.card_label.toUpperCase()] = item;
    });
    updateNoCardRemainingBadge();
    if (state.timelines[0].length === 0 && state.timelines[1].length === 0) {
      dealStartingTimelineCards(false);
    } else {
      renderDigitalTimeline();
    }
    renderCatalogList();
  } catch (err) {
    console.error("Failed to load catalog.json:", err);
  }
}

function checkUrlForCardParam() {
  const params = new URLSearchParams(window.location.search);
  const cardParam = params.get("card") || window.location.hash.replace("#", "");
  if (cardParam) {
    const cleaned = cardParam.toUpperCase().replace(/[^A-Z0-9]/g, "");
    if (state.byId[cleaned]) {
      loadAndPlayCard(state.byId[cleaned], true);
    }
  }
}

// ==================== TABS & NAVIGATION ====================
function initTabs() {
  document.body.setAttribute("data-active-mode", "cards");
  const tabs = document.querySelectorAll(".mode-tab");

  tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset.mode;
      document.body.setAttribute("data-active-mode", mode);

      tabs.forEach((b) => {
        const isActive = b === btn;
        b.classList.toggle("active", isActive);
        if (b.getAttribute("role") === "radio") {
          b.setAttribute("aria-checked", isActive ? "true" : "false");
        }
      });

      document.querySelectorAll(".view-section").forEach((sec) => {
        sec.classList.toggle("active", sec.id === `view-${mode}`);
      });

      const playerPanel = document.getElementById("player-panel");
      const scannerPanel = document.getElementById("scanner-panel");
      if (mode === "rules") {
        playerPanel.classList.add("hidden");
      } else if (mode === "cards") {
        if (state.currentCard) {
          playerPanel.classList.remove("hidden");
          if (scannerPanel) scannerPanel.classList.add("hidden");
        } else {
          if (scannerPanel) scannerPanel.classList.remove("hidden");
        }
      } else if (state.currentCard) {
        playerPanel.classList.remove("hidden");
      }
    });
  });
}

// ==================== HOST BANNER & SCREEN WAKE LOCK ====================
function initHostBannerAndWakeLock() {
  const banner = document.getElementById("host-banner");
  const btnClose = document.getElementById("btn-close-banner");
  const btnTips = document.getElementById("btn-host-tips");

  if (localStorage.getItem("bh_hide_banner") === "1") {
    banner.classList.add("hidden");
  }

  btnClose.addEventListener("click", () => {
    banner.classList.add("hidden");
    localStorage.setItem("bh_hide_banner", "1");
  });

  btnTips.addEventListener("click", () => {
    banner.classList.toggle("hidden");
    localStorage.setItem("bh_hide_banner", banner.classList.contains("hidden") ? "1" : "0");
    requestScreenWakeLock();
  });

  requestScreenWakeLock();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      requestScreenWakeLock();
    }
  });
}

async function requestScreenWakeLock() {
  const statusEl = document.getElementById("wakelock-status");
  if ("wakeLock" in navigator) {
    try {
      state.wakeLock = await navigator.wakeLock.request("screen");
      if (statusEl) statusEl.innerHTML = "3. Screen Keep-Awake: <strong>Active ✅</strong>";
    } catch (e) {
      if (statusEl) statusEl.innerHTML = "3. Screen Keep-Awake: <strong>Tap Screen to Activate</strong>";
    }
  }
}

// ==================== PHYSICAL CARDS: CAMERA QR SCANNER & KEYPAD ====================
function initKeypadAndScanner() {
  // Deck A / B selector
  document.querySelectorAll(".deck-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.selectedDeck = btn.dataset.deck;
      document.querySelectorAll(".deck-btn").forEach((b) => b.classList.toggle("active", b === btn));
    });
  });

  const input = document.getElementById("card-num-input");
  const btnPlayCode = document.getElementById("btn-play-code");

  const triggerInputLookup = () => {
    const raw = input.value.trim().toUpperCase();
    if (!raw) return;
    let code = raw;
    if (/^[AB]\d{1,3}$/.test(raw)) {
      const d = raw[0];
      const n = parseInt(raw.slice(1), 10);
      code = `${d}${String(n).padStart(3, "0")}`;
    } else if (/^\d{1,3}$/.test(raw)) {
      const n = parseInt(raw, 10);
      code = `${state.selectedDeck}${String(n).padStart(3, "0")}`;
    }
    const card = state.byId[code];
    if (card) {
      input.value = "";
      stopCameraScanner();
      loadAndPlayCard(card, true);
    } else {
      input.value = "";
      input.placeholder = `Invalid (${code}) — Try 1-150`;
    }
  };

  btnPlayCode.addEventListener("click", triggerInputLookup);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") triggerInputLookup();
  });

  // Mini keypad buttons
  document.querySelectorAll(".key-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const k = btn.dataset.key;
      if (k === "C") {
        input.value = "";
      } else if (k === "GO") {
        triggerInputLookup();
      } else if (input.value.length < 3) {
        input.value += k;
      }
    });
  });

  // Keypad drawer toggle
  const btnToggleKeypad = document.getElementById("btn-toggle-keypad");
  const keypadDrawer = document.getElementById("manual-keypad-drawer");
  if (btnToggleKeypad && keypadDrawer) {
    btnToggleKeypad.addEventListener("click", () => {
      keypadDrawer.classList.toggle("hidden");
      btnToggleKeypad.textContent = keypadDrawer.classList.contains("hidden")
        ? "⌨️ Type Card # Instead"
        : "✕ Hide Keypad";
    });
  }

  // Camera QR Scanner buttons
  document.getElementById("btn-start-camera").addEventListener("click", startCameraScanner);
  document.getElementById("btn-stop-camera").addEventListener("click", stopCameraScanner);
}

async function startCameraScanner() {
  const container = document.getElementById("camera-container");
  const video = document.getElementById("qr-video");
  const canvas = document.getElementById("qr-canvas");
  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false
    });
    state.cameraStream = stream;
    video.srcObject = stream;
    await video.play();
    container.classList.remove("hidden");

    const scanFrame = () => {
      if (!state.cameraStream) return;
      if (video.readyState === video.HAVE_ENOUGH_DATA) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        if (window.jsQR) {
          const qr = window.jsQR(imgData.data, imgData.width, imgData.height, {
            inversionAttempts: "dontInvert"
          });
          if (qr && qr.data) {
            const matchedCard = parseQrPayload(qr.data);
            if (matchedCard) {
              if (navigator.vibrate) navigator.vibrate(80);
              stopCameraScanner();
              loadAndPlayCard(matchedCard, true);
              return;
            }
          }
        }
      }
      state.scanRaf = requestAnimationFrame(scanFrame);
    };
    state.scanRaf = requestAnimationFrame(scanFrame);
  } catch (err) {
    alert("Camera access was declined or unavailable. You can type the 3-digit Card # directly on the keypad!");
  }
}

function stopCameraScanner() {
  if (state.scanRaf) {
    cancelAnimationFrame(state.scanRaf);
    state.scanRaf = null;
  }
  if (state.cameraStream) {
    state.cameraStream.getTracks().forEach((t) => t.stop());
    state.cameraStream = null;
  }
  const container = document.getElementById("camera-container");
  if (container) container.classList.add("hidden");
}

function parseQrPayload(rawText) {
  if (!rawText) return null;
  const text = rawText.trim();
  // Match ?card=A042 or #A042 or direct A042 / A-042
  const m = text.match(/\b([AB])-?(\d{3})\b/i) || text.match(/card=([AB])(\d{3})/i);
  if (m) {
    const id = `${m[1].toUpperCase()}${m[2]}`;
    if (state.byId[id]) return state.byId[id];
  }
  // Also match Spotify track ID if someone scans a direct Spotify URI/URL
  const sp = text.match(/track[/:]([a-zA-Z0-9]{22})/);
  if (sp) {
    return state.catalog.find((c) => c.spotify_id === sp[1]) || null;
  }
  return null;
}

// ==================== PLAYER & ANTI-SPOILER ENGINE ====================
function initPlayerControls() {
  const btnPlayPause = document.getElementById("btn-play-pause");
  const btnReplay = document.getElementById("btn-replay");
  const btnNextScan = document.getElementById("btn-next-scan");
  const btnReveal = document.getElementById("btn-reveal-answer");
  const btnToggleBlind = document.getElementById("btn-toggle-blind");

  btnPlayPause.addEventListener("click", () => {
    if (!state.currentCard) return;
    if (audioEl.paused) {
      audioEl.play();
    } else {
      audioEl.pause();
    }
  });

  btnReplay.addEventListener("click", () => {
    if (!state.currentCard) return;
    audioEl.currentTime = 0;
    audioEl.play();
  });

  btnNextScan.addEventListener("click", () => {
    audioEl.pause();
    const activeTab = document.querySelector(".mode-tab.active")?.dataset.mode;
    if (activeTab === "nocard") {
      drawRandomMysteryCard();
    } else {
      const scannerPanel = document.getElementById("scanner-panel");
      const playerPanel = document.getElementById("player-panel");
      if (scannerPanel) scannerPanel.classList.remove("hidden");
      if (playerPanel) playerPanel.classList.add("hidden");
      window.scrollTo({ top: 0, behavior: "smooth" });
      startCameraScanner();
    }
  });

  btnReveal.addEventListener("click", () => {
    revealCurrentCardAnswer();
  });

  btnToggleBlind.addEventListener("click", () => {
    state.blindMode = !state.blindMode;
    btnToggleBlind.textContent = state.blindMode
      ? "🙈 Blind Screen (Tap to Reveal)"
      : "👁 Host View (Always Show Answer)";
    if (!state.blindMode && state.currentCard) {
      revealCurrentCardAnswer();
    } else if (state.blindMode && state.currentCard) {
      document.getElementById("answer-card-face").classList.add("hidden");
      document.getElementById("btn-reveal-answer").classList.remove("hidden");
      document.getElementById("vinyl-center-text").textContent = "?";
    }
  });

  // Audio events
  audioEl.addEventListener("play", () => {
    state.isPlaying = true;
    btnPlayPause.innerHTML = "⏸ Pause";
    document.getElementById("vinyl-disc").classList.add("spinning");
    document.getElementById("player-status-text").textContent =
      "Playing 30s Spotify Representative Sample...";
    setSpoilerFreeMediaSession();
  });

  audioEl.addEventListener("pause", () => {
    state.isPlaying = false;
    btnPlayPause.innerHTML = "▶ Play";
    document.getElementById("vinyl-disc").classList.remove("spinning");
    if (audioEl.currentTime >= audioEl.duration - 0.5) {
      document.getElementById("player-status-text").textContent =
        "30s Sample Finished — Tap Replay to Hear Again!";
    } else {
      document.getElementById("player-status-text").textContent = "Paused";
    }
  });

  audioEl.addEventListener("timeupdate", () => {
    const cur = audioEl.currentTime || 0;
    const dur = audioEl.duration || 30;
    const pct = Math.min(100, (cur / dur) * 100);
    document.getElementById("audio-progress-fill").style.width = `${pct}%`;
    document.getElementById("audio-time-current").textContent = formatSec(cur);
    document.getElementById("audio-time-total").textContent = formatSec(dur);
  });

  // Quick Award buttons inside Answer Reveal
  document.querySelectorAll(".btn-award").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.award;
      if (action === "team0-card") updateScore(0, "cards", 1);
      if (action === "team0-token") updateScore(0, "tokens", 1);
      if (action === "team1-card") updateScore(1, "cards", 1);
      if (action === "team1-token") updateScore(1, "tokens", 1);
      btn.textContent = "✅ Added!";
      setTimeout(() => {
        if (action === "team0-card") btn.textContent = "+1 Card Team A";
        if (action === "team0-token") btn.textContent = "+1 Token Team A";
        if (action === "team1-card") btn.textContent = "+1 Card Team B";
        if (action === "team1-token") btn.textContent = "+1 Token Team B";
      }, 900);
    });
  });
}

function loadAndPlayCard(card, autoPlay = true) {
  state.currentCard = card;
  state.playedIds.add(card.card_id);
  localStorage.setItem("bh_played_ids", JSON.stringify([...state.playedIds]));
  updateNoCardRemainingBadge();

  const panel = document.getElementById("player-panel");
  panel.classList.remove("hidden");
  const activeTab = document.querySelector(".mode-tab.active")?.dataset.mode;
  if (activeTab === "cards") {
    const scannerPanel = document.getElementById("scanner-panel");
    if (scannerPanel) scannerPanel.classList.add("hidden");
  }

  document.getElementById("player-card-badge").textContent = `DECK ${card.deck} • #${String(card.card_num).padStart(3, "0")}`;

  // Populate answer card DOM
  document.getElementById("ans-card-id").textContent = card.card_label;
  document.getElementById("ans-decade").textContent = card.decade;
  document.getElementById("ans-year").textContent = card.year;
  document.getElementById("ans-title").textContent = card.title;

  const movieEl = document.getElementById("ans-movie");
  if (card.is_no_film) {
    movieEl.textContent = `🚫 NO FILM (Indipop) • 🎤 ARTIST: ${card.singers}`;
    movieEl.classList.add("no-film-badge");
  } else {
    movieEl.textContent = `🎬 FILM: ${card.movie}`;
    movieEl.classList.remove("no-film-badge");
  }

  document.getElementById("ans-singers").textContent = card.singers;
  document.getElementById("ans-music").textContent = card.music_director;
  document.getElementById("ans-stars").textContent = card.stars;
  document.getElementById("ans-spotify-link").href = card.spotify_url;

  if (state.blindMode) {
    document.getElementById("answer-card-face").classList.add("hidden");
    document.getElementById("btn-reveal-answer").classList.remove("hidden");
    document.getElementById("vinyl-center-text").textContent = "?";
  } else {
    revealCurrentCardAnswer();
  }

  // Load 30s verified Spotify preview stream
  audioEl.src = card.preview_url;
  audioEl.currentTime = 0;
  setSpoilerFreeMediaSession();

  if (autoPlay) {
    audioEl.play().catch(() => {
      document.getElementById("player-status-text").textContent =
        "Ready — Tap ▶ Play to Start Audio!";
      document.getElementById("btn-play-pause").innerHTML = "▶ Play";
    });
  }

  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function revealCurrentCardAnswer() {
  if (!state.currentCard) return;
  document.getElementById("btn-reveal-answer").classList.add("hidden");
  document.getElementById("answer-card-face").classList.remove("hidden");
  document.getElementById("vinyl-center-text").textContent = state.currentCard.year;
}

function setSpoilerFreeMediaSession() {
  if ("mediaSession" in navigator && state.currentCard) {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: `Mystery Track #${state.currentCard.card_id}`,
      artist: "Bollywood Hitster — Name Film & Song!",
      album: "Guess the Release Year Window"
    });
  }
}

function formatSec(sec) {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}:${String(rem).padStart(2, "0")}`;
}

// ==================== MODE 2: NO-CARD MODE & DIGITAL TIMELINE ====================
function initNoCardMode() {
  const select = document.getElementById("nocard-deck-select");
  select.addEventListener("change", () => {
    state.noCardPoolFilter = select.value;
    updateNoCardRemainingBadge();
  });

  document.getElementById("btn-reset-nocard").addEventListener("click", () => {
    state.playedIds.clear();
    localStorage.setItem("bh_played_ids", "[]");
    updateNoCardRemainingBadge();
  });

  document.getElementById("btn-draw-random").addEventListener("click", () => {
    drawRandomMysteryCard();
  });

  document.getElementById("turn-team-0").addEventListener("click", () => setActiveTimelineTeam(0));
  document.getElementById("turn-team-1").addEventListener("click", () => setActiveTimelineTeam(1));

  document.getElementById("btn-deal-starters").addEventListener("click", () => {
    dealStartingTimelineCards(true);
  });

  document.getElementById("btn-add-to-timeline").addEventListener("click", () => {
    checkAndLockDigitalTimelinePlacement();
  });
}

function getFilteredNoCardPool() {
  return state.catalog.filter((c) => {
    if (state.noCardPoolFilter !== "ALL" && c.deck !== state.noCardPoolFilter) return false;
    return !state.playedIds.has(c.card_id);
  });
}

function updateNoCardRemainingBadge() {
  const el = document.getElementById("nocard-remaining");
  if (!el || !state.catalog.length) return;
  const rem = getFilteredNoCardPool().length;
  el.textContent = `${rem} unplayed`;
}

function drawRandomMysteryCard() {
  let pool = getFilteredNoCardPool();
  if (pool.length === 0) {
    state.playedIds.clear();
    pool = getFilteredNoCardPool();
  }
  const pick = pool[Math.floor(Math.random() * pool.length)];
  state.selectedSlotIndex = null;
  document.getElementById("btn-add-to-timeline").disabled = true;
  const fb = document.getElementById("timeline-feedback");
  fb.classList.add("hidden");
  renderDigitalTimeline();
  loadAndPlayCard(pick, true);
}

function setActiveTimelineTeam(teamIdx) {
  state.activeTeam = teamIdx;
  state.selectedSlotIndex = null;
  document.getElementById("turn-team-0").classList.toggle("active", teamIdx === 0);
  document.getElementById("turn-team-1").classList.toggle("active", teamIdx === 1);
  document.getElementById("btn-add-to-timeline").disabled = true;
  document.getElementById("timeline-feedback").classList.add("hidden");
  renderDigitalTimeline();
}

function dealStartingTimelineCards(resetExisting = true) {
  if (!state.catalog.length) return;
  if (!resetExisting && state.timelines[0].length > 0) return;

  // Pick 2 mid-era iconic starters (e.g. 1980s-1990s)
  const midPool = state.catalog.filter((c) => c.year >= 1975 && c.year <= 2005);
  const c0 = midPool[Math.floor(Math.random() * midPool.length)];
  let c1 = midPool[Math.floor(Math.random() * midPool.length)];
  if (c1.card_id === c0.card_id && midPool.length > 1) {
    c1 = midPool[(midPool.indexOf(c0) + 7) % midPool.length];
  }

  state.timelines = [[c0], [c1]];
  state.playedIds.add(c0.card_id);
  state.playedIds.add(c1.card_id);
  localStorage.setItem("bh_timelines", JSON.stringify(state.timelines));
  localStorage.setItem("bh_played_ids", JSON.stringify([...state.playedIds]));

  state.teams[0].cards = 1;
  state.teams[1].cards = 1;
  saveAndRenderScores();
  renderDigitalTimeline();
}

function renderDigitalTimeline() {
  const container = document.getElementById("digital-timeline-slots");
  if (!container) return;
  const tl = state.timelines[state.activeTeam] || [];
  container.innerHTML = "";

  for (let i = 0; i <= tl.length; i++) {
    // Render slot button before card i (or at end)
    const slotBtn = document.createElement("button");
    slotBtn.className = "tl-slot-btn" + (state.selectedSlotIndex === i ? " selected" : "");
    let label = "";
    if (tl.length === 0) {
      label = "Place Here";
    } else if (i === 0) {
      label = `≤ ${tl[0].year}`;
    } else if (i === tl.length) {
      label = `≥ ${tl[tl.length - 1].year}`;
    } else {
      label = `${tl[i - 1].year}–${tl[i].year}`;
    }
    slotBtn.innerHTML = `<div>📍 Slot ${i + 1}</div><div>${label}</div>`;
    slotBtn.addEventListener("click", () => {
      state.selectedSlotIndex = i;
      document.getElementById("btn-add-to-timeline").disabled = !state.currentCard;
      renderDigitalTimeline();
    });
    container.appendChild(slotBtn);

    if (i < tl.length) {
      const c = tl[i];
      const node = document.createElement("div");
      node.className = "tl-card-node";
      node.innerHTML = `
        <div class="tl-card-year">${c.year}</div>
        <div class="tl-card-title" title="${c.title}">${c.title}</div>
      `;
      container.appendChild(node);
    }
  }
}

function checkAndLockDigitalTimelinePlacement() {
  const card = state.currentCard;
  const slot = state.selectedSlotIndex;
  if (!card || slot === null) return;

  const tl = state.timelines[state.activeTeam];
  const minYear = slot === 0 ? -Infinity : tl[slot - 1].year;
  const maxYear = slot === tl.length ? Infinity : tl[slot].year;

  const isCorrect = card.year >= minYear && card.year <= maxYear;
  const fb = document.getElementById("timeline-feedback");
  fb.classList.remove("hidden", "correct", "wrong");

  revealCurrentCardAnswer();

  if (isCorrect) {
    tl.splice(slot, 0, card);
    localStorage.setItem("bh_timelines", JSON.stringify(state.timelines));
    state.teams[state.activeTeam].cards = tl.length;
    saveAndRenderScores();
    fb.classList.add("correct");
    fb.innerHTML = `✅ <strong>CORRECT WINDOW!</strong> "${card.title}" (${card.is_no_film ? "NO FILM — " + card.singers : card.movie}) is from <strong>${card.year}</strong>! Added to ${state.teams[state.activeTeam].name}'s timeline (${tl.length}/10)!`;
  } else {
    fb.classList.add("wrong");
    fb.innerHTML = `❌ <strong>MISSED WINDOW!</strong> You placed it in <strong>${minYear === -Infinity ? "Start" : minYear}–${maxYear === Infinity ? "Now" : maxYear}</strong>, but "${card.title}" (${card.is_no_film ? "NO FILM — " + card.singers : card.movie}) was released in <strong>${card.year}</strong>!`;
  }

  state.selectedSlotIndex = null;
  document.getElementById("btn-add-to-timeline").disabled = true;
  renderDigitalTimeline();
}

// ==================== SCOREBOARD ====================
function initScoreboard() {
  const t0Name = document.getElementById("team0-name");
  const t1Name = document.getElementById("team1-name");

  t0Name.value = state.teams[0].name;
  t1Name.value = state.teams[1].name;

  t0Name.addEventListener("input", () => {
    state.teams[0].name = t0Name.value || "Team A";
    saveAndRenderScores();
  });
  t1Name.addEventListener("input", () => {
    state.teams[1].name = t1Name.value || "Team B";
    saveAndRenderScores();
  });

  document.querySelectorAll(".cnt-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const team = parseInt(btn.dataset.team, 10);
      const field = btn.dataset.field;
      const delta = parseInt(btn.dataset.delta, 10);
      updateScore(team, field, delta);
    });
  });

  document.getElementById("btn-reset-scores").addEventListener("click", () => {
    state.teams[0].cards = 1;
    state.teams[0].tokens = 2;
    state.teams[1].cards = 1;
    state.teams[1].tokens = 2;
    dealStartingTimelineCards(true);
    saveAndRenderScores();
  });

  saveAndRenderScores();
}

function updateScore(teamIdx, field, delta) {
  state.teams[teamIdx][field] = Math.max(0, state.teams[teamIdx][field] + delta);
  saveAndRenderScores();
}

function saveAndRenderScores() {
  localStorage.setItem("bh_teams", JSON.stringify(state.teams));
  document.getElementById("team0-cards").textContent = state.teams[0].cards;
  document.getElementById("team0-tokens").textContent = state.teams[0].tokens;
  document.getElementById("team1-cards").textContent = state.teams[1].cards;
  document.getElementById("team1-tokens").textContent = state.teams[1].tokens;

  document.getElementById("footer-t0-cards").textContent = state.teams[0].cards;
  document.getElementById("footer-t0-tokens").textContent = state.teams[0].tokens;
  document.getElementById("footer-t1-cards").textContent = state.teams[1].cards;
  document.getElementById("footer-t1-tokens").textContent = state.teams[1].tokens;

  const turn0 = document.getElementById("turn-team-0");
  const turn1 = document.getElementById("turn-team-1");
  if (turn0) turn0.textContent = `${state.teams[0].name.split("(")[0].trim()}'s Turn`;
  if (turn1) turn1.textContent = `${state.teams[1].name.split("(")[0].trim()}'s Turn`;
}

// ==================== CATALOG INSPECTOR ====================
function initCatalogInspector() {
  const btnToggle = document.getElementById("btn-toggle-catalog");
  const drawer = document.getElementById("catalog-drawer");
  const searchInput = document.getElementById("catalog-search");
  const decSelect = document.getElementById("catalog-decade-filter");

  btnToggle.addEventListener("click", () => {
    drawer.classList.toggle("hidden");
    btnToggle.textContent = drawer.classList.contains("hidden") ? "Show Catalog" : "Hide Catalog";
  });

  searchInput.addEventListener("input", renderCatalogList);
  decSelect.addEventListener("change", renderCatalogList);
}

function renderCatalogList() {
  const listEl = document.getElementById("catalog-list");
  if (!listEl || !state.catalog.length) return;
  const q = (document.getElementById("catalog-search")?.value || "").toLowerCase().trim();
  const dec = document.getElementById("catalog-decade-filter")?.value || "ALL";

  const filtered = state.catalog.filter((c) => {
    if (dec !== "ALL" && c.decade !== dec) return false;
    if (!q) return true;
    return (
      c.card_id.toLowerCase().includes(q) ||
      c.title.toLowerCase().includes(q) ||
      c.movie.toLowerCase().includes(q) ||
      c.singers.toLowerCase().includes(q) ||
      String(c.year).includes(q)
    );
  });

  listEl.innerHTML = filtered
    .slice(0, 100)
    .map(
      (c) => `
    <div class="cat-item">
      <div class="cat-item-left">
        <strong>${c.card_label}</strong> • <span>${c.year}</span> — <strong>${c.title}</strong>
        <div class="muted-sm">${c.is_no_film ? "🚫 NO FILM • Artist: " + c.singers : "🎬 " + c.movie + " • " + c.singers}</div>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="window.playCardById('${c.card_id}')">▶ Play</button>
    </div>
  `
    )
    .join("");
}

window.playCardById = function (cardId) {
  const card = state.byId[cardId];
  if (card) {
    // Switch to Physical Cards tab so player panel is visible
    document.querySelector('.mode-tab[data-mode="cards"]').click();
    loadAndPlayCard(card, true);
  }
};
