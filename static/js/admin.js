let editingId = null;
let editingEntity = null;
let editingGroup = null;
let allData = {};

const GROUPS = { Trackless: 'trackless', Convencional: 'convencional', Electrico: 'electrico' };
const ENTITY_GROUPS = ['macroprocesos', 'tipos_trabajo', 'acciones'];

document.addEventListener('DOMContentLoaded', () => {
    if (sessionStorage.getItem('admin_verified') === 'true') unlockAdmin();
});

async function verifyPassword() {
    const pw = document.getElementById('adminPassword').value;
    try {
        const r = await fetch('/api/admin/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pw }),
        });
        if (r.ok) {
            sessionStorage.setItem('admin_verified', 'true');
            unlockAdmin();
        } else {
            document.getElementById('passwordError').classList.remove('d-none');
            document.getElementById('adminPassword').value = '';
        }
    } catch {
        document.getElementById('passwordError').classList.remove('d-none');
    }
}

function unlockAdmin() {
    document.getElementById('passwordOverlay').classList.add('d-none');
    document.getElementById('adminContent').classList.remove('d-none');
    loadAllPanels();
}

async function fetchWithTimeout(url, ms = 8000) {
    const ctrl = new AbortController();
    const id = setTimeout(() => ctrl.abort(), ms);
    try {
        const r = await fetch(url, { signal: ctrl.signal });
        clearTimeout(id);
        return r;
    } catch {
        clearTimeout(id);
        throw new Error('timeout');
    }
}

async function loadAllPanels() {
    const entities = ['equipos', 'colaboradores', 'macroprocesos', 'tipos_trabajo', 'acciones', 'niveles', 'turnos'];
    for (const e of entities) {
        try {
            const r = await fetchWithTimeout(`/api/admin/${e}`);
            allData[e] = await r.json();
        } catch { allData[e] = []; }
    }
    renderIndependentPanels();
    for (const g of Object.keys(GROUPS)) {
        renderUnifiedView(g);
    }
}

function switchMainTab(tab) {
    document.querySelectorAll('.main-tab-content').forEach(el => el.classList.add('d-none'));
    const t = document.getElementById(`tab-${tab}`);
    if (t) t.classList.remove('d-none');
    document.querySelectorAll('#mainTabs .nav-link').forEach(el => el.classList.remove('active'));
    document.querySelector(`#mainTabs [data-tab="${tab}"]`)?.classList.add('active');
    if (tab === 'racs' && typeof loadRacsAdmin === 'function') loadRacsAdmin();
}

// ─── Independent panels ───

function renderIndependentPanels() {
    ['equipos', 'colaboradores', 'niveles', 'turnos'].forEach(e => {
        const items = allData[e] || [];
        const panel = document.getElementById(`panel-${e}`);
        if (!panel) return;
        if (!items.length) { panel.innerHTML = '<p class="text-muted small p-2 mb-0">Sin datos</p>'; return; }

        if (e === 'equipos') {
            // Group equipment by action_group
            const groups = { Trackless: [], Convencional: [], Otros: [] };
            items.forEach(cat => {
                const g = cat.action_group === 'Trackless' ? 'Trackless' : cat.action_group === 'Convencional' ? 'Convencional' : 'Otros';
                groups[g].push(cat);
            });
            const groupConfig = [
                { key: 'Trackless', label: 'Trackless', icon: 'bi-truck', color: 'info' },
                { key: 'Convencional', label: 'Convencional', icon: 'bi-tools', color: 'success' },
                { key: 'Otros', label: 'Sin grupo', icon: 'bi-question-circle', color: 'secondary' },
            ];
            let html = '';
            groupConfig.forEach(gc => {
                const list = groups[gc.key];
                if (!list.length) return;
                html += `<div class="mb-2">
                    <div class="d-flex align-items-center gap-2 px-2 py-1" style="border-bottom:1px solid rgba(255,255,255,.06);">
                        <i class="bi ${gc.icon} text-${gc.color}"></i>
                        <span class="fw-bold small text-${gc.color}">${gc.label}</span>
                        <span class="badge bg-${gc.color} bg-opacity-25 text-${gc.color}">${list.length}</span>
                    </div>
                    <div class="table-responsive"><table class="table table-dark table-sm mb-0"><tbody>`;
                list.forEach(cat => {
                    html += `<tr><td class="ps-2"><strong>${cat.name}</strong> <span class="text-muted small">(${cat.subitems?.length||0} sub)</span></td>
                        <td class="text-end text-nowrap">
                            <button class="btn btn-sm btn-outline-info py-0 px-1" onclick="editItem('equipos', ${cat.id})"><i class="bi bi-pencil"></i></button>
                            <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="deleteItem('equipos', ${cat.id})"><i class="bi bi-trash"></i></button>
                        </td></tr>`;
                });
                html += `</tbody></table></div></div>`;
            });
            panel.innerHTML = html || '<p class="text-muted small p-2 mb-0">Sin equipos</p>';

        } else if (e === 'colaboradores') {
            // Group collaborators by group_name
            const groups = { Trackless: [], Convencional: [], Electrico: [] };
            items.forEach(item => {
                const g = item.group_name === 'Trackless' ? 'Trackless' : item.group_name === 'Convencional' ? 'Convencional' : 'Electrico';
                if (!groups[g]) groups[g] = [];
                groups[g].push(item);
            });
            const groupConfig = [
                { key: 'Trackless', label: 'Trackless', icon: 'bi-truck', color: 'info' },
                { key: 'Convencional', label: 'Convencional', icon: 'bi-tools', color: 'success' },
                { key: 'Electrico', label: 'Eléctrico', icon: 'bi-lightning', color: 'warning' },
            ];
            let html = '';
            groupConfig.forEach(gc => {
                const list = groups[gc.key] || [];
                if (!list.length) return;
                html += `<div class="mb-2">
                    <div class="d-flex align-items-center gap-2 px-2 py-1" style="border-bottom:1px solid rgba(255,255,255,.06);">
                        <i class="bi ${gc.icon} text-${gc.color}"></i>
                        <span class="fw-bold small text-${gc.color}">${gc.label}</span>
                        <span class="badge bg-${gc.color} bg-opacity-25 text-${gc.color}">${list.length}</span>
                    </div>
                    <div class="d-flex flex-wrap gap-1 p-2">`;
                list.forEach(item => {
                    html += `<span class="badge bg-${gc.color} bg-opacity-10 text-${gc.color} fs-6 fw-normal px-3 py-2" style="border:1px solid rgba(255,255,255,.06);">${item.name}
                        <button class="btn btn-sm btn-outline-light py-0 px-1 ms-2" onclick="editItem('colaboradores', ${item.id})"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-sm btn-outline-danger py-0 px-1 ms-1" onclick="deleteItem('colaboradores', ${item.id})"><i class="bi bi-trash"></i></button>
                    </span>`;
                });
                html += `</div></div>`;
            });
            panel.innerHTML = html || '<p class="text-muted small p-2 mb-0">Sin colaboradores</p>';

        } else {
            let html = '<div class="d-flex flex-wrap gap-1 p-2">';
            items.forEach(item => {
                html += `<span class="badge bg-secondary fs-6 fw-normal px-3 py-2">${item.name}
                    <button class="btn btn-sm btn-outline-light py-0 px-1 ms-2" onclick="editItem('${e}', ${item.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="deleteItem('${e}', ${item.id})"><i class="bi bi-trash"></i></button>
                </span>`;
            });
            html += '</div>';
            panel.innerHTML = html;
        }
    });
}

// ─── Unified view per group (Macroprocess → WorkTypes → default Action) ───

function deriveTipoKey(group, macroName) {
    let moda = 'Mecánico';
    const n = macroName.toLowerCase();
    if (n.includes('eléctrico') || n.includes('electrico')) moda = 'Eléctrico';
    else if (n.includes('fabric') || n.includes('soldadura')) moda = 'Fabricacion_Soldadura';
    else if (n.includes('instal')) moda = 'Instalaciones';
    else if (n.includes('logistic')) moda = 'Logistica';
    else if (n.includes('servicio')) moda = 'Servicios';
    else if (n.includes('trabajo')) moda = 'Trabajos';
    return `${group}_${moda}`;
}

function getActionsForGroup(group) {
    return (allData['acciones'] || []).filter(a => {
        if (group === 'Trackless') return a.group_key === 'Trackless';
        if (group === 'Convencional') return a.group_key === 'Convencional' || a.group_key === 'Convencional_Electrico';
        if (group === 'Electrico') return a.group_key === 'Electrico' || a.group_key === 'Convencional_Electrico';
        return false;
    });
}

function renderUnifiedView(group) {
    const panel = document.getElementById(`panel-${GROUPS[group]}`);
    if (!panel) return;

    if (!allData['macroprocesos'] || !allData['tipos_trabajo'] || !allData['acciones']) {
        panel.innerHTML = '<div class="text-center py-3 text-muted small">Cargando...</div>';
        return;
    }

    const macroprocesos = allData['macroprocesos'].filter(m => m.group_key === group);
    const allWorkTypes = allData['tipos_trabajo'];
    const acciones = getActionsForGroup(group);
    const accionesHtml = acciones.map(a => `<option value="${a.name}">${a.name}</option>`).join('');

    if (!macroprocesos.length) {
        panel.innerHTML = `<div class="text-center py-3 text-muted small">No hay macroprocesos para ${group}. <br><button class="btn btn-sm btn-success mt-2" onclick="showAddForm('macroprocesos', '${group}')"><i class="bi bi-plus-lg"></i> Agregar Macroproceso</button></div>`;
        return;
    }

    let html = '';
    macroprocesos.forEach((macro, mi) => {
        const tipoKey = deriveTipoKey(group, macro.name);
        const children = allWorkTypes.filter(w => w.type_key === tipoKey);
        html += `<div class="card bg-dark border-secondary mb-3">
            <div class="card-header d-flex justify-content-between align-items-center py-2">
                <strong class="text-${group === 'Trackless' ? 'info' : group === 'Convencional' ? 'success' : 'warning'}">
                    ${group === 'Trackless' ? '🚜' : group === 'Convencional' ? '🔧' : '⚡'} ${macro.name}
                </strong>
                <div>
                    <button class="btn btn-sm btn-outline-secondary py-0 px-1 me-1" onclick="moveItem('macroprocesos', ${macro.id}, 'up')" ${mi===0?'disabled':''} title="Subir"><i class="bi bi-chevron-up"></i></button>
                    <button class="btn btn-sm btn-outline-secondary py-0 px-1 me-2" onclick="moveItem('macroprocesos', ${macro.id}, 'down')" ${mi===macroprocesos.length-1?'disabled':''} title="Bajar"><i class="bi bi-chevron-down"></i></button>
                    <button class="btn btn-sm btn-outline-info py-0 px-1" onclick="editItem('macroprocesos', ${macro.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="deleteItem('macroprocesos', ${macro.id})"><i class="bi bi-trash"></i></button>
                </div>
            </div>
            <div class="card-body p-2">
                <div class="table-responsive"><table class="table table-dark table-sm mb-0"><thead><tr>
                    <th style="width:40%">Trabajo</th>
                    <th style="width:35%">Acción por defecto</th>
                    <th style="width:25%"></th>
                </tr></thead><tbody>`;

        if (!children.length) {
            html += `<tr><td colspan="3" class="text-muted small">Sin trabajos asociados</td></tr>`;
        } else {
            children.forEach((wt, wi) => {
                const first = wi === 0;
                const last = wi === children.length - 1;
                const modalidad = (wt.type_key || '').replace(/^(Trackless|Convencional|Electrico)_/, '');
                html += `<tr>
                    <td class="ps-2">${wt.name} <span class="badge bg-secondary ms-1" style="font-size:0.6rem;">${modalidad}</span></td>
                    <td>
                        <select class="form-select form-select-sm default-action-select" data-wt-id="${wt.id}" style="max-width:220px;">
                            <option value="">— Sin acción —</option>
                            ${acciones.map(a => `<option value="${a.name}" ${wt.default_action === a.name ? 'selected' : ''}>${a.name}</option>`).join('')}
                        </select>
                    </td>
                    <td class="text-end text-nowrap">
                        <button class="btn btn-sm btn-outline-secondary py-0 px-1 me-1" onclick="moveItem('tipos_trabajo', ${wt.id}, 'up')" ${first?'disabled':''} title="Subir"><i class="bi bi-chevron-up"></i></button>
                        <button class="btn btn-sm btn-outline-secondary py-0 px-1 me-2" onclick="moveItem('tipos_trabajo', ${wt.id}, 'down')" ${last?'disabled':''} title="Bajar"><i class="bi bi-chevron-down"></i></button>
                        <button class="btn btn-sm btn-outline-info py-0 px-1" onclick="editItem('tipos_trabajo', ${wt.id})"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="deleteItem('tipos_trabajo', ${wt.id})"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>`;
            });
        }

        html += `</tbody></table></div>
                <button class="btn btn-sm btn-success mt-2" onclick="showAddWorkType('${group}', '${macro.name}')"><i class="bi bi-plus-lg"></i> Agregar trabajo a "${macro.name}"</button>
            </div>
        </div>`;
    });

    // Add action management at bottom
    html += `<div class="card bg-dark border-secondary mt-3">
        <div class="card-header py-2"><strong class="text-secondary">Acciones disponibles para ${group}</strong></div>
        <div class="card-body p-2">
            <div class="d-flex flex-wrap gap-1 align-items-center">
                ${acciones.map(a => `<span class="badge bg-secondary fs-6 fw-normal px-3 py-2">${a.name}
                    <button class="btn btn-sm btn-outline-light py-0 px-1 ms-1" onclick="editItem('acciones', ${a.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-sm btn-outline-danger py-0 px-1 ms-1" onclick="deleteItem('acciones', ${a.id})"><i class="bi bi-trash"></i></button>
                </span>`).join('')}
                <button class="btn btn-sm btn-outline-success ms-2" onclick="showAddForm('acciones', '${group === 'Trackless' ? 'Trackless' : group}')"><i class="bi bi-plus-lg"></i> Agregar acción</button>
            </div>
        </div>
    </div>`;

    panel.innerHTML = html;

    // Bind change events for default action selects
    panel.querySelectorAll('.default-action-select').forEach(sel => {
        sel.addEventListener('change', async function() {
            const wtId = this.dataset.wtId;
            const action = this.value;
            try {
                await fetch(`/api/admin/tipos_trabajo/${wtId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ default_action: action }),
                });
            } catch { alert('Error al guardar acción por defecto'); }
        });
    });
}

function showAddWorkType(group, macroName) {
    const tipoKey = deriveTipoKey(group, macroName);
    const modalidad = tipoKey.replace(/^(Trackless|Convencional|Electrico)_/, '');
    // Map modalidad back to category value
    const modeMap = {
        'Mecánico': 'Mecánico', 'Eléctrico': 'Eléctrico', 'Electrico': 'Eléctrico',
        'Fabricacion_Soldadura': 'Soldadura', 'Instalaciones': 'Instalaciones',
        'Logistica': 'Logistica', 'Servicios': 'Servicios', 'Trabajos': 'Trabajos'
    };
    const defMode = modeMap[modalidad] || 'Mecánico';
    editingId = null;
    editingEntity = 'tipos_trabajo';
    editingGroup = group;
    openFormModal(null, 'tipos_trabajo', group, tipoKey, defMode);
}

// ─── CRUD ───

function showAddForm(entity, groupKey) {
    editingId = null;
    editingEntity = entity;
    editingGroup = groupKey || null;
    openFormModal(null, entity, groupKey);
}

async function editItem(entity, id) {
    editingId = id;
    editingEntity = entity;
    try {
        const r = await fetch(`/api/admin/${entity}`);
        const items = await r.json();
        const item = items.find(i => i.id === id);
        if (item) openFormModal(item, entity);
    } catch (err) { alert('Error: ' + err.message); }
}

function openFormModal(item, entity, groupKey, presetTypeKey, presetMode) {
    const isEdit = item !== null;
    const labels = { macroprocesos: 'Macroproceso', tipos_trabajo: 'Tipo de Trabajo', acciones: 'Acción', equipos: 'Equipo', colaboradores: 'Colaborador', niveles: 'Nivel', turnos: 'Turno' };
    document.getElementById('formModalTitle').textContent = isEdit ? `Editar ${labels[entity]}` : `Agregar ${labels[entity]}`;

    let html = '';
    if (entity === 'macroprocesos') {
        const gk = isEdit ? item.group_key : (groupKey || 'Trackless');
        html += `<div class="mb-3"><label class="form-label">Grupo *</label>
            <select class="form-select" id="field_group_key" required>
                <option value="">Seleccionar...</option>
                ${['Trackless','Convencional','Electrico'].map(g => `<option value="${g}" ${gk===g?'selected':''}>Mantto. ${g}</option>`).join('')}
            </select></div>
            <div class="mb-3"><label class="form-label">Nombre del Macroproceso *</label>
            <input type="text" class="form-control" id="field_name" value="${isEdit ? item.name : ''}" required></div>`;
    } else if (entity === 'tipos_trabajo') {
        const rawKey = isEdit ? (item.type_key || '') : (presetTypeKey || '');
        const defGroup = groupKey || (rawKey.includes('_') ? rawKey.split('_')[0] : (rawKey || 'Trackless'));
        let rawMode = isEdit ? (rawKey.replace(/^(Trackless|Convencional|Electrico)_/, '') || rawKey) : (presetMode || 'Mecánico');
        const defMode = (rawMode === 'Fabricacion_Soldadura') ? 'Soldadura' : rawMode;
        html += `<div class="mb-3"><label class="form-label">Categoría *</label>
            <select class="form-select" id="field_mode" required             onchange="var m=this.value;var g=document.getElementById('field_group').value;var k;if(g!=='Trackless'&&(m==='Instalaciones'||m==='Soldadura')){k=m==='Instalaciones'?'Instalaciones':'Fabricacion_Soldadura'}else{k=g+'_'+m};document.getElementById('field_type_key').value=k">
                <option value="">Seleccionar...</option>
                <option value="Mecánico" ${defMode==='Mecánico'?'selected':''}>Mecánico</option>
                <option value="Eléctrico" ${defMode==='Eléctrico'?'selected':''}>Eléctrico</option>
                <option value="Soldadura" ${defMode==='Soldadura'?'selected':''}>Soldadura y Fabricación</option>
                <option value="Instalaciones" ${defMode==='Instalaciones'?'selected':''}>Instalaciones e Infraestructura</option>
                <option value="Logistica" ${defMode==='Logistica'?'selected':''}>Logística y Traslados</option>
                <option value="Servicios" ${defMode==='Servicios'?'selected':''}>Servicios Generales</option>
                <option value="Trabajos" ${defMode==='Trabajos'?'selected':''}>Trabajos Menos Frecuentes</option>
            </select>
            <div class="form-text text-muted small">Se asigna al grupo ${defGroup === 'Trackless' ? 'Trackless' : (defGroup === 'Convencional' ? 'Convencional' : 'Eléctrico')}.</div></div>
            <div class="mb-3"><label class="form-label">Nombre visible *</label>
            <input type="text" class="form-control" id="field_name" value="${isEdit ? item.name : ''}" required></div>
            <div class="mb-3"><label class="form-label">Acción por defecto</label>
            <select class="form-select" id="field_default_action">
                <option value="">— Sin acción —</option>
                ${getActionsForGroup(defGroup).map(a => `<option value="${a.name}" ${isEdit && item.default_action === a.name ? 'selected' : ''}>${a.name}</option>`).join('')}
            </select>
            <div class="form-text text-muted small">Al seleccionar este trabajo en el formulario, se auto-seleccionará esta acción.</div></div>
            <input type="hidden" id="field_type_key" value="${isEdit ? item.type_key : `${defGroup}_${defMode}`}">
            <input type="hidden" id="field_group" value="${defGroup}">`;
    } else if (entity === 'acciones') {
        const gk = isEdit ? item.group_key : (groupKey || 'Trackless');
        html += `<div class="mb-3"><label class="form-label">Aplica para *</label>
            <select class="form-select" id="field_group_key" required>
                <option value="">Seleccionar...</option>
                <option value="Trackless" ${gk==='Trackless'?'selected':''}>Mantto. Trackless</option>
                <option value="Convencional" ${gk==='Convencional'?'selected':''}>Mantto. Convencional</option>
                <option value="Electrico" ${gk==='Electrico'?'selected':''}>Mantto. Eléctrico</option>
                <option value="Convencional_Electrico" ${gk==='Convencional_Electrico'?'selected':''}>Ambos (Convencional + Eléctrico)</option>
            </select></div>
            <div class="mb-3"><label class="form-label">Nombre de la Acción *</label>
            <input type="text" class="form-control" id="field_name" value="${isEdit ? item.name : ''}" required></div>`;
    } else if (entity === 'equipos') {
        const name = isEdit ? item.name : '';
        const ag = isEdit ? item.action_group : '';
        html += `<div class="mb-3"><label class="form-label">Nombre del equipo *</label>
            <input type="text" class="form-control" id="field_name" value="${name}" required></div>
            <div class="mb-3"><label class="form-label">Grupo de acción *</label>
            <select class="form-select" id="field_action_group" required>
                <option value="">Seleccionar...</option>
                <option value="Trackless" ${ag==='Trackless'?'selected':''}>Trackless</option>
                <option value="Convencional" ${ag==='Convencional'?'selected':''}>Convencional</option>
            </select></div>
            <div class="mb-3"><label class="form-label">Sub-equipos</label>
            <div id="subitemsContainer">`;
        const subs = isEdit ? (item.subitems || []) : [];
        subs.forEach((s, i) => { html += subitemRow(s.name, s.meters, i); });
        html += `</div><button type="button" class="btn btn-sm btn-outline-success mt-1" onclick="addSubitemRow()"><i class="bi bi-plus"></i> Agregar sub-equipo</button></div>`;
    } else if (entity === 'colaboradores') {
        const gn = isEdit ? item.group_name : (groupKey || 'Trackless');
        html += `<div class="mb-3"><label class="form-label">Grupo *</label>
            <select class="form-select" id="field_group_name" required>
                ${['Trackless','Convencional','Electrico'].map(g => `<option value="${g}" ${gn===g?'selected':''}>Mantto. ${g}</option>`).join('')}
            </select></div>
            <div class="mb-3"><label class="form-label">Nombre *</label>
            <input type="text" class="form-control" id="field_name" value="${isEdit ? item.name : ''}" required></div>`;
    } else {
        html += `<div class="mb-3"><label class="form-label">Nombre *</label>
            <input type="text" class="form-control" id="field_name" value="${isEdit ? item.name : ''}" required></div>`;
    }

    document.getElementById('formFields').innerHTML = html;
    const fm = document.getElementById('formModal');
    if (typeof bootstrap !== 'undefined' && fm) {
        bootstrap.Modal.getInstance(fm)?.dispose();
        new bootstrap.Modal(fm).show();
    } else {
        alert('Error al abrir el modal. ¿Bootstrap cargado?');
    }
}

function updateTypeKey() {
    const group = document.getElementById('field_group')?.value;
    const mode = document.getElementById('field_mode')?.value;
    const keyField = document.getElementById('field_type_key');
    if (group && mode) keyField.value = `${group}_${mode}`;
    else keyField.value = '';
}

function subitemRow(name = '', meters = 'fin', idx = 0) {
    return `<div class="row g-2 mb-2 subitem-row">
        <div class="col-5"><input type="text" class="form-control form-control-sm" name="sub_name" value="${name}" placeholder="Nombre"></div>
        <div class="col-5"><input type="text" class="form-control form-control-sm" name="sub_meters" value="${meters}" placeholder="Medidores (fin, horometro_motor, ...)"></div>
        <div class="col-2"><button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('.subitem-row').remove()"><i class="bi bi-x"></i></button></div>
    </div>`;
}

function addSubitemRow() {
    const container = document.getElementById('subitemsContainer');
    if (container) container.insertAdjacentHTML('beforeend', subitemRow());
}

async function saveForm() {
    const entity = editingEntity;
    const data = {};
    const isEdit = editingId !== null;

    if (entity === 'macroprocesos') {
        data.group_key = document.getElementById('field_group_key').value;
        data.name = document.getElementById('field_name').value;
        if (!data.group_key || !data.name) { alert('Complete todos los campos'); return; }
    } else if (entity === 'tipos_trabajo') {
        data.type_key = document.getElementById('field_type_key').value;
        data.name = document.getElementById('field_name').value;
        data.default_action = document.getElementById('field_default_action').value;
        if (!data.type_key || !data.name) { alert('Complete todos los campos'); return; }
    } else if (entity === 'acciones') {
        data.group_key = document.getElementById('field_group_key').value;
        data.name = document.getElementById('field_name').value;
        if (!data.group_key || !data.name) { alert('Complete todos los campos'); return; }
    } else if (entity === 'equipos') {
        data.name = document.getElementById('field_name').value;
        data.action_group = document.getElementById('field_action_group').value;
        const rows = document.querySelectorAll('.subitem-row');
        data.subitems = Array.from(rows).map(row => ({
            name: row.querySelector('[name="sub_name"]').value,
            meters: row.querySelector('[name="sub_meters"]').value || 'fin',
        }));
        if (!data.name || !data.action_group) { alert('Complete todos los campos'); return; }
    } else if (entity === 'colaboradores') {
        data.group_name = document.getElementById('field_group_name').value;
        data.name = document.getElementById('field_name').value;
        if (!data.group_name || !data.name) { alert('Complete todos los campos'); return; }
    } else {
        data.name = document.getElementById('field_name').value;
        if (!data.name) { alert('Complete todos los campos'); return; }
    }

    try {
        let url = `/api/admin/${entity}`;
        let method = 'POST';
        if (isEdit) { url += `/${editingId}`; method = 'PUT'; }
        const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        if (!r.ok) { const err = await r.text(); throw new Error(err); }
        const fmEl = document.getElementById('formModal');
        if (fmEl) bootstrap.Modal.getInstance(fmEl)?.hide();
        await refreshAfterSave(entity);
    } catch (err) { alert('Error: ' + err.message); }
}

async function refreshAfterSave(entity) {
    try {
        const r = await fetch(`/api/admin/${entity}`);
        allData[entity] = await r.json();
    } catch { allData[entity] = []; }

    if (ENTITY_GROUPS.includes(entity)) {
        for (const g of Object.keys(GROUPS)) renderUnifiedView(g);
    } else {
        renderIndependentPanels();
    }
}

async function moveItem(entity, itemId, direction) {
    try {
        const r = await fetch(`/api/admin/${entity}/reorder/${itemId}?direction=${direction}`, { method: 'PUT' });
        if (r.ok) await refreshAfterSave(entity);
        else { const err = await r.json(); alert(err.detail || 'Error al reordenar'); }
    } catch { alert('Error de conexión'); }
}

async function deleteItem(entity, id) {
    if (!confirm('¿Está seguro de eliminar este elemento?')) return;
    try {
        const r = await fetch(`/api/admin/${entity}/${id}`, { method: 'DELETE' });
        if (!r.ok) throw new Error('Error al eliminar');
        await refreshAfterSave(entity);
    } catch (err) { alert('Error: ' + err.message); }
}

function showToast(msg, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const id = 'toast_' + Date.now();
    const bg = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-warning';
    container.insertAdjacentHTML('beforeend',
        `<div id="${id}" class="toast align-items-center text-white ${bg} border-0" role="alert">
            <div class="d-flex"><div class="toast-body">${msg}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div></div>`
    );
    const el = document.getElementById(id);
    if (el) { const t = new bootstrap.Toast(el, { delay: 3000 }); t.show(); }
}

async function saveAllAdmin() {
    const btn = document.querySelector('[onclick="saveAllAdmin()"]');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Guardando...'; }
    try {
        const entities = ['equipos', 'colaboradores', 'macroprocesos', 'tipos_trabajo', 'acciones', 'niveles', 'turnos'];
        for (const e of entities) {
            const r = await fetchWithTimeout(`/api/admin/${e}`);
            allData[e] = await r.json();
        }
        renderIndependentPanels();
        for (const g of Object.keys(GROUPS)) renderUnifiedView(g);
        showToast('✅ Todos los datos guardados correctamente');
    } catch {
        showToast('❌ Error al guardar los datos', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-check2-circle"></i> <span class="d-none d-sm-inline">Guardar todo</span>'; }
    }
}

// Tab switching on page load
document.addEventListener('DOMContentLoaded', () => {
    // Default to independent tab
});
