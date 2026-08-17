document.addEventListener('DOMContentLoaded', () => {
    fetchDevices();

    // Event Listeners
    document.getElementById('btn-search').addEventListener('click', fetchDevices);
    document.getElementById('search-devices').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') fetchDevices();
    });

    // Modal triggers
    document.getElementById('btn-add-device').addEventListener('click', () => openModal());
    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);
    
    document.getElementById('device-form').addEventListener('submit', handleFormSubmit);
});

async function fetchDevices() {
    const tableBody = document.getElementById('devices-table-body');
    tableBody.innerHTML = `<tr><td colspan="6" style="color: var(--text-muted); text-align: center; padding: 2rem;">Loading devices...</td></tr>`;

    const search = document.getElementById('search-devices').value;
    const url = `/api/v1/devices/?search=${encodeURIComponent(search)}`;
    const data = await API.get(url);

    if (!data) {
        tableBody.innerHTML = `<tr><td colspan="6" style="color: var(--error-color); text-align: center; padding: 2rem;">Failed to fetch devices.</td></tr>`;
        return;
    }

    if (!data.results || data.results.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="6" style="color: var(--text-muted); text-align: center; padding: 2rem;">No devices registered.</td></tr>`;
        return;
    }

    tableBody.innerHTML = '';
    data.results.forEach(dev => {
        const tr = document.createElement('tr');
        
        const activeBadge = dev.is_active 
            ? '<span class="badge badge-success">Active</span>' 
            : '<span class="badge badge-danger">Blocked</span>';
        
        const registeredDate = new Date(dev.created_at).toLocaleDateString();

        tr.innerHTML = `
            <td><code><strong>${dev.device_id}</strong></code></td>
            <td>${dev.name}</td>
            <td>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <code id="token-${dev.id}" style="filter: blur(4px); transition: filter 0.2s;">${dev.api_token}</code>
                    <button class="btn btn-secondary btn-sm" style="padding: 0.2rem 0.4rem; font-size: 0.75rem;" onclick="toggleToken(${dev.id})">Reveal</button>
                    <button class="btn btn-secondary btn-sm" style="padding: 0.2rem 0.4rem; font-size: 0.75rem;" onclick="copyToken('${dev.api_token}')">Copy</button>
                </div>
            </td>
            <td>${activeBadge}</td>
            <td>${registeredDate}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="editDevice(${dev.id})">Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteDevice(${dev.id}, '${dev.device_id}')">Delete</button>
            </td>
        `;
        tableBody.appendChild(tr);
    });
}

function toggleToken(id) {
    const code = document.getElementById(`token-${id}`);
    if (code) {
        if (code.style.filter === 'blur(4px)' || code.style.filter === '') {
            code.style.filter = 'none';
        } else {
            code.style.filter = 'blur(4px)';
        }
    }
}

function copyToken(token) {
    navigator.clipboard.writeText(token).then(() => {
        showToast('API token copied to clipboard.', 'success');
    }).catch(err => {
        showToast('Failed to copy token.', 'error');
    });
}

function openModal(dev = null) {
    const modal = document.getElementById('device-modal');
    const form = document.getElementById('device-form');
    
    form.reset();
    document.getElementById('device-id').value = '';
    document.getElementById('dev-device-id').disabled = false;
    
    if (dev) {
        document.getElementById('modal-title').textContent = 'Edit Device';
        document.getElementById('device-id').value = dev.id;
        document.getElementById('dev-device-id').value = dev.device_id;
        document.getElementById('dev-device-id').disabled = true; // device_id is immutable
        document.getElementById('dev-name').value = dev.name;
        document.getElementById('dev-active').checked = dev.is_active;
    } else {
        document.getElementById('modal-title').textContent = 'Register ESP32 Device';
    }
    
    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('device-modal').classList.remove('active');
}

async function editDevice(id) {
    const dev = await API.get(`/api/v1/devices/${id}/`);
    if (dev) {
        openModal(dev);
    }
}

async function deleteDevice(id, deviceId) {
    if (confirm(`Are you sure you want to delete device registration "${deviceId}"?`)) {
        const res = await API.delete(`/api/v1/devices/${id}/`);
        if (res) {
            showToast(`Device "${deviceId}" deleted successfully.`, 'success');
            fetchDevices();
        }
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('device-id').value;
    
    const payload = {
        device_id: document.getElementById('dev-device-id').value.trim(),
        name: document.getElementById('dev-name').value,
        is_active: document.getElementById('dev-active').checked
    };

    let res;
    if (id) {
        res = await API.patch(`/api/v1/devices/${id}/`, payload);
    } else {
        res = await API.post('/api/v1/devices/', payload);
    }

    if (res) {
        showToast(id ? 'Device updated successfully.' : 'Device registered successfully.', 'success');
        closeModal();
        fetchDevices();
    }
}
window.editDevice = editDevice;
window.deleteDevice = deleteDevice;
window.toggleToken = toggleToken;
window.copyToken = copyToken;
