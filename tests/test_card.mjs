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
    `${source}\nexport { getRelatedEntityRecords, normalizeHistoryResponse, METRICS, METRIC_GROUPS, BREAKDOWN, TEXT };`,
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
    "drive_score",
    "avg_consumption",
    "saved_emissions",
  ]);
});

test("Dutch breakdown labels use category translations", () => {
  assert.deepEqual(cardModule.BREAKDOWN.map(([, category]) => cardModule.TEXT.nl[category]), [
    "Rijden", "Laden", "Parkeren", "Persoonlijke uitdaging",
  ]);
});

test("point updates fetch one lightweight page, not a full re-import", async () => {
  const Card = definitions.get("mbecocoach-card");
  const card = Object.create(Card.prototype);
  card._config = { entity: "sensor.total" };
  card._registryEntity = "sensor.total";
  card._entryId = "entry-a";
  card._historyLoading = false;
  card._lastHistoryFetch = 0;
  card._related = { latest_driving_award: "sensor.award" };
  card._hass = { states: { "sensor.award": { last_updated: "2026-10-02T12:00:00Z" } } };
  card._render = () => {};
  let fetches = 0;
  card._fetchHistory = () => { fetches += 1; card._lastHistoryFetch = Date.now(); };
  card.hass = { states: { "sensor.award": { last_updated: "2026-10-02T12:01:00Z" } } };
  card.hass = { states: { "sensor.award": { last_updated: "2026-10-02T12:02:00Z" } } };
  assert.equal(fetches, 1);
  assert.equal(card.hass.callService, undefined);
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

test("pages history with bounded calls and preserves selected entry", async () => {
  const Card = definitions.get("mbecocoach-card");
  const card = Object.create(Card.prototype);
  card._entryId = "entry-a";
  card._historyRequestId = 0;
  card._historyLoading = false;
  card._refreshing = false;
  const calls = [];
  card._hass = { callService: async (...args) => {
    calls.push(args);
    return { response: { total: 17, offset: args[2].offset, awards: [
      { category: "driving", points: 1, occurred_at: "2026-10-01T00:00:00Z" },
    ] } };
  } };
  card._render = () => {};
  await card._fetchHistory(false, 8);
  assert.equal(card._historyOffset, 8);
  assert.deepEqual(calls[0][2], { entry_id: "entry-a", offset: 8, limit: 8 });
  assert.equal(calls[0][5], true);
});

test("card periods describe the API windows without claiming lifetime categories", () => {
  assert.match(cardModule.TEXT.en.total, /all time/);
  assert.match(cardModule.TEXT.en.breakdown, /last 7 days/);
  assert.match(cardModule.TEXT.en.personalPeriod, /current calendar week/);
  assert.match(cardModule.TEXT.nl.breakdown, /afgelopen 7 dagen/);
  assert.deepEqual(cardModule.METRIC_GROUPS.map(([, metrics]) => metrics.length), [3, 2, 2, 2]);
});

test("failed remote re-import retains cached awards without fetching another page", async () => {
  const Card = definitions.get("mbecocoach-card");
  const card = Object.create(Card.prototype);
  const cached = { total: 1, offset: 0, awards: [
    { category: "driving", points: 10, occurred_at: "2026-10-01T00:00:00Z" },
  ] };
  card._history = cached;
  card._historyOffset = 0;
  card._historyError = false;
  card._entryId = "entry-a";
  card._related = { refresh_points_history: "button.fixture_history" };
  card._hass = {
    states: { "button.fixture_history": { state: "2026-10-01T00:00:00Z" } },
    callService: async (domain, service, data, target, notifyOnError) => {
    assert.equal(domain, "button");
    assert.equal(service, "press");
    assert.equal(data.entity_id, "button.fixture_history");
    assert.equal(target, undefined);
    assert.equal(notifyOnError, false);
    throw new Error("Connection failed");
    },
  };
  card._render = () => {};
  card._fetchHistory = () => { throw new Error("History must not be refetched after failure"); };
  await card._refresh();
  assert.equal(card._refreshError, "failed");
  assert.equal(card._historyError, false);
  assert.equal(card._history, cached);
  assert.equal(card._refreshing, false);
  assert.match(cardModule.TEXT.en.refreshFailed, /Cached awards are unchanged/);
  assert.match(cardModule.TEXT.nl.refreshFailed, /Opgeslagen punten zijn ongewijzigd/);
});

test("missing history button shows availability error without claiming a network failure", async () => {
  const Card = definitions.get("mbecocoach-card");
  const card = Object.create(Card.prototype);
  card._entryId = null;
  card._related = {};
  card._historyError = false;
  card._render = () => {};
  card._loadRegistry = async () => {};
  card._hass = { callService: () => { throw new Error("Should not call the button"); } };
  await card._refresh();
  assert.equal(card._refreshError, "unavailable");
  assert.equal(card._historyError, false);
});

test("disabled history button is unavailable even if its registry record remains", async () => {
  const Card = definitions.get("mbecocoach-card");
  const card = Object.create(Card.prototype);
  card._entryId = "entry-a";
  card._related = { refresh_points_history: "button.fixture_history" };
  card._historyError = false;
  card._render = () => {};
  card._hass = {
    states: {},
    callService: () => { throw new Error("Must not press disabled button"); },
  };
  await card._refresh();
  assert.equal(card._refreshError, "unavailable");
  assert.equal(card._historyError, false);
});

test("saved emissions always render with two decimal places", () => {
  const Card = definitions.get("mbecocoach-card");
  const card = Object.create(Card.prototype);
  card._hass = { language: "en" };
  assert.equal(card._number("12.3", 2, 2), "12.30");
  assert.equal(card._number("12.349", 2, 2), "12.35");
  assert.equal(card._number("12.3", 1), "12.3");
});

test("re-import retains keyboard focus across loading renders", async () => {
  class Element {
    constructor(tag) {
      this.tag = tag;
      this.children = [];
      this.dataset = {};
      this.style = {};
      this.disabled = false;
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) {
      this.children = children;
      if (this === root) this.activeElement = null;
    }
    addEventListener() {}
    setAttribute() {}
    focus() { root.activeElement = this; }
    get childElementCount() { return this.children.length; }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    querySelectorAll(selector) {
      const matches = (node) => selector === "[data-focus-key]"
        ? Boolean(node.dataset.focusKey)
        : node.tag === selector;
      return this.children.flatMap((child) => [
        ...(matches(child) ? [child] : []),
        ...child.querySelectorAll(selector),
      ]);
    }
  }
  const root = new Element("shadow");
  const originalDocument = globalThis.document;
  globalThis.document = { createElement: (tag) => new Element(tag) };
  try {
    const Card = definitions.get("mbecocoach-card");
    const card = Object.create(Card.prototype);
    card.shadowRoot = root;
    card._config = { entity: "sensor.total" };
    card._related = { refresh_points_history: "button.history" };
    card._entryId = "entry";
    card._historyRequestId = 0;
    card._historyLoading = false;
    card._historyError = false;
    card._historyOffset = 0;
    card._history = { total: 0, offset: 0, awards: [] };
    card._refreshing = false;
    card._refreshError = false;
    card._pendingFocusKey = null;
    let finishPress;
    card._hass = {
      language: "en",
      states: {
        "sensor.total": { state: "12", attributes: {} },
        "button.history": { state: "2026-10-02T00:00:00Z" },
      },
      callService: async (domain) => domain === "button"
        ? new Promise((resolve) => { finishPress = resolve; })
        : { response: { total: 0, offset: 0, awards: [] } },
    };
    card._render();
    root.querySelectorAll("[data-focus-key]").find((el) => el.dataset.focusKey === "reimport").focus();
    const refresh = card._refresh();
    assert.equal(card._pendingFocusKey, "reimport");
    assert.equal(root.activeElement.tag, "h3");
    finishPress();
    await refresh;
    assert.equal(root.activeElement.dataset.focusKey, "reimport");
    assert.equal(card._pendingFocusKey, null);
  } finally {
    globalThis.document = originalDocument;
  }
});
