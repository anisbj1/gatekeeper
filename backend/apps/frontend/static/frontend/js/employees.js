let currentPage = 1;
let currentSearch = '';

document.addEventListener('DOMContentLoaded', () => {
    fetchEmployees();

    // Event Listeners
    document.getElementById('btn-search').addEventListener('click', () => {
        currentSearch = document.getElementById('search-employees').value;
        currentPage = 1;
        fetchEmployees();
    });

    document.getElementById('search-employees').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentSearch = e.target.value;
            currentPage = 1;
            fetchEmployees();
        }
    });

    document.getElementById('btn-prev').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            fetchEmployees();
        }
    });

    document.getElementById('btn-next').addEventListener('click', () => {
        currentPage++;
        fetchEmployees();
    });

    // Modal triggers
    const modal = document.getElementById('employee-modal');
    document.getElementById('btn-add-employee').addEventListener('click', () => openModal());
    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);
    
    document.getElementById('employee-form').addEventListener('submit', handleFormSubmit);
});

async function fetchEmployees() {
    const tableBody = document.getElementById('employees-table-body');
    tableBody.innerHTML = `<tr><td colspan="8" style="color: var(--text-muted); text-align: center; padding: 2rem;">Loading employees...</td></tr>`;

    const url = `/api/v1/users/?page=${currentPage}&search=${encodeURIComponent(currentSearch)}`;
    const data = await API.get(url);

    if (!data) {
        tableBody.innerHTML = `<tr><td colspan="8" style="color: var(--error-color); text-align: center; padding: 2rem;">Failed to fetch employees.</td></tr>`;
        return;
    }

    if (data.results.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="8" style="color: var(--text-muted); text-align: center; padding: 2rem;">No employees found.</td></tr>`;
        updatePagination(0, false, false);
        return;
    }

    tableBody.innerHTML = '';
    data.results.forEach(emp => {
        const tr = document.createElement('tr');
        
        const fullname = `${emp.first_name} ${emp.last_name}`.trim() || '—';
        const activeBadge = emp.is_active 
            ? '<span class="badge badge-success">Active</span>' 
            : '<span class="badge badge-danger">Inactive</span>';
        
        let privileges = [];
        if (emp.is_superuser) privileges.push('Super');
        else if (emp.is_staff) privileges.push('Staff');
        else privileges.push('User');
        const privilegesText = privileges.join(', ');

        const bioBadge = emp.face_enrolled 
            ? '<span class="badge badge-success">Enrolled</span>' 
            : '<span class="badge badge-danger">Missing</span>';

        const joinDate = new Date(emp.date_joined).toLocaleDateString();

        tr.innerHTML = `
            <td><strong>${emp.username}</strong></td>
            <td>${fullname}</td>
            <td>${emp.email || '—'}</td>
            <td>${activeBadge}</td>
            <td>${privilegesText}</td>
            <td>${bioBadge}</td>
            <td>${joinDate}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="editEmployee(${emp.id})">Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteEmployee(${emp.id}, '${emp.username}')">Delete</button>
            </td>
        `;
        tableBody.appendChild(tr);
    });

    updatePagination(data.count, !!data.previous, !!data.next);
}

function updatePagination(count, hasPrev, hasNext) {
    const info = document.getElementById('pagination-info');
    const start = count === 0 ? 0 : (currentPage - 1) * 10 + 1;
    const end = Math.min(currentPage * 10, count);
    info.textContent = `Showing ${start} to ${end} of ${count} entries`;

    const prevBtn = document.getElementById('btn-prev');
    const nextBtn = document.getElementById('btn-next');
    
    prevBtn.disabled = !hasPrev;
    nextBtn.disabled = !hasNext;
}

function openModal(emp = null) {
    const modal = document.getElementById('employee-modal');
    const form = document.getElementById('employee-form');
    const passwordHelp = document.getElementById('password-help');
    const passwordInput = document.getElementById('emp-password');
    
    form.reset();
    document.getElementById('employee-id').value = '';
    
    if (emp) {
        document.getElementById('modal-title').textContent = 'Edit Employee';
        document.getElementById('employee-id').value = emp.id;
        document.getElementById('emp-username').value = emp.username;
        document.getElementById('emp-username').disabled = true; // Username is immutable
        document.getElementById('emp-first-name').value = emp.first_name;
        document.getElementById('emp-last-name').value = emp.last_name;
        document.getElementById('emp-email').value = emp.email;
        document.getElementById('emp-active').checked = emp.is_active;
        document.getElementById('emp-staff').checked = emp.is_staff;
        
        passwordInput.required = false;
        passwordHelp.style.display = 'inline';
    } else {
        document.getElementById('modal-title').textContent = 'Add Employee';
        document.getElementById('emp-username').disabled = false;
        passwordInput.required = true;
        passwordHelp.style.display = 'none';
    }
    
    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('employee-modal').classList.remove('active');
}

async function editEmployee(id) {
    const emp = await API.get(`/api/v1/users/${id}/`);
    if (emp) {
        openModal(emp);
    }
}

async function deleteEmployee(id, username) {
    if (confirm(`Are you sure you want to permanently delete employee "${username}"?`)) {
        const res = await API.delete(`/api/v1/users/${id}/`);
        if (res) {
            showToast(`Employee "${username}" deleted successfully.`, 'success');
            fetchEmployees();
        }
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('employee-id').value;
    
    const payload = {
        username: document.getElementById('emp-username').value,
        first_name: document.getElementById('emp-first-name').value,
        last_name: document.getElementById('emp-last-name').value,
        email: document.getElementById('emp-email').value,
        is_active: document.getElementById('emp-active').checked,
        is_staff: document.getElementById('emp-staff').checked
    };

    const password = document.getElementById('emp-password').value;
    if (password) {
        payload.password = password;
    }

    let res;
    if (id) {
        // Edit mode (PATCH to only modify fields sent)
        res = await API.patch(`/api/v1/users/${id}/`, payload);
    } else {
        // Create mode
        res = await API.post('/api/v1/users/', payload);
    }

    if (res) {
        showToast(id ? 'Employee updated successfully.' : 'Employee created successfully.', 'success');
        closeModal();
        fetchEmployees();
    }
}
window.editEmployee = editEmployee;
window.deleteEmployee = deleteEmployee;
