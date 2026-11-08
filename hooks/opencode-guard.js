// OpenCode plugin: the same barriers as the Claude Code hook. Each tool call goes to guard.sh.
// guard.sh deny (exit 2) or ask -> the plugin throws, and OpenCode does not run the tool.
// In a headless run there is no human to answer, so "ask" stops the action too.
// Install: copy to <project>/.opencode/plugins/ with ${KIT} replaced by the kit path (bench/run.py does it).
// HARNESS_BASH: the bash to use. On Windows a bare "bash" starts WSL, so give Git Bash (barrier B22).
import { spawnSync } from "node:child_process";

const KIT = "${KIT}";
const NAMES = { bash: "Bash", read: "Read", edit: "Edit", write: "Write", multiedit: "MultiEdit", patch: "Edit" };

export const HarnessGuard = async () => ({
  "tool.execute.before": async (input, output) => {
    const a = (output && output.args) || {};
    const payload = {
      tool_name: NAMES[input.tool] || input.tool,
      tool_input: { command: a.command || "", file_path: a.filePath || a.file_path || a.path || "" },
      session_id: input.sessionID || "",
    };
    const r = spawnSync(process.env.HARNESS_BASH || "bash", [`${KIT}/hooks/guard.sh`], {
      input: JSON.stringify(payload),
      encoding: "utf8",
    });
    if (r.status === 2) throw new Error((r.stderr || "Blocked by guard.sh").trim());
    if ((r.stdout || "").includes('"permissionDecision":"ask"')) {
      const m = /permissionDecisionReason":"([^"]*)/.exec(r.stdout);
      throw new Error(`Blocked by guard.sh: a human must confirm: ${m ? m[1] : "this action"}`);
    }
    // B39: the guard changed the command (the test output goes through the secret mask)
    try {
      const u = JSON.parse(r.stdout || "{}").hookSpecificOutput?.updatedInput;
      if (u && u.command && output && output.args) output.args.command = u.command;
    } catch { /* not JSON: nothing to change */ }
  },
});

export default { id: "mah.guard", server: HarnessGuard };
