// Loads the read-only SnipRiot status. Shows a friendly message until the data folder exists.
(async function () {
  const box = document.getElementById("status");
  try {
    const res = await fetch("/api/status", { credentials: "same-origin" });
    if (res.status === 401) { window.location.href = "/login"; return; }
    const data = await res.json();
    if (!data.available) { box.textContent = data.detail; return; }
    box.innerHTML = "";
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(data.status, null, 2);
    box.appendChild(pre);
  } catch (err) {
    box.textContent = "Could not reach the server: " + err;
  }
})();
