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

test("Monday KST includes weekly discovery and Yahoo supplement with the 07:00 prices", async () => {
  const timestamp = "2026-11-22T22:00:36.000Z";
  const { calls, failure } = await invoke(timestamp);
  assert.equal(failure, undefined);
  assert.deepEqual(calls, {
    "japan_candidate_prices.yml": { scheduled_at: timestamp },
    "crypto_prices.yml": { scheduled_at: timestamp },
    "candidate_collection.yml": { scheduled: true },
    "yahoo_master_cap_batch.yml": { mode: "supplement" },
  });
});

test("Saturday KST retries Friday China/Hong Kong gaps even when Japan dispatch fails", async () => {
  const timestamp = "2026-11-27T22:00:00.000Z";
  const { calls, failure } = await invoke(timestamp, "japan_candidate_prices.yml");
  assert.deepEqual(calls, {
    "china_candidate_prices.yml": { scheduled_at: timestamp, catch_up: true },
    "japan_candidate_prices.yml": { scheduled_at: timestamp },
    "crypto_prices.yml": { scheduled_at: timestamp },
  });
  assert.match(failure.message, /japan_candidate_prices\.yml/);
});

test("07:13 and 07:35 keep their original workflows and UTC timestamp inputs", async () => {
  for (const [minute, workflow] of [[13, "daily_prices.yml"], [35, "candidate_prices_manual.yml"]]) {
    const timestamp = `2026-11-25T22:${minute}:45.000Z`;
    const { calls, failure } = await invoke(timestamp);
    assert.equal(failure, undefined);
    assert.deepEqual(calls, { [workflow]: { scheduled_at: timestamp } });
  }
});

test("Sunday KST and unscheduled hours or minutes dispatch nothing", async () => {
  for (const timestamp of [
    "2026-11-21T22:00:00.000Z", "2026-11-21T22:13:00.000Z", "2026-11-21T22:35:00.000Z",
    "2026-11-22T21:00:00.000Z", "2026-11-22T22:01:00.000Z",
  ]) {
    const { calls, failure } = await invoke(timestamp);
    assert.equal(failure, undefined);
    assert.deepEqual(calls, {});
  }
});

test("Weekday 18:30 KST dispatches only the Mainland and Hong Kong close", async () => {
  for (const day of [23, 24, 25, 26, 27]) {
    const timestamp = `2026-11-${day}T09:30:42.000Z`;
    const { calls, failure } = await invoke(timestamp);
    assert.equal(failure, undefined);
    assert.deepEqual(calls, {
      "china_candidate_prices.yml": { scheduled_at: timestamp, catch_up: false },
    });
  }
  for (const day of [21, 22]) {
    const { calls } = await invoke(`2026-11-${day}T09:30:00.000Z`);
    assert.deepEqual(calls, {});
  }
});
