/**
 * SCR Platform Excel Add-in — Task Pane logic.
 *
 * Runs inside the Office.js task pane iframe.  Communicates with the SCR API
 * via the api-client module (which reads the key from roaming settings) and
 * inserts Excel formulas into the active worksheet.
 */

import { testConnection as apiTestConnection } from "./api-client";

const SCR_API_URL =
  (process.env.SCR_API_URL as string) || "https://api.scrplatform.com";

// ── Office initialisation ──────────────────────────────────────────────────

Office.onReady(() => {
  loadSavedApiKey();
  setupEventListeners();
});

// ── Helpers ────────────────────────────────────────────────────────────────

function loadSavedApiKey(): void {
  const saved: string | undefined =
    Office.context.roamingSettings.get("scrApiKey");
  if (saved) {
    const input = document.getElementById("apiKey") as HTMLInputElement | null;
    if (input) input.value = saved;
    updateStatus("API key loaded from settings.", "info");
  }
}

function setupEventListeners(): void {
  document.getElementById("saveKey")?.addEventListener("click", saveApiKey);
  document
    .getElementById("testConnection")
    ?.addEventListener("click", runTestConnection);
  document
    .getElementById("insertSignalScore")
    ?.addEventListener("click", () => insertFormula("SCR_SIGNAL_SCORE"));
  document
    .getElementById("insertValuation")
    ?.addEventListener("click", () => insertFormula("SCR_VALUATION"));
  document
    .getElementById("insertPortfolioNav")
    ?.addEventListener("click", () => insertPortfolioFormula("nav"));
  document
    .getElementById("insertPortfolioIrr")
    ?.addEventListener("click", () => insertPortfolioFormula("irr"));
}

// ── API key management ─────────────────────────────────────────────────────

async function saveApiKey(): Promise<void> {
  const input = document.getElementById("apiKey") as HTMLInputElement | null;
  const key = input?.value?.trim() ?? "";

  if (!key) {
    updateStatus("Please enter an API key before saving.", "error");
    return;
  }

  Office.context.roamingSettings.set("scrApiKey", key);
  await new Promise<void>((resolve, reject) =>
    Office.context.roamingSettings.saveAsync((result) =>
      result.status === Office.AsyncResultStatus.Succeeded
        ? resolve()
        : reject(result.error)
    )
  );

  updateStatus("API key saved to your Office settings.", "ok");
}

// ── Connection test ────────────────────────────────────────────────────────

async function runTestConnection(): Promise<void> {
  const input = document.getElementById("apiKey") as HTMLInputElement | null;
  const key = input?.value?.trim() ?? "";

  if (!key) {
    updateStatus("Enter an API key first.", "error");
    setConnectionPill(false);
    return;
  }

  updateStatus("Testing connection...", "info");

  const ok = await apiTestConnection(key);
  if (ok) {
    updateStatus("Connected successfully to SCR Platform.", "ok");
    setConnectionPill(true);
  } else {
    updateStatus(
      "Connection failed. Check that your API key is correct and active.",
      "error"
    );
    setConnectionPill(false);
  }
}

// ── Formula insertion ──────────────────────────────────────────────────────

async function insertFormula(functionName: string): Promise<void> {
  const projectInput = document.getElementById(
    "projectSelect"
  ) as HTMLInputElement | null;
  const projectId = projectInput?.value?.trim() ?? "";

  if (!projectId) {
    updateStatus("Enter a Project ID before inserting a formula.", "error");
    return;
  }

  const formula =
    functionName === "SCR_SIGNAL_SCORE"
      ? `=SCR.SIGNAL_SCORE("${projectId}")`
      : `=SCR.VALUATION("${projectId}","enterprise_value")`;

  await insertIntoActiveCell(formula);
}

async function insertPortfolioFormula(metric: string): Promise<void> {
  const portfolioInput = document.getElementById(
    "portfolioInput"
  ) as HTMLInputElement | null;
  const portfolioId = portfolioInput?.value?.trim() ?? "";

  if (!portfolioId) {
    updateStatus("Enter a Portfolio ID before inserting a formula.", "error");
    return;
  }

  const formula = `=SCR.PORTFOLIO("${portfolioId}","${metric}")`;
  await insertIntoActiveCell(formula);
}

async function insertIntoActiveCell(formula: string): Promise<void> {
  try {
    await Excel.run(async (context) => {
      const cell = context.workbook.getActiveCell();
      cell.formulas = [[formula]];
      await context.sync();
    });
    updateStatus(`Inserted: ${formula}`, "ok");
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    updateStatus(`Failed to insert formula: ${msg}`, "error");
  }
}

// ── UI helpers ─────────────────────────────────────────────────────────────

function updateStatus(
  msg: string,
  kind: "ok" | "error" | "info" = "info"
): void {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = msg;
  el.className = `visible ${kind}`;
}

function setConnectionPill(connected: boolean): void {
  const pill = document.getElementById("connectionPill");
  const label = document.getElementById("connectionLabel");
  if (!pill || !label) return;

  pill.className = `connection-pill ${connected ? "connected" : "error"}`;
  label.textContent = connected ? "Connected" : "Disconnected";
}
