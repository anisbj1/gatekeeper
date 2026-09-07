// CSRF Token Helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Toast Notification Manager
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    toast.innerHTML = `
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        toast.style.transition = 'all 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// REST API Client
const API = {
    async request(url, options = {}) {
        const csrfToken = getCookie('csrftoken');
        
        options.headers = {
            ...options.headers,
            'X-CSRFToken': csrfToken
        };

        if (options.body && !(options.body instanceof FormData)) {
            options.headers['Content-Type'] = 'application/json';
            if (typeof options.body === 'object') {
                options.body = JSON.stringify(options.body);
            }
        }

        try {
            const response = await fetch(url, options);

            // Handle session expiry / redirect
            if (response.status === 401) {
                showToast('Session expired. Please log in again.', 'error');
                if (!window.location.pathname.includes('login')) {
                    setTimeout(() => {
                        window.location.href = '/login/';
                    }, 1000);
                }
                return null;
            }

            if (response.status === 403) {
                const data = await response.json().catch(() => ({}));
                showToast(data.error || 'Access denied. You do not have permissions.', 'error');
                return null;
            }

            if (response.status === 422) {
                const data = await response.json().catch(() => ({}));
                showToast(data.message || 'Validation failed. Check your data.', 'error');
                return null;
            }

            if (response.status === 204) {
                return true;
            }

            const data = await response.json();
            
            if (!response.ok) {
                const errMsg = data.error || data.detail || Object.values(data).flat().join(', ') || 'An unknown error occurred';
                showToast(errMsg, 'error');
                return null;
            }

            return data;
        } catch (error) {
            console.error('API Request failed:', error);
            showToast('Network connection failed.', 'error');
            return null;
        }
    },

    get(url) {
        return this.request(url, { method: 'GET' });
    },

    post(url, body) {
        return this.request(url, { method: 'POST', body });
    },

    put(url, body) {
        return this.request(url, { method: 'PUT', body });
    },

    patch(url, body) {
        return this.request(url, { method: 'PATCH', body });
    },

    delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

// Automatic Inactivity Timeout Manager
const IdleTimeoutManager = {
    idleTimeoutMs: 5 * 60 * 1000,      // 5 minutes default
    warningTimeoutMs: 4.5 * 60 * 1000, // 4 minutes 30 seconds default
    warningTimer: null,
    logoutTimer: null,
    warningShown: false,

    init(options = {}) {
        // Only run on authenticated pages (not on login page)
        if (window.location.pathname.includes('/login')) return;

        if (options.timeoutSeconds) {
            this.idleTimeoutMs = options.timeoutSeconds * 1000;
            this.warningTimeoutMs = Math.max(10000, (options.timeoutSeconds - 30) * 1000);
        }

        const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'];
        let throttleTimer = null;

        const activityHandler = () => {
            if (!throttleTimer) {
                throttleTimer = setTimeout(() => {
                    this.resetTimer();
                    throttleTimer = null;
                }, 1000); // Throttle activity checks to once per second
            }
        };

        events.forEach(evt => {
            window.addEventListener(evt, activityHandler, { passive: true });
        });

        this.startTimer();
    },

    resetTimer() {
        if (this.warningShown) {
            this.hideWarning();
        }
        this.clearTimers();
        this.startTimer();
    },

    startTimer() {
        this.warningTimer = setTimeout(() => {
            this.showWarning();
        }, this.warningTimeoutMs);

        this.logoutTimer = setTimeout(() => {
            this.triggerLogout();
        }, this.idleTimeoutMs);
    },

    clearTimers() {
        if (this.warningTimer) clearTimeout(this.warningTimer);
        if (this.logoutTimer) clearTimeout(this.logoutTimer);
    },

    showWarning() {
        this.warningShown = true;
        showToast('Inactivity notice: You will be automatically signed out in 30 seconds.', 'warning');
    },

    hideWarning() {
        this.warningShown = false;
    },

    async triggerLogout() {
        this.clearTimers();
        try {
            await API.post('/api/v1/auth/logout/');
        } catch (e) {
            // ignore network error on logout
        }
        window.location.href = '/login/?reason=inactivity';
    }
};

// Export to window
window.API = API;
window.showToast = showToast;
window.IdleTimeoutManager = IdleTimeoutManager;

