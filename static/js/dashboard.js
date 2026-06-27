// ─── Chart.js defaults ──────────────────────────────────────────────────────
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";

const COLORS = ['#f59e0b','#3b82f6','#10b981','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316','#6366f1','#84cc16','#06b6d4','#d946ef','#eab308','#22c55e','#a855f7'];
const TEAM_COLORS = { 'Mantt. Eq. Trackless': '#f59e0b', 'Mantt. Eq. Convencional': '#10b981', 'Mantt. Eq. Electrico': '#3b82f6' };

let chartInstances = {};
let lastData = null;
let compareMode = false;

function destroy(k) { if (chartInstances[k]) { chartInstances[k].destroy(); delete chartInstances[k]; } }

// ─── Utils ──────────────────────────────────────────────────────────────────
function getTeamLabel(t) { return (t || '').replace('Mantt. Eq. ', ''); }
function shortTeam(t) { const l = getTeamLabel(t); return l === 'Trackless' ? 'TRK' : l === 'Convencional' ? 'CONV' : l === 'Electrico' ? 'ELEC' : l; }

function animateValue(el, end, duration = 800) {
    if (!el) return;
    const start = 0, startTime = performance.now();
    const isFloat = end % 1 !== 0;
    function tick(now) {
        const p = Math.min((now - startTime) / duration, 1), e = 1 - Math.pow(1 - p, 3);
        const v = start + (end - start) * e;
        el.textContent = isFloat ? v.toFixed(1) : Math.floor(v);
        if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

function fmtNum(n) { return n != null ? n.toLocaleString('es-PE') : '0'; }
function fmtPct(n) { return n != null ? n.toFixed(1) + '%' : '0%'; }

// ─── Filters ────────────────────────────────────────────────────────────────
document.getElementById('toggleCompare').addEventListener('change', function() {
    document.getElementById('comparePanel').classList.toggle('show', this.checked);
});

function getFilterParams() {
    const p = {
        date_from: document.getElementById('filterFrom').value || undefined,
        date_to: document.getElementById('filterTo').value || undefined,
        group: document.getElementById('filterGroup').value || undefined,
    };
    if (document.getElementById('toggleCompare').checked) {
        p.compare_from = document.getElementById('cmpFrom').value || undefined;
        p.compare_to = document.getElementById('cmpTo').value || undefined;
    }
    return p;
}

function setDefaultDates() {
    const today = new Date();
    let periodStart;
    if (today.getDate() >= 26) {
        periodStart = new Date(today.getFullYear(), today.getMonth(), 26);
    } else {
        periodStart = new Date(today.getFullYear(), today.getMonth() - 1, 26);
    }
    const periodEnd = new Date(periodStart.getFullYear(), periodStart.getMonth() + 1, 25);
    document.getElementById('filterFrom').value = periodStart.toISOString().split('T')[0];
    document.getElementById('filterTo').value = periodEnd.toISOString().split('T')[0];
    // Previous period
    const prevEnd = new Date(periodStart.getFullYear(), periodStart.getMonth(), 25);
    const prevStart = new Date(prevEnd.getFullYear(), prevEnd.getMonth() - 1, 26);
    document.getElementById('cmpFrom').value = prevStart.toISOString().split('T')[0];
    document.getElementById('cmpTo').value = prevEnd.toISOString().split('T')[0];
}

// ─── Main ───────────────────────────────────────────────────────────────────
async function refreshDashboard() {
    const btn = document.getElementById('refreshBtn');
    btn.classList.add('spinning');
    document.getElementById('lastUpdate').textContent = 'Cargando…';

    try {
        const params = getFilterParams();
        const qs = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, v); });
        const r = await fetch('/api/dashboard/summary?' + qs.toString());
        lastData = await r.json();
        renderAll(lastData);
        document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        document.getElementById('kpiRow').innerHTML =
            `<div class="col-12"><div class="glass p-4 text-center" style="color:#ef4444;"><i class="bi bi-exclamation-triangle-fill me-2"></i>Error: ${e.message}</div></div>`;
    } finally {
        btn.classList.remove('spinning');
    }
}

function applyFilters() { refreshDashboard(); }

// ─── Render all ─────────────────────────────────────────────────────────────
function renderAll(data) {
    const c = data.current;
    document.getElementById('periodLabel').textContent = `📅 ${c.label}`;
    renderKPIs(c, data.comparison);
    renderWorkersToday(c);
    renderMainGrid(c, data.comparison);
    renderOKRs(data.okrs);
}

// ─── KPIs ───────────────────────────────────────────────────────────────────
function renderKPIs(current, comparison) {
    const k = current.kpis;
    const cmp = comparison ? comparison.kpis : null;

    function delta(currentVal, compareVal, reverse = false) {
        if (cmp == null || compareVal == null || compareVal === 0) return { cls: '', text: '' };
        const diff = currentVal - compareVal;
        const pct = ((diff / compareVal) * 100);
        const cls = reverse ? (diff < 0 ? 'up' : diff > 0 ? 'down' : 'neutral') : (diff > 0 ? 'up' : diff < 0 ? 'down' : 'neutral');
        const icon = cls === 'up' ? '▲' : cls === 'down' ? '▼' : '◆';
        const text = `${icon} ${diff >= 0 ? '+' : ''}${diff.toFixed(0)} (${pct >= 0 ? '+' : ''}${pct.toFixed(0)}%) vs anterior`;
        return { cls, text };
    }

    const cards = [
        { icon: 'bi-briefcase-fill',   label: 'Trabajos',         value: k.total_jobs,       border: 'bw', bg: 'bg-wa', color: '#f59e0b', sub: 'en el período', key: 'total_jobs' },
        { icon: 'bi-clock-fill',       label: 'Horas Hombre',     value: k.total_hours + 'h', border: 'bi', bg: 'bg-in', color: '#3b82f6', sub: 'totales', key: 'total_hours' },
        { icon: 'bi-person-fill',      label: 'Trabajadores',     value: k.worker_count,      border: 'bp', bg: 'bg-pr', color: '#8b5cf6', sub: 'reportaron', key: 'worker_count' },
        { icon: 'bi-people-fill',      label: 'Colaboradores',    value: k.collaborator_count, border: 'bg', bg: 'bg-gr', color: '#10b981', sub: 'en labor', key: 'collaborator_count' },
        { icon: 'bi-hourglass-split',  label: 'Duración Prom.',   value: k.avg_duration_min + ' min', border: 'br', bg: 'bg-re', color: '#ef4444', sub: 'por trabajo', key: 'avg_duration_min', reverse: true },
        { icon: 'bi-shield-check',     label: 'Preventivo',       value: fmtPct(k.pm_pct),    border: 'bc', bg: 'bg-or', color: '#f97316', sub: 'del total', key: 'pm_pct', reverse: true },
        { icon: 'bi-exclamation-triangle', label: 'Correctivo',   value: fmtPct(k.cm_pct),    border: 'bp2', bg: 'bg-pu', color: '#a855f7', sub: 'del total', key: 'cm_pct' },
        { icon: 'bi-graph-up',         label: 'Productividad',    value: k.worker_count ? (k.total_jobs / k.worker_count).toFixed(1) + 'x' : '0', border: 'bgr', bg: 'bg-te', color: '#14b8a6', sub: 'trab./trabajador', key: 'total_jobs' },
    ];

    document.getElementById('kpiRow').innerHTML = cards.map((c, i) => {
        const d = cmp ? delta(k[c.key] || 0, cmp[c.key] || 0, c.reverse) : { cls: '', text: '' };
        return `<div class="col-6 col-md-3 col-xl anim-card">
            <div class="glass kpi-card ${c.border}">
                <div class="kpi-icon ${c.bg}"><i class="bi ${c.icon}"></i></div>
                <div class="kpi-value" style="color:${c.color};" data-val="${c.value}">0</div>
                <div class="kpi-label">${c.label}</div>
                <div class="kpi-sub">${c.sub}</div>
                ${d.text ? `<div class="kpi-cmp ${d.cls}">${d.text}</div>` : ''}
            </div>
        </div>`;
    }).join('');

    setTimeout(() => {
        document.querySelectorAll('.kpi-value[data-val]').forEach(el => {
            const val = el.dataset.val;
            const num = parseFloat(val);
            if (!isNaN(num) && val.indexOf('h') === -1 && val.indexOf('min') === -1 && val.indexOf('%') === -1 && val.indexOf('x') === -1) {
                animateValue(el, num, 900);
            } else {
                el.textContent = val;
            }
        });
    }, 250);
}

// ─── Workers Today ──────────────────────────────────────────────────────────
function renderWorkersToday(current) {
    const container = document.getElementById('workersToday');
    if (!container) return;
    if (!current.workers || !current.workers.length) {
        container.innerHTML = '<div style="text-align:center;padding:1.5rem 0;opacity:.4;"><i class="bi bi-inbox" style="font-size:1.5rem;display:block;margin-bottom:.4rem;"></i>Sin datos</div>';
        return;
    }
    const groups = {};
    const avatarColors = ['#f59e0b','#3b82f6','#10b981','#ef4444','#8b5cf6','#ec4899','#14b8a6'];
    current.workers.forEach(w => {
        const key = w.team || 'Otros';
        if (!groups[key]) groups[key] = [];
        groups[key].push(w);
    });
    let idx = 0, html = '';
    for (const [team, ws] of Object.entries(groups)) {
        const tc = TEAM_COLORS[team] || '#94a3b8';
        html += `<div style="margin-bottom:.6rem;">
            <div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.25rem;">
                <span class="team-badge" style="background:${tc}22;color:${tc};">${getTeamLabel(team)}</span>
                <span style="font-size:.65rem;opacity:.4;">${ws.length}</span>
            </div>`;
        ws.forEach(w => {
            const ac = avatarColors[idx++ % avatarColors.length];
            html += `<div class="worker-row"><div class="worker-name"><span class="avatar" style="background:${ac}22;color:${ac};">${w.name.charAt(0)}</span>${w.name}</div></div>`;
        });
        html += '</div>';
    }
    document.getElementById('workersToday').innerHTML = html;
}

// ─── Weeklies ───────────────────────────────────────────────────────────────
function renderWeeklySummaries(current) {
    const container = document.getElementById('weeklySummaries');
    if (!container) return;
    if (!current.weekly_summaries || !current.weekly_summaries.length) {
        container.innerHTML = '<div style="text-align:center;padding:1rem 0;opacity:.4;">Sin datos semanales</div>';
        return;
    }
    container.innerHTML = current.weekly_summaries.map(w => {
        const teams = Object.entries(w.by_team || {}).map(([t, c]) =>
            `<span class="team-badge" style="background:${(TEAM_COLORS[t] || '#94a3b8')}22;color:${TEAM_COLORS[t] || '#94a3b8'};">${shortTeam(t)} ${c}</span>`
        ).join(' ');
        const startParts = w.start ? w.start.split('-') : [];
        const label = startParts.length === 3 ? `${startParts[2]}/${startParts[1]}` : w.week;
        return `<div class="week-row">
            <div style="font-weight:600;font-size:.8rem;">Sem ${w.week.replace(/^\d+-W/, '')}</div>
            <div style="font-weight:600;">${w.count} <span style="font-weight:400;opacity:.4;">trabajos</span></div>
            <div class="d-flex gap-1">${teams}</div>
        </div>`;
    }).join('');
}

// ─── Main Grid ──────────────────────────────────────────────────────────────
function renderMainGrid(current, comparison) {
    const grid = document.getElementById('dashboardGrid');
    compareMode = !!comparison;

    // Row 1: Workers + Team Doughnut
    let html = `<div class="row g-3 mb-4 anim-section">
        <div class="col-lg-4"><div class="glass p-3 h-100">
            <div class="section-title" style="color:#60a5fa;"><i class="bi bi-people-fill"></i> Trabajadores del Período</div>
            <div id="workersToday"></div>
        </div></div>
        <div class="col-lg-4"><div class="glass p-3 h-100">
            <div class="section-title" style="color:#34d399;"><i class="bi bi-pie-chart-fill"></i> Trabajos por Equipo</div>
            <div class="chart-container" style="height:200px;"><canvas id="teamChart"></canvas></div>
        </div></div>
        <div class="col-lg-4"><div class="glass p-3 h-100">
            <div class="section-title" style="color:#fb923c;"><i class="bi bi-arrow-left-right"></i> Turno</div>
            <div class="chart-container" style="height:200px;"><canvas id="shiftChart"></canvas></div>
        </div></div>
    </div>`;

    // Row 2: Top Equipment (horizontal bar) + PM/CM + Macroprocess
    html += `<div class="row g-3 mb-4 anim-section">
        <div class="col-lg-5"><div class="glass p-3 h-100">
            <div class="section-title" style="color:#fbbf24;"><i class="bi bi-bar-chart-fill"></i> Equipos Más Intervenidos</div>
            <div class="chart-container" style="height:210px;"><canvas id="topEquipChart"></canvas></div>
        </div></div>
        <div class="col-lg-3"><div class="glass p-3 h-100">
            <div class="section-title" style="color:#f472b6;"><i class="bi bi-shield-check"></i> PM vs Correctivo</div>
            <div class="chart-container" style="height:210px;"><canvas id="pmCmChart"></canvas></div>
        </div></div>
        <div class="col-lg-4"><div class="glass p-3 h-100">
            <div class="section-title" style="color:#a78bfa;"><i class="bi bi-diagram-3"></i> Macroprocesos</div>
            <div id="macroprocessList"></div>
        </div></div>
    </div>`;

    // Row 3: Daily trend + weekly summaries
    html += `<div class="row g-3 mb-4 anim-section">
        <div class="col-lg-7"><div class="glass p-3">
            <div class="section-title" style="color:#fb923c;"><i class="bi bi-graph-up-arrow"></i> Tendencia Diaria</div>
            <div class="chart-container" style="height:200px;"><canvas id="dailyTrendChart"></canvas></div>
        </div></div>
        <div class="col-lg-5"><div class="glass p-3">
            <div class="section-title" style="color:#38bdf8;"><i class="bi bi-calendar-week"></i> Resumen Semanal</div>
            <div id="weeklySummaries"></div>
        </div></div>
    </div>`;

    // Row 4: Duration by team + Top collaborators
    html += `<div class="row g-3 mb-4 anim-section">
        <div class="col-lg-5"><div class="glass p-3">
            <div class="section-title" style="color:#f472b6;"><i class="bi bi-clock-fill"></i> Duración Prom. por Grupo</div>
            <div id="avgDurationContainer"></div>
        </div></div>
        <div class="col-lg-7"><div class="glass p-3">
            <div class="section-title" style="color:#22d3ee;"><i class="bi bi-trophy-fill"></i> Colaboradores Más Activos</div>
            <div id="topCollabContainer"></div>
        </div></div>
    </div>`;

    // Equipment table
    html += `<div class="row anim-section mb-4">
        <div class="col-12"><div class="glass p-3">
            <div class="section-title" style="color:#94a3b8;"><i class="bi bi-table"></i> Todos los Equipos <span style="font-weight:400;font-size:.7rem;opacity:.4;" id="equipCountLabel"></span></div>
            <div class="table-responsive" style="max-height:350px;overflow-y:auto;">
                <table class="table equip-table mb-0" id="equipTable"><thead><tr><th style="width:28px;">#</th><th>Equipo</th><th class="text-center">Trabajos</th><th class="text-center">Horas</th><th class="text-center">Prom. (min)</th></tr></thead><tbody id="equipTbody"></tbody></table>
            </div>
        </div></div>
    </div>`;

    grid.innerHTML = html;

    // Populate all sections
    renderWorkersToday(current);
    renderTeamChart(current);
    renderShiftChart(current);
    renderTopEquipment(current);
    renderPmCmChart(current);
    renderMacroprocessList(current);
    renderDailyTrend(current);
    renderWeeklySummaries(current);
    renderAvgDuration(current);
    renderTopCollabs(current);
    renderEquipTable(current);

    // Comparison overlays
    if (comparison) {
        // Draw comparison markers
        renderComparisonOverlays(current, comparison);
    }
}

// ─── Team Doughnut ──────────────────────────────────────────────────────────
function renderTeamChart(current) {
    destroy('team');
    const ctx = document.getElementById('teamChart');
    if (!ctx) return;
    const c = ctx.getContext('2d');
    const labels = current.jobs_by_team.map(t => getTeamLabel(t.team));
    const vals = current.jobs_by_team.map(t => t.count);
    const total = vals.reduce((a, b) => a + b, 0);
    const colors = [COLORS[0], COLORS[2], COLORS[1]];
    chartInstances.team = new Chart(c, {
        type: 'doughnut',
        data: { labels, datasets: [{ data: vals, backgroundColor: colors, borderWidth: 0, hoverOffset: 10 }] },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '66%',
            plugins: {
                legend: { position: 'bottom', labels: { color: '#cbd5e1', font: { size: 10 }, padding: 12, usePointStyle: true, pointStyle: 'circle' } },
                tooltip: { backgroundColor: 'rgba(15,23,42,.9)', padding: 10, cornerRadius: 8, callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed} (${((ctx.parsed / total) * 100).toFixed(1)}%)` } }
            }
        },
        plugins: [{
            id: 'centerText',
            beforeDraw(chart) {
                const { width, height, ctx: c2 } = chart;
                c2.save(); c2.textAlign = 'center'; c2.textBaseline = 'middle';
                c2.font = '700 1.6rem Inter, sans-serif'; c2.fillStyle = '#f59e0b';
                c2.fillText(total, width / 2, height / 2 - 4);
                c2.font = '500 .6rem Inter, sans-serif'; c2.fillStyle = 'rgba(255,255,255,.4)';
                c2.fillText('Total', width / 2, height / 2 + 20);
                c2.restore();
            }
        }]
    });
}

// ─── Shift Chart ────────────────────────────────────────────────────────────
function renderShiftChart(current) {
    destroy('shift');
    const ctx = document.getElementById('shiftChart');
    if (!ctx) return;
    const sc = current.shift_comparison || {};
    const labels = Object.keys(sc);
    const vals = Object.values(sc);
    chartInstances.shift = new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{ data: vals, backgroundColor: ['#3b82f6', '#f59e0b', '#64748b'], borderWidth: 0, hoverOffset: 10 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '60%',
            plugins: {
                legend: { position: 'bottom', labels: { color: '#cbd5e1', font: { size: 10 }, usePointStyle: true } },
                tooltip: { backgroundColor: 'rgba(15,23,42,.9)', padding: 10, cornerRadius: 8 }
            }
        }
    });
}

// ─── Top Equipment ──────────────────────────────────────────────────────────
function renderTopEquipment(current) {
    destroy('topEquip');
    const ctx = document.getElementById('topEquipChart');
    if (!ctx) return;
    const items = current.top_equipment || [];
    if (!items.length) { ctx.parentElement.innerHTML = '<div style="text-align:center;padding:2rem 0;opacity:.4;">Sin datos</div>'; return; }
    const labels = items.map(i => i.equipment.length > 20 ? i.equipment.substring(0, 18) + '…' : i.equipment);
    const vals = items.map(i => i.count);
    const bgColors = items.map((_, i) => COLORS[i % COLORS.length] + 'BB');
    const bdColors = items.map((_, i) => COLORS[i % COLORS.length]);
    chartInstances.topEquip = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Trabajos', data: vals, backgroundColor: bgColors, borderColor: bdColors, borderWidth: 1, borderRadius: 5, borderSkipped: false }] },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false, animation: { duration: 700, easing: 'easeOutQuart' },
            plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(15,23,42,.9)', padding: 8, cornerRadius: 8, callbacks: { label: ctx => `${ctx.parsed.x} trabajo${ctx.parsed.x !== 1 ? 's' : ''}` } } },
            scales: { x: { beginAtZero: true, ticks: { stepSize: 1, color: '#64748b', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,.04)' } }, y: { ticks: { color: '#cbd5e1', font: { size: 9 } }, grid: { display: false } } }
        }
    });
}

// ─── PM/CM Chart ────────────────────────────────────────────────────────────
function renderPmCmChart(current) {
    destroy('pmCm');
    const ctx = document.getElementById('pmCmChart');
    if (!ctx) return;
    const pm = current.pm_cm_ratio || {};
    chartInstances.pmCm = new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Preventivo', 'Correctivo', 'Otros'],
            datasets: [{ data: [pm.pm || 0, pm.cm || 0, pm.other || 0], backgroundColor: ['#10b981', '#ef4444', '#64748b'], borderWidth: 0, hoverOffset: 10 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '60%',
            plugins: {
                legend: { position: 'bottom', labels: { color: '#cbd5e1', font: { size: 9 }, usePointStyle: true } },
                tooltip: { backgroundColor: 'rgba(15,23,42,.9)', padding: 8, cornerRadius: 8, callbacks: { label: ctx => `${ctx.label}: ${ctx.parsed} (${((ctx.parsed / (pm.pm + pm.cm + pm.other || 1)) * 100).toFixed(1)}%)` } }
            }
        }
    });
}

// ─── Macroprocess list ──────────────────────────────────────────────────────
function renderMacroprocessList(current) {
    const container = document.getElementById('macroprocessList');
    if (!container) return;
    const items = current.macroprocess_dist || [];
    if (!items.length) { container.innerHTML = '<div style="text-align:center;padding:1rem 0;opacity:.4;">Sin datos</div>'; return; }
    const total = items.reduce((a, b) => a + b.count, 0);
    const top = items.slice(0, 8);
    container.innerHTML = top.map((m, i) => {
        const pct = (m.count / total * 100).toFixed(0);
        return `<div style="margin-bottom:.4rem;">
            <div style="display:flex;justify-content:space-between;font-size:.78rem;margin-bottom:2px;">
                <span>${m.macroprocess.length > 35 ? m.macroprocess.substring(0, 33) + '…' : m.macroprocess}</span>
                <span style="color:${COLORS[i % COLORS.length]};font-weight:600;">${m.count}</span>
            </div>
            <div class="dur-bar-track" style="height:5px;"><div class="dur-bar-fill" style="width:${pct}%;background:${COLORS[i % COLORS.length]};" data-w="${pct}"></div></div>
        </div>`;
    }).join('');
    requestAnimationFrame(() => {
        container.querySelectorAll('.dur-bar-fill').forEach(b => { b.style.width = '0%'; setTimeout(() => { b.style.width = b.dataset.w + '%'; }, 100); });
    });
}

// ─── Daily Trend ────────────────────────────────────────────────────────────
function renderDailyTrend(current) {
    destroy('dailyTrend');
    const ctx = document.getElementById('dailyTrendChart');
    if (!ctx) return;
    const days = current.jobs_per_day || [];
    if (!days.length) { ctx.parentElement.innerHTML = '<div style="text-align:center;padding:1.5rem 0;opacity:.4;">Sin datos</div>'; return; }
    const labels = days.map(d => { const p = d.date.split('-'); return `${p[2]}/${p[1]}`; });
    const vals = days.map(d => d.count);
    const c = ctx.getContext('2d');
    const grad = c.createLinearGradient(0, 0, 0, 200);
    grad.addColorStop(0, 'rgba(251,146,60,.2)'); grad.addColorStop(1, 'rgba(251,146,60,0)');
    chartInstances.dailyTrend = new Chart(c, {
        type: 'line',
        data: { labels, datasets: [{ label: 'Trabajos', data: vals, borderColor: '#fb923c', backgroundColor: grad, fill: true, tension: .35, pointRadius: 3, pointHoverRadius: 6, pointBackgroundColor: '#fb923c', pointBorderColor: '#0b1120', pointBorderWidth: 2, borderWidth: 2 }] },
        options: {
            responsive: true, maintainAspectRatio: false, animation: { duration: 800, easing: 'easeOutQuart' }, interaction: { intersect: false, mode: 'index' },
            plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(15,23,42,.9)', padding: 10, cornerRadius: 8, callbacks: { title: items => `Día ${items[0].label}`, label: ctx => ` ${ctx.parsed.y} trabajo${ctx.parsed.y !== 1 ? 's' : ''}` } } },
            scales: { x: { ticks: { color: '#64748b', font: { size: 9 }, maxTicksLimit: 12 }, grid: { display: false } }, y: { beginAtZero: true, ticks: { stepSize: 1, color: '#64748b', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,.04)' } } }
        }
    });
}

// ─── Avg Duration ───────────────────────────────────────────────────────────
function renderAvgDuration(current) {
    const container = document.getElementById('avgDurationContainer');
    if (!container) return;
    const items = current.avg_duration_by_team || [];
    if (!items.length) { container.innerHTML = '<div style="text-align:center;padding:1.5rem 0;opacity:.4;">Sin datos</div>'; return; }
    const maxVal = Math.max(...items.map(t => t.avg_min));
    container.innerHTML = items.map(t => {
        const pct = maxVal > 0 ? (t.avg_min / maxVal * 100) : 0;
        const color = TEAM_COLORS[t.team] || COLORS[0];
        return `<div style="margin-bottom:.7rem;">
            <div style="display:flex;justify-content:space-between;font-size:.78rem;margin-bottom:3px;">
                <span style="font-weight:600;">${getTeamLabel(t.team)}</span>
                <span style="font-weight:700;color:${color};">${t.avg_min} <span style="font-weight:400;opacity:.4;">min</span></span>
            </div>
            <div class="dur-bar-track"><div class="dur-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,${color},${color}88);" data-w="${pct}"></div></div>
        </div>`;
    }).join('');
    requestAnimationFrame(() => {
        container.querySelectorAll('.dur-bar-fill').forEach(b => { b.style.width = '0%'; setTimeout(() => { b.style.width = b.dataset.w + '%'; }, 120); });
    });
}

// ─── Top Collaborators ──────────────────────────────────────────────────────
function renderTopCollabs(current) {
    const container = document.getElementById('topCollabContainer');
    if (!container) return;
    const items = current.top_collaborators || [];
    if (!items.length) { container.innerHTML = '<div style="text-align:center;padding:1.5rem 0;opacity:.4;">Sin datos</div>'; return; }
    const maxVal = Math.max(...items.map(c => c.count));
    const avatarColors = ['#f59e0b','#3b82f6','#10b981','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316'];
    container.innerHTML = items.map((c, i) => {
        const pct = maxVal > 0 ? (c.count / maxVal * 100) : 0;
        const ac = avatarColors[i % avatarColors.length];
        return `<div class="d-flex align-items-center gap-2" style="margin-bottom:.3rem;padding:.25rem .3rem;border-radius:8px;transition:background .15s;" onmouseover="this.style.background='rgba(255,255,255,.03)'" onmouseout="this.style.background=''">
            <span class="avatar" style="width:22px;height:22px;background:${ac}22;color:${ac};font-size:.55rem;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0;">${c.name.charAt(0)}</span>
            <div style="flex:1;">
                <div style="display:flex;justify-content:space-between;font-size:.78rem;">
                    <span>${c.name}</span>
                    <span style="color:${ac};font-weight:600;">${c.count}</span>
                </div>
                <div class="dur-bar-track" style="height:4px;"><div class="dur-bar-fill" style="width:${pct}%;background:${ac};" data-w="${pct}"></div></div>
            </div>
        </div>`;
    }).join('');
    requestAnimationFrame(() => {
        container.querySelectorAll('.dur-bar-fill').forEach(b => { b.style.width = '0%'; setTimeout(() => { b.style.width = b.dataset.w + '%'; }, 150); });
    });
}

// ─── Equipment Table ────────────────────────────────────────────────────────
function renderEquipTable(current) {
    const tbody = document.getElementById('equipTbody');
    if (!tbody) return;
    const items = current.jobs_by_equipment || [];
    document.getElementById('equipCountLabel').textContent = items.length ? `— ${items.length} equipos` : '';
    if (!items.length) { tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:1.5rem;opacity:.4;">Sin datos</td></tr>'; return; }
    tbody.innerHTML = items.map((e, i) => {
        const rc = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : 'default';
        const ri = i === 0 ? 'bi-trophy-fill' : i === 1 ? 'bi-award-fill' : i === 2 ? 'bi-star-fill' : '';
        const cc = e.count >= 10 ? '#f59e0b' : e.count >= 5 ? '#3b82f6' : '#64748b';
        return `<tr><td><span class="equip-rank ${rc}">${ri ? `<i class="bi ${ri}" style="font-size:.55rem;"></i>` : i + 1}</span></td>
            <td style="font-weight:500;">${e.equipment}</td>
            <td class="text-center"><span class="count-badge" style="background:${cc}22;color:${cc};">${e.count}</span></td>
            <td class="text-center" style="color:rgba(255,255,255,.5);font-size:.75rem;">${e.total_hours || '—'}</td>
            <td class="text-center" style="color:rgba(255,255,255,.4);">${e.avg_duration_min != null ? e.avg_duration_min : '—'}</td></tr>`;
    }).join('');
}

// ─── Comparison Overlays ────────────────────────────────────────────────────
function renderComparisonOverlays(current, comparison) {
    // Comparison data is shown as delta markers on KPIs
    // Also can add a small comparison note
    const grid = document.getElementById('dashboardGrid');
    const note = document.createElement('div');
    note.className = 'glass p-2 mb-3 anim-section';
    note.style.textAlign = 'center';
    note.style.fontSize = '.75rem';
    note.style.opacity = '.6';
    const c = comparison.kpis;
    const curr = current.kpis;
    const diff = curr.total_jobs - c.total_jobs;
    note.innerHTML = `Comparando: <strong>${comparison.label}</strong> vs período actual — 
        <span style="color:${diff >= 0 ? '#10b981' : '#ef4444'};font-weight:600;">${diff >= 0 ? '+' : ''}${diff} trabajos${diff !== 1 ? '' : ''}</span> 
        | ${c.total_hours}h → ${curr.total_hours}h | 
        ${c.worker_count} → ${curr.worker_count} trabajadores`;
    grid.insertBefore(note, grid.firstChild);
}

// ─── OKRs ───────────────────────────────────────────────────────────────────
function renderOKRs(okrs) {
    const container = document.getElementById('okrContainer');
    if (!container || !okrs || !okrs.length) {
        if (container) container.innerHTML = '<div style="text-align:center;padding:1.5rem 0;opacity:.4;">Datos insuficientes para OKRs</div>';
        return;
    }
    const colors = ['#f59e0b', '#3b82f6', '#10b981'];
    const progressColors = { on_track: '#10b981', needs_attention: '#f59e0b', critical: '#ef4444' };
    container.innerHTML = okrs.map((o, oi) => {
        const krs = o.key_results.map(kr => {
            const pct = kr.progress === 'on_track' ? 85 : kr.progress === 'needs_attention' ? 50 : 25;
            const pc = progressColors[kr.progress] || '#64748b';
            return `<div style="margin-bottom:.5rem;padding:.35rem 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;font-size:.78rem;margin-bottom:3px;">
                    <span>${kr.kr}</span>
                    <div class="d-flex align-items-center gap-2">
                        <span style="opacity:.5;font-size:.7rem;">${kr.current}</span>
                        <span style="opacity:.3;">→</span>
                        <span style="font-weight:600;color:${pc};">${kr.target}</span>
                    </div>
                </div>
                <div class="progress-okr"><div class="bar" style="width:${pct}%;background:${pc};" data-w="${pct}"></div></div>
            </div>`;
        }).join('');
        return `<div class="okr-card mb-2" style="border-left-color:${colors[oi % colors.length]};">
            <div style="font-weight:700;font-size:.85rem;margin-bottom:.5rem;color:${colors[oi % colors.length]};">🎯 ${o.objective}</div>
            ${krs}
        </div>`;
    }).join('');
    // Animate bars
    requestAnimationFrame(() => {
        container.querySelectorAll('.progress-okr .bar').forEach(b => { b.style.width = '0%'; setTimeout(() => { b.style.width = b.dataset.w + '%'; }, 200); });
    });
}

// ─── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    setDefaultDates();
    refreshDashboard();
});
