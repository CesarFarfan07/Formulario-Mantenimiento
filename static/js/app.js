let opt = null;
let _searchCursor = null;
let _searchCursorDate = null;
let _searchHasMore = false;
let _searchParams = {};
let _pendingDeleteIds = [];

document.addEventListener('DOMContentLoaded', async () => {
    await loadOptions();
    populateStaticSelects();
    // Create extra entry cards if saved state needs them
    const saved = loadFormState();
    if (saved && saved.entriesCount > 1) {
        const container = document.getElementById('entriesContainer');
        const template = container.querySelector('.entry-card');
        for (let i = 1; i < saved.entriesCount; i++) {
            const clone = template.cloneNode(true);
            container.appendChild(clone);
        }
    }
    document.querySelectorAll('.entry-card').forEach((card, i) => {
        initEntry(card);
    });
    if (saved) {
        if (saved.date) document.getElementById('reportDate').value = saved.date;
        if (saved.shift) document.getElementById('shift').value = saved.shift;
        if (saved.groupName) {
            document.getElementById('groupName').value = saved.groupName;
            onGroupChange();
        }
        // Restore all card fields after onGroupChange (so collaborator checkboxes exist)
        document.querySelectorAll('.entry-card').forEach((card, i) => {
            if (saved.entries && saved.entries[i]) restoreCardState(card, saved.entries[i]);
        });
    }
    renumberEntries();
    updateRemoveButtons();
    if (!saved) {
        document.getElementById('reportDate').value = new Date().toISOString().split('T')[0];
    }
});

// Re-fetch options when returning from admin (bfcache or tab switch)
async function refreshOptions() {
    if (!opt) return;
    try {
        // Save full form state before refreshing
        saveFormState();

        const r = await fetch('/api/options');
        const newOpt = await r.json();

        opt = newOpt;
        populateStaticSelects();

        // Restore from localStorage after re-population
        const saved = loadFormState();
        if (saved) {
            if (saved.date) document.getElementById('reportDate').value = saved.date;
            if (saved.shift) document.getElementById('shift').value = saved.shift;
            if (saved.groupName) {
                document.getElementById('groupName').value = saved.groupName;
                onGroupChange();
            }
            document.querySelectorAll('.entry-card').forEach((card, i) => {
                populateEquipos(card);
                populateMacroprocess(card);
                populateNiveles(card);
                populateActions(card);
                if (saved.entries && saved.entries[i]) restoreCardState(card, saved.entries[i]);
            });
        }
    } catch {}
}

window.addEventListener('pageshow', refreshOptions);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshOptions(); });

async function loadOptions() {
    const r = await fetch('/api/options');
    opt = await r.json();
}

function populateStaticSelects() {
    const shiftSel = document.getElementById('shift');
    shiftSel.innerHTML = '<option value="">Seleccionar...</option>';
    opt.turnos.forEach(t => {
        const o = document.createElement('option'); o.value = t; o.textContent = t; shiftSel.appendChild(o);
    });

    const groupSel = document.getElementById('groupName');
    groupSel.innerHTML = '<option value="">Seleccionar...</option>';
    opt.grupos.forEach(g => {
        const o = document.createElement('option'); o.value = g; o.textContent = g; groupSel.appendChild(o);
    });
}

// ─── FORM PERSISTENCE (localStorage) ──────────────────────────────────────

const STORAGE_KEY = 'formulario_mantto_state';

function saveFormState() {
    const state = {
        date: document.getElementById('reportDate').value,
        shift: document.getElementById('shift').value,
        groupName: document.getElementById('groupName').value,
        entriesCount: document.querySelectorAll('.entry-card').length,
        entries: [],
        savedAt: Date.now(),
    };
    document.querySelectorAll('.entry-card').forEach(card => {
        const entry = {
            macroprocess: card.querySelector('.macroprocess')?.value || '',
            workType: card.querySelector('.work-type')?.value || '',
            actionType: card.querySelector('.action-type')?.value || '',
            description: card.querySelector('.descripcion')?.value || '',
            nivel: card.querySelector('.nivel')?.value || '',
            lugar: card.querySelector('.lugar')?.value || '',
            horaInicio: card.querySelector('.hora-inicio')?.value || '',
            horaFin: card.querySelector('.hora-fin')?.value || '',
            equipoCat: card.querySelector('.equipo-categoria')?.value || '',
            equipoSub: card.querySelector('.equipo-sub')?.value || '',
            equipoOtras: card.querySelector('.equipo-sub-otras')?.value || '',
            horometroMotor: card.querySelector('.horometro-motor')?.value || '',
            horometroJumbo: card.querySelector('.horometro-jumbo')?.value || '',
            horometroVolquetes: card.querySelector('.horometro-volquetes')?.value || '',
            kilometraje: card.querySelector('.kilometraje')?.value || '',
            horometroElectrico: card.querySelector('.horometro-electrico')?.value || '',
            horometroPercusion: card.querySelector('.horometro-percusion')?.value || '',
            colabChecked: [],
            colabOtras: card.querySelector('.entry-colab-otras-input')?.value || '',
        };
        card.querySelectorAll('.colab-check:checked').forEach(cb => {
            if (cb.value !== '__otras__') entry.colabChecked.push(cb.value);
        });
        if (card.querySelector('.colab-check[value="__otras__"]')?.checked) {
            entry.colabChecked.push('__otras__');
        }
        state.entries.push(entry);
    });
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (_) {}
}

function loadFormState() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch (_) { return null; }
}

function clearFormState() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
}

function restoreCardState(card, entry) {
    if (!entry) return;
    const setVal = (sel, val) => {
        const el = card.querySelector(sel);
        if (el && val) el.value = val;
    };
    setVal('.macroprocess', entry.macroprocess);
    setVal('.work-type', entry.workType);
    setVal('.action-type', entry.actionType);
    setVal('.descripcion', entry.description);
    setVal('.nivel', entry.nivel);
    setVal('.lugar', entry.lugar);
    setVal('.hora-inicio', entry.horaInicio);
    setVal('.hora-fin', entry.horaFin);
    setVal('.equipo-categoria', entry.equipoCat);
    if (entry.equipoCat) {
        // Populate sub-equipos dropdown
        const sub = card.querySelector('.equipo-sub');
        const otrasInput = card.querySelector('.equipo-sub-otras');
        if (sub) {
            const catOptions = opt.equipos[entry.equipoCat];
            if (catOptions) {
                sub.innerHTML = '<option value="">Seleccionar...</option>';
                (catOptions.subequipos || []).forEach(eq => {
                    const o = document.createElement('option');
                    o.value = eq.nombre;
                    o.dataset.mide = eq.mide || 'fin';
                    o.textContent = eq.nombre;
                    sub.appendChild(o);
                });
                const defaultMide = catOptions.subequipos?.[0]?.mide || 'fin';
                const o = document.createElement('option');
                o.value = '__otras__';
                o.dataset.mide = defaultMide;
                o.textContent = 'Otras (especifique)';
                sub.appendChild(o);
                card.querySelector('.medidores-section').classList.remove('d-none');
            }
        }
        if (sub) sub.value = entry.equipoSub || '';
        if (otrasInput) {
            otrasInput.value = entry.equipoOtras || '';
            otrasInput.classList.toggle('d-none', entry.equipoSub !== '__otras__');
        }
        // Show meters
        if (entry.equipoSub) {
            const subOpt = sub?.options[sub.selectedIndex];
            const mide = subOpt?.dataset?.mide || null;
            if (mide) showMeters(card, mide);
        }
    }
    setVal('.horometro-motor', entry.horometroMotor);
    setVal('.horometro-jumbo', entry.horometroJumbo);
    setVal('.horometro-volquetes', entry.horometroVolquetes);
    setVal('.kilometraje', entry.kilometraje);
    setVal('.horometro-electrico', entry.horometroElectrico);
    setVal('.horometro-percusion', entry.horometroPercusion);

    // Restore collaborators
    if (entry.colabChecked && entry.colabChecked.length) {
        card.querySelectorAll('.colab-check').forEach(cb => {
            if (entry.colabChecked.includes(cb.value)) cb.checked = true;
        });
        const otrasRow = card.querySelector('.entry-colab-otras-row');
        const otrasInput = card.querySelector('.entry-colab-otras-input');
        if (entry.colabChecked.includes('__otras__') && otrasRow && otrasInput) {
            otrasRow.classList.remove('d-none');
            otrasInput.value = entry.colabOtras || '';
        }
    }
}

// Auto-save on field changes (debounced)
let _saveTimer = null;
function autoSave() {
    if (_saveTimer) clearTimeout(_saveTimer);
    _saveTimer = setTimeout(saveFormState, 500);
}
document.addEventListener('change', autoSave);
document.addEventListener('input', autoSave);

// ─── ENTRY SETUP ───────────────────────────────────────────────────────────

function initEntry(card) {
    const hi = card.querySelector('.hora-inicio');
    const hf = card.querySelector('.hora-fin');
    const dur = card.querySelector('.duracion');
    calcularDuracion(hi, hf, dur);
    populateEquipos(card);
    populateNiveles(card);
}

function populateEquipos(card) {
    const sel = card.querySelector('.equipo-categoria');
    sel.innerHTML = '<option value="">Seleccionar...</option>';
    Object.keys(opt.equipos).sort().forEach(nombre => {
        const o = document.createElement('option'); o.value = nombre; o.textContent = nombre; sel.appendChild(o);
    });
}

function populateNiveles(card) {
    const sel = card.querySelector('.nivel');
    sel.innerHTML = '<option value="">Seleccionar...</option>';
    opt.niveles.forEach(n => {
        const o = document.createElement('option'); o.value = n; o.textContent = n; sel.appendChild(o);
    });
}

function onGroupChange() {
    const group = document.getElementById('groupName').value;

    if (!group) {
        document.querySelectorAll('.entry-card').forEach(card => {
            card.querySelector('.entry-colab-section')?.classList.add('d-none');
        });
        return;
    }

    const key = group.includes('Trackless') ? 'Trackless' : group.includes('Convencional') ? 'Convencional' : 'Electrico';
    const maxSelect = opt.colab_max_select || 4;

    document.querySelectorAll('.entry-card').forEach(card => {
        const section = card.querySelector('.entry-colab-section');
        if (!section) return;
        section.classList.remove('d-none');
        section.querySelector('.colab-max-label').textContent = maxSelect;

        const container = section.querySelector('.entry-colab-checkboxes');
        container.innerHTML = '';
        const cols = opt.colaboradores[key] || [];
        const uniqueId = 'card_' + Math.random().toString(36).substr(2, 6);

        cols.forEach((name, i) => {
            const div = document.createElement('div');
            div.className = 'col-md-4 col-lg-3';
            div.innerHTML = `<div class="form-check">
                <input class="form-check-input colab-check" type="checkbox" value="${name}" id="${uniqueId}_colab_${i}">
                <label class="form-check-label" for="${uniqueId}_colab_${i}">${name}</label>
            </div>`;
            container.appendChild(div);
        });

        const otrasRow = section.querySelector('.entry-colab-otras-row');
        otrasRow.classList.add('d-none');
        section.querySelector('.entry-colab-otras-input').value = '';

        const div = document.createElement('div');
        div.className = 'col-md-4 col-lg-3';
        div.innerHTML = `<div class="form-check">
            <input class="form-check-input colab-check" type="checkbox" value="__otras__" id="${uniqueId}_colab_otras">
            <label class="form-check-label" for="${uniqueId}_colab_otras"><strong>Otros</strong></label>
        </div>`;
        container.appendChild(div);

        // Add change listeners for this card's checkboxes
        container.querySelectorAll('.colab-check').forEach(cb => {
            cb.addEventListener('change', () => onCardColabChange(card));
        });

        populateMacroprocess(card);
        populateActions(card);
    });
}

function onCardColabChange(card) {
    const section = card.querySelector('.entry-colab-section');
    if (!section) return;
    const max = opt.colab_max_select || 4;
    const checks = section.querySelectorAll('.colab-check:checked');
    const otrasCheck = section.querySelector('.colab-check[value="__otras__"]');

    if (checks.length > max) {
        checks[checks.length - 1].checked = false;
        alert(`Solo puede seleccionar hasta ${max} colaboradores.`);
        return;
    }

    const otrasRow = section.querySelector('.entry-colab-otras-row');
    const otrasInput = section.querySelector('.entry-colab-otras-input');
    if (otrasCheck && otrasCheck.checked) {
        otrasRow.classList.remove('d-none');
    } else {
        otrasRow.classList.add('d-none');
        otrasInput.value = '';
    }
}

function populateMacroprocess(card) {
    const group = document.getElementById('groupName').value;
    const sel = card.querySelector('.macroprocess');
    sel.innerHTML = '<option value="">Seleccionar...</option>';
    if (!group) return;
    const key = group.includes('Trackless') ? 'Trackless' : group.includes('Convencional') ? 'Convencional' : 'Electrico';
    const opts = opt.macroprocesos[key] || [];
    opts.forEach(p => {
        const o = document.createElement('option'); o.value = p; o.textContent = p; sel.appendChild(o);
    });
}

function populateActions(card) {
    const group = document.getElementById('groupName').value;
    const action = card.querySelector('.action-type');
    action.innerHTML = '<option value="">Seleccionar...</option>';
    if (!group) return;
    let gKey;
    if (group.includes('Trackless')) gKey = 'Trackless';
    else if (group.includes('Convencional')) gKey = 'Convencional';
    else gKey = 'Electrico';

    let opts = opt.acciones[gKey] || [];
    // Fallback: include old combined key for backward compat
    const oldKey = 'Convencional_Electrico';
    if (opt.acciones[oldKey] && (gKey === 'Convencional' || gKey === 'Electrico')) {
        opts = [...new Set([...opts, ...opt.acciones[oldKey]])];
    }
    opts.forEach(a => {
        const o = document.createElement('option'); o.value = a; o.textContent = a; action.appendChild(o);
    });
}

function getTipoKey(gKey, macro) {
    let moda = 'Mecánico';
    const n = macro.toLowerCase();
    if (n.includes('eléctrico') || n.includes('electrico')) moda = 'Eléctrico';
    else if (n.includes('fabric') || n.includes('soldadura')) moda = 'Fabricacion_Soldadura';
    else if (n.includes('instal')) moda = 'Instalaciones';
    else if (n.includes('logistic')) moda = 'Logistica';
    else if (n.includes('servicio')) moda = 'Servicios';
    else if (n.includes('trabajo')) moda = 'Trabajos';

    const key = `${gKey}_${moda}`;
    // Try group-specific key first; fall back to shared key for backward compat
    if (opt.tipos_trabajo[key] && opt.tipos_trabajo[key].length > 0) return key;
    if (moda === 'Fabricacion_Soldadura' && opt.tipos_trabajo['Fabricacion_Soldadura'] && opt.tipos_trabajo['Fabricacion_Soldadura'].length) return 'Fabricacion_Soldadura';
    if (moda === 'Instalaciones' && opt.tipos_trabajo['Instalaciones'] && opt.tipos_trabajo['Instalaciones'].length) return 'Instalaciones';
    return key;
}

function onMacroprocessChange(sel) {
    const card = sel.closest('.entry-card');
    const group = document.getElementById('groupName').value;
    const macro = sel.value;
    const wt = card.querySelector('.work-type');
    wt.innerHTML = '<option value="">Seleccionar...</option>';

    if (!group || !macro) return;

    const gKey = group.includes('Trackless') ? 'Trackless' : group.includes('Convencional') ? 'Convencional' : 'Electrico';
    const tipoKey = getTipoKey(gKey, macro);

    const opts = opt.tipos_trabajo[tipoKey] || [];
    opts.forEach(p => {
        const val = typeof p === 'string' ? p : p.name;
        const o = document.createElement('option'); o.value = val; o.textContent = val;
        o.dataset.defaultAction = typeof p === 'string' ? '' : (p.default_action || '');
        wt.appendChild(o);
    });
}

// Auto-select action when work type changes
document.addEventListener('change', function(e) {
    if (e.target.classList.contains('work-type')) {
        const sel = e.target;
        const card = sel.closest('.entry-card');
        if (card) {
            const actionSel = card.querySelector('.action-type');
            const defAction = sel.options[sel.selectedIndex]?.dataset?.defaultAction;
            if (defAction && actionSel) {
                Array.from(actionSel.options).forEach(function(opt) {
                    if (opt.value === defAction) opt.selected = true;
                });
            }
        }
    }
});

function onEquipoCategoriaChange(sel) {
    const card = sel.closest('.entry-card');
    const sub = card.querySelector('.equipo-sub');
    const otrasInput = card.querySelector('.equipo-sub-otras');
    sub.innerHTML = '<option value="">Seleccionar...</option>';
    otrasInput.classList.add('d-none');
    otrasInput.value = '';

    const cat = sel.value;
    if (!cat || !opt.equipos[cat]) {
        card.querySelector('.medidores-section').classList.add('d-none');
        return;
    }

    (opt.equipos[cat].subequipos || []).forEach(eq => {
        const o = document.createElement('option');
        o.value = eq.nombre;
        o.dataset.mide = eq.mide || 'fin';
        o.textContent = eq.nombre;
        sub.appendChild(o);
    });

    const defaultMide = getDefaultMide(cat);
    const o = document.createElement('option');
    o.value = '__otras__';
    o.dataset.mide = defaultMide;
    o.textContent = 'Otras (especifique)';
    sub.appendChild(o);

    card.querySelector('.medidores-section').classList.remove('d-none');
    showMeters(card, null);
}

function getDefaultMide(cat) {
    const first = opt.equipos[cat]?.subequipos?.[0];
    return first?.mide || 'fin';
}

function onSubEquipoChange(sel) {
    const card = sel.closest('.entry-card');
    const selected = sel.options[sel.selectedIndex];
    const mide = selected?.dataset?.mide || 'fin';

    const otrasInput = card.querySelector('.equipo-sub-otras');
    if (selected?.value === '__otras__') {
        otrasInput.classList.remove('d-none');
    } else {
        otrasInput.classList.add('d-none');
        otrasInput.value = '';
    }

    showMeters(card, mide);
}

function showMeters(card, mide) {
    card.querySelectorAll('.medidor-fin, .medidor-horometro-motor, .medidor-horometro-jumbo, .medidor-horometro-volquetes, .medidor-kilometraje, .medidor-horometro-electrico, .medidor-horometro-percusion').forEach(el => el.classList.add('d-none'));

    if (!mide) {
        card.querySelector('.medidores-section').classList.add('d-none');
        return;
    }

    card.querySelector('.medidores-section').classList.remove('d-none');

    const meters = mide.split(',');

    if (meters.includes('fin')) {
        card.querySelector('.medidor-fin').classList.remove('d-none');
    }
    if (meters.includes('horometro_motor')) {
        const el = card.querySelector('.medidor-horometro-motor');
        el.classList.remove('d-none');
        validarMedidor(el.querySelector('input'), 'Horómetro de Motor');
    }
    if (meters.includes('horometro_jumbo')) {
        card.querySelector('.medidor-horometro-jumbo').classList.remove('d-none');
        validarMedidor(card.querySelector('.medidor-horometro-jumbo input'), 'Horómetro Jumbo');
        card.querySelector('.medidor-horometro-electrico').classList.remove('d-none');
        validarMedidor(card.querySelector('.medidor-horometro-electrico input'), 'Horómetro Eléctrico');
        card.querySelector('.medidor-horometro-percusion').classList.remove('d-none');
        validarMedidor(card.querySelector('.medidor-horometro-percusion input'), 'Horómetro de Percusión');
    }
    if (meters.includes('horometro_volquetes')) {
        const el = card.querySelector('.medidor-horometro-volquetes');
        el.classList.remove('d-none');
        validarMedidor(el.querySelector('input'), 'Horómetro de Motor');
    }
    if (meters.includes('kilometraje')) {
        const el = card.querySelector('.medidor-kilometraje');
        el.classList.remove('d-none');
        validarMedidor(el.querySelector('input'), 'Kilometraje');
    }
}

function validarMedidor(input, label) {
    if (!input) return;
    const card = input.closest('.entry-card');
    const equipoSub = card?.querySelector('.equipo-sub')?.value;

    // Show last reading reference if available
    if (equipoSub) {
        fetch(`/api/equipment/${encodeURIComponent(equipoSub)}/last-reading`)
            .then(r => r.json())
            .then(data => {
                if (data.found) {
                    const cls = [...input.classList].find(c => c.startsWith('horometro-') || c === 'kilometraje');
                    const clsMap = {
                        'horometro-motor': 'horometer_motor',
                        'horometro-jumbo': 'horometer_motor_jumbo',
                        'horometro-volquetes': 'horometer_motor_volquetes',
                        'horometro-electrico': 'horometer_electric',
                        'horometro-percusion': 'horometer_percussion',
                        'kilometraje': 'kilometer',
                    };
                    const key = clsMap[cls];
                    if (key && data.readings[key] !== null && data.readings[key] !== undefined) {
                        let ref = input.parentElement.querySelector('.last-reading-ref');
                        if (!ref) {
                            ref = document.createElement('small');
                            ref.className = 'last-reading-ref text-muted d-block';
                            ref.style.cssText = 'font-size:0.65rem;line-height:1;margin-top:2px;';
                            input.parentElement.appendChild(ref);
                        }
                        ref.textContent = `Anterior: ${data.readings[key]}`;
                    }
                }
            })
            .catch(() => {});
    }
}

function calcularDuracion(startInp, endInp, durInp) {
    const calc = () => {
        if (startInp.value && endInp.value) {
            const [h1, m1] = startInp.value.split(':').map(Number);
            const [h2, m2] = endInp.value.split(':').map(Number);
            const t1 = h1 * 60 + m1;
            const t2 = h2 * 60 + m2;
            const diff = t2 >= t1 ? t2 - t1 : (t2 + 1440) - t1;
            const h = Math.floor(diff / 60);
            const m = diff % 60;
            durInp.value = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
        }
    };
    startInp.addEventListener('change', calc);
    endInp.addEventListener('change', calc);
}
function confirmYesNo(msg) {
    return new Promise(resolve => {
        const modalEl = document.getElementById('confirmModal');
        const body = modalEl.querySelector('.modal-body');
        body.textContent = msg;
        // Use a single Modal instance to avoid backdrop accumulation
        if (!window._confirmModal) {
            window._confirmModal = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });
        }
        // Wait for full hide animation before resolving, so next modal can show cleanly
        modalEl._confirmResolve = resolve;
        window._confirmModal.show();
    });
}
document.getElementById('confirmYes')?.addEventListener('click', () => {
    const modal = document.getElementById('confirmModal');
    const resolve = modal._confirmResolve;
    modal._confirmResolve = null;
    window._confirmModal?.hide();
    // Resolve after hide animation completes so backdrop is removed
    modal.addEventListener('hidden.bs.modal', () => resolve?.(true), { once: true });
});
document.getElementById('confirmNo')?.addEventListener('click', () => {
    const modal = document.getElementById('confirmModal');
    const resolve = modal._confirmResolve;
    modal._confirmResolve = null;
    window._confirmModal?.hide();
    modal.addEventListener('hidden.bs.modal', () => resolve?.(false), { once: true });
});

async function addEntry() {
    const container = document.getElementById('entriesContainer');
    const cards = container.querySelectorAll('.entry-card');
    const clone = cards[0].cloneNode(true);

    // Collect previous entry values BEFORE cloning
    const previousEntry = cards[cards.length - 1];
    let prevNivel = null, prevLugar = null, prevColabs = null;
    let prevEquipoCat = null, prevEquipoSub = null, prevEquipoOtras = null;
    let prevHorometroMotor = null, prevHorometroJumbo = null, prevHorometroVolquetes = null;
    let prevKilometraje = null, prevHorometroElectrico = null, prevHorometroPercusion = null;

    if (previousEntry) {
        prevNivel = previousEntry.querySelector('.nivel')?.value;
        prevLugar = previousEntry.querySelector('.lugar')?.value;
        prevColabs = getCardColaboradores(previousEntry);
        prevEquipoCat = previousEntry.querySelector('.equipo-categoria')?.value;
        prevEquipoSub = previousEntry.querySelector('.equipo-sub')?.value;
        prevEquipoOtras = previousEntry.querySelector('.equipo-sub-otras')?.value;
        prevHorometroMotor = previousEntry.querySelector('.horometro-motor')?.value;
        prevHorometroJumbo = previousEntry.querySelector('.horometro-jumbo')?.value;
        prevHorometroVolquetes = previousEntry.querySelector('.horometro-volquetes')?.value;
        prevKilometraje = previousEntry.querySelector('.kilometraje')?.value;
        prevHorometroElectrico = previousEntry.querySelector('.horometro-electrico')?.value;
        prevHorometroPercusion = previousEntry.querySelector('.horometro-percusion')?.value;
    }

    // Reset clone fields
    clone.querySelectorAll('input, textarea, select').forEach(el => {
        if (el.tagName === 'SELECT') el.selectedIndex = 0;
        else if (el.type === 'checkbox') el.checked = false;
        else el.value = '';
    });

    // Reset per-entry collaborator section in clone
    const cloneColabSection = clone.querySelector('.entry-colab-section');
    if (cloneColabSection) {
        cloneColabSection.classList.add('d-none');
        cloneColabSection.querySelector('.entry-colab-checkboxes').innerHTML = '';
        cloneColabSection.querySelector('.entry-colab-otras-row').classList.add('d-none');
        cloneColabSection.querySelector('.entry-colab-otras-input').value = '';
        const doneBtn = cloneColabSection.querySelector('.entry-colab-done');
        doneBtn.classList.add('d-none');
        doneBtn.style.boxShadow = '';
        doneBtn.onclick = null;
    }

    container.appendChild(clone);
    renumberEntries();
    updateRemoveButtons();
    clone.querySelector('.remove-entry').style.display = 'inline-block';

    initEntry(clone);
    const group = document.getElementById('groupName').value;
    if (group) {
        populateMacroprocess(clone);
        populateActions(clone);
        // Repopulate collaborators in this new card
        const key = group.includes('Trackless') ? 'Trackless' : group.includes('Convencional') ? 'Convencional' : 'Electrico';
        const maxSelect = opt.colab_max_select || 4;
        const cs = clone.querySelector('.entry-colab-section');
        if (cs) {
            cs.classList.remove('d-none');
            cs.querySelector('.colab-max-label').textContent = maxSelect;
            const container2 = cs.querySelector('.entry-colab-checkboxes');
            const uniqueId = 'card_' + Math.random().toString(36).substr(2, 6);
            (opt.colaboradores[key] || []).forEach((name, i) => {
                const d = document.createElement('div');
                d.className = 'col-md-4 col-lg-3';
                d.innerHTML = `<div class="form-check">
                    <input class="form-check-input colab-check" type="checkbox" value="${name}" id="${uniqueId}_colab_${i}">
                    <label class="form-check-label" for="${uniqueId}_colab_${i}">${name}</label>
                </div>`;
                container2.appendChild(d);
            });
            const div = document.createElement('div');
            div.className = 'col-md-4 col-lg-3';
            div.innerHTML = `<div class="form-check">
                <input class="form-check-input colab-check" type="checkbox" value="__otras__" id="${uniqueId}_colab_otras">
            <label class="form-check-label" for="${uniqueId}_colab_otras"><strong>Otros</strong></label>
            </div>`;
            container2.appendChild(div);
            container2.querySelectorAll('.colab-check').forEach(cb => {
                cb.addEventListener('change', () => onCardColabChange(clone));
            });
        }
    }

    // Copy data from previous entry with sequential questions
    if (previousEntry && (prevNivel || prevLugar)) {
        let copyTrabajadores = false;
        let copyNivel = false;
        let copyLugar = false;

        // Step 1: Ask about workers (only if previous entry had collaborators)
        if (prevColabs) {
            copyTrabajadores = await confirmYesNo('¿Son los mismos trabajadores que la entrada anterior?');
        }

        // If not same workers → show per-entry collaborator section in the cloned card
        if (!copyTrabajadores) {
            const cs = clone.querySelector('.entry-colab-section');
            if (cs) {
                cs.classList.remove('d-none');
                cs.scrollIntoView({ behavior: 'smooth', block: 'center' });
                cs.style.transition = 'box-shadow 0.3s';
                cs.style.boxShadow = '0 0 0 3px #ffc107';
                const doneBtn = cs.querySelector('.entry-colab-done');
                doneBtn.classList.remove('d-none');
                await new Promise(resolve => {
                    doneBtn.onclick = () => {
                        doneBtn.classList.add('d-none');
                        cs.style.boxShadow = '';
                        resolve();
                    };
                });
            }
        }

        // Step 2: Ask about nivel
        if (prevNivel) {
            copyNivel = await confirmYesNo('¿Es el mismo nivel de trabajo?');
        }

        // Step 3: Ask about lugar (only if yes to nivel)
        if (copyNivel && prevLugar) {
            copyLugar = await confirmYesNo('¿Es la misma labor o lugar de trabajo?');
        }

        // Step 4: Ask about equipment (only if previous entry had equipment)
        let copyEquipo = false;
        if (prevEquipoCat) {
            copyEquipo = await confirmYesNo('¿Es el mismo equipo que la entrada anterior?');
        }

        // Apply copies
        if (copyTrabajadores && previousEntry) {
            const srcChecks = previousEntry.querySelectorAll('.colab-check');
            const dstChecks = clone.querySelectorAll('.colab-check');
            srcChecks.forEach(src => {
                if (src.checked) {
                    dstChecks.forEach(dst => { if (dst.value === src.value) dst.checked = true; });
                }
            });
            const srcOtras = previousEntry.querySelector('.entry-colab-otras-input');
            const dstOtrasInput = clone.querySelector('.entry-colab-otras-input');
            const dstOtrasRow = clone.querySelector('.entry-colab-otras-row');
            if (srcOtras?.value) {
                if (dstOtrasInput) dstOtrasInput.value = srcOtras.value;
                if (dstOtrasRow) dstOtrasRow.classList.remove('d-none');
                dstChecks.forEach(dst => { if (dst.value === '__otras__') dst.checked = true; });
            }
        }

        if (copyNivel && prevNivel) {
            const dstNivel = clone.querySelector('.nivel');
            if (dstNivel) {
                Array.from(dstNivel.options).forEach(opt => {
                    if (opt.value === prevNivel) opt.selected = true;
                });
            }
        }

        if (copyLugar && prevLugar) {
            const dstLugar = clone.querySelector('.lugar');
            if (dstLugar) dstLugar.value = prevLugar;
        }

        // Apply equipment copy (equipo, sub-equipo, sub-otras, meter fields + horometers)
        if (copyEquipo && prevEquipoCat) {
            clone.dataset.sameEquipo = 'true';
            const dstCat = clone.querySelector('.equipo-categoria');
            const dstSub = clone.querySelector('.equipo-sub');
            const dstOtras = clone.querySelector('.equipo-sub-otras');
            if (dstCat) {
                dstCat.value = prevEquipoCat;
                // Trigger change to populate sub-equipos
                const evt = new Event('change', { bubbles: true });
                dstCat.dispatchEvent(evt);
            }
            if (dstSub && prevEquipoSub) {
                // Wait briefly for sub-equipo options to be populated by the change event
                setTimeout(() => {
                    dstSub.value = prevEquipoSub;
                    if (prevEquipoSub === '__otras__' && dstOtras) {
                        dstOtras.value = prevEquipoOtras || '';
                        dstOtras.classList.remove('d-none');
                    }
                    // Show meter fields based on selected sub-equipo
                    const selectedOpt = dstSub.options[dstSub.selectedIndex];
                    const mide = selectedOpt?.dataset?.mide || null;
                    const metersSection = clone.querySelector('.medidores-section');
                    if (metersSection) {
                        metersSection.classList.remove('d-none');
                        // Hide all meter inputs first
                        metersSection.querySelectorAll('.meter-input').forEach(el => el.classList.add('d-none'));
                        metersSection.querySelector('.medidor-fin')?.classList.add('d-none');
                    }
                    if (mide) showMeters(clone, mide);
                    // Copy horometer/kilometer values from previous entry
                    const setVal = (sel, val) => {
                        const el = clone.querySelector(sel);
                        if (el && val) el.value = val;
                    };
                    setVal('.horometro-motor', prevHorometroMotor);
                    setVal('.horometro-jumbo', prevHorometroJumbo);
                    setVal('.horometro-volquetes', prevHorometroVolquetes);
                    setVal('.kilometraje', prevKilometraje);
                    setVal('.horometro-electrico', prevHorometroElectrico);
                    setVal('.horometro-percusion', prevHorometroPercusion);
                }, 100);
            }
        }
    }

    clone.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function removeEntry(btn) {
    const container = document.getElementById('entriesContainer');
    if (container.querySelectorAll('.entry-card').length <= 1) return;
    btn.closest('.entry-card').remove();
    renumberEntries();
    updateRemoveButtons();
}

function renumberEntries() {
    document.querySelectorAll('#entriesContainer .entry-card').forEach((card, i) => {
        card.querySelector('.entry-num').textContent = `#${i + 1}`;
    });
}

function updateRemoveButtons() {
    const n = document.querySelectorAll('#entriesContainer .entry-card').length;
    document.querySelectorAll('#entriesContainer .remove-entry').forEach(btn => {
        btn.style.display = n > 1 ? 'inline-block' : 'none';
    });
}

function getCardColaboradores(card) {
    if (!card) return null;
    const section = card.querySelector('.entry-colab-section');
    if (!section) return null;
    const checks = section.querySelectorAll('.colab-check:checked');
    const names = [];
    checks.forEach(c => {
        if (c.value === '__otras__') {
            const otras = section.querySelector('.entry-colab-otras-input')?.value?.trim();
            if (otras) names.push(otras);
        } else {
            names.push(c.value);
        }
    });
    return names.length > 0 ? names.join(', ') : null;
}

// ─── SUBMIT ─────────────────────────────────────────────────────────────────

document.getElementById('reportForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Enviando...';

    try {
        const group = document.getElementById('groupName').value;
        const gKey = group.includes('Trackless') ? 'Trackless' : group.includes('Convencional') ? 'Convencional' : 'Electrico';

        const entries = [];
        document.querySelectorAll('.entry-card').forEach(card => {
            const getVal = (sel) => { const v = card.querySelector(sel)?.value?.trim(); return v || null; };

            const subSel = card.querySelector('.equipo-sub');
            const subOpt = subSel?.options[subSel.selectedIndex];
            const isOtras = subOpt?.value === '__otras__';
            const otrasVal = card.querySelector('.equipo-sub-otras')?.value?.trim();
            const equipoSub = subOpt?.value || null;
            const equipoSubText = isOtras ? (otrasVal || 'Otras') : equipoSub;

            const equipoCategoria = getVal('.equipo-categoria');

            const mide = subOpt?.dataset?.mide || null;
            const readMeter = (cls) => {
                const el = card.querySelector(cls);
                if (!el) return null;
                const parentMeterDiv = el.closest('[class*="medidor-"]');
                if (parentMeterDiv && parentMeterDiv.classList.contains('d-none')) return null;
                const v = parseFloat(el.value);
                return isNaN(v) ? null : v;
            };

            const entry = {
                macroprocess: getVal('.macroprocess'),
                work_type: getVal('.work-type'),
                action: getVal('.action-type'),
                description: getVal('.descripcion'),
                level: getVal('.nivel'),
                location: getVal('.lugar'),
                start_time_int: getVal('.hora-inicio'),
                end_time_int: getVal('.hora-fin'),
                duration: getVal('.duracion'),
                equipment: equipoSubText || equipoCategoria,
                horometer_motor: readMeter('.horometro-motor'),
                horometer_motor_jumbo: readMeter('.horometro-jumbo'),
                horometer_motor_volquetes: readMeter('.horometro-volquetes'),
                horometer_electric: readMeter('.horometro-electrico'),
                horometer_percussion: readMeter('.horometro-percusion'),
                kilometer: readMeter('.kilometraje'),
                collaborators: getCardColaboradores(card),
            };

            entry._categoria = equipoCategoria;
            entries.push(entry);
        });

        const wn = (document.getElementById('workerName').value || '').trim() || 'Trabajador';
        const payload = {
            worker_name: wn,
            worker_email: wn.toLowerCase().replace(/[^a-z0-9]/g, '.') + '@mina.com',
            date: document.getElementById('reportDate').value,
            shift: document.getElementById('shift').value,
            group_name: group,
            start_time: null,
            end_time: null,
            collaborators_trackless: null,
            collaborators_convencional: null,
            collaborators_electrico: null,
            entries: entries.map(e => { const { _files, ...rest } = e; return rest; }),
        };

        const res = await fetch('/api/reports', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const errText = await res.text();
            throw new Error(errText || 'Error del servidor');
        }

        const report = await res.json();

        let successHtml = `<div class="alert alert-success">✅ Reporte <strong>#${report.id}</strong> enviado correctamente.</div>`;

        report.entries.forEach((e, i) => {
            const meterLines = [];
            if (e.horometer_motor) meterLines.push(`🔄 Horómetro Motor: <strong>${e.horometer_motor}</strong>`);
            if (e.horometer_motor_jumbo) meterLines.push(`🔄 Horómetro Jumbo: <strong>${e.horometer_motor_jumbo}</strong>`);
            if (e.horometer_motor_volquetes) meterLines.push(`🔄 Horómetro Motor: <strong>${e.horometer_motor_volquetes}</strong>`);
            if (e.horometer_electric) meterLines.push(`⚡ Horómetro Eléctrico: <strong>${e.horometer_electric}</strong>`);
            if (e.horometer_percussion) meterLines.push(`🔨 Horómetro Percusión: <strong>${e.horometer_percussion}</strong>`);
            if (e.kilometer) meterLines.push(`📏 Kilometraje: <strong>${e.kilometer}</strong>`);

            const entryColabs = entries[i].collaborators || e.collaborators || '—';
            successHtml += `
<div class="mb-3 p-3 border border-warning rounded" style="background:rgba(245,158,11,0.05)">
  <h6 class="text-warning mb-2">🔧 Trabajo #${i + 1}</h6>
  <table style="width:100%;font-size:0.9rem;">
    <tr><td style="width:140px;color:#94a3b8;vertical-align:top;">👥 Grupo</td><td><strong>${payload.group_name}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">🧑‍🔧 Colaboradores</td><td><strong>${entryColabs}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">📋 Detalle</td><td><strong>${e.action || '—'}</strong>${e.description ? '<br>' + e.description : ''}</td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">⚙️ Equipo</td><td><strong>${e.equipment || '—'}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">🏷️ Familia</td><td><strong>${entries[i]._categoria || '—'}</strong></td></tr>
    ${meterLines.length ? `<tr><td style="color:#94a3b8;vertical-align:top;">📊 Medidores</td><td>${meterLines.join('<br>')}</td></tr>` : ''}
    <tr><td style="color:#94a3b8;vertical-align:top;">⏱️ Tiempo</td><td><strong>${e.start_time_int || '?'} → ${e.end_time_int || '?'}</strong> (🕒 ${e.duration || '—'})</td></tr>
  </table>
</div>`;
        });

        // Build WhatsApp text
        const waText = buildWhatsAppText(report, entries, payload) + `\n\n🦺 *RACS*: Envía tus 2 reportes semanales → ${window.location.origin}/racs`;
        const waUrl = getWhatsAppUrl(waText);
        const waEncoded = encodeURIComponent(waText);
        successHtml += `<div class="mt-3 text-center d-flex gap-2 justify-content-center flex-wrap">
            <a href="${waUrl}" target="_blank" class="btn btn-success btn-sm px-3">
                <i class="bi bi-whatsapp me-1"></i> Enviar por WhatsApp
            </a>
            <button onclick="copyToClipboard('${waEncoded.replace(/'/g, "\\'")}')" class="btn btn-outline-secondary btn-sm px-3">
                <i class="bi bi-clipboard me-1"></i> Copiar texto
            </button>
        </div>`;

        showModal('✅ Reporte Enviado', successHtml);
        clearFormState();

        document.getElementById('reportForm').reset();
        document.getElementById('reportDate').value = new Date().toISOString().split('T')[0];
        document.querySelectorAll('.entry-card').forEach((c, i) => { if (i > 0) c.remove(); });
        // Reset per-entry collaborators in remaining card
        document.querySelectorAll('.entry-colab-section').forEach(sec => {
            sec.classList.add('d-none');
            sec.querySelector('.entry-colab-checkboxes').innerHTML = '';
            sec.querySelector('.entry-colab-otras-row').classList.add('d-none');
            sec.querySelector('.entry-colab-otras-input').value = '';
        });
        renumberEntries();
        updateRemoveButtons();
        loadRecentReports(20);
    } catch (err) {
        showModal('Error', `<div class="alert alert-danger">Error al enviar: ${err.message}</div>`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-send"></i> Enviar Reporte';
    }
});

// ─── SEARCH ──────────────────────────────────────────────────────────────────

document.getElementById('searchCollapse')?.addEventListener('show.bs.collapse', () => {
    if (!document.querySelector('#searchResults tr')) {
        loadRecentReports(20);
    }
});

async function loadRecentReports(limit = 20) {
    document.getElementById('searchWorker').value = '';
    document.getElementById('searchDateFrom').value = '';
    document.getElementById('searchDateTo').value = '';
    _searchCursor = null;
    _searchCursorDate = null;
    _searchHasMore = false;
    _searchParams = {};
    await fetchReports({ limit }, true);
}

async function searchReports() {
    _searchCursor = null;
    _searchCursorDate = null;
    _searchHasMore = false;
    const w = document.getElementById('searchWorker').value;
    const f = document.getElementById('searchDateFrom').value;
    const t = document.getElementById('searchDateTo').value;
    _searchParams = {};
    if (w) _searchParams.worker_name = w;
    if (f) _searchParams.date_from = f;
    if (t) _searchParams.date_to = t;
    await fetchReports({ ..._searchParams, limit: 50 }, true);
}

async function fetchReports(params, replace = false) {
    const container = document.getElementById('searchResults');
    if (replace) container.innerHTML = '<p class="text-muted small">Cargando...</p>';
    try {
        if (_searchCursor && _searchCursorDate) {
            params.cursor = _searchCursor;
            params.cursor_date = _searchCursorDate;
        }
        const qs = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') qs.set(k, v); });
        const r = await fetch(`/api/reports?${qs}`);
        const data = await r.json();
        const reports = data.data || [];
        _searchHasMore = data.has_more || false;
        if (data.next_cursor) {
            _searchCursor = data.next_cursor[0];
            _searchCursorDate = data.next_cursor[1];
        } else {
            _searchCursor = null;
            _searchCursorDate = null;
        }
        if (replace) {
            renderReportsTable(reports, container);
        } else {
            appendReportsTable(reports, container);
        }
    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
    }
}

function renderReportsTable(reports, container) {
    if (!reports.length) {
        container.innerHTML = '<div class="alert alert-info">No se encontraron reportes.</div>';
        _searchHasMore = false;
        return;
    }
    window._allReports = reports.slice();

    let html = `<div class="d-flex justify-content-between align-items-center mb-2">
        <div>
            <button class="btn btn-sm btn-outline-danger d-none" id="batchDeleteBtn" onclick="promptBatchDelete()"><i class="bi bi-trash"></i> Eliminar seleccionados <span id="batchCount">0</span></button>
        </div>
        <label class="text-muted small"><input type="checkbox" id="selectAllCheck" onchange="toggleSelectAll()"> Seleccionar todo</label>
    </div>`;
    html += `<div class="table-responsive"><table class="table table-sm table-hover mb-1" style="min-width:600px;">
        <thead><tr class="table-dark">
            <th style="width:30px"></th><th>#</th><th>🌓 Turno</th><th>🧑‍🔧 Trabajador</th><th>🧑‍🔧 Colaboradores</th><th>🔧 Trabajos</th><th></th>
        </tr></thead><tbody>`;

    const grouped = groupReports(reports);
    let firstGroup = true;
    for (const [group, dates] of grouped) {
        if (!firstGroup) html += `<tr class="separator-row"><td colspan="7" style="padding:4px 0;"></td></tr>`;
        firstGroup = false;
        html += `<tr class="group-header"><td colspan="7">👥 ${group}</td></tr>`;
        for (const [dateStr, dateReports] of dates) {
            html += `<tr class="date-subheader"><td colspan="7">📅 ${formatDate(dateStr)} (${dateReports.length})</td></tr>`;
            for (const rp of dateReports) {
                const colabs = [];
                if (rp.collaborators_trackless) colabs.push(rp.collaborators_trackless);
                if (rp.collaborators_convencional) colabs.push(rp.collaborators_convencional);
                if (rp.collaborators_electrico) colabs.push(rp.collaborators_electrico);
                const colabText = colabs.join(', ').substring(0, 60) + (colabs.join(', ').length > 60 ? '...' : '');
                const workerCell = rp.worker_name || '—';
                html += `<tr>
                    <td><input type="checkbox" class="report-check" value="${rp.id}" onchange="updateBatchDeleteBtn()"></td>
                    <td>${rp.id}</td>
                    <td>${rp.shift}</td>
                    <td>${workerCell}</td>
                    <td title="${colabs.join(', ')}">${colabText}</td>
                    <td>${(rp.entries || []).length}</td>
                    <td class="text-nowrap">
                        <button class="btn btn-sm btn-outline-info" onclick="viewReport(${rp.id})"><i class="bi bi-eye"></i></button>
                        <button class="btn btn-sm btn-outline-warning" onclick="editReport(${rp.id})"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteReport(${rp.id})"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>`;
            }
        }
    }
    html += '</tbody></table></div>';

    if (_searchHasMore) {
        html += `<div class="text-center mt-2"><button class="btn btn-outline-light btn-sm" onclick="loadMoreReports()"><i class="bi bi-plus-circle"></i> Ver más</button></div>`;
    }
    html += `<p class="text-muted small mt-1">${_searchHasMore ? 'Mostrando primeros ' + reports.length : reports.length} reporte(s)</p>`;
    container.innerHTML = html;
}

function appendReportsTable(newReports, container) {
    if (window._allReports) {
        window._allReports = window._allReports.concat(newReports);
    } else {
        window._allReports = newReports.slice();
    }
    renderReportsTable(window._allReports, container);
}

function groupReports(reports) {
    const map = new Map();
    for (const rp of reports) {
        const g = rp.group_name || 'Sin grupo';
        const d = rp.date;
        if (!map.has(g)) map.set(g, new Map());
        const dates = map.get(g);
        if (!dates.has(d)) dates.set(d, []);
        dates.get(d).push(rp);
    }
    const sorted = new Map();
    [...map.keys()].sort().forEach(g => {
        const dates = map.get(g);
        const sortedDates = new Map([...dates.entries()].sort((a, b) => b[0].localeCompare(a[0])));
        sorted.set(g, sortedDates);
    });
    return sorted;
}

function loadMoreReports() {
    fetchReports({ ..._searchParams, limit: 50 }, false);
}

async function exportCSV() {
    const params = new URLSearchParams();
    const f = document.getElementById('searchDateFrom').value;
    const t = document.getElementById('searchDateTo').value;
    if (f) params.set('date_from', f);
    if (t) params.set('date_to', t);
    window.location.href = `/api/reports/export/csv?${params}`;
}

async function exportExcel() {
    const params = new URLSearchParams();
    const f = document.getElementById('searchDateFrom').value;
    const t = document.getElementById('searchDateTo').value;
    if (f) params.set('date_from', f);
    if (t) params.set('date_to', t);
    window.location.href = `/api/reports/export/excel?${params}`;
}

async function viewReport(id) {
    try {
        const r = await (await fetch(`/api/reports/${id}`)).json();

        // ── Header info ──
        let html = `<div class="mb-3 p-3 border border-info rounded" style="background:rgba(13,110,253,0.05)">
            <div class="d-flex align-items-center gap-2 mb-2">
                <span style="font-size:1.5rem;">📋</span>
                <h5 class="mb-0 text-info">Reporte <strong>#${r.id}</strong></h5>
            </div>
            <table style="width:100%;font-size:0.9rem;">
                <tr><td style="width:100px;color:#94a3b8;">📅 Fecha</td><td><strong>${formatDate(r.date)}</strong></td></tr>
                <tr><td style="color:#94a3b8;">🌓 Turno</td><td><strong>${r.shift}</strong></td></tr>
                <tr><td style="color:#94a3b8;">👥 Grupo</td><td><strong>${r.group_name}</strong></td></tr>
            </table>
        </div>`;

        // ── Entries ──
        (r.entries || []).forEach((e, i) => {
            const colabs = e.collaborators || '—';

            const meterLines = [];
            if (e.horometer_motor) meterLines.push(`🔄 Horómetro Motor: <strong>${e.horometer_motor}</strong>`);
            if (e.horometer_motor_jumbo) meterLines.push(`🔄 Horómetro Jumbo: <strong>${e.horometer_motor_jumbo}</strong>`);
            if (e.horometer_motor_volquetes) meterLines.push(`🔄 Horómetro Motor: <strong>${e.horometer_motor_volquetes}</strong>`);
            if (e.horometer_electric) meterLines.push(`⚡ Horómetro Eléctrico: <strong>${e.horometer_electric}</strong>`);
            if (e.horometer_percussion) meterLines.push(`🔨 Horómetro Percusión: <strong>${e.horometer_percussion}</strong>`);
            if (e.kilometer) meterLines.push(`📏 Kilometraje: <strong>${e.kilometer}</strong>`);

            html += `
<div class="mb-3 p-3 border border-warning rounded" style="background:rgba(245,158,11,0.05)">
  <h6 class="text-warning mb-2">🔧 Trabajo #${i + 1}</h6>
  <table style="width:100%;font-size:0.9rem;">
    <tr><td style="width:140px;color:#94a3b8;vertical-align:top;">🏭 Macroproceso</td><td><strong>${e.macroprocess || '—'}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">📌 Tipo de Trabajo</td><td><strong>${e.work_type || '—'}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">⚡ Acción</td><td><strong>${e.action || '—'}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">🧑‍🔧 Colaboradores</td><td><strong>${colabs}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">📝 Descripción</td><td>${e.description || '—'}</td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">⚙️ Equipo</td><td><strong>${e.equipment || '—'}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">📊 Nivel</td><td><strong>${e.level || '—'}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">📍 Lugar</td><td><strong>${e.location || '—'}</strong></td></tr>
    <tr><td style="color:#94a3b8;vertical-align:top;">⏱️ Tiempo</td><td><strong>${e.start_time_int || '?'} → ${e.end_time_int || '?'}</strong> (🕒 ${e.duration || '—'})</td></tr>
    ${meterLines.length ? `<tr><td style="color:#94a3b8;vertical-align:top;">📊 Medidores</td><td>${meterLines.join('<br>')}</td></tr>` : ''}
  </table>
</div>`;
        });

        // WhatsApp button + copy button
        const waText = buildWhatsAppText(r, null, r) + `\n\n🦺 *RACS*: Envía tus 2 reportes semanales → ${window.location.origin}/racs`;
        const waUrl = getWhatsAppUrl(waText);
        const waEncoded = encodeURIComponent(waText);
        html += `<div class="mt-3 text-center d-flex gap-2 justify-content-center flex-wrap">
            <a href="${waUrl}" target="_blank" class="btn btn-success btn-sm px-3">
                <i class="bi bi-whatsapp me-1"></i> Enviar por WhatsApp
            </a>
            <button onclick="editReportFromView(${r.id})" class="btn btn-outline-warning btn-sm px-3">
                <i class="bi bi-pencil me-1"></i> Editar
            </button>
            <button onclick="copyToClipboard('${waEncoded.replace(/'/g, "\\'")}')" class="btn btn-outline-secondary btn-sm px-3">
                <i class="bi bi-clipboard me-1"></i> Copiar texto
            </button>
        </div>`;

        showModal(`📋 Reporte #${r.id}`, html);
    } catch (err) {
        showModal('Error', `<div class="alert alert-danger">${err.message}</div>`);
    }
}

function formatDate(isoDate) {
    if (!isoDate) return '—';
    const parts = isoDate.split('-');
    if (parts.length !== 3) return isoDate;
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
}

function showModal(title, body) {
    document.getElementById('resultModalTitle').textContent = title;
    document.getElementById('resultModalBody').innerHTML = body;
    new bootstrap.Modal(document.getElementById('resultModal')).show();
}

// ─── WHATSAPP ───────────────────────────────────────────────────────────────

function getWhatsAppUrl(text) {
    const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const encoded = encodeURIComponent(text);
    if (isMobile) {
        return `whatsapp://send?text=${encoded}`;
    }
    return `https://web.whatsapp.com/send?text=${encoded}`;
}

function getWhatsAppGroup(groupName) {
    if (groupName.includes('Trackless')) return 'REPORTE DIARIO DE MANTTO TRACKLES GENERAL';
    if (groupName.includes('Convencional')) return 'TALLER SOLDADURA Y MECANICA CONVENCIONAL';
    if (groupName.includes('Electrico')) return 'ELECTRICISTAS';
    return 'REPORTE DE MANTENIMIENTO';
}

function copyToClipboard(encodedText) {
    const text = decodeURIComponent(encodedText);
    navigator.clipboard.writeText(text).then(() => {
        showToast('✅ Texto copiado al portapapeles');
    }).catch(() => {
        // Fallback for older browsers
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('✅ Texto copiado al portapapeles');
    });
}

function buildWhatsAppText(report, entriesData, payload) {
    const group = payload?.group_name || report.group_name;
    const sep = '═══════════════════════════════';
    let msg = `📋 *REPORTE DE MANTENIMIENTO #${report.id}*\n`;
    msg += `📅 Fecha: ${formatDate(report.date)}\n`;
    msg += `🌓 Turno: ${report.shift}\n`;
    msg += `👥 Grupo: ${group}\n\n`;

    (report.entries || []).forEach((e, i) => {
        const ed = entriesData?.[i] || {};
        const colabs = ed.collaborators || e.collaborators || '—';

        msg += `🔧 *TRABAJO #${i + 1}*\n`;
        msg += `🏭 Macroproceso: ${e.macroprocess || '—'}\n`;
        msg += `📌 Tipo: ${e.work_type || '—'}\n`;
        msg += `⚡ Acción: ${e.action || '—'}\n`;
        msg += `🧑‍🔧 Colaboradores: ${colabs}\n`;
        msg += `📝 Descripción: ${e.description || '—'}\n`;
        msg += `⚙️ Equipo: ${e.equipment || '—'}\n`;
        msg += `📊 Nivel: ${e.level || '—'}\n`;
        msg += `📍 Lugar: ${e.location || '—'}\n`;
        msg += `⏱️ Tiempo: ${e.start_time_int || '?'} → ${e.end_time_int || '?'} (🕒 ${e.duration || '—'})\n`;

        const meters = [];
        if (e.horometer_motor) meters.push(`🔄 H.Motor: ${e.horometer_motor}`);
        if (e.horometer_motor_jumbo) meters.push(`🔄 H.Jumbo: ${e.horometer_motor_jumbo}`);
        if (e.horometer_motor_volquetes) meters.push(`🔄 H.Motor: ${e.horometer_motor_volquetes}`);
        if (e.horometer_electric) meters.push(`⚡ H.Eléctrico: ${e.horometer_electric}`);
        if (e.horometer_percussion) meters.push(`🔨 H.Percusión: ${e.horometer_percussion}`);
        if (e.kilometer) meters.push(`📏 Km: ${e.kilometer}`);
        if (meters.length) msg += `📊 Medidores: ${meters.join(' | ')}\n`;

        msg += `\n${sep}\n\n`;
    });

    msg += `📲 *Enviado desde el Sistema de Reporte Diario*`;
    return msg;
}

// ─── TOAST ──────────────────────────────────────────────────────────────────

function showToast(msg, type = 'success') {
    const container = document.getElementById('toastContainer') || (() => {
        const c = document.createElement('div');
        c.id = 'toastContainer';
        c.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
        document.body.appendChild(c);
        return c;
    })();
    const t = document.createElement('div');
    t.className = `alert alert-${type} alert-dismissible fade show mb-0`;
    t.style.cssText = 'min-width:280px;box-shadow:0 8px 32px rgba(0,0,0,0.3);border-radius:12px;';
    t.innerHTML = `${msg} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    container.appendChild(t);
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 4000);
}

// ─── DAILY REPORTS ─────────────────────────────────────────────────────────

let dailyReportsVisible = false;

function toggleDailyReports() {
    const panel = document.getElementById('dailyReportsPanel');
    dailyReportsVisible = !dailyReportsVisible;
    panel.classList.toggle('d-none', !dailyReportsVisible);
    if (dailyReportsVisible) {
        loadDailyReports();
        // Default date = yesterday
        const d = new Date();
        d.setDate(d.getDate() - 1);
        document.getElementById('dailyReportDate').value = d.toISOString().split('T')[0];
    }
}

async function loadDailyReports() {
    const container = document.getElementById('dailyReportsList');
    try {
        const r = await fetch('/api/daily-reports');
        const dates = await r.json();
        if (!dates.length) {
            container.innerHTML = '<p class="text-muted">No hay fechas con reportes.</p>';
            return;
        }
        let html = '<div class="table-responsive"><table class="table table-sm"><thead><tr class="table-dark"><th>📅 Fecha</th><th></th></tr></thead><tbody>';
        for (const item of dates) {
            const d = item.date;
            html += `<tr>
                <td>${d}</td>
                <td class="text-end"><button class="btn btn-sm btn-success" onclick="downloadDailyReport('${d}')"><i class="bi bi-download"></i> Descargar</button></td>
            </tr>`;
        }
        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<p class="text-danger">Error: ${err.message}</p>`;
    }
}

async function downloadDailyReport(dateStr) {
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    try {
        const r = await fetch('/api/daily-reports/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_date: dateStr }),
        });
        if (!r.ok) throw new Error(await r.text());
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Reporte_Diario_${dateStr}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('✅ Descarga iniciada');
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-download"></i> Descargar';
    }
}

async function generateDailyReport() {
    const dateInput = document.getElementById('dailyReportDate').value;
    if (!dateInput) { alert('Selecciona una fecha'); return; }
    const btn = document.querySelector('#dailyReportsPanel .btn-primary');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Generando...';
    try {
        const r = await fetch('/api/daily-reports/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_date: dateInput }),
        });
        if (!r.ok) throw new Error(await r.text());
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Reporte_Diario_${dateInput}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('✅ Reporte generado y descargado');
        loadDailyReports();
    } catch (err) {
        showModal('Error', `<div class="alert alert-danger">${err.message}</div>`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-file-earmark-plus"></i> Generar Reporte';
    }
}

// ─── DELETE REPORTS ────────────────────────────────────────────────────

function deleteReport(id) {
    _pendingDeleteIds = [id];
    const modal = document.getElementById('deletePasswordModal');
    document.getElementById('deletePasswordInput').value = '';
    document.getElementById('deletePasswordError').classList.add('d-none');
    if (typeof bootstrap !== 'undefined' && modal) new bootstrap.Modal(modal).show();
}

function promptBatchDelete() {
    const checks = document.querySelectorAll('.report-check:checked');
    _pendingDeleteIds = Array.from(checks).map(cb => parseInt(cb.value));
    if (!_pendingDeleteIds.length) return;
    const modal = document.getElementById('deletePasswordModal');
    document.getElementById('deletePasswordInput').value = '';
    document.getElementById('deletePasswordError').classList.add('d-none');
    if (typeof bootstrap !== 'undefined' && modal) new bootstrap.Modal(modal).show();
}

async function confirmDeleteWithPassword() {
    const pw = document.getElementById('deletePasswordInput').value;
    if (!pw) return;
    const btn = document.querySelector('#deletePasswordModal .btn-danger');
    btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Eliminando...';
    try {
        const r = await fetch('/api/reports/delete-verify', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pw }),
        });
        if (!r.ok) {
            document.getElementById('deletePasswordError').classList.remove('d-none');
            btn.disabled = false; btn.innerHTML = '<i class="bi bi-trash"></i> Eliminar';
            return;
        }
        // Password correct — execute delete
        if (_pendingDeleteIds.length === 1) {
            const dr = await fetch(`/api/reports/${_pendingDeleteIds[0]}?password=${encodeURIComponent(pw)}`, { method: 'DELETE' });
            if (!dr.ok) { const e = await dr.text(); alert('Error: ' + e); return; }
        } else {
            const dr = await fetch('/api/reports/batch-delete', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: _pendingDeleteIds, password: pw }),
            });
            if (!dr.ok) { const e = await dr.text(); alert('Error: ' + e); return; }
        }
        bootstrap.Modal.getInstance(document.getElementById('deletePasswordModal'))?.hide();
        showModal('Eliminado', `<div class="alert alert-success">${_pendingDeleteIds.length} reporte(s) eliminado(s) correctamente.</div>`);
        _pendingDeleteIds = [];
        loadRecentReports(20);
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        btn.disabled = false; btn.innerHTML = '<i class="bi bi-trash"></i> Eliminar';
    }
}

function toggleSelectAll() {
    const checked = document.getElementById('selectAllCheck').checked;
    document.querySelectorAll('.report-check').forEach(cb => cb.checked = checked);
    updateBatchDeleteBtn();
}

function updateBatchDeleteBtn() {
    const count = document.querySelectorAll('.report-check:checked').length;
    const btn = document.getElementById('batchDeleteBtn');
    if (!btn) return;
    if (count > 0) {
        btn.classList.remove('d-none');
        btn.querySelector('#batchCount').textContent = `(${count})`;
    } else {
        btn.classList.add('d-none');
    }
}

let _editReportData = null;

function editReport(id) {
    fetch(`/api/reports/${id}`)
        .then(r => r.json())
        .then(r => {
            _editReportData = r;
            document.getElementById('editReportId').value = r.id;
            document.getElementById('editReportDate').value = r.date;
            document.getElementById('editReportShift').value = r.shift || '';
            document.getElementById('editReportGroup').value = r.group_name || '';
            document.getElementById('editPasswordInput').value = '';
            document.getElementById('editPasswordError').classList.add('d-none');
            new bootstrap.Modal(document.getElementById('editReportModal')).show();
        })
        .catch(err => alert('Error al cargar reporte: ' + err.message));
}

async function confirmEditReport() {
    const id = document.getElementById('editReportId').value;
    const date = document.getElementById('editReportDate').value;
    const shift = document.getElementById('editReportShift').value;
    const group = document.getElementById('editReportGroup').value;
    const password = document.getElementById('editPasswordInput').value;
    if (!password) return;
    if (!date) { alert('Debe seleccionar una fecha'); return; }
    if (!shift) { alert('Debe seleccionar un turno'); return; }
    if (!group) { alert('Debe seleccionar un grupo'); return; }
    const btn = document.querySelector('#editReportModal .btn-info');
    btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Guardando...';
    try {
        const r = await fetch(`/api/reports/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password, date, shift, group_name: group }),
        });
        if (!r.ok) {
            document.getElementById('editPasswordError').classList.remove('d-none');
            btn.disabled = false; btn.innerHTML = '<i class="bi bi-check-lg"></i> Guardar';
            return;
        }
        bootstrap.Modal.getInstance(document.getElementById('editReportModal'))?.hide();
        showToast('✅ Reporte #' + id + ' actualizado correctamente');
        _editReportData = null;
        loadRecentReports(20);
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        btn.disabled = false; btn.innerHTML = '<i class="bi bi-check-lg"></i> Guardar';
    }
}

function editReportFromView(id) {
    bootstrap.Modal.getInstance(document.getElementById('resultModal'))?.hide();
    editReport(id);
}
