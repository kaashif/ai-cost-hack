const body = document.querySelector("#leaderboard-body");
const updated = document.querySelector("#leaderboard-updated");

function cell(text, className) {
  const element = document.createElement("td");
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function showEmpty(message) {
  body.replaceChildren();
  const row = document.createElement("tr");
  const empty = cell(message, "leaderboard-empty");
  empty.colSpan = 4;
  row.append(empty);
  body.append(row);
}

fetch("leaderboard.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error("leaderboard unavailable");
    return response.json();
  })
  .then((data) => {
    if (!Array.isArray(data.entries) || data.entries.length === 0) {
      showEmpty("Results will appear here after judging.");
      return;
    }

    body.replaceChildren();
    for (const entry of data.entries) {
      const row = document.createElement("tr");
      row.append(cell(`#${entry.rank}`, "leaderboard-rank"));

      const teamCell = document.createElement("td");
      const link = document.createElement("a");
      link.className = "leaderboard-team";
      link.href = entry.repo_url;
      link.textContent = entry.team_name;
      link.rel = "noopener noreferrer";
      link.target = "_blank";
      teamCell.append(link);
      row.append(teamCell);

      row.append(cell(Number(entry.quality_score).toFixed(1), ""));
      row.append(cell(`$${Number(entry.cost_usd).toFixed(4)}`, "leaderboard-cost"));
      body.append(row);
    }

    if (data.generated_at) {
      const timestamp = new Date(data.generated_at);
      updated.textContent = `Updated ${timestamp.toLocaleString()}`;
    }
  })
  .catch(() => {
    showEmpty("Leaderboard is temporarily unavailable.");
    updated.textContent = "Could not load results";
  });
