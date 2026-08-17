document.addEventListener('DOMContentLoaded', () => {
    // Initial fetch
    refreshDashboard();

    // Set polling interval (every 5 seconds)
    setInterval(refreshDashboard, 5000);
});

async function refreshDashboard() {
    await Promise.all([
        fetchStats(),
        fetchCardScans(),
        fetchBiometricAttempts()
    ]);
}

async function fetchStats() {
    const stats = await API.get('/api/v1/dashboard/stats/');
    if (stats) {
        document.getElementById('stats-employees').textContent = stats.employees_count;
        document.getElementById('stats-cards').textContent = stats.cards_count;
        document.getElementById('stats-biometrics').textContent = stats.face_profiles_count;
        document.getElementById('stats-devices').textContent = stats.devices_count;
        
        const todayBadge = document.getElementById('activity-today-badge');
        if (todayBadge) {
            todayBadge.textContent = `Today: ${stats.today_attempts_count} (${stats.today_granted_count} OK / ${stats.today_denied_count} Err)`;
        }
    }
}

async function fetchCardScans() {
    const data = await API.get('/api/v1/logs/access/?ordering=-timestamp&limit=5');
    const container = document.getElementById('card-scans-list');
    if (!container) return;

    if (!data || !data.results || data.results.length === 0) {
        container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 1rem;">No recent scans.</div>`;
        return;
    }

    container.innerHTML = '';
    data.results.slice(0, 5).forEach(log => {
        const item = document.createElement('div');
        item.className = 'activity-item';
        
        const badgeClass = log.authorized ? 'badge-success' : 'badge-danger';
        const badgeText = log.authorized ? 'Granted' : 'Denied';
        const timeStr = formatTimestamp(log.timestamp);

        item.innerHTML = `
            <div class="activity-info">
                <span class="badge ${badgeClass}">${badgeText}</span>
                <div>
                    <strong style="display: block;">${log.user_details}</strong>
                    <span style="color: var(--text-muted); font-size: 0.75rem;">Card: ${log.card_uid} • Device: ${log.device_id}</span>
                </div>
            </div>
            <span class="activity-time">${timeStr}</span>
        `;
        container.appendChild(item);
    });
}

async function fetchBiometricAttempts() {
    const data = await API.get('/api/v1/face/logs/biometric/?ordering=-timestamp&limit=5');
    const container = document.getElementById('biometric-attempts-list');
    if (!container) return;

    if (!data || !data.results || data.results.length === 0) {
        container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 1rem;">No recent biometric attempts.</div>`;
        return;
    }

    container.innerHTML = '';
    data.results.slice(0, 5).forEach(attempt => {
        const item = document.createElement('div');
        item.className = 'activity-item';
        
        const badgeClass = attempt.authorized ? 'badge-success' : 'badge-danger';
        const badgeText = attempt.authorized ? 'Match' : 'Mismatch';
        const confStr = attempt.confidence_score !== null ? `${(attempt.confidence_score * 100).toFixed(0)}%` : 'N/A';
        const timeStr = formatTimestamp(attempt.timestamp);
        
        let details = `Confidence: ${confStr}`;
        if (attempt.error_message) {
            details += ` (${attempt.error_message})`;
        }

        item.innerHTML = `
            <div class="activity-info">
                <span class="badge ${badgeClass}">${badgeText}</span>
                <div>
                    <strong style="display: block;">User: ${attempt.username}</strong>
                    <span style="color: var(--text-muted); font-size: 0.75rem;">Device: ${attempt.device_id_code} • ${details}</span>
                </div>
            </div>
            <span class="activity-time">${timeStr}</span>
        `;
        container.appendChild(item);
    });
}

function formatTimestamp(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (e) {
        return '';
    }
}
