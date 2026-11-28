import assert from "node:assert/strict";
import test from "node:test";
import scheduler from "../automation/stage-radar-scheduler.mjs";

async function invoke(timestamp, failedWorkflow) {
  const calls = {};
  let noRetry = false;
  let failure;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    const workflow = url.split("/").at(-2);
    assert.equal(options.method, "POST");
    assert.equal(options.headers.Authorization, "Bearer mock-token");
    assert.equal(Object.hasOwn(calls, workflow), false);
    const body = JSON.parse(options.body);
    assert.equal(body.ref, "data-validation-mvp");
    calls[workflow] = body.inputs;
    return workflow === failedWorkflow ? { ok: false, status: 503 } : { ok: true, status: 204 };
  };
  try {
    await scheduler.scheduled(
      { scheduledTime: Date.parse(timestamp), noRetry() { noRetry = true; } },
      { GITHUB_TOKEN: "mock-token" },
    );
  } catch (error) {
    failure = error;
  } finally {
    globalThis.fetch = originalFetch;
  }
  assert.equal(noRetry, true);
  return { calls, failure };
}

test("Monday and Saturday 07:00 KST dispatch one operating workflow", async () => {
  for (const timestamp of ["2026-11-22T22:00:36.000Z", "2026-11-27T22:00:00.000Z"]) {
    const { calls, failure } = await invoke(timestamp);
    assert.equal(failure, undefined);
    assert.deepEqual(calls, { "daily_prices.yml": { scheduled_at: timestamp } });
  }
});

test("Superseded schedules and Sunday 07:00 KST dispatch nothing", async () => {
  for (const timestamp of [
    "2026-11-21T22:00:00.000Z", "2026-11-25T22:13:00.000Z", "2026-11-25T22:35:00.000Z",
    "2026-11-22T21:00:00.000Z", "2026-11-22T22:01:00.000Z",
  ]) {
    const { calls, failure } = await invoke(timestamp);
    assert.equal(failure, undefined);
    assert.deepEqual(calls, {});
  }
});

test("Local and crypto closes use distinct schedules and weekdays", async () => {
  for (const [hour, minute, workflow] of [
    ["00", "15", "crypto_prices.yml"],
    ["07", "30", "japan_candidate_prices.yml"],
    ["09", "30", "china_candidate_prices.yml"],
  ]) {
    for (const day of [21, 22, 23, 24, 25, 26, 27]) {
      const timestamp = `2026-11-${day}T${hour}:${minute}:42.000Z`;
      const { calls, failure } = await invoke(timestamp);
      assert.equal(failure, undefined);
      assert.deepEqual(calls, day >= 23 || hour === "00"
        ? { [workflow]: { scheduled_at: timestamp } } : {});
    }
  }
});

test("A dispatch failure identifies its workflow and does not request other jobs", async () => {
  const timestamp = "2026-11-27T22:00:00.000Z";
  const { calls, failure } = await invoke(timestamp, "daily_prices.yml");
  assert.deepEqual(calls, { "daily_prices.yml": { scheduled_at: timestamp } });
  assert.match(failure.message, /daily_prices\.yml.*503/);
});
