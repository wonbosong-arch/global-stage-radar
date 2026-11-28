const WORKFLOWS_URL =
  "https://api.github.com/repos/wonbosong-arch/global-stage-radar/actions/workflows";
function scheduledWorkflow(time) {
  const day = time.getUTCDay();
  const slot = time.toISOString().slice(11, 16);
  if (slot === "00:15") return "crypto_prices.yml";
  if (slot === "22:00" && day !== 6) return "daily_prices.yml";
  if (day === 0 || day === 6) return undefined;
  if (slot === "07:30") return "japan_candidate_prices.yml";
  if (slot === "09:30") return "china_candidate_prices.yml";
}

async function dispatch(workflow, inputs, token, scheduledAt) {
  const response = await fetch(`${WORKFLOWS_URL}/${workflow}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "stage-radar-scheduler",
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref: "data-validation-mvp", inputs }),
  });

  if (!response.ok) {
    throw new Error(`Dispatch of ${workflow} failed: ${response.status}`);
  }

  console.log("%s requested for %s", workflow, scheduledAt);
}

export default {
  async fetch() {
    return new Response("Stage Radar Scheduler");
  },

  async scheduled(controller, env) {
    controller.noRetry();

    const time = new Date(controller.scheduledTime);
    const workflow = scheduledWorkflow(time);
    if (!workflow) {
      console.log("Skipped: outside approved schedule");
      return;
    }
    if (!env.GITHUB_TOKEN) {
      throw new Error("GITHUB_TOKEN missing");
    }
    const scheduledAt = time.toISOString();
    await dispatch(workflow, { scheduled_at: scheduledAt }, env.GITHUB_TOKEN, scheduledAt);
  },
};
