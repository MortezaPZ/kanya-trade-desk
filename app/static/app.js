const $ = (id) => document.getElementById(id);
const errorBox = $("error");
const ALIGN = {
  up: "صعودی",
  down: "نزولی",
  mixed: "مخلوط",
  range: "رنج",
  unclear: "نامشخص",
  aligned_up: "هم‌جهت صعودی",
  aligned_down: "هم‌جهت نزولی",
  conflict: "تعارض تایم‌فریم",
};
const GROUP = { metals: "فلزات", energy: "انرژی", index: "شاخص", crypto: "کریپتو", fx: "ارز", other: "سایر" };
const PATTERN = {
  doji: "دوجی",
  pin_bull: "پین صعودی",
  pin_bear: "پین نزولی",
  engulf_bull: "اینگالف صعودی",
  engulf_bear: "اینگالف نزولی",
};

function element(tag, value = "", className = "") {
  const el = document.createElement(tag);
  el.textContent = value == null ? "" : String(value);
  if (className) el.className = className;
  return el;
}

function trendClass(t) {
  if (t === "up" || t === "aligned_up") return "up";
  if (t === "down" || t === "aligned_down") return "down";
  return "";
}

function fa(t) {
  return ALIGN[t] || t || "—";
}

async function getJson(url, options) {
  errorBox.textContent = "";
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function setSymbol(name) {
  $("symbol").value = name;
}

function makePositionsTable(positions) {
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headerRow = document.createElement("tr");
  ["نماد", "جهت", "حجم", "حد ضرر", "سود"].forEach((label) => headerRow.append(element("th", label)));
  head.append(headerRow);
  const body = document.createElement("tbody");
  if (!positions.length) {
    const row = document.createElement("tr");
    const cell = element("td", "معامله بازی نیست");
    cell.colSpan = 5;
    row.append(cell);
    body.append(row);
  } else {
    positions.forEach((position) => {
      const row = document.createElement("tr");
      [position.symbol, position.type, position.volume, position.sl || "—", position.profit].forEach((value) => {
        row.append(element("td", value));
      });
      body.append(row);
    });
  }
  table.append(head, body);
  return table;
}

function renderFrames(frames) {
  const cards = (frames || []).map((frame) => {
    const card = element("article", "", "frame");
    card.append(element("h4", frame.timeframe));
    card.append(element("p", `روند ${fa(frame.trend)}`, trendClass(frame.trend)));
    card.append(element("p", `ساختار ${fa(frame.structure)}`));
    const patterns = (frame.patterns || []).map((pattern) => PATTERN[pattern] || pattern).join("، ");
    card.append(element("p", patterns || "بدون الگو", "small"));
    return card;
  });
  $("frames").replaceChildren(...cards);
}

async function refreshStatus() {
  const st = await getJson("/api/status");
  $("engine-chip").textContent = st.engine_configured
    ? `تحلیل AI: آمادهٔ درخواست (${st.engine_protocol || "API"})`
    : "تحلیل AI: API لازم است";
  const privacy = $("privacy-note");
  if (st.engine_configured) {
    privacy.textContent = "درخواست تحلیل فقط نماد، قیمت، شاخص‌های فنی و حداکثر ۴۰ کندل بسته‌شده از هر تایم‌فریم را می‌فرستد؛ موجودی، معاملات باز، حجم محاسبه‌شده و یادداشت شما محلی می‌مانند. اتصال API با اولین درخواست تحلیل سنجیده می‌شود.";
    privacy.classList.remove("hidden");
  } else {
    privacy.textContent = `${st.engine_message_fa || "تنظیمات API کامل نیست."} تا آن زمان تحلیل AI انجام نمی‌شود و قواعد محلی را نباید تحلیل AI تلقی کرد.`;
    privacy.classList.remove("hidden");
  }
  if (!st.connected) {
    $("account-chip").textContent = "ترمینال وصل نیست";
    $("banner").classList.remove("hidden");
    $("banner").textContent = "متاتریدر ۵ را روی همین سیستم باز و لاگین کنید؛ صفحه اتصال را دوباره بررسی می‌کند. دادهٔ ساختگی نشان داده نمی‌شود.";
    ["exposure", "watchlist", "tick", "frames", "briefing", "positions", "review-box"].forEach((id) => {
      $(id).replaceChildren();
    });
    return st;
  }
  $("banner").classList.add("hidden");
  const account = st.account;
  $("account-chip").textContent = `حساب متصل | اکوئیتی ${account.equity} ${account.currency} | فقط‌خواندنی`;
  const exposure = st.exposure || {};
  const exposureBox = $("exposure");
  exposureBox.replaceChildren(
    element("h3", "ریسک حساب"),
    element("p", `موجودی ${exposure.balance} — اکوئیتی ${exposure.equity} — شناور ${exposure.floating_pnl} (${exposure.floating_pct || 0}٪) — حاشیه ${exposure.used_margin_pct}٪ — باز ${exposure.open_count}`),
  );
  const positionsBox = $("positions");
  positionsBox.replaceChildren(element("h3", "معاملات باز"), makePositionsTable(st.positions || []));
  return st;
}

async function refreshWatchlist() {
  try {
    const data = await getJson("/api/watchlist");
    const cards = data.cards.map((cardData) => {
      const card = element("article", "", "frame");
      card.dataset.symbol = cardData.symbol;
      card.append(element("h4", cardData.symbol));
      card.append(element("p", GROUP[cardData.group] || "", "small"));
      card.append(element("p", fa(cardData.alignment), trendClass(cardData.alignment)));
      card.append(element("p", cardData.tick ? cardData.tick.bid : "—"));
      if (cardData.error) card.append(element("p", cardData.error, "small"));
      card.onclick = () => {
        setSymbol(cardData.symbol);
        $("load").click();
      };
      return card;
    });
    $("watchlist").replaceChildren(...cards);
    return true;
  } catch (err) {
    errorBox.textContent = err.message;
    return false;
  }
}

$("watch").onclick = refreshWatchlist;

$("load").onclick = async () => {
  try {
    const symbol = $("symbol").value.trim();
    const data = await getJson(`/api/market/${encodeURIComponent(symbol)}`);
    const tick = $("tick");
    tick.replaceChildren(
      element("strong", data.symbol),
      element("span", ` bid ${data.tick.bid} / ask ${data.tick.ask} — ${fa(data.alignment)} `),
      element("span", `ATR حدود ${Number(data.atr).toFixed(4)}`, "small"),
    );
    renderFrames(data.frames);
  } catch (err) {
    errorBox.textContent = err.message;
  }
};

$("brief").onclick = async () => {
  try {
    const body = {
      symbol: $("symbol").value.trim(),
      entry_note: $("entry-note").value.trim(),
      save: true,
    };
    const stopRaw = $("stop").value;
    if (stopRaw) body.stop_distance = Number(stopRaw);
    const data = await getJson("/api/briefing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const brief = data.briefing;
    const hint = data.size_hint;
    const box = $("briefing");
    if (brief.source !== "engine") {
      $("engine-chip").textContent = `تحلیل AI: غیرفعال — ${brief.engine_message_fa || "پاسخ معتبر دریافت نشد"}`;
    } else {
      $("engine-chip").textContent = `تحلیل AI: پاسخ دریافت شد (${brief.protocol || "API"})`;
    }
    const content = [
      element("h3", brief.source === "engine" ? `تحلیل AI پیش از ورود (${brief.protocol || "API"})` : "مشاوره پیش از ورود — تحلیل AI فعال نیست"),
      element("p", brief.market_fa || ""),
      element("p", `سناریوهای مشروط: ${brief.scenario_fa || "—"}`),
      element("p", `ریسک: ${brief.risk_fa || ""}`),
      element("p", `زیر نظر: ${brief.watch_fa || ""}`),
      element("p", brief.fit_fa || ""),
      element("p", `حجم پیشنهادی ${hint.suggested_lots} لات برای ریسک ${hint.risk_pct}٪ — محاسبه محلی است و سفارش ارسال نمی‌شود. ${brief.source === "engine" ? "تفسیر بازار از API است." : `وضعیت API: ${brief.engine_message_fa || "پاسخ قابل‌استفاده دریافت نشد."}`}`, "small"),
    ];
    if (hint.minimum_lot_exceeds_risk) {
      content.push(element("p", "ریسک مجاز از حداقل حجم بروکر کمتر است؛ حجم پیشنهادی صفر شده است.", "error"));
    }
    if (hint.volume_spec_missing) {
      content.push(element("p", "مشخصات حداقل حجم یا گام حجم این نماد از بروکر دریافت نشد؛ حجم پیشنهادی قابل محاسبه نیست.", "error"));
    }
    box.replaceChildren(...content);
    renderFrames(data.frames);
  } catch (err) {
    errorBox.textContent = err.message;
  }
};

$("review").onclick = async () => {
  try {
    const symbol = $("symbol").value.trim();
    const data = await getJson(`/api/review/${encodeURIComponent(symbol)}`);
    const deal = data.last_deal;
    const box = $("review-box");
    const content = [element("h3", "مرور بعد از معامله"), element("p", data.note_fa || "")];
    if (data.entry_note) content.push(element("p", `دلیل ثبت‌شده: ${data.entry_note}`));
    content.push(element("p", deal
      ? `آخرین معامله: حجم ${deal.volume}، قیمت ${deal.price}، نتیجه ${deal.profit}`
      : "معاملهٔ اخیری برای این نماد در تاریخچه نیست.", "small"));
    box.replaceChildren(...content);
  } catch (err) {
    errorBox.textContent = err.message;
  }
};

let searchTimer;
$("search").oninput = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    try {
      const query = $("search").value.trim();
      const data = await getJson(`/api/symbols?q=${encodeURIComponent(query)}`);
      const options = (data.matches || []).map((symbol) => {
        const option = document.createElement("option");
        option.value = symbol.name;
        option.textContent = symbol.description || "";
        return option;
      });
      $("symbol-list").replaceChildren(...options);
    } catch (err) {
      errorBox.textContent = err.message;
    }
  }, 250);
};

async function refreshDashboard() {
  let nextRefreshMs = 12000;
  try {
    const st = await refreshStatus();
    if (st.connected) {
      await refreshWatchlist();
      nextRefreshMs = 30000;
    }
  } catch (err) {
    errorBox.textContent = err.message;
  }
  window.setTimeout(refreshDashboard, nextRefreshMs);
}

refreshDashboard();
