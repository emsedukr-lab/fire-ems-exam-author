import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";

export type WorkspaceStatus = "empty" | "needs_review" | "approved";

export interface WorkspaceCounts {
  sourceDocuments: number;
  examItems: number;
  reviewEntries: number;
  variantItems: number;
  distractorRecords: number;
  checklistPassed: number;
  checklistTotal: number;
}

export interface WorkspaceOutputMap {
  pastAnalysis: string;
  distractorMandalart: string;
  summaryBook: string;
  mockExam: string;
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  status: WorkspaceStatus;
  counts: WorkspaceCounts;
}

export interface WorkspaceSnapshot extends WorkspaceSummary {
  rootPath: string;
  manifest: Record<string, unknown>;
  bank: Record<string, unknown>;
  reviewQueue: Array<Record<string, unknown>>;
  outputs: WorkspaceOutputMap;
}

const WEB_ROOT = process.cwd();
const REPO_ROOT = path.resolve(WEB_ROOT, "..");
const WORKSPACES_ROOT = path.join(REPO_ROOT, "workspaces");
const SCRIPTS_ROOT = path.join(REPO_ROOT, "scripts");
const PYTHON_BIN = process.env.FIRE_EMS_PYTHON ?? "python3";

function slugify(value: string) {
  return value
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^a-z0-9가-힣]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
}

function stripExtension(filename: string) {
  const ext = path.extname(filename);
  return ext ? filename.slice(0, -ext.length) : filename;
}

function sanitizeFilename(filename: string) {
  return filename.replace(/[^\w.\-가-힣]+/g, "-");
}

function currentTimestamp() {
  return new Date().toISOString();
}

async function ensureWorkspacesRoot() {
  await fs.mkdir(WORKSPACES_ROOT, { recursive: true });
}

async function fileExists(targetPath: string) {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function readJson<T>(targetPath: string, fallback: T): Promise<T> {
  try {
    const content = await fs.readFile(targetPath, "utf-8");
    return JSON.parse(content) as T;
  } catch {
    return fallback;
  }
}

async function readText(targetPath: string) {
  try {
    return await fs.readFile(targetPath, "utf-8");
  } catch {
    return "";
  }
}

async function runPythonScript(scriptName: string, args: string[]) {
  const scriptPath = path.join(SCRIPTS_ROOT, scriptName);
  return new Promise<{ stdout: string; stderr: string }>((resolve, reject) => {
    const child = spawn(PYTHON_BIN, [scriptPath, ...args], {
      cwd: REPO_ROOT,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"]
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });

    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
        return;
      }
      reject(new Error(stderr || stdout || `${scriptName} exited with code ${code}`));
    });
  });
}

function deriveStatus(examItems: number, reviewEntries: number): WorkspaceStatus {
  if (examItems === 0) {
    return "empty";
  }
  if (reviewEntries > 0) {
    return "needs_review";
  }
  return "approved";
}

function deriveCounts(bank: Record<string, unknown>, manifest: Record<string, unknown>, reviewQueue: Array<Record<string, unknown>>): WorkspaceCounts {
  const sourceDocuments = Array.isArray((manifest as { source_documents?: unknown[] }).source_documents)
    ? ((manifest as { source_documents?: unknown[] }).source_documents?.length ?? 0)
    : 0;
  const examItems = Array.isArray((bank as { exam_items?: unknown[] }).exam_items)
    ? ((bank as { exam_items?: unknown[] }).exam_items?.length ?? 0)
    : 0;
  const itemMandalarts = Array.isArray((bank as { item_mandalarts?: Array<{ variant_items?: unknown[]; completion_checklist?: Array<{ passed?: boolean }> }> }).item_mandalarts)
    ? ((bank as { item_mandalarts?: Array<{ variant_items?: unknown[]; completion_checklist?: Array<{ passed?: boolean }> }> }).item_mandalarts ?? [])
    : [];
  const variantItems = itemMandalarts.reduce((sum, item) => sum + (item.variant_items?.length ?? 0), 0);
  const checklistTotal = itemMandalarts.length;
  const checklistPassed = itemMandalarts.filter((item) => (item.completion_checklist ?? []).every((check) => check.passed)).length;
  const distractorRecords = Array.isArray((bank as { distractor_mandalarts?: unknown[] }).distractor_mandalarts)
    ? ((bank as { distractor_mandalarts?: unknown[] }).distractor_mandalarts?.length ?? 0)
    : 0;

  return {
    sourceDocuments,
    examItems,
    reviewEntries: reviewQueue.length,
    variantItems,
    distractorRecords,
    checklistPassed,
    checklistTotal
  };
}

async function readWorkspaceMeta(workspaceRoot: string, workspaceId: string) {
  return readJson(path.join(workspaceRoot, "workspace.json"), {
    id: workspaceId,
    name: workspaceId,
    createdAt: currentTimestamp(),
    updatedAt: currentTimestamp()
  });
}

async function readWorkspaceSnapshot(workspaceId: string): Promise<WorkspaceSnapshot | null> {
  const workspaceRoot = path.join(WORKSPACES_ROOT, workspaceId);
  if (!(await fileExists(workspaceRoot))) {
    return null;
  }

  const meta = await readWorkspaceMeta(workspaceRoot, workspaceId);
  const manifest = await readJson<Record<string, unknown>>(path.join(workspaceRoot, "sources", "intake-manifest.json"), {});
  const bank = await readJson<Record<string, unknown>>(path.join(workspaceRoot, "bank", "exam-bank.json"), {});
  const reviewQueue = await readJson<Array<Record<string, unknown>>>(path.join(workspaceRoot, "review", "review-queue.json"), []);
  const outputs: WorkspaceOutputMap = {
    pastAnalysis: await readText(path.join(workspaceRoot, "outputs", "past-analysis.md")),
    distractorMandalart: await readText(path.join(workspaceRoot, "outputs", "distractor-mandalart.md")),
    summaryBook: await readText(path.join(workspaceRoot, "outputs", "summary-book.md")),
    mockExam: await readText(path.join(workspaceRoot, "outputs", "mock-exam-set-01.md"))
  };

  const counts = deriveCounts(bank, manifest, reviewQueue);
  return {
    id: String((meta as { id?: string }).id ?? workspaceId),
    name: String((meta as { name?: string }).name ?? workspaceId),
    createdAt: String((meta as { createdAt?: string }).createdAt ?? currentTimestamp()),
    updatedAt: String((meta as { updatedAt?: string }).updatedAt ?? currentTimestamp()),
    rootPath: workspaceRoot,
    status: deriveStatus(counts.examItems, counts.reviewEntries),
    counts,
    manifest,
    bank,
    reviewQueue,
    outputs
  };
}

export async function listWorkspaces() {
  await ensureWorkspacesRoot();
  const entries = await fs.readdir(WORKSPACES_ROOT, { withFileTypes: true });
  const snapshots = await Promise.all(
    entries
      .filter((entry) => entry.isDirectory())
      .map((entry) => readWorkspaceSnapshot(entry.name))
  );

  return snapshots
    .filter((snapshot): snapshot is WorkspaceSnapshot => snapshot !== null)
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
    .map<WorkspaceSummary>((snapshot) => ({
      id: snapshot.id,
      name: snapshot.name,
      createdAt: snapshot.createdAt,
      updatedAt: snapshot.updatedAt,
      status: snapshot.status,
      counts: snapshot.counts
    }));
}

export async function getWorkspaceSnapshot(workspaceId: string) {
  return readWorkspaceSnapshot(workspaceId);
}

export async function createWorkspaceFromUpload(input: { name?: string; files: File[] }) {
  await ensureWorkspacesRoot();

  const baseName = (input.name && input.name.trim()) || stripExtension(input.files[0]?.name ?? "ems-session");
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const workspaceId = `${timestamp}-${slugify(baseName) || "ems-session"}`;
  const workspaceRoot = path.join(WORKSPACES_ROOT, workspaceId);
  const incomingDir = path.join(workspaceRoot, "incoming");

  await fs.mkdir(incomingDir, { recursive: true });
  await fs.writeFile(
    path.join(workspaceRoot, "workspace.json"),
    JSON.stringify(
      {
        id: workspaceId,
        name: baseName,
        createdAt: currentTimestamp(),
        updatedAt: currentTimestamp()
      },
      null,
      2
    ) + "\n",
    "utf-8"
  );

  await runPythonScript("init_exam_workspace.py", [workspaceRoot]);

  const savedFiles: string[] = [];
  for (const file of input.files) {
    const filename = sanitizeFilename(file.name || `upload-${savedFiles.length + 1}`);
    const destination = path.join(incomingDir, filename);
    const bytes = Buffer.from(await file.arrayBuffer());
    await fs.writeFile(destination, bytes);
    savedFiles.push(destination);
  }

  await runPythonScript("extract_source_text.py", ["--workspace", workspaceRoot, ...savedFiles]);
  await runPythonScript("run_analysis_pipeline.py", ["--workspace", workspaceRoot]);

  const snapshot = await readWorkspaceSnapshot(workspaceId);
  if (!snapshot) {
    throw new Error("Workspace was created but could not be loaded.");
  }
  return snapshot;
}

export async function rerunWorkspace(workspaceId: string) {
  const workspaceRoot = path.join(WORKSPACES_ROOT, workspaceId);
  if (!(await fileExists(workspaceRoot))) {
    throw new Error("Workspace not found.");
  }

  await runPythonScript("run_analysis_pipeline.py", ["--workspace", workspaceRoot]);
  const workspaceMetaPath = path.join(workspaceRoot, "workspace.json");
  const meta = await readWorkspaceMeta(workspaceRoot, workspaceId);
  await fs.writeFile(
    workspaceMetaPath,
    JSON.stringify(
      {
        ...meta,
        updatedAt: currentTimestamp()
      },
      null,
      2
    ) + "\n",
    "utf-8"
  );

  const snapshot = await readWorkspaceSnapshot(workspaceId);
  if (!snapshot) {
    throw new Error("Workspace could not be reloaded.");
  }
  return snapshot;
}
