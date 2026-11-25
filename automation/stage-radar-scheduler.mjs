const DISPATCH_URL =
  "https://api.github.com/repos/wonbosong-arch/global-stage-radar/actions/workflows/daily_prices.yml/dispatches";

export default {
  async fetch() {
    return new Response("Stage Radar Scheduler");
  },

  async scheduled(controller, env) {
    controller.noRetry();

    const time = new Date(controller.scheduledTime);
    if (time.getUTCHours() !== 22 || time.getUTCMinutes() !== 13 || time.getUTCDay() === 6) {
      console.log("Skipped: outside approved schedule");
      return;
    }

    if (!env.GITHUB_TOKEN) {
      throw new Error("GITHUB_TOKEN missing");
    }

    // GitHub checks the saved snapshot after acquiring the shared KIS queue.
    const response = await fetch(DISPATCH_URL, {
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
      throw new Error(`Dispatch failed: ${response.status}`);
    }

    console.log("Daily price collection requested for %s", time.toISOString());
  },
};
