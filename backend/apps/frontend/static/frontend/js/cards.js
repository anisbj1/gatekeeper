let currentPage = 1;
let currentSearch = '';
let currentActiveFilter = '';

document.addEventListener('DOMContentLoaded', () => {
    fetchCards();

    // Event Listeners
    document.getElementById('btn-search').addEventListener('click', () => {
        currentSearch = document.getElementById('search-cards').value;
        currentActiveFilter = document.getElementById('filter-active').value;
        currentPage = 1;
        fetchCards();
    });

    document.getElementById('search-cards').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentSearch = e.target.value;
            currentPage = 1;
            fetchCards();
        }
    });

    document.getElementById('btn-prev').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            fetchCards();
        }
    });

    document.getElementById('btn-next').addEventListener('click', () => {
        currentPage++;
        fetchCards();
    });

    // Modal triggers
    document.getElementById('btn-add-card').addEventListener('click', () => openModal());
    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('btn-cancel-modal').addEventListener('click', closeModal);
    
    document.getElementById('card-form').addEventListener('submit', handleFormSubmit);
});

async function fetchCards() {
    const tableBody = document.getElementById('cards-table-body');
    tableBody.innerHTML = `<tr><td colspan="6" style="color: var(--text-muted); text-align: center; padding: 2rem;">Loading cards...</td></tr>`;

    let url = `/api/v1/cards/?page=${currentPage}&search=${encodeURIComponent(currentSearch)}`;
    if (currentActiveFilter !== '') {
        url += `&is_active=${currentActiveFilter}`;
    }
    const data = await API.get(url);

    if (!data) {
        tableBody.innerHTML = `<tr><td colspan="6" style="color: var(--error-color); text-align: center; padding: 2rem;">Failed to fetch cards.</td></tr>`;
        return;
    }

    if (data.results.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="6" style="color: var(--text-muted); text-align: center; padding: 2rem;">No cards found.</td></tr>`;
        updatePagination(0, false, false);
        return;
    }

    tableBody.innerHTML = '';
    data.results.forEach(card => {
        const tr = document.createElement('tr');
        
        const activeBadge = card.is_active 
            ? '<span class="badge badge-success">Active</span>' 
            : '<span class="badge badge-danger">Blocked</span>';
        
        const createdDate = new Date(card.created_at).toLocaleDateString() + ' ' + new Date(card.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const updatedDate = new Date(card.updated_at).toLocaleDateString() + ' ' + new Date(card.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

        tr.innerHTML = `
            <td><code><strong>${card.uid}</strong></code></td>
            <td>${card.user_details}</td>
            <td>${activeBadge}</td>
            <td>${createdDate}</td>
            <td>${updatedDate}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="editCard(${card.id})">Edit</button>
                <button class="btn btn-danger btn-sm" onclick="deleteCard(${card.id}, '${card.uid}')">Delete</button>
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

function openModal(card = null) {
    const modal = document.getElementById('card-modal');
    const form = document.getElementById('card-form');
    
    form.reset();
    document.getElementById('card-id').value = '';
    document.getElementById('card-uid-input').disabled = false;
    
    if (card) {
        document.getElementById('modal-title').textContent = 'Edit Card';
        document.getElementById('card-id').value = card.id;
        document.getElementById('card-uid-input').value = card.uid;
        document.getElementById('card-uid-input').disabled = true; // UID is immutable
        document.getElementById('card-user-select').value = card.user;
        document.getElementById('card-active').checked = card.is_active;
    } else {
        document.getElementById('modal-title').textContent = 'Register RFID Card';
    }
    
    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('card-modal').classList.remove('active');
}

async function editCard(id) {
    const card = await API.get(`/api/v1/cards/${id}/`);
    if (card) {
        openModal(card);
    }
}

async function deleteCard(id, uid) {
    if (confirm(`Are you sure you want to delete RFID card registration "${uid}"?`)) {
        const res = await API.delete(`/api/v1/cards/${id}/`);
        if (res) {
            showToast(`Card "${uid}" deleted successfully.`, 'success');
            fetchCards();
        }
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('card-id').value;
    
    const payload = {
        uid: document.getElementById('card-uid-input').value.trim().toUpperCase(),
        user: parseInt(document.getElementById('card-user-select').value),
        is_active: document.getElementById('card-active').checked
    };

    let res;
    if (id) {
        // Edit mode (PATCH to avoid re-validating read-only fields)
        res = await API.patch(`/api/v1/cards/${id}/`, payload);
    } else {
        // Create mode
        res = await API.post('/api/v1/cards/', payload);
    }

    if (res) {
        showToast(id ? 'Card updated successfully.' : 'Card registered successfully.', 'success');
        closeModal();
        fetchCards();
    }
}
window.editCard = editCard;
window.deleteCard = deleteCard;
