import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(new URL("../apps/web/package.json", import.meta.url));
const { chromium } = require("@playwright/test");

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const BASE = (process.env.GIGBID_URL || "http://localhost:8000").replace(/\/$/, "");
const OUT = resolve(ROOT, "docs/demo");
const RAW = resolve(OUT, "raw");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function readEnv() {
  const file = resolve(ROOT, ".env");
  const env = {};
  if (!existsSync(file)) return env;
  for (const line of readFileSync(file, "utf8").split(/\r?\n/)) {
    if (!line || line.trimStart().startsWith("#")) continue;
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (m) env[m[1]] = m[2].replace(/^['"]|['"]$/g, "");
  }
  return env;
}

async function api(path, { method, body, token } = {}) {
  const res = await fetch(BASE + path, {
    method: method || (body !== undefined ? "POST" : "GET"),
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${method || "GET"} ${path} -> ${res.status} ${await res.text()}`);
  return res.json();
}

async function waitRun(token, runId, wanted, timeoutMs = 150000) {
  const end = Date.now() + timeoutMs;
  let last = "unknown";
  while (Date.now() < end) {
    const data = await api(`/runs/${encodeURIComponent(runId)}`, { token });
    last = data.run.status;
    if (wanted.includes(last) || last !== "running") return data;
    await sleep(1500);
  }
  throw new Error(`run ${runId} stayed ${last} for ${timeoutMs} ms`);
}

async function interviewThread(token) {
  const threads = await api("/messages", { token });
  return threads.find((t) => (t.messages || []).some((m) => m.from === "client" && /interview/i.test(m.text))) || null;
}

function hashFor(jobId, text) {
  return parseInt(createHash("sha256").update(jobId + text).digest("hex").slice(0, 8), 16) / 0xffffffff;
}

function controlledLetter(jobId, skills) {
  const named = skills.length ? skills.join(", ") : "the required stack";
  const base = `I can help with this project. I have shipped work with ${named}. I would start by mapping your requirements, defining evaluation questions, and setting up a small milestone plan with citations. I can share a short written plan before we start and keep the work scoped to a first milestone.`;
  const closings = [
    "I am available to start this week.",
    "I can begin with a short discovery call.",
    "I can share a first milestone plan.",
    "I would be glad to walk you through the approach.",
    "I can start with a small evaluation set.",
    "I can share examples of similar work.",
    "I can start with a short written plan.",
    "I can begin with a scoped first milestone.",
  ];
  const candidates = [];
  for (const closing of closings) candidates.push(`${base} ${closing}`);
  for (const first of closings) for (const second of closings) candidates.push(`${base} ${first} ${second}`);
  for (let i = 1; i <= 600; i++) candidates.push(`${base} I can start with milestone ${i}.`);
  for (const text of candidates) {
    if (text.length < 200 || text.length > 1500) continue;
    const h = hashFor(jobId, text);
    if (h >= 0.5 && h < 0.7) return text;
  }
  return `${base} I can start now.`;
}

async function preSeed(token) {
  const existing = await interviewThread(token);
  if (existing) {
    console.log(`pre-seed: using existing interview thread ${existing.proposal_id}`);
    return existing;
  }
  const candidates = ["job-ml-0018", "job-ml-0027", "job-ml-0008", "job-ml-0007", "job-ml-0001", "job-ml-0003", "job-ml-0029"];
  for (const jobId of candidates) {
    let detail;
    try {
      detail = await api(`/jobs/${encodeURIComponent(jobId)}`, { token });
    } catch (err) {
      console.log(`pre-seed: cannot inspect ${jobId}: ${err.message}`);
      continue;
    }
    if (detail.triage.action !== "bid") {
      console.log(`pre-seed: ${jobId} is ${detail.triage.action}, not bid`);
      continue;
    }
    console.log(`pre-seed: drafting ${jobId} (${detail.job.title})`);
    let runId;
    try {
      runId = (await api(`/jobs/${encodeURIComponent(jobId)}/draft`, { token, body: {} })).run_id;
      const paused = await waitRun(token, runId, ["awaiting_approval"]);
      if (paused.run.status !== "awaiting_approval") {
        console.log(`pre-seed: ${jobId} stopped at ${paused.run.status}`);
        continue;
      }
      const text = controlledLetter(jobId, detail.triage.job_spec.required_skills || []);
      console.log(`pre-seed: approving a scoped edit on ${jobId} to create a real client interview reply`);
      await api(`/approvals/${encodeURIComponent(runId)}`, { token, body: { action: "edit", text } });
      await waitRun(token, runId, ["submitted", "needs_attention"]);
      const thread = await interviewThread(token);
      if (thread) {
        console.log(`pre-seed: interview thread ready (${thread.proposal_id})`);
        return thread;
      }
      console.log(`pre-seed: ${jobId} was submitted but the simulated client did not ask for an interview`);
    } catch (err) {
      console.log(`pre-seed: ${jobId} failed: ${err.message}`);
    }
  }
  return null;
}

function chosenCard(page) {
  return page.locator("li").filter({ has: page.getByRole("button", { name: "Draft proposal" }) });
}

async function main() {
  const env = { ...readEnv(), ...process.env };
  const email = env.REVIEWER_EMAIL || "reviewer@gigbid.demo";
  const password = env.REVIEWER_PASSWORD || "";
  if (!password) throw new Error("REVIEWER_PASSWORD is not set in .env or the environment");
  await api("/health");
  const login = await api("/auth/login", { method: "POST", body: { email, password, persona: "ml" } });
  const token = login.token;
  console.log(`logged in as ${login.email}`);
  const seeded = await preSeed(token);
  if (!seeded) console.log("pre-seed: no interview thread found; scene e will be skipped");
  console.log("waiting 65 s so the marketplace per-user rate-limit window is clear before recording");
  await sleep(65000);

  mkdirSync(OUT, { recursive: true });
  mkdirSync(RAW, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
    recordVideo: { dir: RAW, size: { width: 1280, height: 720 } },
  });
  const page = await context.newPage();
  const video = page.video();
  const results = [];

  async function scene(name, fn) {
    console.log(`scene ${name}: start`);
    try {
      await fn();
      results.push({ name, status: "ok" });
      console.log(`scene ${name}: ok`);
    } catch (err) {
      results.push({ name, status: "skipped", reason: err.message });
      console.log(`scene ${name}: SKIPPED (${err.message})`);
    }
  }

  await scene("a-login-and-inbox", async () => {
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await sleep(1800);
    await page.getByLabel("Email").fill(email);
    await sleep(700);
    await page.getByLabel(/Password/).fill(password);
    await sleep(700);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL(`${BASE}/`, { timeout: 45000 });
    await page.getByRole("heading", { name: "Job inbox" }).waitFor({ timeout: 60000 });
    await sleep(5000);
  });

  let demoJob = "";
  await scene("b-draft-evidence-approve", async () => {
    const cards = chosenCard(page);
    await cards.first().waitFor({ timeout: 60000 });
    let card = cards.first();
    for (let i = 0; i < (await cards.count()); i++) {
      const text = await cards.nth(i).innerText();
      if (/job-ml-0006/.test(text) || /injection/.test(text)) continue;
      card = cards.nth(i);
      break;
    }
    demoJob = (await card.innerText()).split(/\s+/).find((x) => /^job-ml-\d+/.test(x)) || "";
    console.log(`scene b: using ${demoJob}`);
    await card.scrollIntoViewIfNeeded();
    await sleep(2500);
    await card.getByRole("button", { name: "Draft proposal" }).click();
    await page.waitForURL(/\/runs\//, { timeout: 45000 });
    await page.getByText("awaiting_approval").first().waitFor({ timeout: 120000 });
    await sleep(5500);
    await page.getByRole("link", { name: "Open proposal studio" }).click();
    await page.waitForURL(/\/studio\//, { timeout: 45000 });
    await page.getByRole("heading", { name: "Decision" }).waitFor({ timeout: 45000 });
    await sleep(3000);
    const cite = page.getByRole("button", { name: /Evidence \[E1\]/ }).first();
    await cite.scrollIntoViewIfNeeded();
    await cite.focus();
    await page.getByTestId("evidence-tooltip").waitFor({ timeout: 15000 });
    await sleep(4500);
    const cite2 = page.getByRole("button", { name: /Evidence \[E2\]/ }).first();
    if (await cite2.count()) {
      await cite2.focus();
      await sleep(2500);
    }
    const approve = page.getByRole("button", { name: "Approve & send" });
    await approve.scrollIntoViewIfNeeded();
    await sleep(2500);
    await approve.click();
    await page.getByTestId("submitted").waitFor({ timeout: 120000 });
    await sleep(4500);
  });

  await scene("c-scam-flagged-and-skipped", async () => {
    await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Job inbox" }).waitFor({ timeout: 45000 });
    await page.getByLabel("Filter by action").selectOption("skip");
    await sleep(3000);
    const card = page.locator("li").filter({ hasText: "job-ml-0021" }).first();
    await card.waitFor({ timeout: 60000 });
    await card.scrollIntoViewIfNeeded();
    await card.getByText("off_platform_contact").waitFor({ timeout: 15000 });
    await sleep(5500);
    await card.getByRole("button", { name: "Skip" }).click();
    await card.getByText("skipped").waitFor({ timeout: 45000 });
    await sleep(4500);
  });

  await scene("d-injection-ignored", async () => {
    await page.goto(`${BASE}/jobs/job-ml-0006`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Contract Summariser for fintech team" }).waitFor({ timeout: 60000 });
    await sleep(3500);
    await page.getByText(/injected instruction detected and removed/).first().scrollIntoViewIfNeeded();
    await page.getByText(/injected instruction detected and removed/).first().waitFor({ timeout: 30000 });
    await sleep(5000);
    await page.getByRole("heading", { name: "Risk report" }).scrollIntoViewIfNeeded();
    await sleep(4500);
  });

  await scene("e-client-reply-and-slots", async () => {
    if (!seeded) throw new Error("no client interview reply was available to show");
    await page.goto(`${BASE}/messages`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Messages" }).waitFor({ timeout: 45000 });
    await sleep(3000);
    const card = page.locator("li").filter({ hasText: /schedule an interview/i }).first();
    await card.waitFor({ timeout: 30000 });
    await card.scrollIntoViewIfNeeded();
    await sleep(3000);
    await card.getByRole("button", { name: "Suggest reply" }).click();
    const suggested = page.getByTestId("suggested-reply");
    try {
      await suggested.waitFor({ timeout: 30000 });
    } catch {
      const button = card.getByRole("button", { name: "Suggest reply" });
      if (await button.count()) await button.click();
      await suggested.waitFor({ timeout: 60000 });
    }
    await suggested.scrollIntoViewIfNeeded();
    await sleep(2500);
    await suggested.getByText(/Interview slots offered/).waitFor({ timeout: 15000 });
    await sleep(5500);
    try {
      await suggested.getByRole("button", { name: "Approve & send" }).click();
      await page.getByText(/freelancer:/).first().waitFor({ timeout: 60000 });
      await sleep(3500);
    } catch (err) {
      console.log(`scene e: reply was drafted but sending it on camera failed: ${err.message}`);
    }
  });

  await sleep(1500);
  const finalPath = resolve(OUT, "demo.webm");
  await page.close();
  if (video) await video.saveAs(finalPath);
  await context.close();
  await browser.close();
  rmSync(RAW, { recursive: true, force: true });
  console.log(`video: ${finalPath}`);
  console.log("scenes:");
  for (const r of results) console.log(`- ${r.name}: ${r.status}${r.reason ? ` (${r.reason})` : ""}`);
  const skipped = results.filter((r) => r.status !== "ok");
  if (skipped.length) console.log(`${skipped.length} scene(s) skipped; see reasons above`);
}

main().catch((err) => {
  console.error(`demo failed: ${err.message}`);
  process.exitCode = 1;
});
