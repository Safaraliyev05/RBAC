from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Strictly throttle login attempts: 5 per minute per IP."""
    scope = 'login'


class RegisterRateThrottle(AnonRateThrottle):
    """Throttle registration: 10 per minute per IP."""
    scope = 'auth'
