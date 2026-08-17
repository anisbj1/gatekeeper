document.addEventListener('DOMContentLoaded', () => {
    fetchRules();
    fetchSchedules();

    // Form Submits
    document.getElementById('rule-form').addEventListener('submit', handleRuleSubmit);
    document.getElementById('schedule-form').addEventListener('submit', handleScheduleSubmit);

    // Modal triggers
    document.getElementById('btn-add-rule').addEventListener('click', () => openRuleModal());
    document.getElementById('btn-add-schedule').addEventListener('click', () => openScheduleModal());
});

// --- Subject Toggle ---
function toggleSubjectSelects(type) {
    const userGroup = document.getElementById('rule-user-group');
    const cardGroup = document.getElementById('rule-card-group');
    const userSelect = document.getElementById('rule-user-select');
    const cardSelect = document.getElementById('rule-card-select');

    if (type === 'user') {
        userGroup.style.display = 'block';
        cardGroup.style.display = 'none';
        cardSelect.value = '';
        userSelect.required = true;
        cardSelect.required = false;
    } else {
        userGroup.style.display = 'none';
        cardGroup.style.display = 'block';
        userSelect.value = '';
        cardSelect.required = true;
        userSelect.required = false;
    }
}

// --- Access Rules API ---
async function fetchRules() {
    const tableBody = document.getElementById('rules-table-body');
    tableBody.innerHTML = `<tr><td colspan="7" style="color: var(--text-muted); text-align: center; padding: 2rem;">Loading rules...</td></tr>`;

    const data = await API.get('/api/v1/rules/');
    if (!data) {
        tableBody.innerHTML = `<tr><td colspan="7" style="color: var(--error-color); text-align: center; padding: 2rem;">Failed to fetch rules.</td></tr>`;
        return;
    }

    if (data.results.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" style="color: var(--text-muted); text-align: center; padding: 2rem;">No access rules configured.</td></tr>`;
        return;
    }

    tableBody.innerHTML = '';
    data.results.forEach(rule => {
        const tr = document.createElement('tr');
        
        let subjectText = '';
        if (rule.user) {
            subjectText = `👤 ${rule.user_details}`;
        } else if (rule.card) {
            subjectText = `💳 Card: ${rule.card_uid} (${rule.user_details})`;
        }

        const schedText = rule.schedule ? rule.schedule_name : '🟢 24/7 Access';
        const startD = rule.start_date || '—';
        const endD = rule.end_date || '—';

        const activeBadge = rule.is_active 
            ? '<span class="badge badge-success">Enforced</span>' 
            : '<span class="badge badge-danger">Disabled</span>';

        tr.innerHTML = `
            <td><strong>${subjectText}</strong></td>
            <td>${rule.device_name}</td>
            <td>${schedText}</td>
            <td>${startD}</td>
            <td>${endD}</td>
            <td>${activeBadge}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="editRule(${rule.id})">Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteRule(${rule.id})">Delete</button>
            </td>
        `;
        tableBody.appendChild(tr);
    });
}

function openRuleModal(rule = null) {
    const modal = document.getElementById('rule-modal');
    const form = document.getElementById('rule-form');
    
    form.reset();
    document.getElementById('rule-id').value = '';
    toggleSubjectSelects('user');
    document.querySelector('input[name="subject_type"][value="user"]').checked = true;

    if (rule) {
        document.getElementById('rule-modal-title').textContent = 'Edit Access Rule';
        document.getElementById('rule-id').value = rule.id;
        
        if (rule.user) {
            toggleSubjectSelects('user');
            document.querySelector('input[name="subject_type"][value="user"]').checked = true;
            document.getElementById('rule-user-select').value = rule.user;
        } else if (rule.card) {
            toggleSubjectSelects('card');
            document.querySelector('input[name="subject_type"][value="card"]').checked = true;
            document.getElementById('rule-card-select').value = rule.card;
        }

        document.getElementById('rule-device-select').value = rule.device;
        document.getElementById('rule-schedule-select').value = rule.schedule || '';
        document.getElementById('rule-start-date').value = rule.start_date || '';
        document.getElementById('rule-end-date').value = rule.end_date || '';
        document.getElementById('rule-active').checked = rule.is_active;
    } else {
        document.getElementById('rule-modal-title').textContent = 'Add Access Rule';
    }
    
    modal.classList.add('active');
}

function closeRuleModal() {
    document.getElementById('rule-modal').classList.remove('active');
}

async function editRule(id) {
    const rule = await API.get(`/api/v1/rules/${id}/`);
    if (rule) {
        openRuleModal(rule);
    }
}

async function deleteRule(id) {
    if (confirm('Are you sure you want to delete this access rule?')) {
        const res = await API.delete(`/api/v1/rules/${id}/`);
        if (res) {
            showToast('Access rule deleted successfully.', 'success');
            fetchRules();
        }
    }
}

async function handleRuleSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('rule-id').value;
    
    const subjectType = document.querySelector('input[name="subject_type"]:checked').value;
    const payload = {
        device: parseInt(document.getElementById('rule-device-select').value),
        schedule: document.getElementById('rule-schedule-select').value ? parseInt(document.getElementById('rule-schedule-select').value) : null,
        start_date: document.getElementById('rule-start-date').value || null,
        end_date: document.getElementById('rule-end-date').value || null,
        is_active: document.getElementById('rule-active').checked
    };

    if (subjectType === 'user') {
        payload.user = parseInt(document.getElementById('rule-user-select').value);
        payload.card = null;
    } else {
        payload.card = parseInt(document.getElementById('rule-card-select').value);
        payload.user = null;
    }

    if (!payload.user && !payload.card) {
        showToast('Please select an employee or RFID card.', 'error');
        return;
    }

    let res;
    if (id) {
        res = await API.put(`/api/v1/rules/${id}/`, payload);
    } else {
        res = await API.post('/api/v1/rules/', payload);
    }

    if (res) {
        showToast(id ? 'Rule updated successfully.' : 'Rule created successfully.', 'success');
        closeRuleModal();
        fetchRules();
    }
}


// --- Schedules API ---
async function fetchSchedules() {
    const tableBody = document.getElementById('schedules-table-body');
    tableBody.innerHTML = `<tr><td colspan="4" style="color: var(--text-muted); text-align: center; padding: 2rem;">Loading schedules...</td></tr>`;

    const data = await API.get('/api/v1/schedules/');
    if (!data) {
        tableBody.innerHTML = `<tr><td colspan="4" style="color: var(--error-color); text-align: center; padding: 2rem;">Failed to fetch schedules.</td></tr>`;
        return;
    }

    if (data.results.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="4" style="color: var(--text-muted); text-align: center; padding: 2rem;">No schedules configured.</td></tr>`;
        return;
    }

    tableBody.innerHTML = '';
    data.results.forEach(sched => {
        const tr = document.createElement('tr');
        
        // Allowed days
        let days = [];
        if (sched.monday) days.push('Mon');
        if (sched.tuesday) days.push('Tue');
        if (sched.wednesday) days.push('Wed');
        if (sched.thursday) days.push('Thu');
        if (sched.friday) days.push('Fri');
        if (sched.saturday) days.push('Sat');
        if (sched.sunday) days.push('Sun');
        const daysStr = days.join(', ') || 'No Days Selected';

        const startT = sched.start_time.substring(0, 5);
        const endT = sched.end_time.substring(0, 5);

        tr.innerHTML = `
            <td><strong>${sched.name}</strong></td>
            <td>${daysStr}</td>
            <td><code>${startT} - ${endT}</code></td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="editSchedule(${sched.id})">Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteSchedule(${sched.id}, '${sched.name}')">Delete</button>
            </td>
        `;
        tableBody.appendChild(tr);
    });
}

function openScheduleModal(sched = null) {
    const modal = document.getElementById('schedule-modal');
    const form = document.getElementById('schedule-form');
    
    form.reset();
    document.getElementById('schedule-id').value = '';

    if (sched) {
        document.getElementById('schedule-modal-title').textContent = 'Edit Schedule';
        document.getElementById('schedule-id').value = sched.id;
        document.getElementById('sched-name').value = sched.name;
        document.getElementById('sched-mon').checked = sched.monday;
        document.getElementById('sched-tue').checked = sched.tuesday;
        document.getElementById('sched-wed').checked = sched.wednesday;
        document.getElementById('sched-thu').checked = sched.thursday;
        document.getElementById('sched-fri').checked = sched.friday;
        document.getElementById('sched-sat').checked = sched.saturday;
        document.getElementById('sched-sun').checked = sched.sunday;
        
        // Slice time formats (HH:MM:SS -> HH:MM)
        document.getElementById('sched-start-time').value = sched.start_time.substring(0, 5);
        document.getElementById('sched-end-time').value = sched.end_time.substring(0, 5);
    } else {
        document.getElementById('schedule-modal-title').textContent = 'Add Access Schedule';
    }
    
    modal.classList.add('active');
}

function closeScheduleModal() {
    document.getElementById('schedule-modal').classList.remove('active');
}

async function editSchedule(id) {
    const sched = await API.get(`/api/v1/schedules/${id}/`);
    if (sched) {
        openScheduleModal(sched);
    }
}

async function deleteSchedule(id, name) {
    if (confirm(`Are you sure you want to delete schedule "${name}"? This will affect all access rules pointing to it.`)) {
        const res = await API.delete(`/api/v1/schedules/${id}/`);
        if (res) {
            showToast(`Schedule "${name}" deleted successfully.`, 'success');
            fetchSchedules();
            fetchRules(); // Rules list will update schedules references
        }
    }
}

async function handleScheduleSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('schedule-id').value;
    
    const payload = {
        name: document.getElementById('sched-name').value,
        monday: document.getElementById('sched-mon').checked,
        tuesday: document.getElementById('sched-tue').checked,
        wednesday: document.getElementById('sched-wed').checked,
        thursday: document.getElementById('sched-thu').checked,
        friday: document.getElementById('sched-fri').checked,
        saturday: document.getElementById('sched-sat').checked,
        sunday: document.getElementById('sched-sun').checked,
        start_time: document.getElementById('sched-start-time').value,
        end_time: document.getElementById('sched-end-time').value
    };

    if (!Object.values(payload).slice(1, 8).some(val => val === true)) {
        showToast('Please select at least one day of the week.', 'error');
        return;
    }

    if (payload.end_time <= payload.start_time) {
        showToast('End time must be strictly after start time.', 'error');
        return;
    }

    let res;
    if (id) {
        res = await API.put(`/api/v1/schedules/${id}/`, payload);
    } else {
        res = await API.post('/api/v1/schedules/', payload);
    }

    if (res) {
        showToast(id ? 'Schedule updated successfully.' : 'Schedule created successfully.', 'success');
        closeScheduleModal();
        fetchSchedules();
        
        // Reload schedules lists
        location.reload(); // Refresh django template options
    }
}

window.editRule = editRule;
window.deleteRule = deleteRule;
window.editSchedule = editSchedule;
window.deleteSchedule = deleteSchedule;
window.toggleSubjectSelects = toggleSubjectSelects;
window.closeRuleModal = closeRuleModal;
window.closeScheduleModal = closeScheduleModal;
