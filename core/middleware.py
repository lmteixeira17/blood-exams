"""
Middleware for the blood exams system.
"""

from django.shortcuts import redirect


class ProfileCompletionMiddleware:
    """Redirect authenticated users to complete their profile if DOB or gender is missing."""

    EXEMPT_URLS = [
        '/complete-profile/',
        '/logout/',
        '/health/',
        '/admin/',
        '/accounts/',
        '/static/',
        '/media/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Skip profile check when admin is impersonating another user
            if request.user.is_superuser and request.session.get('_impersonate_user_id'):
                return self.get_response(request)
            profile = getattr(request.user, 'profile', None)
            if profile and (not profile.date_of_birth or not profile.gender):
                path = request.path_info
                if not any(path.startswith(exempt) for exempt in self.EXEMPT_URLS):
                    return redirect('complete_profile')
        return self.get_response(request)
