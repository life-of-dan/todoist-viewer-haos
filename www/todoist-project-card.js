/**
 * Todoist Project Card (read-only) — fixed build
 * File name should be: /local/todoist-project-card.js
 * Usage:
 *   type: custom:todoist-project-card
 *   entity: sensor.todoist_tasks
 *   show_completed: false
 */
class TodoistProjectCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._config || !this._config.entity) return;
    this._state = hass.states[this._config.entity];
    this.render();
  }

  setConfig(config) {
    if (!config.entity) throw new Error('entity is required');
    this._config = { show_completed: false, ...config };
    this.style.display = 'block';
    this.render();
  }

  getCardSize() {
    return 4;
  }

  render() {
    if (!this._hass || !this._config) return;
    const state = this._state;
    if (!state) {
      this.innerHTML =
        '<ha-card><div class="empty">Entity ' +
        this._config.entity +
        ' not found</div></ha-card>';
      return;
    }

    const attrs = state.attributes || {};
    const tasks = (attrs.tasks || [])
      .slice()
      .sort((a, b) => (a.order || 0) - (b.order || 0));
    const sections = attrs.sections || {};

    // Build hierarchy
    const byId = new Map();
    for (const t of tasks) {
      t.children = [];
      byId.set(t.id, t);
    }
    const roots = [];
    for (const t of tasks) {
      if (t.parent_id && byId.has(t.parent_id))
        byId.get(t.parent_id).children.push(t);
      else roots.push(t);
    }

    // Group roots by section
    const sectionGroups = {};
    for (const t of roots) {
      const sid = t.section_id || 'none';
      if (!sectionGroups[sid]) sectionGroups[sid] = [];
      sectionGroups[sid].push(t);
    }

    const showCompleted = !!this._config.show_completed;

    const escape = (str) =>
      String(str ?? '').replace(
        /[&<>"']/g,
        (m) =>
          ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
          }[m])
      );

    const renderLabels = (labels) => {
      if (!labels || !labels.length) return '';
      let html = '';
      for (const l of labels)
        html += '<span class="label">#' + escape(l) + '</span>';
      return html;
    };

    const renderDue = (due) => {
      if (!due) return '';
      const s = due.string || due.date || due.datetime || '';
      return '<span class="due">' + escape(s) + '</span>';
    };

    const renderTask = (t, depth) => {
      if (!showCompleted && t.completed) return '';
      const pClass = 'p' + (t.priority || 1);
      let html = '';
      html +=
        '<div class="task depth-' +
        depth +
        (t.completed ? ' completed' : '') +
        '">';
      html += '  <div class="bullet ' + pClass + '"></div>';
      html += '  <div class="content">';
      html += '    <div class="line">';
      html += '      <span class="text">' + escape(t.content || '') + '</span>';
      html += renderLabels(t.labels);
      html += renderDue(t.due);
      html += '    </div>';
      if (t.description)
        html += '    <div class="desc">' + escape(t.description) + '</div>';
      html += '  </div>';
      html += '</div>';
      if (t.children && t.children.length) {
        html += '<div class="children">';
        for (const c of t.children) html += renderTask(c, depth + 1);
        html += '</div>';
      }
      return html;
    };

    // Order sections
    const sectionOrder = Object.values(sections)
      .sort((a, b) => (a.order || 0) - (b.order || 0))
      .map((s) => s.id);
    const keys = Array.from(
      new Set(sectionOrder.concat(Object.keys(sectionGroups)))
    );

    // Build sections HTML first (avoid nested template literals)
    let sectionsHtml = '';
    for (const sid of keys) {
      const arr = sectionGroups[sid] || [];
      let items = '';
      for (const t of arr) items += renderTask(t, 0);
      if (!items) continue;
      const sObj = sections[sid];
      const title =
        sObj && sObj.name ? sObj.name : sid === 'none' ? '' : 'Section';
      sectionsHtml += '<div class="section">';
      if (title)
        sectionsHtml +=
          '<div class="section-title">' +
          escape(title) +
          '<hr class="separator"></div>';
      sectionsHtml += items + '</div>';
    }

    const emptyHtml =
      !tasks || tasks.length === 0 ? '<div class="empty">No tasks</div>' : '';
    this.innerHTML = `
      <ha-card>
        <div class="wrap">
          ${sectionsHtml}
          ${emptyHtml}
        </div>
      </ha-card>
      <style>
        .wrap{ padding: 12px 16px 16px; }
        .separator { width: 100%; overflow: visible; height: 0; margin-inline-start: 10px; border: 0.5px solid var(--primary-text-color); margin-block-start: auto; margin-block-end: auto; }
        .section{ margin-bottom: 12px; }
        .section-title{ font-weight:600; opacity:.8; margin:8px 0 6px; text-transform:uppercase; font-size:.72rem; letter-spacing:.04em; display: flex; flex-direction: row; }
        .task{ display:grid; grid-template-columns:16px 1fr; gap:10px; align-items:start; margin:6px 0; }
        .task .bullet{ margin-top:20%; width:12px; height:12px; border-radius:50%; border:2px solid var(--divider-color); }
        .task .bullet.p4{ border-color:#db4c3f; } .task .bullet.p3{ border-color:#eb8909; } .task .bullet.p2{ border-color:#246fe0; } .task .bullet.p1{ border-color:var(--divider-color); }
        .task.completed .text{ text-decoration:line-through; opacity:.6; }
        .task .line{ display:flex; gap:8px; align-items:baseline; justify-content:space-between; }
        .task .text{ font-size:1rem; font-weight:500; }
        .task .desc{ font-size:.9rem; opacity:.8; margin-top:2px; }
        .due{ font-size:.78rem; padding:2px 6px; border-radius:10px; background:var(--ha-card-background); border:1px solid var(--divider-color); opacity:.8; }
        .labels{ display:flex; flex-wrap:wrap; gap:6px; margin-top:6px; }
        .label{ font-size:.72rem; padding:2px 6px; border-radius:6px; background:rgba(127,127,127,.15); border:1px solid var(--divider-color); }
        .children{ margin-left:18px; border-left:1px dashed var(--divider-color); padding-left:12px; }
        .empty{ padding:16px; opacity:.7; }
      </style>
    `;
  }
}

if (!customElements.get('todoist-project-card')) {
  customElements.define('todoist-project-card', TodoistProjectCard);
}
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'todoist-project-card',
  name: 'Todoist Project Card',
  description:
    'Read-only card for displaying Todoist project tasks (with subtasks).',
});
