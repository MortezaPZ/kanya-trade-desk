const $ = (id) => document.getElementById(id);
const errorBox = $("error");

async function getJson(url, options) {
  errorBox.textContent = "";
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function trendClass(t) {
  if (t === "up" || t === "aligned_up") return "up";
  if (t === "down" || t === "aligned_down") return "down";
  return "";
}

async function loadAccount() {
  try {
    const data = await getJson("/api/account");
    const a = data.account;
    $("account-chip").textContent = `${a.login} | ${a.equity} ${a.currency} | فقط‌خواندنی`;
    const rows = (data.positions || [])
      .map(
        (p) => `<tr><td>${p.symbol}</td><td>${p.type}</td><td>${p.volume}</td><td>${p.profit}</td></tr>`
      )
      .join("");
    $("positions").innerHTML = `<h3>معاملات باز</h3>
      <table><thead><tr><th>نماد</th><th>جهت</th><th>حجم</th><th>سود</th></tr></thead>
      <tbody>${rows || "<tr><td colspan=4>معامله بازی نیست</td></tr>"}</tbody></table>`;
  } catch (err) {
    $("account-chip").textContent = "ترمینال در دسترس نیست";
    errorBox.textContent = err.message;
  }
}

$("load").onclick = async () => {
  try {
    const symbol = $("symbol").value.trim();
    const data = await getJson(`/api/market/${encodeURIComponent(symbol)}`);
    $("tick").innerHTML = `<strong>${data.symbol}</strong> bid ${data.tick.bid} / ask ${data.tick.ask}
      — هم‌راستایی: <span class="${trendClass(data.alignment)}">${data.alignment}</span>`;
    $("frames").innerHTML = data.frames
      .map(
        (f) => `<article class="frame">
          <h4>${f.timeframe}</h4>
          <p class="${trendClass(f.trend)}">روند ${f.trend}</p>
          <p>ساختار ${f.structure}</p>
          <p>الگو ${(f.patterns || []).join("، ") || "—"}</p>
        </article>`
      )
      .join("");
  } catch (err) {
    errorBox.textContent = err.message;
  }
};

$("brief").onclick = async () => {
  try {
    const symbol = $("symbol").value.trim();
    const data = await getJson("/api/briefing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol }),
    });
    const b = data.briefing;
    $("briefing").innerHTML = `<h3>مشاوره</h3>
      <p>${b.market_fa || ""}</p>
      <p><strong>ریسک:</strong> ${b.risk_fa || ""}</p>
      <p><strong>زیر نظر:</strong> ${b.watch_fa || ""}</p>
      <p>${b.fit_fa || ""}</p>
      <p class="muted">منبع: ${b.source || ""} | حجم پیشنهادی فقط راهنماست: ${data.size_hint.suggested_lots}</p>`;
  } catch (err) {
    errorBox.textContent = err.message;
  }
};

loadAccount();
