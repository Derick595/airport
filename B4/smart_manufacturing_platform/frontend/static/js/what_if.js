const WhatIfLab = {
  initialized: false,

  init() {
    if (this.initialized) return;
    this.initialized = true;
    document.getElementById("what-if-type").addEventListener("change", () => this.updateResources());
    document.getElementById("what-if-form").addEventListener("submit", event => this.simulate(event));
    this.updateResources();
  },

  updateResources() {
    // `App` is declared with top-level `const`, so it is available globally to
    // sibling scripts but is intentionally not exposed as `window.App`.
    const data = typeof App !== "undefined" ? App.data : null;
    if (!data) return;
    const type = document.getElementById("what-if-type").value;
    const select = document.getElementById("what-if-resource");
    const resources = type === "machine_failure" ? data.machines.map(x => [x.id, `${x.id} - ${x.name}`])
      : type === "material_hold" ? data.materials.map(x => [x.lot_id, `${x.lot_id} - ${x.name}`])
      : data.operators.map(x => [x.id, `${x.id} - ${x.name}`]);
    select.replaceChildren(...resources.map(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      return option;
    }));
  },

  async simulate(event) {
    event.preventDefault();
    const button = event.currentTarget.querySelector("button[type='submit']");
    button.disabled = true;
    button.textContent = "Calculating cascade...";
    try {
      const result = await API.runWhatIf({
        scenario_type: document.getElementById("what-if-type").value,
        resource_id: document.getElementById("what-if-resource").value
      });
      this.render(result);
    } catch (error) {
      alert(error.message);
    } finally {
      button.disabled = false;
      button.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles mr-1"></i> Simulate impact';
    }
  },

  metric(label, value, tone) {
    const card = document.createElement("div");
    card.className = `bg-slate-900 border border-slate-800 rounded-xl p-4 what-if-${tone}`;
    const labelEl = document.createElement("div");
    labelEl.className = "text-xs text-slate-400";
    labelEl.textContent = label;
    const valueEl = document.createElement("div");
    valueEl.className = "text-2xl font-bold text-white mt-1";
    valueEl.textContent = value;
    card.append(labelEl, valueEl);
    return card;
  },

  render(result) {
    document.getElementById("what-if-empty").classList.add("hidden");
    const root = document.getElementById("what-if-results");
    root.classList.remove("hidden");
    root.replaceChildren();

    const metrics = document.createElement("div");
    metrics.className = "grid grid-cols-2 lg:grid-cols-4 gap-4";
    metrics.append(
      this.metric("Risk score", `${result.risk_score}/100`, result.risk_level.toLowerCase()),
      this.metric("Affected orders", String(result.affected_run_count), "violet"),
      this.metric("Units at risk", String(result.units_at_risk), "amber"),
      this.metric("Estimated delay", `${result.estimated_delay_hours}h`, "blue")
    );

    const panel = document.createElement("div");
    panel.className = "bg-slate-900 border border-slate-800 rounded-xl p-5 grid lg:grid-cols-3 gap-6";
    const impact = document.createElement("section");
    impact.className = "lg:col-span-2";
    const heading = document.createElement("h3");
    heading.className = "font-bold text-white";
    heading.textContent = result.title;
    const explanation = document.createElement("p");
    explanation.className = "text-xs text-slate-400 mt-1";
    explanation.textContent = result.explanation;
    impact.append(heading, explanation);
    const list = document.createElement("div");
    list.className = "mt-4 space-y-2";
    if (!result.affected_runs.length) {
      const safe = document.createElement("p");
      safe.className = "text-sm text-emerald-400";
      safe.textContent = "No active or queued order currently depends on this resource.";
      list.appendChild(safe);
    }
    result.affected_runs.forEach(run => {
      const row = document.createElement("div");
      row.className = "flex flex-wrap justify-between gap-2 bg-slate-800/70 rounded-lg p-3 text-xs";
      const name = document.createElement("span");
      name.className = "text-slate-200";
      name.textContent = `${run.order_number} · ${run.product_name}`;
      const status = document.createElement("span");
      status.className = run.overdue ? "text-rose-400 font-bold" : "text-amber-300 font-bold";
      status.textContent = `${run.status} · ${run.remaining_units} units${run.overdue ? " · OVERDUE" : ""}`;
      row.append(name, status);
      list.appendChild(row);
    });
    impact.appendChild(list);

    const action = document.createElement("section");
    const actionTitle = document.createElement("h3");
    actionTitle.className = "font-bold text-white";
    actionTitle.textContent = "Recommended response";
    const steps = document.createElement("ol");
    steps.className = "mt-3 space-y-3 text-xs text-slate-300";
    result.recommended_response.forEach((text, index) => {
      const step = document.createElement("li");
      step.className = "flex gap-2";
      const number = document.createElement("span");
      number.className = "what-if-step";
      number.textContent = String(index + 1);
      const copy = document.createElement("span");
      copy.textContent = text;
      step.append(number, copy);
      steps.appendChild(step);
    });
    const alternatives = document.createElement("p");
    alternatives.className = "mt-4 text-xs text-cyan-400";
    alternatives.textContent = result.alternatives.length ? `Available alternatives: ${result.alternatives.join(", ")}` : "No immediate alternative is available.";
    action.append(actionTitle, steps, alternatives);
    panel.append(impact, action);
    root.append(metrics, panel);
  }
};

window.WhatIfLab = WhatIfLab;
