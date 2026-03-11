/**
 * Todoist Project Card
 * Resource URL: /api/todoist_viewer/todoist-project-card.js
 */
class TodoistProjectCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._config?.entity) {
      return;
    }

    this._state = hass.states[this._config.entity];
    this.render();
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('entity is required');
    }

    this._config = { show_completed: false, ...config };
    this.style.display = 'block';
    this.render();
  }

  getCardSize() {
    return 4;
  }

  render() {
    if (!this._hass || !this._config) {
      return;
    }

    const state = this._state;
    if (!state) {
      this.innerHTML =
        '<ha-card><div class="empty">Entity ' +
        this._config.entity +
        ' not found</div></ha-card>';
      return;
    }

    const attributes = state.attributes || {};
    const tasks = (attributes.tasks || [])
      .map((task) => ({ ...task, children: [] }))
      .sort((left, right) => (left.order || 0) - (right.order || 0));
    const sections = attributes.sections || {};

    const byId = new Map();
    for (const task of tasks) {
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
      task.children.sort((left, right) => (left.order || 0) - (right.order || 0));
    }

    const sectionGroups = {};
    for (const task of roots) {
      const sectionId = task.section_id || 'none';
      if (!sectionGroups[sectionId]) {
        sectionGroups[sectionId] = [];
      }
      sectionGroups[sectionId].push(task);
    }

    const showCompleted = Boolean(this._config.show_completed);

    const escape = (value) =>
      String(value ?? '').replace(
        /[&<>"']/g,
        (match) =>
          ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
          })[match]
      );

    const renderLabels = (labels) => {
      if (!labels?.length) {
        return '';
      }

      return labels
        .map((label) => '<span class="label">#' + escape(label) + '</span>')
        .join('');
    };

    const renderDue = (due) => {
      if (!due) {
        return '';
      }

      const dueString = due.string || due.date || due.datetime || '';
      return '<span class="due">' + escape(dueString) + '</span>';
    };

    const renderTask = (task, depth) => {
      if (!showCompleted && task.completed) {
        return '';
      }

      let html = '';
      html +=
        '<div class="task depth-' +
        depth +
        (task.completed ? ' completed' : '') +
        '">';
      html += '  <div class="bullet p' + (task.priority || 1) + '"></div>';
      html += '  <div class="content">';
      html += '    <div class="line">';
      html += '      <span class="text">' + escape(task.content || '') + '</span>';
      html += renderLabels(task.labels);
      html += renderDue(task.due);
      html += '    </div>';

      if (task.description) {
        html += '    <div class="desc">' + escape(task.description) + '</div>';
      }

      html += '  </div>';
      html += '</div>';

      if (task.children?.length) {
        html += '<div class="children">';
        for (const child of task.children) {
          html += renderTask(child, depth + 1);
        }
        html += '</div>';
      }

      return html;
    };

    const sectionOrder = Object.values(sections)
      .sort((left, right) => (left.order || 0) - (right.order || 0))
      .map((section) => section.id);
    const sectionKeys = Array.from(
      new Set(sectionOrder.concat(Object.keys(sectionGroups)))
    );

    let sectionsHtml = '';
    for (const sectionId of sectionKeys) {
      const sectionTasks = sectionGroups[sectionId] || [];
      const items = sectionTasks.map((task) => renderTask(task, 0)).join('');
      if (!items) {
        continue;
      }

      const section = sections[sectionId];
      const title =
        section?.name ? section.name : sectionId === 'none' ? '' : 'Section';

      sectionsHtml += '<div class="section">';
      if (title) {
        sectionsHtml +=
          '<div class="section-title">' +
          escape(title) +
          '<hr class="separator"></div>';
      }
      sectionsHtml += items;
      sectionsHtml += '</div>';
    }

    const emptyHtml =
      tasks.length === 0 ? '<div class="empty">No tasks</div>' : '';

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
        .section-title{ font-weight:600; opacity:.8; margin:8px 0 6px; text-transform:uppercase; font-size:.72rem; letter-spacing:.04em; display:flex; flex-direction:row; }
        .task{ display:grid; grid-template-columns:16px 1fr; gap:10px; align-items:start; margin:6px 0; }
        .task .bullet{ margin-top:20%; width:12px; height:12px; border-radius:50%; border:2px solid var(--divider-color); }
        .task .bullet.p4{ border-color:#db4c3f; } .task .bullet.p3{ border-color:#eb8909; } .task .bullet.p2{ border-color:#246fe0; } .task .bullet.p1{ border-color:var(--divider-color); }
        .task.completed .text{ text-decoration:line-through; opacity:.6; }
        .task .line{ display:flex; gap:8px; align-items:baseline; justify-content:space-between; }
        .task .text{ font-size:1rem; font-weight:500; }
        .task .desc{ font-size:.9rem; opacity:.8; margin-top:2px; }
        .due{ font-size:.78rem; padding:2px 6px; border-radius:10px; background:var(--ha-card-background); border:1px solid var(--divider-color); opacity:.8; }
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
  description: 'Read-only card for displaying Todoist project tasks and subtasks.',
});
