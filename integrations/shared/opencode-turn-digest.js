// turn-digest: add the per-turn directives digest to every agent model request (OpenCode v2 plugin).
// Contract: default export { id, setup(ctx) }; ctx.session.hook("context", event => event.system.push({type:"text", text}))
//   runs immediately before each agent-loop model call and is not persisted into history.
//   The "prompt" hook was not used: it only exposes prompt.text, and edits there become the persisted user message.
// Sources: https://opencode.ai/v2/docs/build/plugins/server (Sessions > Model requests, Lifecycle > Context),
//          https://opencode.ai/v2/docs/build/plugins/migrate-v1 (V1 "chat.message"/system.transform -> V2 session hooks).
// Derived from a previously installed OpenCode v2 adapter. Verify activation in the target host after installation.
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const SCRIPT = process.env.PYE_TURN_DIGEST_SCRIPT ?? fileURLToPath(new URL("./turn-digest.sh", import.meta.url));
const TIMEOUT_MS = 5000;

function digestFor(directory) {
  try {
    return execFileSync("sh", [SCRIPT], {
      input: JSON.stringify({ cwd: directory }),
      encoding: "utf8",
      timeout: TIMEOUT_MS,
      stdio: ["pipe", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
}

export default {
  id: "turn-digest",
  async setup(ctx) {
    const directory = ctx.location?.directory ?? process.cwd();
    await ctx.session.hook("context", (event) => {
      const text = digestFor(directory);
      if (text && Array.isArray(event.system)) event.system.push({ type: "text", text });
    });
  },
};
