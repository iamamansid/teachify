/**
 * Teachify VS Code thin client (stub / v0.1).
 *
 * This extension does NOT contain teaching logic. It spawns the Teachify
 * MCP server (../dist/server.js) and shows tasks + the current step in a
 * sidebar webview. All guidance, verification, hints, and quizzes come
 * from the MCP server via stdio JSON-RPC.
 *
 * This is intentionally minimal: the MCP server is the product. The
 * extension is a convenience so learners never leave VS Code.
 */
import * as vscode from "vscode";
import { spawn, ChildProcess } from "node:child_process";
import * as path from "node:path";
import * as fs from "node:fs";

let serverProcess: ChildProcess | undefined;
let panel: vscode.WebviewPanel | undefined;
let requestId = 0;
const pending = new Map<number, (result: unknown) => void>();

function serverPath(context: vscode.ExtensionContext): string {
  // Extension lives in vscode-extension/; server lives in ../dist/server.js
  const fromConfig = vscode.workspace.getConfiguration("teachify").get<string>("serverPath");
  if (fromConfig && fs.existsSync(fromConfig)) return fromConfig;
  return path.join(context.extensionPath, "..", "dist", "server.js");
}

function startServer(context: vscode.ExtensionContext): void {
  if (serverProcess) return;
  const srv = serverPath(context);
  serverProcess = spawn(process.execPath, [srv], { stdio: ["pipe", "pipe", "pipe"] });
  serverProcess.stdout?.on("data", (chunk: Buffer) => {
    for (const line of chunk.toString().split("\n")) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        const resolve = pending.get(msg.id);
        if (resolve) {
          pending.delete(msg.id);
          resolve(msg.result);
        }
      } catch {
        // Non-JSON line: MCP servers log to stderr, so ignore here.
      }
    }
  });
  serverProcess.stderr?.on("data", (d: Buffer) => {
    // Server logs go to the output channel, not the UI.
    output.appendLine(d.toString());
  });
}

let output: vscode.OutputChannel;

async function callTool(tool: string, args: Record<string, unknown>): Promise<unknown> {
  if (!serverProcess?.stdin) throw new Error("Teachify server is not running.");
  const id = ++requestId;
  const req = {
    jsonrpc: "2.0",
    id,
    method: "tools/call",
    params: { name: tool, arguments: args },
  };
  const promise = new Promise<unknown>((resolve) => pending.set(id, resolve));
  serverProcess.stdin.write(JSON.stringify(req) + "\n");
  return promise;
}

function renderWebview(tasksHtml: string): string {
  return `<!DOCTYPE html><html><body style="font-family: sans-serif; padding: 12px;">
  <h2>Teachify — Learn by Doing</h2>
  <p>The AI guides. <strong>You type every line.</strong></p>
  ${tasksHtml}
  <p style="color:#888; font-size:12px;">Teaching logic lives in the Teachify MCP server. This panel is a thin client.</p>
  </body></html>`;
}

export function activate(context: vscode.ExtensionContext): void {
  output = vscode.window.createOutputChannel("Teachify");
  context.subscriptions.push(output);
  startServer(context);

  const showTasks = vscode.commands.registerCommand("teachify.showTasks", async () => {
    try {
      const res = (await callTool("teach_list_tasks", {})) as { content?: Array<{ text?: string }> };
      const parsed = JSON.parse(res?.content?.[0]?.text ?? "{}");
      const tasks = (parsed.tasks ?? []) as Array<{ id: string; title: string; level: string; steps: number }>;
      const html = tasks.length
        ? `<ul>${tasks.map((t) => `<li><b>${t.title}</b> — ${t.level}, ${t.steps} steps <code>${t.id}</code></li>`).join("")}</ul>`
        : "<p>No tasks found. Build the MCP server first: <code>npm run build</code> in the teachify folder.</p>";
      if (!panel) {
        panel = vscode.window.createWebviewPanel("teachify", "Teachify", vscode.ViewColumn.Beside, {});
        panel.onDidDispose(() => (panel = undefined));
      }
      panel.webview.html = renderWebview(html);
      panel.reveal();
    } catch (err) {
      vscode.window.showErrorMessage(`Teachify: could not reach MCP server. Build it first (npm run build). ${err}`);
    }
  });

  const startTeach = vscode.commands.registerCommand("teachify.startTeach", async () => {
    const taskId = await vscode.window.showQuickPick(["js-express-hello", "java-spring-hello"], {
      placeHolder: "Pick a task — Teachify guides, you type.",
    });
    if (!taskId) return;
    try {
      const res = (await callTool("teach_start_task", { taskId, mode: "teach" })) as {
        content?: Array<{ text?: string }>;
      };
      const parsed = JSON.parse(res?.content?.[0]?.text ?? "{}");
      const step = parsed.currentStep;
      if (!panel) {
        panel = vscode.window.createWebviewPanel("teachify", "Teachify", vscode.ViewColumn.Beside, {});
        panel.onDidDispose(() => (panel = undefined));
      }
      panel.webview.html = renderWebview(
        `<h3>Step ${step?.stepNumber}/${step?.totalSteps}: ${step?.title ?? ""}</h3>` +
          `<p>${step?.instruction ?? ""}</p><p><i>Why: ${step?.why ?? ""}</i></p>` +
          `<p>File: <code>${step?.file ?? ""}</code> — ${step?.fileHint ?? ""}</p>` +
          `<p>Session: <code>${parsed.sessionId ?? ""}</code></p>` +
          `<p>Use the chat + <code>teach_check_step</code> to verify each step.</p>`
      );
      panel.reveal();
      vscode.window.showInformationMessage(`Teachify started: ${parsed.task?.title ?? taskId}. You type — I guide.`);
    } catch (err) {
      vscode.window.showErrorMessage(`Teachify: could not start task. ${err}`);
    }
  });

  context.subscriptions.push(showTasks, startTeach);
}

export function deactivate(): void {
  serverProcess?.kill();
  serverProcess = undefined;
}
