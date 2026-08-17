let currentPage = 1;
let currentSearch = '';
let currentAuthFilter = '';
let currentLogType = 'access'; // 'access' or 'biometric'

document.addEventListener('DOMContentLoaded', () => {
    fetchLogs();

    // Event Listeners
    document.getElementById('btn-filter').addEventListener('click', () => {
        currentSearch = document.getElementById('search-logs').value;
        currentAuthFilter = document.getElementById('filter-auth').value;
        
        const typeSelect = document.getElementById('filter-log-type');
        if (currentLogType !== typeSelect.value) {
            currentLogType = typeSelect.value;
            toggleTableViews();
        }
        
        currentPage = 1;
        fetchLogs();
    });

    document.getElementById('search-logs').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('btn-filter').click();
        }
    });

    document.getElementById('btn-prev').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            fetchLogs();
        }
    });

    document.getElementById('btn-next').addEventListener('click', () => {
        currentPage++;
        fetchLogs();
    });
});

function toggleTableViews() {
    const cardWrapper = document.getElementById('card-scans-table-wrapper');
    const bioWrapper = document.getElementById('biometric-attempts-table-wrapper');
    
    if (currentLogType === 'access') {
        cardWrapper.style.display = 'block';
        bioWrapper.style.display = 'none';
    } else {
        cardWrapper.style.display = 'none';
        bioWrapper.style.display = 'block';
    }
}

async function fetchLogs() {
    let url = '';
    let tableBody = null;
    let colCount = 5;

    if (currentLogType === 'access') {
        url = `/api/v1/logs/access/?page=${currentPage}&search=${encodeURIComponent(currentSearch)}`;
        tableBody = document.getElementById('access-logs-table-body');
        colCount = 5;
    } else {
        url = `/api/v1/face/logs/biometric/?page=${currentPage}&search=${encodeURIComponent(currentSearch)}`;
        tableBody = document.getElementById('biometric-logs-table-body');
        colCount = 8;
    }

    if (currentAuthFilter !== '') {
        url += `&authorized=${currentAuthFilter}`;
    }

    tableBody.innerHTML = `<tr><td colspan="${colCount}" style="color: var(--text-muted); text-align: center; padding: 2rem;">Loading log records...</td></tr>`;

    const data = await API.get(url);

    if (!data) {
        tableBody.innerHTML = `<tr><td colspan="${colCount}" style="color: var(--error-color); text-align: center; padding: 2rem;">Failed to fetch log entries.</td></tr>`;
        return;
    }

    if (data.results.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="${colCount}" style="color: var(--text-muted); text-align: center; padding: 2rem;">No logs found matching criteria.</td></tr>`;
        updatePagination(0, false, false);
        return;
    }

    tableBody.innerHTML = '';
    
    if (currentLogType === 'access') {
        data.results.forEach(log => {
            const tr = document.createElement('tr');
            const activeBadge = log.authorized 
                ? '<span class="badge badge-success">Granted</span>' 
                : '<span class="badge badge-danger">Denied</span>';
            const timeStr = new Date(log.timestamp).toLocaleString();
            
            tr.innerHTML = `
                <td><code>${timeStr}</code></td>
                <td><strong>${log.user_details}</strong></td>
                <td><code>${log.card_uid}</code></td>
                <td><code>${log.device_id}</code></td>
                <td>${activeBadge}</td>
            `;
            tableBody.appendChild(tr);
        });
    } else {
        data.results.forEach(attempt => {
            const tr = document.createElement('tr');
            const activeBadge = attempt.authorized 
                ? '<span class="badge badge-success">Match</span>' 
                : '<span class="badge badge-danger">Mismatch</span>';
            const timeStr = new Date(attempt.timestamp).toLocaleString();
            const confStr = attempt.confidence_score !== null ? `${(attempt.confidence_score * 100).toFixed(1)}%` : '—';
            const speedStr = `${attempt.processing_time_ms} ms`;
            
            tr.innerHTML = `
                <td><code>${timeStr}</code></td>
                <td><strong>${attempt.username}</strong></td>
                <td><code>${attempt.card_uid || '—'}</code></td>
                <td><code>${attempt.device_id_code}</code></td>
                <td><code>${confStr}</code></td>
                <td>${activeBadge}</td>
                <td>${speedStr}</td>
                <td style="color: var(--text-muted); font-size: 0.85rem;">${attempt.error_message || '—'}</td>
            `;
            tableBody.appendChild(tr);
        });
    }

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
