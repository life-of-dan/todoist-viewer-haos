/**
 * Todoist Project Card
 * Resource URL: /api/todoist_viewer/todoist-project-card.js
 */
const TODOIST_PROJECT_CARD_TAG = "todoist-project-card";
const TODOIST_PROJECT_CARD_EDITOR_TAG = "todoist-project-card-editor";

class TodoistProjectCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement(TODOIST_PROJECT_CARD_EDITOR_TAG);
  }

  static getStubConfig(hass) {
    const entity = getTodoistViewerEntities(hass)[0]?.entity_id;
    return entity ? { entity, show_completed: false } : { show_completed: false };
  }

  set hass(hass) {
    this._hass = hass;
    this._state = this._config?.entity ? hass.states[this._config.entity] : null;
    this.render();
  }

  setConfig(config) {
    this._config = { show_completed: false, ...config };
    this.style.display = "block";
    this.render();
  }

  getCardSize() {
    return 4;
  }

  render() {
    if (!this._hass || !this._config) {
      return;
    }

    if (!this._config.entity) {
      this.innerHTML =
        '<ha-card><div class="empty">Select a Todoist Viewer sensor in the card editor.</div></ha-card>';
      return;
    }

    const state = this._state;
    if (!state) {
      this.innerHTML =
        "<ha-card><div class=\"empty\">Entity " +
        escapeHtml(this._config.entity) +
        " not found</div></ha-card>";
      return;
    }

    const attributes = state.attributes || {};
    const allTasks = normalizeTasks(attributes.tasks || []);
    const sections = normalizeSections(attributes.sections || {});
    const projects = normalizeProjects(attributes.projects || {}, state);
    const showCompleted = Boolean(this._config.show_completed);
    const selectedProjectId = String(this._config.project_id || "");
    const selectedProject = projects.find(
      (project) => project.id === selectedProjectId
    );

    let contentHtml = "";

    if (selectedProjectId) {
      contentHtml = renderProjectContent({
        projectTitle: selectedProject?.name || "",
        tasks: allTasks.filter((task) => task.project_id === selectedProjectId),
        sections,
        showCompleted,
        showProjectTitle: false,
      });
    } else if (projects.length > 1) {
      contentHtml = projects
        .map((project) =>
          renderProjectContent({
            projectTitle: project.name,
            tasks: allTasks.filter((task) => task.project_id === project.id),
            sections,
            showCompleted,
            showProjectTitle: true,
          })
        )
        .join("");

      const unassignedTasks = allTasks.filter(
        (task) =>
          !task.project_id || !projects.some((project) => project.id === task.project_id)
      );
      contentHtml += renderProjectContent({
        projectTitle: "Unassigned",
        tasks: unassignedTasks,
        sections,
        showCompleted,
        showProjectTitle: unassignedTasks.length > 0,
      });
    } else {
      contentHtml = renderProjectContent({
        projectTitle: projects[0]?.name || "",
        tasks: allTasks,
        sections,
        showCompleted,
        showProjectTitle: false,
      });
    }

    const emptyHtml = contentHtml
      ? ""
      : '<div class="empty">No tasks</div>';

    this.innerHTML = `
      <ha-card>
        <div class="wrap">
          ${contentHtml}
          ${emptyHtml}
        </div>
      </ha-card>
      <style>
        .wrap { padding: 12px 16px 16px; }
        .project { margin-bottom: 18px; }
        .project:last-child { margin-bottom: 0; }
        .project-title {
          font-size: .82rem;
          font-weight: 700;
          letter-spacing: .06em;
          margin: 0 0 10px;
          text-transform: uppercase;
          opacity: .78;
        }
        .separator {
          width: 100%;
          overflow: visible;
          height: 0;
          margin-inline-start: 10px;
          border: 0.5px solid var(--primary-text-color);
          margin-block-start: auto;
          margin-block-end: auto;
        }
        .section { margin-bottom: 12px; }
        .section:last-child { margin-bottom: 0; }
        .section-title {
          font-weight: 600;
          opacity: .8;
          margin: 8px 0 6px;
          text-transform: uppercase;
          font-size: .72rem;
          letter-spacing: .04em;
          display: flex;
          flex-direction: row;
        }
        .task {
          display: grid;
          grid-template-columns: 16px 1fr;
          gap: 10px;
          align-items: start;
          margin: 6px 0;
        }
        .task .bullet {
          margin-top: 20%;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          border: 2px solid var(--divider-color);
        }
        .task .bullet.p4 { border-color: #db4c3f; }
        .task .bullet.p3 { border-color: #eb8909; }
        .task .bullet.p2 { border-color: #246fe0; }
        .task .bullet.p1 { border-color: var(--divider-color); }
        .task.completed .text { text-decoration: line-through; opacity: .6; }
        .task .line {
          display: flex;
          gap: 8px;
          align-items: baseline;
          justify-content: space-between;
          flex-wrap: wrap;
        }
        .task .text { font-size: 1rem; font-weight: 500; }
        .task .desc { font-size: .9rem; opacity: .8; margin-top: 2px; }
        .due {
          font-size: .78rem;
          padding: 2px 6px;
          border-radius: 10px;
          background: var(--ha-card-background);
          border: 1px solid var(--divider-color);
          opacity: .8;
        }
        .label {
          font-size: .72rem;
          padding: 2px 6px;
          border-radius: 6px;
          background: rgba(127, 127, 127, .15);
          border: 1px solid var(--divider-color);
        }
        .children {
          margin-left: 18px;
          border-left: 1px dashed var(--divider-color);
          padding-left: 12px;
        }
        .empty { padding: 16px; opacity: .7; }
      </style>
    `;
  }
}

class TodoistProjectCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = { show_completed: false, ...config };
    this._render();
  }

  _render() {
    if (!this.shadowRoot || !this._config) {
      return;
    }

    const entities = getTodoistViewerEntities(this._hass);
    const selectedState = this._config.entity
      ? this._hass?.states?.[this._config.entity]
      : null;
    const projectOptions = getProjectOptions(selectedState);
    const selectedProjectId = projectOptions.some(
      (project) => project.id === this._config.project_id
    )
      ? this._config.project_id
      : "";

    this.shadowRoot.innerHTML = `
      <style>
        .editor {
          display: grid;
          gap: 16px;
          padding: 4px 0;
        }
        .field {
          display: grid;
          gap: 6px;
        }
        .label {
          color: var(--secondary-text-color);
          font-size: .9rem;
          font-weight: 500;
        }
        .control,
        .toggle {
          box-sizing: border-box;
          width: 100%;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          background: var(--card-background-color, var(--ha-card-background, #fff));
          color: var(--primary-text-color);
          font: inherit;
        }
        .control {
          min-height: 44px;
          padding: 0 12px;
        }
        .toggle-wrap {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .toggle {
          width: 18px;
          height: 18px;
          margin: 0;
        }
        .hint {
          color: var(--secondary-text-color);
          font-size: .9rem;
          line-height: 1.4;
        }
      </style>
      <div class="editor">
        <label class="field">
          <span class="label">Todoist sensor</span>
          <select class="control" data-field="entity">
            <option value="">Select a Todoist Viewer sensor</option>
            ${entities
              .map(
                (state) =>
                  `<option value="${escapeHtml(state.entity_id)}"${
                    state.entity_id === this._config.entity ? " selected" : ""
                  }>${escapeHtml(getEntityLabel(state))}</option>`
              )
              .join("")}
          </select>
        </label>

        <label class="field">
          <span class="label">Show completed tasks</span>
          <span class="toggle-wrap">
            <input
              class="toggle"
              type="checkbox"
              data-field="show_completed"
              ${this._config.show_completed ? "checked" : ""}
            >
            <span>${this._config.show_completed ? "Enabled" : "Disabled"}</span>
          </span>
        </label>

        ${
          projectOptions.length > 1
            ? `
              <label class="field">
                <span class="label">Project</span>
                <select class="control" data-field="project_id">
                  ${projectOptions
                    .map(
                      (project) =>
                        `<option value="${escapeHtml(project.id)}"${
                          project.id === selectedProjectId ? " selected" : ""
                        }>${escapeHtml(project.name)}</option>`
                    )
                    .join("")}
                </select>
              </label>
            `
            : ""
        }

        ${
          entities.length === 0
            ? '<div class="hint">No Todoist Viewer sensors were found. Add the integration first, then reopen the editor.</div>'
            : ""
        }
      </div>
    `;

    this.shadowRoot
      .querySelector('[data-field="entity"]')
      ?.addEventListener("change", (event) => this._onEntityChanged(event));
    this.shadowRoot
      .querySelector('[data-field="show_completed"]')
      ?.addEventListener("change", (event) => this._onToggleChanged(event));
    this.shadowRoot
      .querySelector('[data-field="project_id"]')
      ?.addEventListener("change", (event) => this._onProjectChanged(event));
  }

  _onEntityChanged(event) {
    const entity = String(event.target.value || "");
    const nextConfig = { ...this._config, entity };
    const selectedState = entity ? this._hass?.states?.[entity] : null;
    const validProjectIds = new Set(
      getProjectOptions(selectedState).map((project) => project.id)
    );

    if (!validProjectIds.has(nextConfig.project_id || "")) {
      delete nextConfig.project_id;
    }

    this._updateConfig(nextConfig);
  }

  _onToggleChanged(event) {
    this._updateConfig({
      ...this._config,
      show_completed: Boolean(event.target.checked),
    });
  }

  _onProjectChanged(event) {
    const projectId = String(event.target.value || "");
    const nextConfig = { ...this._config };

    if (projectId) {
      nextConfig.project_id = projectId;
    } else {
      delete nextConfig.project_id;
    }

    this._updateConfig(nextConfig);
  }

  _updateConfig(config) {
    this._config = normalizeConfig(config);
    fireEvent(this, "config-changed", { config: this._config });
    this._render();
  }
}

function normalizeConfig(config) {
  const normalized = {
    show_completed: false,
    ...config,
  };

  if (!normalized.entity) {
    delete normalized.entity;
  }

  if (!normalized.project_id) {
    delete normalized.project_id;
  }

  normalized.show_completed = Boolean(normalized.show_completed);
  return normalized;
}

function getTodoistViewerEntities(hass) {
  if (!hass?.states) {
    return [];
  }

  return Object.values(hass.states)
    .filter((state) => isTodoistViewerState(state))
    .sort((left, right) => getEntityLabel(left).localeCompare(getEntityLabel(right)));
}

function isTodoistViewerState(state) {
  if (!state?.entity_id?.startsWith("sensor.")) {
    return false;
  }

  const attributes = state.attributes || {};
  return (
    Array.isArray(attributes.tasks) &&
    typeof attributes.sections === "object" &&
    typeof attributes.projects === "object"
  );
}

function getEntityLabel(state) {
  return (
    state.attributes?.friendly_name ||
    state.attributes?.name ||
    state.entity_id
  );
}

function getProjectOptions(state) {
  const projects = normalizeProjects(state?.attributes?.projects || {}, state);
  if (projects.length <= 1) {
    return projects;
  }

  return [{ id: "", name: "All projects" }, ...projects];
}

function normalizeProjects(projectMap, state) {
  const projects = Object.values(projectMap || {})
    .filter((project) => project && project.id)
    .map((project) => ({
      id: String(project.id),
      name: String(project.name || project.id),
      order: Number(project.order || 0),
    }))
    .sort(sortByOrderThenName);

  if (projects.length > 0) {
    return projects;
  }

  const taskProjectIds = Array.from(
    new Set(
      normalizeTasks(state?.attributes?.tasks || [])
        .map((task) => task.project_id)
        .filter(Boolean)
    )
  );

  if (taskProjectIds.length === 1) {
    return [
      {
        id: taskProjectIds[0],
        name: getEntityLabel(state),
        order: 0,
      },
    ];
  }

  return taskProjectIds.map((projectId, index) => ({
    id: projectId,
    name: projectId,
    order: index,
  }));
}

function normalizeTasks(tasks) {
  return (Array.isArray(tasks) ? tasks : [])
    .map((task) => ({
      ...task,
      id: String(task.id || ""),
      parent_id: task.parent_id ? String(task.parent_id) : null,
      project_id: task.project_id ? String(task.project_id) : null,
      section_id: task.section_id ? String(task.section_id) : null,
      order: Number(task.order || 0),
      priority: Number(task.priority || 1),
      completed: Boolean(task.completed),
      children: [],
    }))
    .sort(sortByOrderThenId);
}

function normalizeSections(sections) {
  const normalizedSections = {};
  for (const [sectionId, section] of Object.entries(sections || {})) {
    normalizedSections[String(sectionId)] = {
      id: String(section.id || sectionId),
      name: String(section.name || ""),
      order: Number(section.order || 0),
    };
  }

  return normalizedSections;
}

function renderProjectContent({
  projectTitle,
  tasks,
  sections,
  showCompleted,
  showProjectTitle,
}) {
  const sectionHtml = renderSections(tasks, sections, showCompleted);
  if (!sectionHtml) {
    return "";
  }

  return `
    <div class="project">
      ${showProjectTitle ? `<div class="project-title">${escapeHtml(projectTitle)}</div>` : ""}
      ${sectionHtml}
    </div>
  `;
}

function renderSections(tasks, sections, showCompleted) {
  const { roots } = buildTaskTree(tasks);
  const sectionGroups = {};

  for (const task of roots) {
    const sectionId = task.section_id || "none";
    if (!sectionGroups[sectionId]) {
      sectionGroups[sectionId] = [];
    }
    sectionGroups[sectionId].push(task);
  }

  const sectionOrder = Object.values(sections)
    .sort(sortByOrderThenName)
    .map((section) => section.id);
  const sectionKeys = Array.from(
    new Set(sectionOrder.concat(Object.keys(sectionGroups)))
  );

  return sectionKeys
    .map((sectionId) => {
      const sectionTasks = sectionGroups[sectionId] || [];
      const items = sectionTasks
        .map((task) => renderTask(task, 0, showCompleted))
        .join("");

      if (!items) {
        return "";
      }

      const section = sections[sectionId];
      const title =
        section?.name ? section.name : sectionId === "none" ? "" : "Section";

      return `
        <div class="section">
          ${
            title
              ? `<div class="section-title">${escapeHtml(title)}<hr class="separator"></div>`
              : ""
          }
          ${items}
        </div>
      `;
    })
    .join("");
}

function buildTaskTree(tasks) {
  const byId = new Map();
  for (const task of tasks) {
    task.children = [];
    byId.set(task.id, task);
  }

  const roots = [];
  for (const task of tasks) {
    if (task.parent_id && byId.has(task.parent_id)) {
      byId.get(task.parent_id).children.push(task);
    } else {
      roots.push(task);
    }
  }

  for (const task of tasks) {
    task.children.sort(sortByOrderThenId);
  }

  roots.sort(sortByOrderThenId);
  return { roots };
}

function renderTask(task, depth, showCompleted) {
  if (!showCompleted && task.completed) {
    return "";
  }

  let html = "";
  html +=
    `<div class="task depth-${depth}${task.completed ? " completed" : ""}">`;
  html += `  <div class="bullet p${task.priority || 1}"></div>`;
  html += '  <div class="content">';
  html += '    <div class="line">';
  html += `      <span class="text">${escapeHtml(task.content || "")}</span>`;
  html += renderLabels(task.labels);
  html += renderDue(task.due);
  html += "    </div>";

  if (task.description) {
    html += `    <div class="desc">${escapeHtml(task.description)}</div>`;
  }

  html += "  </div>";
  html += "</div>";

  if (task.children?.length) {
    const childrenHtml = task.children
      .map((child) => renderTask(child, depth + 1, showCompleted))
      .join("");

    if (childrenHtml) {
      html += `<div class="children">${childrenHtml}</div>`;
    }
  }

  return html;
}

function renderLabels(labels) {
  if (!Array.isArray(labels) || labels.length === 0) {
    return "";
  }

  return labels
    .map((label) => `<span class="label">#${escapeHtml(label)}</span>`)
    .join("");
}

function renderDue(due) {
  if (!due) {
    return "";
  }

  const dueString = due.string || due.date || due.datetime || "";
  return dueString
    ? `<span class="due">${escapeHtml(dueString)}</span>`
    : "";
}

function sortByOrderThenId(left, right) {
  return (
    Number(left.order || 0) - Number(right.order || 0) ||
    String(left.id || "").localeCompare(String(right.id || ""))
  );
}

function sortByOrderThenName(left, right) {
  return (
    Number(left.order || 0) - Number(right.order || 0) ||
    String(left.name || "").localeCompare(String(right.name || "")) ||
    String(left.id || "").localeCompare(String(right.id || ""))
  );
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (match) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[match]
  );
}

function fireEvent(node, type, detail = {}, options = {}) {
  const event = new Event(type, {
    bubbles: options.bubbles ?? true,
    cancelable: Boolean(options.cancelable),
    composed: options.composed ?? true,
  });
  event.detail = detail;
  node.dispatchEvent(event);
  return event;
}

if (!customElements.get(TODOIST_PROJECT_CARD_TAG)) {
  customElements.define(TODOIST_PROJECT_CARD_TAG, TodoistProjectCard);
}

if (!customElements.get(TODOIST_PROJECT_CARD_EDITOR_TAG)) {
  customElements.define(
    TODOIST_PROJECT_CARD_EDITOR_TAG,
    TodoistProjectCardEditor
  );
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: TODOIST_PROJECT_CARD_TAG,
  name: "Todoist Project Card",
  description:
    "Read-only card for displaying Todoist project tasks with a visual editor.",
});
