const WORKFLOWS_URL =
  "https://api.github.com/repos/wonbosong-arch/global-stage-radar/actions/workflows";
const WORKFLOW_BY_MINUTE = {
  13: "daily_prices.yml",
  35: "candidate_prices_manual.yml",
};

export default {
  async fetch() {
    return new Response("Stage Radar Scheduler");
  },

  async scheduled(controller, env) {
    controller.noRetry();

    const time = new Date(controller.scheduledTime);
    const workflow = WORKFLOW_BY_MINUTE[time.getUTCMinutes()];
    if (time.getUTCHours() !== 22 || !workflow || time.getUTCDay() === 6) {
      console.log("Skipped: outside approved schedule");
      return;
    }

    if (!env.GITHUB_TOKEN) {
      throw new Error("GITHUB_TOKEN missing");
    }

    // GitHub checks the saved snapshot after acquiring the shared KIS queue.
    const response = await fetch(`${WORKFLOWS_URL}/${workflow}/dispatches`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "stage-radar-scheduler",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({
        ref: "data-validation-mvp",
        inputs: { scheduled_at: time.toISOString() },
      }),
    });

    if (!response.ok) {
      throw new Error(`Dispatch of ${workflow} failed: ${response.status}`);
    }

    console.log("%s requested for %s", workflow, time.toISOString());
  },
};
