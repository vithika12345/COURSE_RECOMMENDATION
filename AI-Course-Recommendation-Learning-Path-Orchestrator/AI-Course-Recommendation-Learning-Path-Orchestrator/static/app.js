const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

let currentPlan = null;
let lastProfile = null;

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => toast.classList.remove("show"), 3500);
}

function navigate(view) {
  $$(".view").forEach(v => v.classList.remove("active-view"));
  $(`#${view}`).classList.add("active-view");
  $$(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.view === view));
}

$$(".nav-item").forEach(btn => btn.addEventListener("click", () => navigate(btn.dataset.view)));

$("#themeBtn").addEventListener("click", () => {
  document.body.classList.toggle("dark");
  localStorage.setItem("pathpilot-theme", document.body.classList.contains("dark") ? "dark" : "light");
});
if (localStorage.getItem("pathpilot-theme") === "dark") document.body.classList.add("dark");

function profileFromForm() {
  return {
    goal: $("#goal").value.trim(),
    level: $("#level").value,
    weekly_hours: Number($("#hours").value),
    interests: $("#interests").value.trim(),
    duration_weeks: Number($("#duration").value),
    learning_style: $("#style").value,
    constraints: $("#constraints").value.trim()
  };
}

function setAgentStates(states) {
  const rows = $$(".agent-row");
  rows.forEach((row, i) => {
    row.classList.remove("done");
    row.querySelector(".agent-state").textContent = states[i] || "idle";
  });
  $("#agentCount").textContent = `0/4`;
}

async function animateAgents() {
  const rows = $$(".agent-row");
  rows.forEach(r => { r.classList.remove("done"); r.querySelector(".agent-state").textContent = "idle"; });
  $("#agentCount").textContent = "0/4";
  for (let i = 0; i < rows.length; i++) {
    rows[i].querySelector(".agent-state").textContent = "working";
    await new Promise(r => setTimeout(r, 420));
    rows[i].classList.add("done");
    rows[i].querySelector(".agent-state").textContent = "complete";
    $("#agentCount").textContent = `${i + 1}/4`;
  }
}

function renderPlan(plan) {
  currentPlan = plan;
  $("#planTitle").textContent = `Your ${plan.roadmap.length}-week roadmap`;
  $("#planSummary").textContent = plan.summary;
  $("#durationBadge").textContent = `${plan.roadmap.length} weeks • ${lastProfile?.weekly_hours || "—"}h/week`;

  $("#milestones").innerHTML = (plan.milestones || []).map((m, i) =>
    `<div class="milestone"><span>MILESTONE ${i + 1}</span><p>${escapeHtml(m)}</p></div>`
  ).join("");

  $("#roadmapGrid").classList.remove("empty-state");
  $("#roadmapGrid").innerHTML = (plan.roadmap || []).map(w => `
    <article class="week-card">
      <span class="week-no">WEEK ${w.week}</span><span class="hours">${w.hours}h</span>
      <h3>${escapeHtml(w.focus)}</h3>
      <ul>${(w.objectives || []).map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
      <div class="deliverable"><b>Deliverable:</b> ${escapeHtml(w.deliverable)}</div>
    </article>
  `).join("");

  const sources = plan.sources || [];
  $("#resourcesGrid").classList.remove("empty-state");
  $("#resourcesGrid").innerHTML = sources.length ? sources.map(s => `
    <article class="resource">
      <span class="source-tag">TAVILY SOURCE</span><span class="score">${s.score || ""}</span>
      <h3>${escapeHtml(s.title)}</h3>
      <p>${escapeHtml(s.snippet || "Research result used by the orchestrator.")}</p>
      <a href="${safeUrl(s.url)}" target="_blank" rel="noopener">Open source ↗</a>
    </article>
  `).join("") : `<div class="empty-state"><div class="empty-icon">↗</div><h3>No web sources returned</h3><p>Add a Tavily key to enable live research.</p></div>`;

  $("#agentTimeline").innerHTML = `
    <div class="timeline-item"><span class="timeline-dot"></span><div><b>Profile Agent</b><p>Structured ${escapeHtml(lastProfile.goal)} for ${escapeHtml(lastProfile.level)} level and ${lastProfile.weekly_hours} hours/week.</p></div></div>
    <div class="timeline-item"><span class="timeline-dot"></span><div><b>Research Agent</b><p>Gathered ${sources.length} current web resources with Tavily.</p></div></div>
    <div class="timeline-item"><span class="timeline-dot"></span><div><b>Recommendation Agent</b><p>Matched resources using learner level, interests, duration and constraints.</p></div></div>
    <div class="timeline-item"><span class="timeline-dot"></span><div><b>Roadmap Agent</b><p>Sequenced prerequisites, practice tasks, deliverables and milestones.</p></div></div>
  `;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
}

function safeUrl(url) {
  try {
    const u = new URL(url);
    return ["http:", "https:"].includes(u.protocol) ? u.href : "#";
  } catch { return "#"; }
}

$("#profileForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  lastProfile = profileFromForm();
  if (!lastProfile.goal) return;
  const btn = e.submitter;
  btn.disabled = true;
  btn.innerHTML = "<span>◌</span> Orchestrating... <span>...</span>";
  setAgentStates([]);
  try {
    const response = await fetch("/api/generate", {
      method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(lastProfile)
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "Could not generate a plan.");
    currentPlan = data.plan;
    renderPlan(currentPlan);
    localStorage.setItem("pathpilot-last-plan", JSON.stringify({profile:lastProfile, plan:currentPlan}));
    await animateAgents();
    navigate("roadmap");
    showToast("Learning path generated successfully.");
  } catch (err) {
    showToast(err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = "<span>✦</span> Build my learning path <span>→</span>";
  }
});

$("#sampleBtn").addEventListener("click", () => {
  $("#goal").value = "Become a backend developer with Python";
  $("#level").value = "Beginner";
  $("#hours").value = 8;
  $("#interests").value = "Python, APIs, SQL, databases";
  $("#duration").value = "8";
  $("#style").value = "Project based";
  $("#constraints").value = "Prefer free or low-cost resources. I want a portfolio project at the end.";
  showToast("Sample learner profile loaded.");
});

$("#exportBtn").addEventListener("click", () => {
  if (!currentPlan) return showToast("Generate a learning path first.");
  const blob = new Blob([JSON.stringify({profile:lastProfile, plan:currentPlan}, null, 2)], {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "pathpilot-learning-plan.json";
  a.click();
  URL.revokeObjectURL(a.href);
  showToast("Plan exported as JSON.");
});

const saved = localStorage.getItem("pathpilot-last-plan");
if (saved) {
  try {
    const parsed = JSON.parse(saved);
    lastProfile = parsed.profile;
    currentPlan = parsed.plan;
    renderPlan(currentPlan);
  } catch {}
}
