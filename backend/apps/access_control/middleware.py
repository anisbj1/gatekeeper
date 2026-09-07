import time
from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from apps.security_logs.services import AdminAuditService

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '127.0.0.1'


class SessionSecurityMiddleware:
    """
    Middleware enforcing strict session security policies:
    1. Maximum absolute lifetime: 24 hours (86,400s) from session creation.
    2. Inactivity timeout: 5 minutes (300s) from the last active request.
    3. Immediate session invalidation if user account is disabled (is_active=False).
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.idle_timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT_SECONDS', 300) # 5 minutes
        self.max_age = getattr(settings, 'SESSION_MAX_AGE_SECONDS', 86400)          # 24 hours

    def __call__(self, request):
        if request.user.is_authenticated:
            now_ts = time.time()
            client_ip = get_client_ip(request)

            # 1. Immediate termination if account was deactivated / blocked
            if not request.user.is_active:
                username = request.user.username
                logout(request)
                request.session.flush()
                AdminAuditService.log_event(
                    event_type='SESSION_EXPIRED',
                    actor='System',
                    target_user=username,
                    ip_address=client_ip,
                    details='Active session terminated immediately: account is disabled/locked.'
                )
                if self._is_api_request(request):
                    return JsonResponse({'error': 'Account is disabled. Session terminated.'}, status=403)
                return redirect('frontend:login')

            # 2. Check session timestamps
            created_at = request.session.get('_session_created_at')
            last_activity = request.session.get('_session_last_activity')

            # Initialize timestamps on fresh session
            if created_at is None:
                request.session['_session_created_at'] = now_ts
                created_at = now_ts

            if last_activity is None:
                request.session['_session_last_activity'] = now_ts
                last_activity = now_ts

            # 3. Check Maximum Absolute Lifetime (24 Hours)
            if (now_ts - created_at) > self.max_age:
                username = request.user.username
                logout(request)
                request.session.flush()
                AdminAuditService.log_event(
                    event_type='SESSION_EXPIRED',
                    actor='System',
                    target_user=username,
                    ip_address=client_ip,
                    details=f'Session reached maximum allowed lifetime ({self.max_age}s / 24h).'
                )
                if self._is_api_request(request):
                    return JsonResponse(
                        {'error': 'Session expired (maximum 24h lifetime reached). Please log in again.'},
                        status=401
                    )
                return redirect('frontend:login')

            # 4. Check Inactivity Timeout (5 Minutes)
            if (now_ts - last_activity) > self.idle_timeout:
                username = request.user.username
                logout(request)
                request.session.flush()
                AdminAuditService.log_event(
                    event_type='SESSION_EXPIRED',
                    actor='System',
                    target_user=username,
                    ip_address=client_ip,
                    details=f'Session expired due to inactivity ({self.idle_timeout}s / 5min).'
                )
                if self._is_api_request(request):
                    return JsonResponse(
                        {'error': 'Session expired due to inactivity (5 minutes). Please log in again.'},
                        status=401
                    )
                return redirect('frontend:login')

            # 5. Session is valid -> refresh last activity timestamp
            request.session['_session_last_activity'] = now_ts

        response = self.get_response(request)
        return response

    def _is_api_request(self, request):
        return (
            request.path.startswith('/api/') or
            request.headers.get('Accept') == 'application/json' or
            request.content_type == 'application/json'
        )
