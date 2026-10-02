const DOMAIN = "mbecocoach";
const CARD_TYPE = "mbecocoach-card";
const TOTAL_SUFFIX = "_account_total_points";
const CATEGORIES = ["driving", "charging", "parking"];
const BREAKDOWN = [
  ["recent_driving_points", "driving"],
  ["recent_charging_points", "charging"],
  ["recent_parking_points", "parking"],
  ["recent_personal_challenge_points", "personal_challenge"],
];
const METRICS = [
  ["drive_score", "Drive score"],
  ["avg_consumption", "Average consumption"],
  ["saved_emissions", "Saved emissions"],
  ["daily_drive_score", "Daily drive score"],
  ["daily_consumption", "Daily consumption"],
  ["weekly_drive_score", "Weekly drive score"],
  ["weekly_consumption", "Weekly consumption"],
  ["monthly_drive_score", "Monthly drive score"],
  ["monthly_consumption", "Monthly consumption"],
];
const METRIC_GROUPS = [
  ["personalPeriod", METRICS.slice(0, 3)],
  ["dailyPeriod", METRICS.slice(3, 5)],
  ["weeklyPeriod", METRICS.slice(5, 7)],
  ["monthlyPeriod", METRICS.slice(7)],
];
const HISTORY_PAGE_SIZE = 8;

const TEXT = {
  en: {
    title: "Eco Coach",
    subtitle: "Your account points and driving insights",
    total: "Total account points · all time",
    breakdown: "Points breakdown · last 7 days",
    metrics: "Your stats",
    personalPeriod: "Personal · current calendar week",
    dailyPeriod: "Daily summary",
    weeklyPeriod: "Weekly summary",
    monthlyPeriod: "Monthly summary",
    history: "Recent awards",
    viewAwards: "View awards →",
    retry: "Try again",
    previous: "Previous",
    next: "Next",
    historyRange: (first, last, total) => `${first}–${last} of ${total} awards`,
    refresh: "Re-import history",
    loading: "Loading points history…",
    noAwards: "No individual awards are available yet.",
    noBreakdown: "Points breakdown is not available.",
    noMetrics: "Statistics are not available.",
    configure: "Choose the Total account points sensor in this card's settings.",
    invalidEntity: "Select an Eco Coach Total account points sensor.",
    registryError: "Eco Coach entities could not be discovered. Check the card configuration and try again.",
    historyError: "Points history could not be loaded. Try again.",
    refreshUnavailable: "Re-import is unavailable. Check that the Eco Coach history button is enabled.",
    refreshFailed: "Re-import failed. Cached awards are unchanged; check the Eco Coach connection and try later.",
    refreshing: "Re-importing…",
    driving: "Driving",
    charging: "Charging",
    parking: "Parking",
    personal_challenge: "Personal challenge",
    drive_score: "Drive score",
    avg_consumption: "Average consumption",
    saved_emissions: "Saved emissions",
    daily_drive_score: "Daily drive score",
    daily_consumption: "Daily consumption",
    weekly_drive_score: "Weekly drive score",
    weekly_consumption: "Weekly consumption",
    monthly_drive_score: "Monthly drive score",
    monthly_consumption: "Monthly consumption",
  },
  nl: {
    title: "Eco Coach",
    subtitle: "Punten en rij-inzichten van je account",
    total: "Totaal aantal accountpunten · vanaf het begin",
    breakdown: "Puntenoverzicht · afgelopen 7 dagen",
    metrics: "Jouw statistieken",
    personalPeriod: "Persoonlijk · huidige kalenderweek",
    dailyPeriod: "Dagoverzicht",
    weeklyPeriod: "Weekoverzicht",
    monthlyPeriod: "Maandoverzicht",
    history: "Recente punten",
    viewAwards: "Bekijk toekenningen →",
    retry: "Opnieuw proberen",
    previous: "Vorige",
    next: "Volgende",
    historyRange: (first, last, total) => `${first}–${last} van ${total} toekenningen`,
    refresh: "Geschiedenis opnieuw importeren",
    loading: "Puntenoverzicht laden…",
    noAwards: "Er zijn nog geen losse punten beschikbaar.",
    noBreakdown: "Puntenoverzicht is niet beschikbaar.",
    noMetrics: "Statistieken zijn niet beschikbaar.",
    configure: "Kies de sensor Totaal aantal accountpunten in de kaartinstellingen.",
    invalidEntity: "Selecteer een Eco Coach-sensor voor het totaal aantal accountpunten.",
    registryError: "Eco Coach-entiteiten konden niet worden gevonden. Controleer de kaartinstellingen en probeer opnieuw.",
    historyError: "Puntenoverzicht kon niet worden geladen. Probeer het later opnieuw.",
    refreshUnavailable: "Herimport is niet beschikbaar. Controleer of de Eco Coach-geschiedenisknop is ingeschakeld.",
    refreshFailed: "Herimport mislukt. Opgeslagen punten zijn ongewijzigd; controleer de verbinding met Eco Coach en probeer het later opnieuw.",
    refreshing: "Opnieuw importeren…",
    driving: "Rijden",
    charging: "Laden",
    parking: "Parkeren",
    personal_challenge: "Persoonlijke uitdaging",
    drive_score: "Rijscore",
    avg_consumption: "Gemiddeld verbruik",
    saved_emissions: "Bespaarde uitstoot",
    daily_drive_score: "Dagelijkse rijscore",
    daily_consumption: "Dagelijks verbruik",
    weekly_drive_score: "Wekelijkse rijscore",
    weekly_consumption: "Wekelijks verbruik",
    monthly_drive_score: "Maandelijkse rijscore",
    monthly_consumption: "Maandelijks verbruik",
  },
};

const STYLE = `
  :host { display: block; }
  ha-card {
    overflow: hidden;
    color: var(--primary-text-color);
    background: var(--ha-card-background, var(--card-background-color));
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-card-border-radius, 20px);
  }
  .content { padding: clamp(16px, 4vw, 26px); }
  .top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
  .eyebrow { color: var(--secondary-text-color); font-size: 0.78rem; letter-spacing: .08em; text-transform: uppercase; }
  h2 { margin: 4px 0 0; font-size: 1.25rem; font-weight: 650; }
  .subtitle { margin: 5px 0 0; color: var(--secondary-text-color); font-size: .9rem; }
  .refresh {
    flex: 0 1 auto; max-width: 50%; border: 1px solid var(--divider-color); border-radius: 999px;
    padding: 9px 14px; background: var(--secondary-background-color);
    color: var(--primary-text-color); font: inherit; cursor: pointer;
  }
  .refresh:hover { border-color: var(--primary-color); }
  .refresh:disabled { cursor: wait; opacity: .65; }
  .clickable { cursor: pointer; font: inherit; text-align: left; color: inherit; }
  .clickable:hover { outline: 2px solid var(--primary-color); }
  .clickable:focus-visible, .refresh:focus-visible, .paging button:focus-visible {
    outline: 3px solid var(--primary-color); outline-offset: 2px;
  }
  .hero {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    margin-top: 22px; padding: 22px; border: 0; border-radius: 16px;
    background: linear-gradient(125deg, var(--success-color, #16865b), var(--primary-color, #477f70));
    color: var(--text-primary-color, #fff); font: inherit;
  }
  .hero-label { font-size: .9rem; opacity: .9; }
  .hero-link { display: block; margin-top: 10px; font-size: .85rem; text-decoration: underline; }
  .total { margin-top: 5px; font-size: clamp(2.3rem, 9vw, 3.7rem); line-height: 1; font-weight: 720; letter-spacing: -.04em; }
  .star { font-size: 2.1rem; opacity: .9; }
  section { margin-top: 24px; }
  h3 { margin: 0 0 12px; font-size: 1rem; font-weight: 650; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 135px), 1fr)); gap: 10px; }
  .tile {
    min-width: 0; padding: 14px; border: 0; border-radius: 13px;
    background: var(--secondary-background-color);
  }
  .tile-label { color: var(--secondary-text-color); font-size: .82rem; }
  .tile-value { margin-top: 6px; font-size: 1.25rem; font-weight: 650; overflow-wrap: anywhere; }
  .tile-unit { font-size: .8rem; font-weight: 500; white-space: nowrap; }
  .period { margin: 18px 0 10px; color: var(--secondary-text-color); font-size: .85rem; }
  .paging { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 14px; }
  .paging button { padding: 7px 11px; border-radius: 8px; border: 1px solid var(--divider-color);
    background: var(--secondary-background-color); color: var(--primary-text-color); cursor: pointer; }
  .paging button:disabled { opacity: .5; cursor: default; }
  .paging span { color: var(--secondary-text-color); font-size: .8rem; text-align: center; }
  .awards { display: grid; gap: 2px; }
  .award {
    display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; align-items: center;
    gap: 11px; padding: 10px 2px; border-bottom: 1px solid var(--divider-color);
  }
  .award:last-child { border-bottom: 0; }
  .dot {
    display: grid; place-items: center; width: 36px; height: 36px; border-radius: 50%;
    background: var(--primary-color); color: var(--text-primary-color, #fff); font-weight: 700;
  }
  .award-name { font-weight: 580; }
  .award-date { margin-top: 3px; color: var(--secondary-text-color); font-size: .8rem; }
  .award-points { white-space: nowrap; font-weight: 700; }
  .message { margin: 10px 0 0; color: var(--secondary-text-color); font-size: .9rem; }
  .error { color: var(--error-color); }
  @media (max-width: 420px) {
    .top { gap: 8px; }
    .refresh { padding: 8px 10px; }
    .content { padding: 16px; }
    .hero { padding: 18px; }
  }
`;

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function getRelatedEntityRecords(registry, selectedEntityId) {
  if (!Array.isArray(registry)) return { entryId: null, entities: [], valid: false };
  const selected = registry.find((item) => item?.entity_id === selectedEntityId);
  const uniqueId = selected?.unique_id;
  const valid = selected?.platform === DOMAIN && typeof uniqueId === "string" && uniqueId.endsWith(TOTAL_SUFFIX);
  if (!valid) return { entryId: null, entities: [], valid: false };

  const prefix = uniqueId.slice(0, -TOTAL_SUFFIX.length);
  const entryId = typeof selected.config_entry_id === "string" ? selected.config_entry_id : null;
  const entities = registry.filter((item) => {
    if (item?.platform !== DOMAIN || typeof item.entity_id !== "string") return false;
    const sameEntry = entryId !== null && item.config_entry_id === entryId;
    const sameUniqueIdPrefix =
      typeof item.unique_id === "string" && item.unique_id.startsWith(`${prefix}_`);
    return sameUniqueIdPrefix && (entryId === null || sameEntry);
  });
  return { entryId, entities, valid: true, prefix };
}

function normalizeHistoryResponse(response) {
  if (!isRecord(response) || !isRecord(response.response)) {
    throw new TypeError("Missing points history service response");
  }
  const payload = response.response;
  if (
    !isRecord(payload) ||
    !Number.isInteger(payload.total) ||
    payload.total < 0 ||
    !Number.isInteger(payload.offset) ||
    payload.offset < 0 ||
    !Array.isArray(payload.awards)
  ) {
    throw new TypeError("Invalid points history response");
  }
  const awards = payload.awards.map((award) => {
    if (
      !isRecord(award) ||
      !CATEGORIES.includes(award.category) ||
      !Number.isInteger(award.points) ||
      award.points < 0 ||
      typeof award.occurred_at !== "string" ||
      !Number.isFinite(Date.parse(award.occurred_at))
    ) {
      throw new TypeError("Invalid points history award");
    }
    return {
      category: award.category,
      points: award.points,
      occurred_at: award.occurred_at,
    };
  });
  return { total: payload.total, offset: payload.offset, awards };
}

class EcoCoachCardEditor extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (this._picker) {
      this._picker.hass = hass;
      this._picker.label = this._isDutch() ? "Totaal aantal accountpunten" : "Total account points";
    }
  }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  _isDutch() {
    return String(this._hass?.language || "").toLowerCase().startsWith("nl");
  }

  _render() {
    if (!this._config) return;
    const picker = document.createElement("ha-entity-picker");
    picker.label = this._isDutch() ? "Totaal aantal accountpunten" : "Total account points";
    picker.includeDomains = ["sensor"];
    picker.hass = this._hass;
    picker.value = this._config.entity || "";
    picker.addEventListener("value-changed", (event) => {
      const entity = event.detail?.value || "";
      this._config = { ...this._config, entity };
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          bubbles: true,
          composed: true,
          detail: { config: this._config },
        }),
      );
    });
    this._picker = picker;
    this.replaceChildren(picker);
  }
}

class EcoCoachCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._registryEntity = null;
    this._registryRequestEntity = null;
    this._registryLoading = false;
    this._registryError = false;
    this._invalidEntity = false;
    this._entryId = null;
    this._related = {};
    this._historyRequestId = 0;
    this._historyLoading = false;
    this._historyError = false;
    this._history = { total: 0, offset: 0, awards: [] };
    this._historyOffset = 0;
    this._lastHistoryFetch = 0;
    this._refreshing = false;
    this._refreshError = false;
    this._pendingFocusKey = null;
  }

  static getConfigElement() {
    if (!customElements.get("mbecocoach-card-editor")) {
      customElements.define("mbecocoach-card-editor", EcoCoachCardEditor);
    }
    return document.createElement("mbecocoach-card-editor");
  }

  static getStubConfig() {
    return { entity: "" };
  }

  setConfig(config) {
    if (!isRecord(config)) throw new Error("Card configuration must be an object");
    const entity = typeof config.entity === "string" ? config.entity : "";
    if (entity !== this._config.entity) this._resetEntity();
    this._config = { ...config, entity };
    this._render();
    if (this._hass && entity) this._loadRegistry();
  }

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    const entity = this._config.entity;
    if (entity && this._registryEntity !== entity) this._loadRegistry();
    else if (this._entryId && !this._historyLoading && Date.now() - this._lastHistoryFetch >= 60_000) {
      const watched = [
        "account_total_points",
        "latest_driving_award",
        "latest_charging_award",
        "latest_parking_award",
        ...BREAKDOWN.map(([suffix]) => suffix),
      ];
      if (watched.some((key) => {
        const id = this._related[key];
        return id && previous?.states?.[id]?.last_updated !== hass.states?.[id]?.last_updated;
      })) this._fetchHistory();
    }
    this._render();
  }

  get hass() {
    return this._hass;
  }

  getCardSize() {
    return 5;
  }

  _resetEntity() {
    this._registryEntity = null;
    this._registryRequestEntity = null;
    this._registryLoading = false;
    this._registryError = false;
    this._invalidEntity = false;
    this._entryId = null;
    this._related = {};
    this._historyRequestId += 1;
    this._historyLoading = false;
    this._historyError = false;
    this._history = { total: 0, offset: 0, awards: [] };
    this._historyOffset = 0;
    this._lastHistoryFetch = 0;
    this._refreshError = false;
    this._pendingFocusKey = null;
  }

  async _loadRegistry(force = false) {
    const entity = this._config.entity;
    const hass = this._hass;
    if (!entity || !hass?.callWS || (!force && this._registryRequestEntity === entity)) return;
    this._registryEntity = entity;
    this._registryRequestEntity = entity;
    this._registryLoading = true;
    this._registryError = false;
    this._render();
    try {
      const registry = await hass.callWS({ type: "config/entity_registry/list" });
      if (this._config.entity !== entity) return;
      const result = getRelatedEntityRecords(registry, entity);
      if (!result.valid) {
        this._invalidEntity = true;
        this._registryError = true;
        this._entryId = null;
        this._related = {};
      } else {
        this._invalidEntity = false;
        this._entryId = result.entryId;
        this._related = {};
        for (const item of result.entities) {
          if (!isRecord(item) || typeof item.unique_id !== "string") continue;
          const suffix = item.unique_id.slice(result.prefix.length + 1);
          if (item.entity_id.startsWith("sensor.") || item.entity_id.startsWith("button.")) {
            this._related[suffix] = item.entity_id;
          }
        }
        if (!this._entryId) this._registryError = true;
      }
      this._registryLoading = false;
      this._render();
      if (this._entryId) this._fetchHistory();
    } catch (_error) {
      if (this._config.entity !== entity) return;
      this._registryLoading = false;
      this._registryError = true;
      this._invalidEntity = false;
      this._render();
    }
  }

  async _fetchHistory(force = false, offset = 0) {
    const entryId = this._entryId;
    const hass = this._hass;
    if (!entryId || !hass?.callService || (this._historyLoading && !force)) return;
    const requestId = ++this._historyRequestId;
    this._lastHistoryFetch = Date.now();
    this._historyLoading = true;
    this._historyError = false;
    this._render();
    try {
      const response = await hass.callService(
        DOMAIN,
        "get_points_history",
        { entry_id: entryId, offset, limit: HISTORY_PAGE_SIZE },
        undefined,
        undefined,
        true,
      );
      const history = normalizeHistoryResponse(response);
      if (requestId !== this._historyRequestId || entryId !== this._entryId) return;
      this._history = history;
      this._historyOffset = history.offset;
      this._historyError = false;
      this._refreshError = false;
    } catch (_error) {
      if (requestId !== this._historyRequestId) return;
      this._historyError = true;
    } finally {
      if (requestId === this._historyRequestId) {
        this._historyLoading = false;
        this._render();
      }
    }
  }

  async _refresh() {
    if (this._refreshing) return;
    this._refreshing = true;
    this._refreshError = false;
    this._render();
    try {
      if (!this._entryId || !this._related.refresh_points_history) {
        await this._loadRegistry(true);
      }
      const buttonId = this._related.refresh_points_history;
      const button = this._state(buttonId);
      if (!this._entryId || !button || button.state === "unavailable") {
        this._refreshError = "unavailable";
        return;
      }
      await this._hass.callService("button", "press", {
        entity_id: buttonId,
      }, undefined, false);
      await this._fetchHistory(true);
    } catch (_error) {
      this._refreshError = "failed";
    } finally {
      this._refreshing = false;
      this._render();
    }
  }

  _language() {
    return String(this._hass?.language || "en").toLowerCase().startsWith("nl") ? "nl" : "en";
  }

  _number(value, digits = 0) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    const locale = this._hass?.language || "en";
    return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(number);
  }

  _state(entityId) {
    return entityId ? this._hass?.states?.[entityId] || null : null;
  }

  _moreInfo(entityId) {
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId },
    }));
  }

  _appendMessage(parent, text, error = false) {
    const message = document.createElement("p");
    message.className = error ? "message error" : "message";
    message.textContent = text;
    parent.append(message);
  }

  _section(parent, title) {
    const section = document.createElement("section");
    const heading = document.createElement("h3");
    heading.textContent = title;
    section.append(heading);
    parent.append(section);
    return section;
  }

  _render() {
    if (!this.shadowRoot) return;
    const active = this.shadowRoot.activeElement;
    const focusKey = active?.dataset?.focusKey || this._pendingFocusKey;
    const language = this._language();
    const labels = TEXT[language];
    const style = document.createElement("style");
    style.textContent = STYLE;
    const card = document.createElement("ha-card");
    const content = document.createElement("div");
    content.className = "content";

    const top = document.createElement("div");
    top.className = "top";
    const heading = document.createElement("div");
    const eyebrow = document.createElement("div");
    eyebrow.className = "eyebrow";
    eyebrow.textContent = "Mercedes Eco Coach";
    const title = document.createElement("h2");
    title.textContent = labels.title;
    const subtitle = document.createElement("p");
    subtitle.className = "subtitle";
    subtitle.textContent = labels.subtitle;
    heading.append(eyebrow, title, subtitle);

    const refresh = document.createElement("button");
    refresh.className = "refresh";
    refresh.type = "button";
    refresh.dataset.focusKey = "reimport";
    refresh.textContent = this._refreshing ? labels.refreshing : labels.refresh;
    refresh.disabled = this._refreshing || this._historyLoading || this._registryLoading;
    refresh.addEventListener("click", () => this._refresh());
    top.append(heading, refresh);
    content.append(top);

    const hero = document.createElement("button");
    hero.className = "hero clickable";
    hero.type = "button";
    hero.dataset.focusKey = "hero";
    hero.style.width = "100%";
    hero.addEventListener("click", () => this.shadowRoot.querySelector("#eco-coach-history")?.scrollIntoView({
      behavior: "smooth", block: "start",
    }));
    const totalGroup = document.createElement("div");
    const totalLabel = document.createElement("div");
    totalLabel.className = "hero-label";
    totalLabel.textContent = labels.total;
    const total = document.createElement("div");
    total.className = "total";
    const totalState = this._state(this._config.entity);
    total.textContent = totalState && !["unknown", "unavailable"].includes(totalState.state)
      ? this._number(totalState.state)
      : "—";
    const heroLink = document.createElement("span");
    heroLink.className = "hero-link";
    heroLink.textContent = labels.viewAwards;
    totalGroup.append(totalLabel, total, heroLink);
    const star = document.createElement("div");
    star.className = "star";
    star.setAttribute("aria-hidden", "true");
    star.textContent = "✦";
    hero.append(totalGroup, star);
    content.append(hero);

    if (!this._config.entity) {
      this._appendMessage(content, labels.configure);
    } else if (this._registryError) {
      this._appendMessage(content, this._invalidEntity ? labels.invalidEntity : labels.registryError, true);
    } else if (this._registryLoading) {
      this._appendMessage(content, labels.loading);
    }

    const breakdownSection = this._section(content, labels.breakdown);
    const breakdownGrid = document.createElement("div");
    breakdownGrid.className = "grid";
    let breakdownCount = 0;
    for (const [suffix, category] of BREAKDOWN) {
      const state = this._state(this._related[suffix]);
      if (!state) continue;
      const tile = document.createElement("button");
      tile.className = "tile clickable";
      tile.type = "button";
      tile.dataset.focusKey = `tile:${this._related[suffix]}`;
      tile.addEventListener("click", () => this._moreInfo(this._related[suffix]));
      const label = document.createElement("div");
      label.className = "tile-label";
      label.textContent = labels[category];
      const value = document.createElement("div");
      value.className = "tile-value";
      value.textContent = ["unknown", "unavailable"].includes(state.state) ? "—" : this._number(state.state);
      tile.append(label, value);
      breakdownGrid.append(tile);
      breakdownCount += 1;
    }
    if (breakdownCount) breakdownSection.append(breakdownGrid);
    else this._appendMessage(breakdownSection, labels.noBreakdown);

    const metricSection = this._section(content, labels.metrics);
    let metricCount = 0;
    for (const [period, metrics] of METRIC_GROUPS) {
      const metricGrid = document.createElement("div");
      metricGrid.className = "grid";
      for (const [suffix, fallback] of metrics) {
        const entityId = this._related[suffix];
        if (!entityId) continue;
        const state = this._state(entityId);
        const tile = document.createElement("button");
        tile.className = "tile clickable";
        tile.type = "button";
        tile.dataset.focusKey = `tile:${entityId}`;
        tile.addEventListener("click", () => this._moreInfo(entityId));
        const label = document.createElement("div");
        label.className = "tile-label";
        label.textContent = labels[suffix] || fallback;
        const value = document.createElement("div");
        value.className = "tile-value";
        value.textContent = state && !["unknown", "unavailable"].includes(state.state)
          ? this._number(state.state, suffix === "saved_emissions" ? 2 : 1) : "—";
        const unit = state?.attributes?.unit_of_measurement;
        if (unit) {
          const unitLabel = document.createElement("span");
          unitLabel.className = "tile-unit";
          unitLabel.textContent = ` ${unit}`;
          value.append(unitLabel);
        }
        tile.append(label, value);
        metricGrid.append(tile);
        metricCount += 1;
      }
      if (metricGrid.childElementCount) {
        const periodLabel = document.createElement("h4");
        periodLabel.className = "period";
        periodLabel.textContent = labels[period];
        metricSection.append(periodLabel, metricGrid);
      }
    }
    if (!metricCount) this._appendMessage(metricSection, labels.noMetrics);

    const historySection = this._section(content, labels.history);
    historySection.id = "eco-coach-history";
    historySection.querySelector("h3").tabIndex = -1;
    if (this._refreshError) {
      this._appendMessage(historySection, labels[this._refreshError === "unavailable"
        ? "refreshUnavailable" : "refreshFailed"], true);
    }
    if (this._historyError) {
      this._appendMessage(historySection, labels.historyError, true);
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "refresh";
      retry.textContent = labels.retry;
      retry.dataset.focusKey = "retry";
      retry.addEventListener("click", () => this._fetchHistory());
      historySection.append(retry);
    }
    else if (this._historyLoading) this._appendMessage(historySection, labels.loading);
    else if (this._history.awards.length === 0 && this._historyOffset === 0) this._appendMessage(historySection, labels.noAwards);
    else {
      const awards = document.createElement("div");
      awards.className = "awards";
      const dateFormatter = new Intl.DateTimeFormat(this._hass?.language || "en", {
        dateStyle: "medium",
        timeStyle: "short",
      });
      for (const award of this._history.awards) {
        const row = document.createElement("div");
        row.className = "award";
        const dot = document.createElement("div");
        dot.className = "dot";
        dot.setAttribute("aria-hidden", "true");
        dot.textContent = (labels[award.category] || award.category).slice(0, 1).toLocaleUpperCase(language);
        const detail = document.createElement("div");
        const name = document.createElement("div");
        name.className = "award-name";
        name.textContent = labels[award.category] || award.category;
        const date = document.createElement("div");
        date.className = "award-date";
        date.textContent = dateFormatter.format(new Date(award.occurred_at));
        detail.append(name, date);
        const points = document.createElement("div");
        points.className = "award-points";
        points.textContent = `+${this._number(award.points)}`;
        row.append(dot, detail, points);
        awards.append(row);
      }
      historySection.append(awards);
      const paging = document.createElement("div");
      paging.className = "paging";
      const previous = document.createElement("button");
      previous.type = "button";
      previous.textContent = labels.previous;
      previous.dataset.focusKey = "page:previous";
      previous.disabled = this._historyLoading || this._historyOffset === 0;
      previous.addEventListener("click", () => this._fetchHistory(false, Math.max(0, this._historyOffset - HISTORY_PAGE_SIZE)));
      const range = document.createElement("span");
      range.textContent = labels.historyRange(
        this._historyOffset + 1, this._historyOffset + this._history.awards.length, this._history.total,
      );
      const next = document.createElement("button");
      next.type = "button";
      next.textContent = labels.next;
      next.dataset.focusKey = "page:next";
      next.disabled = this._historyLoading || !this._history.awards.length
        || this._historyOffset + this._history.awards.length >= this._history.total;
      next.addEventListener("click", () => this._fetchHistory(false, this._historyOffset + this._history.awards.length));
      paging.append(previous, range, next);
      historySection.append(paging);
    }

    card.append(content);
    this.shadowRoot.replaceChildren(style, card);
    if ((active || this._pendingFocusKey) && focusKey) {
      const controls = [...this.shadowRoot.querySelectorAll("[data-focus-key]")];
      const target = controls.find((control) => control.dataset.focusKey === focusKey && !control.disabled);
      if (target) {
        target.focus();
        this._pendingFocusKey = null;
      } else if (focusKey.startsWith("page:")) {
        this._pendingFocusKey = this._historyLoading ? focusKey : null;
        const fallback = this._historyLoading ? null : controls.find((control) =>
          control.dataset.focusKey.startsWith("page:") && !control.disabled);
        (fallback || historySection.querySelector("h3")).focus();
      } else if (focusKey === "reimport" && this._refreshing) {
        this._pendingFocusKey = focusKey;
        historySection.querySelector("h3").focus();
      } else {
        this._pendingFocusKey = null;
      }
    }
  }
}

if (typeof customElements !== "undefined") {
  if (!customElements.get(CARD_TYPE)) customElements.define(CARD_TYPE, EcoCoachCard);
  if (!customElements.get("mbecocoach-card-editor")) {
    customElements.define("mbecocoach-card-editor", EcoCoachCardEditor);
  }
}

if (typeof window !== "undefined") {
  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === CARD_TYPE)) {
    window.customCards.push({
      type: CARD_TYPE,
      name: "Mercedes Eco Coach",
      description: "Account points, point history, and Eco Coach driving statistics.",
      preview: true,
    });
  }
}
