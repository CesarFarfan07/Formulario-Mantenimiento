let _racsPeriod = null;
let _allWorkers = [];

const RACS_TIPOS = [
    [1,"Caída de objetos"],[2,"Caída de personas"],[3,"Carga / descarga mineral / desmonte"],[4,"Dar servicio a equipo en funcionamiento"],
    [5,"Derrumbe, Deslizamiento"],[6,"Desactivar dispositivos de seguridad"],[7,"Desatoro de chutes, tolvas"],[8,"Desprendimiento de rocas"],
    [9,"Energía eléctrica"],[10,"Falta / En mal estado EPP"],[11,"Equipos, Herramientas defectuosos"],[12,"Explosivos"],
    [13,"Exposición a ruido"],[14,"Falta o fuga de aire / agua"],[15,"Falta accesorios / insumos / herramientas"],[16,"Fugas y/o derrames"],
    [17,"Guardas o barreras inadecuadas"],[18,"Herramientas"],[19,"Iluminación"],[20,"Incumplimiento a PETS/ Estándares"],
    [21,"Intoxicación por alimentos"],[22,"Izaje"],[23,"Manejo de residuos peligrosos"],[24,"Manga de ventilación"],
    [25,"Manipulación de materiales"],[26,"Maquinarias en movimiento"],[27,"No usa EPP / Uso inadecuado EPP"],[28,"Falta de orden / limpieza"],
    [29,"Perforación"],[30,"Radiación"],[31,"Residuos biológicos"],[32,"Residuos sólidos"],[33,"Seguros de sujeción"],
    [34,"Señalización (falta/ en mal estado)"],[35,"Sobresfuerzo o falsos movimientos"],[36,"Sostenimiento de labor"],[37,"Sustancias Peligrosas"],
    [38,"Temperaturas extremas"],[39,"Tránsito de vehículos"],[40,"Usar equipo o herramienta defectuoso"],[41,"Ventilación deficiente"],[42,"Otros"]
];

async function loadPeriod() {
    try {
        const r = await fetch('/api/racs/period');
        _racsPeriod = await r.json();
        const start = new Date(_racsPeriod.period_start);
        const end = new Date(_racsPeriod.period_end);
        const fmt = (d) => d.toLocaleDateString('es-PE', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
        document.querySelectorAll('#periodLabel, #dashboardPeriodLabel').forEach(el => {
            if (el) el.textContent = `Período: ${fmt(start)} → ${fmt(end)}`;
        });
    } catch (e) {
        console.error('Error loading period:', e);
    }
}

async function loadWorkers() {
    try {
        const r = await fetch('/api/racs/workers');
        _allWorkers = await r.json();
    } catch (e) {
        console.error('Error loading workers:', e);
    }
}

function getWorkerData(name) {
    for (const g of _allWorkers) {
        for (const w of g.workers) {
            if (w.name === name) return { group: g.group, guardia: w.guardia || '', cargo: w.cargo || '', on_site: w.on_site };
        }
    }
    return null;
}

function populateWorkerSelect() {
    const sel = document.getElementById('racsWorker');
    if (!sel) return;
    sel.innerHTML = '<option value="">Seleccionar...</option>';
    for (const group of _allWorkers) {
        const optGroup = document.createElement('optgroup');
        optGroup.label = group.group;
        for (const w of group.workers) {
            const opt = document.createElement('option');
            opt.value = w.name;
            const restLabel = w.on_site ? '' : ' (descanso)';
            opt.textContent = w.name + restLabel;
            opt.dataset.group = group.group;
            opt.dataset.guardia = w.guardia || '';
            opt.dataset.cargo = w.cargo || '';
            opt.dataset.onSite = w.on_site ? '1' : '0';
            optGroup.appendChild(opt);
        }
        sel.appendChild(optGroup);
    }
}

function populateChecklist() {
    const container = document.getElementById('racsChecklist');
    if (!container) return;
    container.innerHTML = '';
    for (const [num, label] of RACS_TIPOS) {
        const div = document.createElement('div');
        div.className = 'check-item';
        div.dataset.value = `${num}. ${label}`;
        div.innerHTML = `<span class="num">${num}</span>${label}`;
        div.addEventListener('click', function() {
            const wasSelected = this.classList.contains('selected');
            document.querySelectorAll('#racsChecklist .check-item').forEach(el => el.classList.remove('selected'));
            if (!wasSelected) this.classList.add('selected');
            const isOtros = this.dataset.value === '42. Otros';
            document.getElementById('racsOtrosContainer').style.display = isOtros && !wasSelected ? 'block' : 'none';
            if (!isOtros || wasSelected) document.getElementById('racsOtrosTexto').value = '';
            updateChecklistHidden();
        });
        container.appendChild(div);
    }
}

function updateChecklistHidden() {
    const selected = document.querySelector('#racsChecklist .check-item.selected');
    let val = selected ? selected.dataset.value : '';
    if (val === '42. Otros') {
        const texto = document.getElementById('racsOtrosTexto').value.trim();
        if (texto) val = `42. ${texto}`;
    }
    document.getElementById('racsTipoDescripcion').value = val;
    document.getElementById('racsDescripcionTipoLabel').textContent = val || '—';
}

async function loadNiveles() {
    const sel = document.getElementById('racsNivel');
    if (!sel) return;
    try {
        const r = await fetch('/api/options');
        const opts = await r.json();
        sel.innerHTML = '<option value="">Seleccionar...</option>';
        if (opts.niveles) {
            for (const n of opts.niveles) {
                const opt = document.createElement('option');
                opt.value = n;
                opt.textContent = n;
                sel.appendChild(opt);
            }
        }
    } catch (e) {
        console.error('Error loading niveles:', e);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadPeriod();
    await loadWorkers();
    populateWorkerSelect();
    populateChecklist();
    loadNiveles();
    updateWorkerDisplay();

    document.getElementById('racsWorker')?.addEventListener('change', updateWorkerDisplay);
    document.getElementById('racsOtrosTexto')?.addEventListener('input', updateChecklistHidden);

    const form = document.getElementById('racsForm');
    if (form) {
        form.addEventListener('submit', submitRacs);
    }

    if (document.getElementById('racsTeamsContainer')) {
        loadDashboard();
    }
});

function updateWorkerDisplay() {
    const sel = document.getElementById('racsWorker');
    if (!sel) return;
    const opt = sel.selectedOptions[0];
    if (opt && opt.value) {
        const cargo = opt.dataset.cargo || '';
        const guardia = opt.dataset.guardia || '';
        document.getElementById('racsCargoDisplay').value = cargo;
        document.getElementById('racsGuardiaDisplay').value = guardia ? `Guardia ${guardia}` : '—';
        document.getElementById('racsRecibeLabel').textContent = opt.value;
        document.getElementById('racsCargoAreaLabel').textContent = cargo || '—';
    } else {
        document.getElementById('racsCargoDisplay').value = '';
        document.getElementById('racsGuardiaDisplay').value = '';
    }
}

function getWorkerGroup(name) {
    const data = getWorkerData(name);
    return data ? data.group : '';
}

async function submitRacs(e) {
    e.preventDefault();
    const btn = document.getElementById('racsSubmitBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Enviando...';

    const workerName = document.getElementById('racsWorker').value;
    const categoria = document.getElementById('racsCategoria').value;
    const tipo = document.getElementById('racsTipo').value;
    const turno = document.getElementById('racsTurno').value;
    const tipoDescripcion = document.getElementById('racsTipoDescripcion').value;
    const descripcion = document.getElementById('racsDescripcion').value.trim();
    const accionCorrectiva = document.getElementById('racsAccion').value.trim();
    const ubicacion = document.getElementById('racsUbicacion').value.trim();
    const referencia = document.getElementById('racsReferencia').value.trim();
    const riesgo = document.getElementById('racsRiesgo').value;
    const nivel = document.getElementById('racsNivel').value;
    const fechaReporte = document.getElementById('racsFechaDisplay').value;
    const sendWA = document.getElementById('racsWAToggle')?.classList.contains('btn-success');

    if (!workerName) { alert('Selecciona un trabajador'); btn.disabled = false; btn.innerHTML = '<i class="bi bi-shield-check"></i> ENVIAR REPORTE RACS'; return; }
    if (!referencia) { alert('Escribe una referencia del lugar'); document.getElementById('racsReferencia').focus(); btn.disabled = false; btn.innerHTML = '<i class="bi bi-shield-check"></i> ENVIAR REPORTE RACS'; return; }
    if (!descripcion) { alert('Describe el reporte observado'); document.getElementById('racsDescripcion').focus(); btn.disabled = false; btn.innerHTML = '<i class="bi bi-shield-check"></i> ENVIAR REPORTE RACS'; return; }
    if (!accionCorrectiva) { alert('Escribe la acción correctiva propuesta o realizada'); document.getElementById('racsAccion').focus(); btn.disabled = false; btn.innerHTML = '<i class="bi bi-shield-check"></i> ENVIAR REPORTE RACS'; return; }

    const groupName = getWorkerGroup(workerName);

    try {
        const r = await fetch('/api/racs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ worker_name: workerName, group_name: groupName, categoria, tipo, turno, descripcion, ubicacion, referencia, nivel, fecha_reporte: fechaReporte, riesgo, accion_correctiva: accionCorrectiva, tipo_descripcion: tipoDescripcion }),
        });
        if (!r.ok) throw new Error(await r.text());
        const data = await r.json();
        let racsId = data.id;

        let waText = `🦺 *RACS REPORTADO*\n\n`;
        waText += `👤 Trabajador: ${workerName}\n`;
        waText += `📋 Categoría: ${categoria}\n`;
        waText += `📋 Tipo: ${tipo}\n`;
        waText += `🔄 Turno: ${turno}\n`;
        waText += `📅 Fecha: ${fechaReporte}\n`;
        waText += `📊 Nivel: ${nivel || '—'}\n`;
        waText += `📍 Ubicación: ${ubicacion || '—'}\n`;
        waText += `📍 Referencia: ${referencia || '—'}\n`;
        waText += `⚠️ Riesgo: ${riesgo}\n`;
        if (descripcion) waText += `📝 Descripción: ${descripcion}\n`;
        if (accionCorrectiva) waText += `🔧 Acción Correctiva: ${accionCorrectiva}\n`;
        if (tipoDescripcion) waText += `📌 Tipo específico: ${tipoDescripcion}\n`;
        waText += `\n_Período vigente_`;
        waText += `\n_Enviado desde Sistema RACS_`;

        let resultHtml = `<div class="alert alert-success">✅ RACS #${racsId} enviado correctamente. <a href="/api/racs/${racsId}/excel" target="_blank" class="btn btn-sm btn-outline-light ms-2"><i class="bi bi-file-earmark-excel"></i> Descargar Excel</a></div>`;
        resultHtml += `<div class="text-center d-flex gap-2 justify-content-center flex-wrap">`;
        if (sendWA !== false) {
            const waUrl = getWhatsAppUrl(waText);
            resultHtml += `<a href="${waUrl}" target="_blank" class="btn btn-success btn-sm px-3"><i class="bi bi-whatsapp me-1"></i> Abrir WhatsApp</a>`;
            setTimeout(() => window.open(waUrl, '_blank'), 300);
        }
        resultHtml += `<button onclick="copyToClipboard('${encodeURIComponent(waText).replace(/'/g, "\\'")}')" class="btn btn-outline-secondary btn-sm px-3"><i class="bi bi-clipboard me-1"></i> Copiar texto</button>`;
        resultHtml += `</div>`;

        document.getElementById('racsResult').innerHTML = resultHtml;
        document.getElementById('racsForm').reset();
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('racsFechaDisplay').value = today;
        document.getElementById('racsRiesgo').value = 'Alto';
        document.getElementById('racsTipo').value = 'Condición Subestándar';
        document.getElementById('racsCategoria').value = 'Seguridad y Salud Ocupacional';
        document.getElementById('racsTurno').value = 'DÍA';
        document.querySelectorAll('.check-item').forEach(el => el.classList.remove('selected'));
        document.getElementById('racsOtrosContainer').style.display = 'none';
        document.getElementById('racsOtrosTexto').value = '';
        document.querySelectorAll('.btn-option[data-tipo]').forEach((b,i) => { b.classList.toggle('active-cond', i===1); b.classList.toggle('active', i===1); });
        document.querySelectorAll('.btn-option[data-categoria]').forEach((b,i) => { b.classList.toggle('active-ss', i===0); b.classList.toggle('active', i===0); });
        document.querySelectorAll('.btn-option.turno').forEach((b,i) => b.classList.toggle('active', i===0));
        document.querySelectorAll('.riesgo-btn').forEach((b,i) => b.classList.toggle('active', i===0));
        updateChecklistHidden();
        updateWorkerDisplay();
    } catch (err) {
        document.getElementById('racsResult').innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-shield-check"></i> ENVIAR REPORTE RACS';
    }
}

document.getElementById('racsWAToggle')?.addEventListener('click', function() {
    this.classList.toggle('btn-success');
    this.classList.toggle('btn-outline-success');
    const icon = this.querySelector('i');
    if (this.classList.contains('btn-success')) {
        icon.style.color = '#fff';
    } else {
        icon.style.color = '#22c55e';
    }
});
if (document.getElementById('racsWAToggle')) {
    document.getElementById('racsWAToggle').classList.add('btn-success');
}

async function loadDashboard() {
    try {
        const r = await fetch('/api/racs/dashboard-data');
        const data = await r.json();

        document.getElementById('summaryComplete').textContent = data.summary.complete;
        document.getElementById('summaryPartial').textContent = data.summary.partial;
        document.getElementById('summaryMissing').textContent = data.summary.missing;
        document.getElementById('summaryTotal').textContent = data.summary.on_site;
        const restEl = document.getElementById('summaryRest');
        if (restEl) restEl.textContent = data.summary.on_rest;

        const container = document.getElementById('racsTeamsContainer');
        let html = '';
        for (const team of data.teams) {
            const onSite = team.workers.filter(w => w.on_site);
            const count2 = onSite.filter(w => w.count >= 2).length;
            const count1 = onSite.filter(w => w.count === 1).length;
            const count0 = onSite.filter(w => w.count === 0).length;
            html += `<div class="mb-3">
                <div class="d-flex align-items-center justify-content-between mb-1">
                    <span class="fw-bold" style="font-size:0.95rem;">👥 <span class="team-label">${team.team}</span></span>
                    <span class="small text-muted">✅ ${count2} 🟡 ${count1} 🔴 ${count0}</span>
                </div>`;
            for (const w of team.workers) {
                const bar = '█'.repeat(w.count) + '░'.repeat(Math.max(0, 2 - w.count));
                const cls = w.count >= 2 ? 'text-success' : w.count === 1 ? 'text-warning' : 'text-danger';
                const guardiaColors = {A:'#3b82f6', B:'#22c55e', C:'#f97316'};
                const gColor = guardiaColors[w.guardia] || '#6b7280';
                const gBadge = w.guardia ? `<span class="badge me-1" style="background:${gColor};color:#fff;font-size:0.65rem;border-radius:4px;">Guardia ${w.guardia}</span>` : '';
                if (w.on_site) {
                    html += `<div class="d-flex align-items-center justify-content-between py-1 px-2 rounded mb-1" style="background:rgba(30,41,59,0.5);" data-count="${w.count}" data-name="${w.name}">
                        <span>${gBadge} ${w.name}</span>
                        <span class="${cls} fw-bold">${bar} ${w.count}/2</span>
                    </div>`;
                } else {
                    html += `<div class="d-flex align-items-center justify-content-between py-1 px-2 rounded mb-1" style="background:rgba(30,41,59,0.15);opacity:0.65;" data-count="${w.count}" data-name="${w.name}">
                        <span><span class="text-warning me-1" title="Descanso">🌙</span>${gBadge} ${w.name} <span class="text-muted small">(descanso)</span></span>
                        <span class="text-muted small">${bar} ${w.count}/2</span>
                    </div>`;
                }
            }
            html += `</div>`;
        }
        container.innerHTML = html;
        loadRacsHistory();
    } catch (e) {
        document.getElementById('racsTeamsContainer').innerHTML = `<div class="alert alert-danger">Error: ${e.message}</div>`;
    }
}

async function loadRacsHistory() {
    const container = document.getElementById('racsHistoryContainer');
    try {
        const r = await fetch('/api/racs/list');
        const list = await r.json();
        if (!list.length) {
            container.innerHTML = '<p class="text-muted small">No hay RACS registrados en este período.</p>';
            return;
        }
        let html = '<div class="table-responsive" style="max-height:350px;overflow-y:auto;"><table class="table table-sm table-hover"><thead><tr class="table-dark"><th>#</th><th>Trabajador</th><th>Categoría</th><th>Tipo</th><th>Descripción</th><th>Riesgo</th><th>Nivel</th><th>Lugar</th><th>Referencia</th><th>Turno</th><th>Fecha</th><th></th></tr></thead><tbody>';
        for (const item of list) {
            const d = new Date(item.created_at);
            const dateFmt = d.toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
            const fechaR = item.fecha_reporte || dateFmt.split(',')[0];
            const riesgoColor = item.riesgo === 'Alto' ? 'text-danger' : item.riesgo === 'Medio' ? 'text-warning' : 'text-success';
            html += `<tr>
                <td>${item.id}</td>
                <td>${item.worker_name}</td>
                <td><span class="badge" style="background:${item.categoria === 'Medio Ambiente' ? '#10b981' : '#3b82f6'};">${item.categoria || '—'}</span></td>
                <td>${item.tipo === 'Acto Subestándar' ? '⚠️ Acto' : '⚠️ Condición'}</td>
                <td>${item.descripcion || '—'}</td>
                <td class="${riesgoColor} fw-bold">${item.riesgo || '—'}</td>
                <td>${item.nivel || '—'}</td>
                <td>${item.ubicacion || '—'}</td>
                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${item.referencia || ''}">${item.referencia || '—'}</td>
                <td>${item.turno || '—'}</td>
                <td>${fechaR}</td>
                <td><a href="/api/racs/${item.id}/excel" target="_blank" class="btn btn-outline-light btn-sm py-0 px-1" title="Descargar Excel"><i class="bi bi-file-earmark-excel"></i></a></td>
            </tr>`;
        }
        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<p class="text-danger">Error: ${e.message}</p>`;
    }
}

function getWhatsAppUrl(text) {
    const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const encoded = encodeURIComponent(text);
    return isMobile ? `whatsapp://send?text=${encoded}` : `https://web.whatsapp.com/send?text=${encoded}`;
}

function copyToClipboard(encoded) {
    const text = decodeURIComponent(encoded);
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => showToast('📋 Texto copiado al portapapeles')).catch(() => fallbackCopy(text));
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed'; ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); showToast('📋 Texto copiado'); } catch (e) { alert('No se pudo copiar. Selecciona y copia manualmente.'); }
    document.body.removeChild(ta);
}

function showToast(msg) {
    const old = document.querySelector('.racs-toast');
    if (old) old.remove();
    const div = document.createElement('div');
    div.className = 'racs-toast';
    div.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#1e293b;color:#e8edf5;padding:12px 20px;border-radius:10px;border:1px solid #334155;z-index:9999;box-shadow:0 8px 30px rgba(0,0,0,0.5);font-size:0.9rem;animation:fadeIn 0.3s;';
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => { div.style.opacity = '0'; div.style.transition = 'opacity 0.5s'; setTimeout(() => div.remove(), 500); }, 3000);
}

function notifyMissingRacs() {
    const teams = document.querySelectorAll('#racsTeamsContainer > div');
    let missing = [];
    let partial = [];
    const guardiaNames = {A:'Guardia A', B:'Guardia B', C:'Guardia C'};

    teams.forEach(teamDiv => {
        const rows = teamDiv.querySelectorAll('[data-name]');
        rows.forEach(row => {
            const name = row.dataset.name;
            const count = parseInt(row.dataset.count) || 0;
            const badgeEl = row.querySelector('.badge');
            const guardiaText = badgeEl ? badgeEl.textContent.trim() : 'Sin guardia';
            if (name) {
                const info = { name, guardia: guardiaText };
                if (count === 0) missing.push(info);
                else if (count === 1) partial.push(info);
            }
        });
    });

    if (!missing.length && !partial.length) {
        showToast('✅ Todos los trabajadores han completado sus RACS');
        return;
    }

    function groupByGuardia(arr) {
        const groups = {};
        for (const item of arr) {
            if (!groups[item.guardia]) groups[item.guardia] = [];
            groups[item.guardia].push(item.name);
        }
        return groups;
    }

    let text = '📢 *COMUNICADO RACS*\n\n⚠️ Compañeros que aún NO han completado sus RACS:\n\n';

    if (missing.length) {
        text += '🔴 *URGENTE (0/2):*\n';
        const byGuardia = groupByGuardia(missing);
        for (const [g, names] of Object.entries(byGuardia)) {
            text += `  *${g}*\n`;
            for (const n of names) {
                text += `    • ${n}\n`;
            }
        }
        text += '\n';
    }
    if (partial.length) {
        text += '🟡 *PARCIAL (1/2):*\n';
        const byGuardia = groupByGuardia(partial);
        for (const [g, names] of Object.entries(byGuardia)) {
            text += `  *${g}*\n`;
            for (const n of names) {
                text += `    • ${n}\n`;
            }
        }
        text += '\n';
    }
    text += '📌 Recuerden: deben enviar mínimo *2 RACS* por semana.\n';
    text += '✅ Los que ya cumplieron, gracias por su compromiso.\n\n';
    text += '📍 Enviar en: ' + window.location.origin + '/racs';

    window.open(getWhatsAppUrl(text), '_blank');
}