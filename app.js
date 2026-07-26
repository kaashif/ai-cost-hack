const results = {
  baseline: {
    pass: true,
    quality: "100",
    cost: "$0.038",
    calls: "1",
    finding: "Missing owner check",
    note: "Accurate, but sends all context to an expensive model.",
  },
  cheap: {
    pass: false,
    quality: "45",
    cost: "$0.002",
    calls: "1",
    finding: "No issue found",
    note: "Very cheap, but it misses the cross-tenant deletion. Ineligible.",
  },
  smart: {
    pass: true,
    quality: "94",
    cost: "$0.009",
    calls: "1",
    finding: "Missing owner check",
    note: "Selects the relevant context and routes to a smaller capable model.",
  },
};

const status = document.querySelector("#result-status");
const quality = document.querySelector("#result-quality");
const cost = document.querySelector("#result-cost");
const calls = document.querySelector("#result-calls");
const finding = document.querySelector("#result-finding");
const note = document.querySelector("#result-note");

document.querySelectorAll("[data-strategy]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-strategy]").forEach((candidate) => {
      candidate.setAttribute("aria-selected", String(candidate === button));
    });
    const result = results[button.dataset.strategy];
    status.textContent = `QUALITY GATE: ${result.pass ? "PASS" : "FAIL"}`;
    status.className = `status ${result.pass ? "pass" : "fail"}`;
    quality.textContent = result.quality;
    cost.textContent = result.cost;
    calls.textContent = result.calls;
    finding.textContent = result.finding;
    note.textContent = result.note;
  });
});

const copyButton = document.querySelector(".copy-button");
copyButton.addEventListener("click", async () => {
  const text = document.querySelector(`#${copyButton.dataset.copyTarget}`).innerText;
  const copyStatus = document.querySelector("#copy-status");
  try {
    await navigator.clipboard.writeText(text);
    copyStatus.textContent = "COPIED TO CLIPBOARD";
  } catch {
    copyStatus.textContent = "SELECT THE COMMANDS AND COPY MANUALLY";
  }
});

