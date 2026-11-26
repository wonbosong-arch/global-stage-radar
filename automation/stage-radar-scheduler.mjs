const WORKFLOWS_URL =
  "https://api.github.com/repos/wonbosong-arch/global-stage-radar/actions/workflows";
const PRICE_WORKFLOWS = {
  0: ["china_candidate_prices.yml", "japan_candidate_prices.yml", "crypto_prices.yml"],
  13: ["daily_prices.yml"],
  35: ["candidate_prices_manual.yml"],
};

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
    const minute = time.getUTCMinutes();
    const workflows = PRICE_WORKFLOWS[minute];
    if (time.getUTCHours() !== 22 || !workflows || time.getUTCDay() === 6) {
      console.log("Skipped: outside approved schedule");
      return;
    }

    if (!env.GITHUB_TOKEN) {
      throw new Error("GITHUB_TOKEN missing");
    }

    const scheduledAt = time.toISOString();
    // GitHub checks saved prices after acquiring the relevant collection queue.
    const requests = workflows.map((workflow) => [workflow, { scheduled_at: scheduledAt }]);
    if (minute === 0 && time.getUTCDay() === 0) {
      // Sunday UTC corresponds to Monday KST.
      requests.push(
        ["candidate_collection.yml", { scheduled: true }],
        ["yahoo_master_cap_batch.yml", { mode: "supplement" }],
      );
    }

    const results = await Promise.allSettled(
      requests.map(([workflow, inputs]) => dispatch(workflow, inputs, env.GITHUB_TOKEN, scheduledAt)),
    );
    const failures = results.flatMap((result, index) =>
      result.status === "rejected" ? [requests[index][0]] : [],
    );
    if (failures.length) {
      for (const result of results) {
        if (result.status === "rejected") console.error(result.reason.message);
      }
      throw new Error(`Dispatch failed for: ${failures.join(", ")}`);
    }
  },
};
