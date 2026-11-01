/*
 * Satel Integra alarm card – served by the satel_integra (extended) integration.
 *
 *   type: custom:satel-integra-alarm-card
 *   entity: alarm_control_panel.<panel>_wszystkie_strefy
 *
 * Partitions, zones, outputs, troubles and the event log are discovered from the
 * same Satel Integra entry. Optional: title, show_zones, show_outputs,
 * show_history (default true), confirm_outputs (default true), exclude (entity ids).
 */

const CARD_VERSION = "2026.11.6";

const FEATURE = { ARM_HOME: 1, ARM_AWAY: 2, ARM_NIGHT: 4, ARM_CUSTOM_BYPASS: 16 };

const I18N = {
  pl: {
    disarmed: "Czuwanie wyłączone",
    armed_away: ["Czuwanie pełne", "Uzbrojony – poza domem"],
    armed_custom_bypass: ["Pełne + blokady", "Częściowo uzbrojony"],
    armed_home: ["Bez wewnętrznych", "Uzbrojony – w domu"],
    armed_night: ["Bez wewnętrznych i opóźnień", "Uzbrojony – noc"],
    arming: "Czas na wyjście",
    pending: "Czas na wejście",
    triggered: "Alarm",
    unavailable: "Brak połączenia z centralą",
    unknown: "Stan nieznany",
    btn_away: ["Pełne", "Poza domem"],
    btn_custom_bypass: ["Pełne + blokady", "Niestandardowe"],
    btn_home: ["Bez wewnętrznych", "W domu"],
    btn_night: ["Bez wewn. i opóźnień", "Noc"],
    disarm: "Wyłącz czuwanie",
    clear: "Wyłącz i skasuj alarm",
    partitions: "Strefy",
    zones: "Wejścia",
    outputs: "Wyjścia",
    history: "Dziennik zdarzeń",
    load_history: "Pokaż ostatnie zdarzenia",
    loading: "Wczytywanie…",
    armed_of: (a, n) => (a === n ? (n === 1 ? "Strefa czuwa" : `Czuwają wszystkie strefy (${n})`) : `Czuwa ${a} z ${n} stref`),
    all_disarmed: (n) => (n === 1 ? "Strefa bez czuwania" : "Wszystkie strefy bez czuwania"),
    alarm_in: (names) => `Alarm: ${names}`,
    ready: "Gotowa do uzbrojenia",
    not_ready: (names) => `Naruszone wejścia: ${names}`,
    violated: "naruszone wejścia",
    alarm_memory: "pamięć alarmu",
    open: "Naruszone",
    closed: "Spokój",
    tamper: "Sabotaż",
    zone_alarm: "Alarm",
    bypassed: "Zablokowane",
    bypass: "Zablokuj wejście",
    unbypass: "Odblokuj wejście",
    on: "Włączone",
    off: "Wyłączone",
    confirm: "Dotknij ponownie",
    code: "Kod",
    cancel: "Anuluj",
    ok: "OK",
    troubles: "Awarie",
    service_mode: "Tryb serwisowy",
    no_events: "Brak nowych zdarzeń od uruchomienia",
    last_event: "Ostatnie zdarzenie",
    error: "Nie udało się",
    no_entity: "Wybierz panel „Wszystkie strefy” integracji Satel Integra (extended).",
  },
  en: {
    disarmed: "Disarmed",
    armed_away: ["Full arming", "Armed away"],
    armed_custom_bypass: ["Full + bypasses", "Partially armed"],
    armed_home: ["No interior zones", "Armed home"],
    armed_night: ["No interior, no delays", "Armed night"],
    arming: "Exit delay",
    pending: "Entry delay",
    triggered: "Alarm",
    unavailable: "Panel not connected",
    unknown: "Unknown state",
    btn_away: ["Full", "Away"],
    btn_custom_bypass: ["Full + bypasses", "Custom"],
    btn_home: ["No interior", "Home"],
    btn_night: ["No interior, no delays", "Night"],
    disarm: "Disarm",
    clear: "Disarm and clear alarm",
    partitions: "Partitions",
    zones: "Zones",
    outputs: "Outputs",
    history: "Event log",
    load_history: "Show recent events",
    loading: "Loading…",
    armed_of: (a, n) => (a === n ? `All partitions armed (${n})` : `${a} of ${n} partitions armed`),
    all_disarmed: (n) => (n === 1 ? "Partition disarmed" : "All partitions disarmed"),
    alarm_in: (names) => `Alarm: ${names}`,
    ready: "Ready to arm",
    not_ready: (names) => `Violated zones: ${names}`,
    violated: "violated zones",
    alarm_memory: "alarm memory",
    open: "Violated",
    closed: "Normal",
    tamper: "Tamper",
    zone_alarm: "Alarm",
    bypassed: "Bypassed",
    bypass: "Bypass zone",
    unbypass: "Unbypass zone",
    on: "On",
    off: "Off",
    confirm: "Tap again",
    code: "Code",
    cancel: "Cancel",
    ok: "OK",
    troubles: "Troubles",
    service_mode: "Service mode",
    no_events: "No new events since start",
    last_event: "Last event",
    error: "Failed",
    no_entity: "Select the “All partitions” panel of Satel Integra (extended).",
  },
};

const STATE_COLOR = {
  disarmed: "var(--satel-disarmed)",
  armed_away: "var(--satel-mode0)",
  armed_custom_bypass: "var(--satel-mode1)",
  armed_home: "var(--satel-mode2)",
  armed_night: "var(--satel-mode3)",
  arming: "var(--satel-arming)",
  pending: "var(--satel-pending)",
  triggered: "var(--satel-alarm)",
};

const STATE_ICON = {
  disarmed: "mdi:shield-off-outline",
  armed_away: "mdi:shield-lock",
  armed_custom_bypass: "mdi:shield-half-full",
  armed_home: "mdi:shield-home",
  armed_night: "mdi:shield-moon",
  arming: "mdi:shield-sync",
  pending: "mdi:shield-alert-outline",
  triggered: "mdi:shield-alert",
  unavailable: "mdi:shield-remove-outline",
};

const ZONE_ICON = {
  door: ["mdi:door-closed", "mdi:door-open"],
  garage_door: ["mdi:garage", "mdi:garage-open"],
  window: ["mdi:window-closed", "mdi:window-open"],
  motion: ["mdi:motion-sensor-off", "mdi:motion-sensor"],
  occupancy: ["mdi:home-outline", "mdi:home"],
  smoke: ["mdi:smoke-detector-variant", "mdi:smoke-detector-variant-alert"],
  moisture: ["mdi:water-off", "mdi:water-alert"],
  opening: ["mdi:square-outline", "mdi:square"],
  vibration: ["mdi:vibrate-off", "mdi:vibrate"],
  glass: ["mdi:window-closed-variant", "mdi:window-shutter-alert"],
};

const ARMED = ["armed_away", "armed_custom_bypass", "armed_home", "armed_night"];

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class SatelIntegraAlarmCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._pin = null; // {action, digits}
    this._confirm = null; // entity waiting for second tap
    this._history = null; // null = not loaded, [] = loaded
    this._historyLoading = false;
    this._busy = null;
    this._sig = "";
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("keydown", (ev) => this._onKey(ev));
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "entity", required: true, selector: { entity: { domain: "alarm_control_panel", integration: "satel_integra" } } },
        { name: "title", selector: { text: {} } },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "show_zones", default: true, selector: { boolean: {} } },
            { name: "show_outputs", default: true, selector: { boolean: {} } },
            { name: "show_history", default: true, selector: { boolean: {} } },
            { name: "confirm_outputs", default: true, selector: { boolean: {} } },
          ],
        },
      ],
    };
  }

  static getStubConfig(hass) {
    const entry = Object.values(hass.entities || {}).find(
      (e) => e.platform === "satel_integra" && String(e.translation_key || "").startsWith("all_partitions"),
    );
    return { entity: entry ? entry.entity_id : "" };
  }

  setConfig(config) {
    this._config = {
      show_zones: true,
      show_outputs: true,
      show_history: true,
      confirm_outputs: true,
      exclude: [],
      ...config,
    };
    this._sig = "";
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const sig = this._signature();
    if (sig !== this._sig) {
      this._sig = sig;
      this._render();
    }
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  // ---------- data ----------

  _t(key, ...args) {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").startsWith("pl") ? "pl" : "en";
    let v = I18N[lang][key];
    if (Array.isArray(v)) v = v[this._modes ? 0 : 1];
    return typeof v === "function" ? v(...args) : v;
  }

  _discover() {
    const hass = this._hass;
    const main = hass.entities?.[this._config.entity];
    const result = { partitions: [], zones: [], outputs: [], system: [], event: null };
    if (!main) return result;
    const entryIds = new Set(hass.devices?.[main.device_id]?.config_entries || []);
    const byDevice = {};
    for (const e of Object.values(hass.entities)) {
      if (e.platform !== "satel_integra" || e.hidden || this._config.exclude.includes(e.entity_id)) continue;
      const dev = hass.devices?.[e.device_id];
      if (!dev || !dev.config_entries.some((id) => entryIds.has(id))) continue;
      (byDevice[e.device_id] ||= []).push(e);
    }
    for (const [deviceId, ents] of Object.entries(byDevice)) {
      const find = (domain, tk) =>
        ents.find((e) => e.entity_id.startsWith(domain + ".") && (e.translation_key || null) === tk);
      if (deviceId === main.device_id) {
        result.system = ents.filter((e) => e.entity_id.startsWith("binary_sensor."));
        result.event = ents.find((e) => e.entity_id.startsWith("event."))?.entity_id || null;
        continue;
      }
      const panel = ents.find(
        (e) => e.entity_id.startsWith("alarm_control_panel.") && e.entity_id !== this._config.entity,
      );
      if (panel) {
        result.partitions.push({
          panel: panel.entity_id,
          violated: find("binary_sensor", "partition_violated_zones")?.entity_id,
          memory: find("binary_sensor", "partition_alarm_memory")?.entity_id,
        });
        continue;
      }
      const bypass = find("switch", "zone_bypass");
      const tamper = find("binary_sensor", "zone_tamper");
      const sensor = find("binary_sensor", null);
      if (sensor && (bypass || tamper)) {
        result.zones.push({
          sensor: sensor.entity_id,
          tamper: tamper?.entity_id,
          alarm: find("binary_sensor", "zone_alarm")?.entity_id,
          bypass: bypass?.entity_id,
        });
        continue;
      }
      const sw = find("switch", null);
      if (sw) result.outputs.push({ entity: sw.entity_id, switchable: true });
      else if (sensor) result.outputs.push({ entity: sensor.entity_id, switchable: false });
    }
    const st = (id) => hass.states[id];
    const num = (p) => st(p.panel)?.attributes.partition_number ?? 99;
    result.partitions.sort((a, b) => num(a) - num(b));
    const name = (id) => st(id)?.attributes.friendly_name || id;
    result.zones.sort((a, b) => name(a.sensor).localeCompare(name(b.sensor)));
    result.outputs.sort((a, b) => name(a.entity).localeCompare(name(b.entity)));
    return result;
  }

  _signature() {
    if (!this._hass || !this._config) return "";
    const d = (this._data = this._discover());
    const ids = [
      this._config.entity,
      d.event,
      ...d.system.map((e) => e.entity_id),
      ...d.partitions.flatMap((p) => [p.panel, p.violated, p.memory]),
      ...d.zones.flatMap((z) => [z.sensor, z.tamper, z.alarm, z.bypass]),
      ...d.outputs.map((o) => o.entity),
    ].filter(Boolean);
    return ids
      .map((id) => {
        const s = this._hass.states[id];
        return s ? `${id}=${s.state}:${s.last_updated}` : `${id}=-`;
      })
      .join("|");
  }

  // ---------- actions ----------

  _call(domain, service, data, target) {
    return this._hass.callService(domain, service, data, target).catch((err) => {
      this.dispatchEvent(
        new CustomEvent("hass-notification", {
          detail: { message: `${this._t("error")}: ${err?.message || err}` },
          bubbles: true,
          composed: true,
        }),
      );
    });
  }

  async _panelAction(action, code) {
    const service = {
      away: "alarm_arm_away",
      custom_bypass: "alarm_arm_custom_bypass",
      home: "alarm_arm_home",
      night: "alarm_arm_night",
      disarm: "alarm_disarm",
    }[action];
    this._busy = action;
    this._render();
    await this._call("alarm_control_panel", service, code ? { code } : {}, { entity_id: this._config.entity });
    this._busy = null;
    this._render();
  }

  _requestAction(action) {
    const main = this._hass.states[this._config.entity];
    const needsCode =
      main?.attributes.code_format && (action === "disarm" || main.attributes.code_arm_required !== false);
    if (needsCode) {
      this._pin = { action, digits: "" };
      this._render();
      this.shadowRoot.querySelector(".keypad")?.focus();
    } else {
      this._panelAction(action);
    }
  }

  _onKey(ev) {
    if (!this._pin) return;
    if (/^[0-9]$/.test(ev.key)) this._pinInput(ev.key);
    else if (ev.key === "Backspace") this._pinInput("back");
    else if (ev.key === "Enter") this._pinInput("ok");
    else if (ev.key === "Escape") this._pinInput("cancel");
    else return;
    ev.preventDefault();
  }

  _pinInput(key) {
    const pin = this._pin;
    if (!pin) return;
    if (key === "cancel") this._pin = null;
    else if (key === "back") pin.digits = pin.digits.slice(0, -1);
    else if (key === "ok") {
      this._pin = null;
      if (pin.digits) this._panelAction(pin.action, pin.digits);
    } else if (pin.digits.length < 16) pin.digits += key;
    this._render();
    this.shadowRoot.querySelector(".keypad")?.focus();
  }

  _toggleOutput(entityId) {
    if (this._config.confirm_outputs && this._confirm !== entityId) {
      this._confirm = entityId;
      clearTimeout(this._confirmTimer);
      this._confirmTimer = setTimeout(() => {
        this._confirm = null;
        this._render();
      }, 3000);
      this._render();
      return;
    }
    this._confirm = null;
    this._call("switch", "toggle", {}, { entity_id: entityId });
  }

  async _loadHistory() {
    this._historyLoading = true;
    this._render();
    try {
      const res = await this._hass.connection.sendMessagePromise({
        type: "call_service",
        domain: "satel_integra",
        service: "read_event_log",
        service_data: { count: 15 },
        return_response: true,
      });
      this._history = res?.response?.events || [];
    } catch (err) {
      this._history = [];
      this.dispatchEvent(
        new CustomEvent("hass-notification", {
          detail: { message: `${this._t("error")}: ${err?.message || err}` },
          bubbles: true,
          composed: true,
        }),
      );
    }
    this._historyLoading = false;
    this._render();
  }

  _moreInfo(entityId) {
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
  }

  _onClick(ev) {
    const el = ev.target.closest("[data-act]");
    if (!el) return;
    const { act, arg } = el.dataset;
    if (act === "arm") this._requestAction(arg);
    else if (act === "pin") this._pinInput(arg);
    else if (act === "info") this._moreInfo(arg);
    else if (act === "bypass") this._call("switch", "toggle", {}, { entity_id: arg });
    else if (act === "output") this._toggleOutput(arg);
    else if (act === "history") this._loadHistory();
  }

  // ---------- rendering ----------

  _ring(states) {
    const n = Math.max(states.length, 1);
    const r = 46;
    const c = 2 * Math.PI * r;
    const gap = n > 1 ? 9 : 0;
    const seg = c / n - gap;
    return states
      .map((s, i) => {
        const color = STATE_COLOR[s] || "var(--satel-unknown)";
        const offset = -(i * (c / n)) + c / 4;
        return `<circle class="seg ${s === "triggered" ? "alarm" : ""}" cx="60" cy="60" r="${r}" stroke="${color}"
          stroke-dasharray="${seg} ${c - seg}" stroke-dashoffset="${offset}"></circle>`;
      })
      .join("");
  }

  _render() {
    if (!this._config || !this._hass) return;
    const hass = this._hass;
    const main = hass.states[this._config.entity];
    if (!main) {
      this.shadowRoot.innerHTML = `${STYLE}<ha-card><div class="empty">${esc(this._t("no_entity"))}</div></ha-card>`;
      return;
    }
    const reg = hass.entities?.[this._config.entity];
    this._modes = String(reg?.translation_key || "").endsWith("_modes") || !!(main.attributes.supported_features & FEATURE.ARM_NIGHT);
    const d = this._data || this._discover();
    const state = main.state;
    const attrs = main.attributes;
    const parts = attrs.partitions ? Object.entries(attrs.partitions) : [];
    const partStates = parts.map(([, p]) => p.state);
    const armedCount = partStates.filter((s) => ARMED.includes(s)).length;
    const color = STATE_COLOR[state] || "var(--satel-unknown)";
    const label = this._t(state) || state;
    const alarmNames = parts.filter(([, p]) => p.state === "triggered").map(([n]) => n);
    const sub =
      state === "unavailable"
        ? ""
        : state === "triggered" && alarmNames.length
          ? this._t("alarm_in", alarmNames.join(", "))
          : armedCount
          ? this._t("armed_of", armedCount, parts.length)
          : this._t("all_disarmed", parts.length);
    const notReady = parts.filter(([, p]) => p.violated_zones).map(([n]) => n);
    const readiness =
      state === "disarmed" || attrs.partially_armed
        ? notReady.length
          ? `<span class="warn">${esc(this._t("not_ready", notReady.join(", ")))}</span>`
          : `<span>${esc(this._t("ready"))}</span>`
        : "";

    const f = attrs.supported_features || 0;
    const actions = [
      ["away", FEATURE.ARM_AWAY, "armed_away", "mdi:shield-lock"],
      ["custom_bypass", FEATURE.ARM_CUSTOM_BYPASS, "armed_custom_bypass", "mdi:shield-half-full"],
      ["home", FEATURE.ARM_HOME, "armed_home", "mdi:shield-home"],
      ["night", FEATURE.ARM_NIGHT, "armed_night", "mdi:shield-moon"],
    ].filter(([, bit]) => f & bit);
    const unavailable = state === "unavailable";
    const isArmedish = state !== "disarmed" && !unavailable;

    const buttons = actions
      .map(
        ([a, , s, icon]) => `<button class="mode ${state === s ? "current" : ""}" style="--c:${STATE_COLOR[s]}"
          data-act="arm" data-arg="${a}" ${unavailable || this._busy ? "disabled" : ""}>
          <ha-icon icon="${icon}"></ha-icon><span>${esc(this._t("btn_" + a))}</span></button>`,
      )
      .join("");
    const disarm = `<button class="disarm ${isArmedish ? "primary" : ""}" data-act="arm" data-arg="disarm"
        ${unavailable || this._busy ? "disabled" : ""}>
        <ha-icon icon="mdi:shield-off-outline"></ha-icon><span>${esc(this._t(state === "triggered" ? "clear" : "disarm"))}</span></button>`;

    const keypad = this._pin
      ? `<div class="keypad" tabindex="0" role="dialog" aria-label="${esc(this._t("code"))}">
          <div class="pin" aria-live="polite">${this._pin.digits ? "●".repeat(this._pin.digits.length) : `<span class="ph">${esc(this._t("code"))}</span>`}</div>
          <div class="keys">
            ${["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((k) => `<button data-act="pin" data-arg="${k}">${k}</button>`).join("")}
            <button data-act="pin" data-arg="back" aria-label="⌫"><ha-icon icon="mdi:backspace-outline"></ha-icon></button>
            <button data-act="pin" data-arg="0">0</button>
            <button class="ok" data-act="pin" data-arg="ok">${esc(this._t("ok"))}</button>
          </div>
          <button class="link" data-act="pin" data-arg="cancel">${esc(this._t("cancel"))}</button>
        </div>`
      : "";

    const partitionRows = d.partitions
      .map((p) => {
        const s = hass.states[p.panel];
        if (!s) return "";
        const ps = s.state;
        const chips = [];
        if (p.violated && hass.states[p.violated]?.state === "on") chips.push(["warn", this._t("violated")]);
        if (p.memory && hass.states[p.memory]?.state === "on") chips.push(["alarm", this._t("alarm_memory")]);
        return `<button class="part" data-act="info" data-arg="${p.panel}" style="--c:${STATE_COLOR[ps] || "var(--satel-unknown)"}">
          <span class="bar"></span>
          <span class="pname">${esc(s.attributes.friendly_name)}</span>
          <span class="pstate">${esc(this._t(ps) || ps)}</span>
          ${chips.map(([k, t]) => `<span class="chip ${k}">${esc(t)}</span>`).join("")}
        </button>`;
      })
      .join("");

    const zoneTiles = this._config.show_zones
      ? d.zones
          .map((z) => {
            const s = hass.states[z.sensor];
            if (!s) return "";
            const on = s.state === "on";
            const tamper = z.tamper && hass.states[z.tamper]?.state === "on";
            const alarm = z.alarm && hass.states[z.alarm]?.state === "on";
            const bypassed = z.bypass && hass.states[z.bypass]?.state === "on";
            const icons = ZONE_ICON[s.attributes.device_class] || ["mdi:shield-home-outline", "mdi:shield-home"];
            const cls = [on ? "on" : "", tamper ? "tamper" : "", alarm ? "alarm" : "", bypassed ? "bypassed" : ""].join(" ");
            const status = bypassed ? this._t("bypassed") : on ? this._t("open") : this._t("closed");
            return `<div class="zone ${cls}">
              <button class="zmain" data-act="info" data-arg="${z.sensor}">
                <ha-icon icon="${icons[on ? 1 : 0]}"></ha-icon>
                <span class="zname">${esc(s.attributes.friendly_name)}</span>
                <span class="zstate">${esc(status)}${tamper ? ` · ${esc(this._t("tamper"))}` : ""}${alarm ? ` · ${esc(this._t("zone_alarm"))}` : ""}</span>
              </button>
              ${
                z.bypass
                  ? `<button class="zbypass" data-act="bypass" data-arg="${z.bypass}" title="${esc(this._t(bypassed ? "unbypass" : "bypass"))}" aria-label="${esc(this._t(bypassed ? "unbypass" : "bypass"))}" aria-pressed="${bypassed}">
                      <ha-icon icon="${bypassed ? "mdi:lock" : "mdi:lock-open-variant-outline"}"></ha-icon></button>`
                  : ""
              }
            </div>`;
          })
          .join("")
      : "";

    const outputTiles = this._config.show_outputs
      ? d.outputs
          .map((o) => {
            const s = hass.states[o.entity];
            if (!s) return "";
            const on = s.state === "on";
            const confirming = this._confirm === o.entity;
            const tag = o.switchable ? "button" : "div";
            const act = o.switchable ? `data-act="output" data-arg="${o.entity}"` : "";
            return `<${tag} class="out ${on ? "on" : ""} ${confirming ? "confirm" : ""} ${o.switchable ? "" : "ro"}" ${act} aria-pressed="${on}">
              <span class="led"></span>
              <span class="oname">${esc(s.attributes.friendly_name)}</span>
              <span class="ostate">${esc(confirming ? this._t("confirm") : on ? this._t("on") : this._t("off"))}</span>
            </${tag}>`;
          })
          .join("")
      : "";

    const troubles = d.system
      .map((e) => hass.states[e.entity_id])
      .filter((s) => s && s.state === "on" && hass.entities[s.entity_id]?.translation_key !== "troubles_memory")
      .map((s) => `<button class="chip alarm" data-act="info" data-arg="${s.entity_id}">${esc(s.attributes.friendly_name)}</button>`)
      .join("");

    let history = "";
    if (this._config.show_history && d.event) {
      const ev = hass.states[d.event];
      const last =
        ev && ev.attributes.text
          ? `<div class="evt"><span class="etime">${esc(this._fmtTime(ev.attributes.time))}</span>
             <span class="etext">${esc(ev.attributes.text)}</span>
             <span class="esrc">${esc([ev.attributes.partition_name, ev.attributes.source_name].filter(Boolean).join(", "))}</span></div>`
          : `<div class="muted">${esc(this._t("no_events"))}</div>`;
      const list =
        this._history && this._history.length
          ? this._history
              .map(
                (e) => `<div class="evt ${e.class === "zone_alarm" || e.class === "partition_alarm" ? "is-alarm" : ""}">
              <span class="etime">${esc(this._fmtTime(e.time))}</span>
              <span class="etext">${esc(e.text || `#${e.code}`)}</span>
              <span class="esrc">${esc([e.partition_name, e.source_name].filter(Boolean).join(", "))}</span></div>`,
              )
              .join("")
          : "";
      history = `<section>
        <h3>${esc(this._t("history"))}</h3>
        ${this._history ? list || `<div class="muted">—</div>` : last}
        ${
          this._history
            ? ""
            : `<button class="link" data-act="history" ${this._historyLoading ? "disabled" : ""}>${esc(
                this._historyLoading ? this._t("loading") : this._t("load_history"),
              )}</button>`
        }
      </section>`;
    }

    const title = this._config.title
      ? `<div class="title">${esc(this._config.title)}</div>`
      : "";

    this.shadowRoot.innerHTML = `${STYLE}
      <ha-card class="${state}" style="--state:${color}">
        ${title}
        <div class="hero">
          <div class="ring ${state === "triggered" ? "pulse" : ""}">
            <svg viewBox="0 0 120 120" aria-hidden="true">
              <circle class="track" cx="60" cy="60" r="46"></circle>
              ${this._ring(partStates.length ? partStates : [state])}
            </svg>
            <ha-icon icon="${STATE_ICON[state] || "mdi:shield-outline"}"></ha-icon>
          </div>
          <div class="status">
            <div class="label">${esc(label)}</div>
            <div class="sub">${esc(sub)}</div>
            <div class="ready">${readiness}</div>
          </div>
        </div>
        ${keypad || `<div class="actions">${buttons}${disarm}</div>`}
        ${troubles ? `<div class="troubles">${troubles}</div>` : ""}
        ${partitionRows ? `<section><h3>${esc(this._t("partitions"))}</h3><div class="parts">${partitionRows}</div></section>` : ""}
        ${zoneTiles ? `<section><h3>${esc(this._t("zones"))}</h3><div class="zones">${zoneTiles}</div></section>` : ""}
        ${outputTiles ? `<section><h3>${esc(this._t("outputs"))}</h3><div class="outs">${outputTiles}</div></section>` : ""}
        ${history}
      </ha-card>`;
    if (this._pin) this.shadowRoot.querySelector(".keypad")?.focus();
  }

  _fmtTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const lang = this._hass?.locale?.language || this._hass?.language || "pl";
    const today = new Date();
    const sameDay = d.toDateString() === today.toDateString();
    return sameDay
      ? d.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" })
      : d.toLocaleString(lang, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }
}

const STYLE = `<style>
  :host {
    --satel-disarmed: #2f9e6e;
    --satel-mode0: #c8412f;
    --satel-mode1: #b04a7d;
    --satel-mode2: #d57a1f;
    --satel-mode3: #5b5fc7;
    --satel-arming: #d8a019;
    --satel-pending: #e2731a;
    --satel-alarm: #e52b2b;
    --satel-unknown: var(--disabled-text-color, #9e9e9e);
    --satel-violated: #e0a21a;
    --fg: var(--primary-text-color);
    --muted: var(--secondary-text-color);
    --line: var(--divider-color, rgba(127,127,127,.25));
    --tile: color-mix(in srgb, var(--fg) 4%, transparent);
  }
  ha-card { padding: 18px 18px 14px; overflow: hidden; }
  .title { font-size: 1rem; font-weight: 500; color: var(--muted); margin-bottom: 6px; }
  .empty { padding: 8px 0; color: var(--muted); }
  button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; text-align: left; }
  button:focus-visible, .keypad:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; border-radius: 10px; }
  button[disabled] { opacity: .45; cursor: default; }

  .hero { display: flex; align-items: center; gap: 18px; }
  .ring { position: relative; width: 104px; height: 104px; flex: none; }
  .ring svg { width: 100%; height: 100%; transform: rotate(0deg); }
  .ring .track { fill: none; stroke: var(--line); stroke-width: 9; }
  .ring .seg { fill: none; stroke-width: 9; stroke-linecap: butt; transition: stroke .4s; }
  .ring ha-icon { position: absolute; inset: 0; margin: auto; width: 40px; height: 40px; --mdc-icon-size: 40px; color: var(--state); }
  .ring.pulse { animation: pulse 1s ease-in-out infinite; }
  @keyframes pulse { 50% { transform: scale(1.05); filter: drop-shadow(0 0 10px var(--satel-alarm)); } }
  .status { min-width: 0; }
  .label { font-size: 1.55rem; line-height: 1.15; font-weight: 600; letter-spacing: -.01em; color: var(--state); }
  .sub { margin-top: 4px; color: var(--fg); font-variant-numeric: tabular-nums; }
  .ready { margin-top: 2px; color: var(--muted); font-size: .9rem; }
  .ready .warn { color: var(--satel-violated); }

  .actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 18px; }
  .mode, .disarm { display: flex; align-items: center; gap: 8px; min-height: 48px; padding: 8px 12px; border-radius: 12px;
    border: 1px solid var(--line); background: var(--tile); line-height: 1.2; min-width: 0; }
  .mode span { overflow-wrap: anywhere; }
  .mode ha-icon { color: var(--c); flex: none; }
  .mode.current { border-color: var(--c); background: color-mix(in srgb, var(--c) 16%, transparent); font-weight: 600; }
  .mode:hover:not([disabled]), .disarm:hover:not([disabled]) { border-color: var(--fg); }
  .disarm ha-icon { color: var(--satel-disarmed); flex: none; }
  .disarm { grid-column: 1 / -1; justify-content: center; }
  .disarm.primary { justify-content: center; background: var(--satel-disarmed); border-color: var(--satel-disarmed); color: #fff; font-weight: 600; }
  .disarm.primary ha-icon { color: #fff; }
  ha-card.triggered .disarm.primary { background: var(--satel-alarm); border-color: var(--satel-alarm); }

  .keypad { margin-top: 18px; display: grid; justify-items: center; gap: 10px; }
  .pin { font-size: 1.5rem; letter-spacing: .3em; min-height: 2rem; font-variant-numeric: tabular-nums; }
  .pin .ph { letter-spacing: 0; font-size: 1rem; color: var(--muted); }
  .keys { display: grid; grid-template-columns: repeat(3, 64px); gap: 8px; }
  .keys button { height: 52px; border-radius: 50%; border: 1px solid var(--line); background: var(--tile); text-align: center; font-size: 1.25rem; display: grid; place-items: center; }
  .keys button.ok { border-radius: 26px; font-size: .9rem; font-weight: 600; background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
  .link { color: var(--primary-color); padding: 6px 2px; font-size: .9rem; }

  .troubles { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
  section { margin-top: 18px; }
  h3 { margin: 0 0 8px; font-size: .95rem; font-weight: 600; color: var(--muted); }

  .parts { display: grid; gap: 2px; }
  .part { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 8px 4px 8px 0; border-radius: 8px; }
  .part:hover { background: var(--tile); }
  .part .bar { width: 4px; align-self: stretch; min-height: 22px; border-radius: 2px; background: var(--c); }
  .pname { font-weight: 500; }
  .pstate { color: var(--c); margin-left: auto; font-size: .92rem; }
  .chip { font-size: .78rem; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); }
  .chip.warn { color: var(--satel-violated); border-color: color-mix(in srgb, var(--satel-violated) 50%, transparent); }
  .chip.alarm { color: var(--satel-alarm); border-color: color-mix(in srgb, var(--satel-alarm) 50%, transparent); }

  .zones { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
  .zone { position: relative; display: flex; border-radius: 12px; background: var(--tile); border: 1px solid transparent; }
  .zmain { flex: 1; display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; column-gap: 10px; padding: 10px 6px 10px 12px; min-width: 0; }
  .zmain ha-icon { grid-row: 1 / 3; align-self: center; color: var(--muted); }
  .zname { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .zstate { font-size: .82rem; color: var(--muted); }
  .zone.on { background: color-mix(in srgb, var(--satel-violated) 14%, transparent); }
  .zone.on ha-icon { color: var(--satel-violated); }
  .zone.tamper, .zone.alarm { border-color: var(--satel-alarm); }
  .zone.tamper .zstate, .zone.alarm .zstate { color: var(--satel-alarm); }
  .zone.bypassed .zmain { opacity: .55; }
  .zbypass { width: 40px; display: grid; place-items: center; color: var(--muted); border-left: 1px solid var(--line); border-radius: 0 12px 12px 0; }
  .zone.bypassed .zbypass { color: var(--satel-mode2); }

  .outs { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
  .out { display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; column-gap: 10px; padding: 10px 12px; border-radius: 12px; background: var(--tile); }
  .out .led { grid-row: 1 / 3; align-self: center; width: 10px; height: 10px; border-radius: 50%; background: var(--line); }
  .out.on .led { background: var(--satel-arming); box-shadow: 0 0 8px var(--satel-arming); }
  .oname { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ostate { font-size: .82rem; color: var(--muted); }
  .out.confirm { outline: 2px solid var(--satel-arming); }
  .out.confirm .ostate { color: var(--satel-arming); font-weight: 600; }
  .out.ro { cursor: default; }

  .evt { display: grid; grid-template-columns: 5.5em 1fr; column-gap: 10px; padding: 5px 0; border-bottom: 1px solid var(--line); font-size: .9rem; }
  .evt:last-of-type { border-bottom: 0; }
  .etime { color: var(--muted); font-variant-numeric: tabular-nums; grid-row: 1 / 3; }
  .esrc { color: var(--muted); font-size: .82rem; }
  .evt.is-alarm .etext { color: var(--satel-alarm); }
  .muted { color: var(--muted); font-size: .9rem; }

  @media (prefers-reduced-motion: reduce) { .ring.pulse { animation: none; } .ring .seg { transition: none; } }
  @media (max-width: 420px) { .ring { width: 84px; height: 84px; } .label { font-size: 1.3rem; } }
</style>`;

if (!customElements.get("satel-integra-alarm-card")) {
  customElements.define("satel-integra-alarm-card", SatelIntegraAlarmCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "satel-integra-alarm-card",
    name: "Satel Integra – alarm",
    description: "Arming modes, partitions, zones, outputs and event log of a Satel INTEGRA panel.",
    preview: true,
    documentationURL: "https://github.com/tomaszsluszniak/ha-satel-integra-plus",
  });
  console.info(`%c SATEL-INTEGRA-ALARM-CARD %c ${CARD_VERSION} `, "background:#c8412f;color:#fff", "");
}
