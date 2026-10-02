import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

globalThis.HTMLElement = class {};
const definitions = new Map();
globalThis.customElements = {
  define(name, value) {
    definitions.set(name, value);
  },
  get(name) {
    return definitions.get(name);
  },
};
globalThis.window = { customCards: [] };

const source = await readFile(
  new URL("../custom_components/mbecocoach/frontend/mbecocoach-card.js", import.meta.url),
  "utf8",
);
const cardModule = await import(
  `data:text/javascript;base64,${Buffer.from(
    `${source}\nexport { getRelatedEntityRecords, normalizeHistoryResponse, METRICS };`,
  ).toString("base64")}`,
);

test("registers the Lovelace card and visual editor", () => {
  assert.equal(definitions.has("mbecocoach-card"), true);
  assert.equal(definitions.has("mbecocoach-card-editor"), true);
  assert.equal(window.customCards[0].type, "mbecocoach-card");
  assert.equal(window.customCards[0].preview, true);
});

test("discovers vehicle entities by config entry and total-points unique ID", () => {
  const registry = [
    {
      entity_id: "sensor.eco_total",
      unique_id: "WDB123_account_total_points",
      platform: "mbecocoach",
      config_entry_id: "entry-a",
    },
    {
      entity_id: "sensor.eco_driving",
      unique_id: "WDB123_recent_driving_points",
      platform: "mbecocoach",
      config_entry_id: "entry-a",
    },
    {
      entity_id: "button.eco_refresh",
      unique_id: "WDB123_refresh_points_history",
      platform: "mbecocoach",
      config_entry_id: "entry-a",
    },
    {
      entity_id: "sensor.other_vehicle",
      unique_id: "VIN456_recent_driving_points",
      platform: "mbecocoach",
      config_entry_id: "entry-b",
    },
    {
      entity_id: "sensor.same_vehicle_other_account",
      unique_id: "WDB123_recent_driving_points",
      platform: "mbecocoach",
      config_entry_id: "entry-b",
    },
    {
      entity_id: "sensor.unrelated",
      unique_id: "OTHER_recent_driving_points",
      platform: "mbecocoach",
      config_entry_id: "entry-a",
    },
  ];
  const result = cardModule.getRelatedEntityRecords(registry, "sensor.eco_total");
  assert.equal(result.entryId, "entry-a");
  assert.equal(result.valid, true);
  assert.deepEqual(result.entities.map((item) => item.entity_id), [
    "sensor.eco_total",
    "sensor.eco_driving",
    "button.eco_refresh",
  ]);
});

test("personal statistics use actual Eco Coach sensor keys", () => {
  assert.deepEqual(cardModule.METRICS.slice(0, 3).map(([key]) => key), [
    "personal_drive_score",
    "personal_avg_consumption",
    "personal_saved_emissions",
  ]);
});

test("falls back to the selected total sensor unique-ID prefix", () => {
  const registry = [
    { entity_id: "sensor.total", unique_id: "VIN123_account_total_points", platform: "mbecocoach" },
    { entity_id: "sensor.score", unique_id: "VIN123_weekly_drive_score", platform: "mbecocoach" },
  ];
  const result = cardModule.getRelatedEntityRecords(registry, "sensor.total");
  assert.equal(result.entryId, null);
  assert.deepEqual(result.entities.map((item) => item.entity_id), ["sensor.total", "sensor.score"]);
});

test("rejects a selected entity that is not this integration's total-points sensor", () => {
  const registry = [
    { entity_id: "sensor.not_total", unique_id: "VIN123_drive_score", platform: "mbecocoach" },
    { entity_id: "sensor.total", unique_id: "VIN123_account_total_points", platform: "other" },
  ];
  assert.equal(cardModule.getRelatedEntityRecords(registry, "sensor.not_total").valid, false);
  assert.equal(cardModule.getRelatedEntityRecords(registry, "sensor.total").valid, false);
});

test("normalizes valid award history and rejects unsafe or malformed records", () => {
  assert.deepEqual(
    cardModule.normalizeHistoryResponse({
      context: { id: "request-id" },
      response: {
        total: 1,
        offset: 0,
        awards: [{ category: "charging", points: 12, occurred_at: "2026-01-10T12:00:00+00:00" }],
      },
    }),
    {
      total: 1,
      offset: 0,
      awards: [{ category: "charging", points: 12, occurred_at: "2026-01-10T12:00:00+00:00" }],
    },
  );
  assert.throws(
    () =>
      cardModule.normalizeHistoryResponse({
        response: {
          total: 1,
          offset: 0,
          awards: [{ category: "<img>", points: 12, occurred_at: "2026-01-10T12:00:00Z" }],
        },
      }),
    TypeError,
  );
  assert.throws(
    () =>
      cardModule.normalizeHistoryResponse({
        response: {
          total: 1,
          offset: 0,
          awards: [{ category: "driving", points: -1, occurred_at: "not a date" }],
        },
      }),
    TypeError,
  );
  assert.throws(
    () => cardModule.normalizeHistoryResponse({ context: { id: "request-id" } }),
    TypeError,
  );
  assert.throws(
    () => cardModule.normalizeHistoryResponse({ total: 0, offset: 0, awards: [] }),
    TypeError,
  );
});

test("requests history through the sixth callService argument and reads the response envelope", async () => {
  const Card = definitions.get("mbecocoach-card");
  const card = Object.create(Card.prototype);
  const calls = [];
  card._entryId = "entry-a";
  card._historyRequestId = 0;
  card._historyLoading = false;
  card._refreshing = false;
  card._hass = {
    callService: async (...args) => {
      calls.push(args);
      return {
        context: { id: "request-id" },
        response: {
          total: 1,
          offset: 0,
          awards: [{ category: "parking", points: 3, occurred_at: "2026-10-01T12:00:00Z" }],
        },
      };
    },
  };
  card._render = () => {};
  await card._fetchHistory();
  assert.deepEqual(calls, [[
    "mbecocoach",
    "get_points_history",
    { entry_id: "entry-a", offset: 0, limit: 8 },
    undefined,
    undefined,
    true,
  ]]);
  assert.equal(card._history.awards[0].points, 3);
  assert.equal(card._historyError, false);
});

test("shows a history error when callService returns only context", async () => {
  const Card = definitions.get("mbecocoach-card");
  const card = Object.create(Card.prototype);
  card._entryId = "entry-a";
  card._historyRequestId = 0;
  card._historyLoading = false;
  card._refreshing = false;
  card._history = { total: 0, offset: 0, awards: [] };
  card._hass = { callService: async () => ({ context: { id: "request-id" } }) };
  card._render = () => {};
  await card._fetchHistory();
  assert.equal(card._historyError, true);
  assert.equal(card._historyLoading, false);
  assert.deepEqual(card._history.awards, []);
});
