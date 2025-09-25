# Updated authentication.py
from rest_framework import authentication, exceptions
from django.core.cache import cache
from django.conf import settings
import logging

# Update this import to use the combined authentication
from .supabase_auth import verify_token_combined as verify_token_with_supabase
from .supabase_client import get_user_profile_by_id, get_roles_by_user_id

logger = logging.getLogger(__name__)

# Cache settings
ROLE_CACHE_PREFIX = "user_roles_"
ROLE_CACHE_TTL = 60 * 5  # 5 minutes
TOKEN_CACHE_PREFIX = "supabase_token_"
TOKEN_CACHE_TTL = 60 * 10  # 10 minutes

class SupabaseUser:
    """
    Enhanced user-like object for DRF use with additional features.
    """
    def __init__(self, sub=None, email=None, roles=None, raw_token_payload=None):
        self.id = sub
        self.email = email
        self.roles = roles or []
        self.is_authenticated = True
        self.raw_payload = raw_token_payload or {}
        
        # Additional properties from token payload
        self.email_verified = raw_token_payload.get('email_verified', False) if raw_token_payload else False
        self.user_metadata = raw_token_payload.get('user_metadata', {}) if raw_token_payload else {}
        self.app_metadata = raw_token_payload.get('app_metadata', {}) if raw_token_payload else {}
        self.verification_method = raw_token_payload.get('verification_method', 'unknown') if raw_token_payload else 'unknown'

    def has_role(self, role_name):
        """Check if user has a specific role (case-insensitive)"""
        return role_name.lower() in [r.lower() for r in self.roles]
    
    def has_any_role(self, role_names):
        """Check if user has any of the specified roles"""
        if isinstance(role_names, str):
            role_names = [role_names]
        return any(self.has_role(role) for role in role_names)
    
    def get_display_name(self):
        """Get user's display name from metadata or email"""
        if self.user_metadata:
            return (
                self.user_metadata.get('full_name') or 
                self.user_metadata.get('name') or 
                self.email or 
                f"User {self.id[:8] if self.id else 'Unknown'}"
            )
        return self.email or f"User {self.id[:8] if self.id else 'Unknown'}"
    
    def __str__(self):
        return f"SupabaseUser(id={self.id}, email={self.email}, roles={self.roles})"

class SupabaseAuthentication(authentication.BaseAuthentication):
    """
    Enhanced Supabase JWT authentication using combined verification methods.
    """
    def authenticate(self, request):
        # Extract token from header
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != b'bearer':
            return None
        
        if len(header) == 1:
            raise exceptions.AuthenticationFailed("Invalid token header. No credentials provided.")
        
        if len(header) > 2:
            raise exceptions.AuthenticationFailed(
                "Invalid token header. Token string should not contain spaces."
            )

        token = header[1].decode('utf-8')

        # Use combined Supabase verification with caching
        payload = self._verify_token_with_cache(token)
        if not payload:
            raise exceptions.AuthenticationFailed("Invalid token: Token verification failed")

        # Extract user information
        user_id = payload.get('sub')
        email = payload.get('email')

        if not user_id:
            raise exceptions.AuthenticationFailed("Invalid token: No user ID found")

        # Server-side role lookup (cached)
        roles = self._get_user_roles(user_id, payload)

        user = SupabaseUser(
            sub=user_id, 
            email=email, 
            roles=roles, 
            raw_token_payload=payload
        )
        
        # Log successful authentication in debug mode
        if getattr(settings, 'DEBUG', False):
            logger.debug(f"User authenticated: {email} via {payload.get('verification_method', 'unknown')}")
        
        return (user, token)
    
    def _verify_token_with_cache(self, token):
        """
        Verify token with caching to reduce API calls
        """
        # Create cache key from token (use first 32 chars for security)
        cache_key = TOKEN_CACHE_PREFIX + token[:32]
        cached_payload = cache.get(cache_key)
        
        if cached_payload:
            return cached_payload
        
        # Verify with combined method
        payload = verify_token_with_supabase(token)
        
        # Cache successful verification
        if payload:
            cache.set(cache_key, payload, TOKEN_CACHE_TTL)
        
        return payload
    
    def _get_user_roles(self, user_id, payload):
        """
        Get user roles with caching and multiple fallback sources
        """
        cache_key = ROLE_CACHE_PREFIX + user_id
        roles = cache.get(cache_key)
        
        if roles is None:
            # Try multiple sources for roles
            roles = self._fetch_roles_from_multiple_sources(user_id, payload)
            # Cache the result
            cache.set(cache_key, roles, ROLE_CACHE_TTL)
        
        return roles
    
    def _fetch_roles_from_multiple_sources(self, user_id, payload):
        """
        Fetch roles from multiple sources in order of preference
        """
        # Source 1: Token payload role (if not default)
        token_role = payload.get('role')
        if token_role and token_role != 'authenticated':
            return [token_role]
        
        # Source 2: App metadata roles
        app_metadata = payload.get('app_metadata', {})
        if app_metadata.get('roles'):
            return app_metadata['roles'] if isinstance(app_metadata['roles'], list) else [app_metadata['roles']]
        if app_metadata.get('role'):
            return [app_metadata['role']]
        
        # Source 3: User profile in database
        try:
            profile = get_user_profile_by_id(user_id)
            if profile and profile.get('role'):
                return [profile['role']]
        except Exception as e:
            logger.warning(f"Failed to get user profile for {user_id}: {e}")
        
        # Source 4: Roles table lookup
        try:
            roles = get_roles_by_user_id(user_id)
            if roles:
                return roles
        except Exception as e:
            logger.warning(f"Failed to get roles for user {user_id}: {e}")
        
        # Default: return empty roles list
        return []

class EnhancedSupabaseAuthentication(SupabaseAuthentication):
    """
    Enhanced version with additional features like token refresh capability
    """
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except exceptions.AuthenticationFailed as e:
            # Log authentication failures for monitoring
            logger.info(f"Authentication failed: {str(e)}")
            
            # You could implement token refresh logic here if needed
            # For now, just re-raise the exception
            raise e
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return 'Bearer realm="api"'

# Utility functions
def get_authenticated_user_from_request(request):
    """
    Utility function to get authenticated user directly from request
    Use this in your views if you prefer not using DRF authentication classes
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return None
        
    token = auth_header.split(' ')[1]
    user_data = verify_token_with_supabase(token)
    
    if user_data:
        # Also need to fetch roles for this utility function
        user_id = user_data.get('sub')
        cache_key = ROLE_CACHE_PREFIX + user_id
        roles = cache.get(cache_key)
        
        if roles is None:
            # Simple role lookup for utility function
            try:
                profile = get_user_profile_by_id(user_id)
                roles = [profile.get('role')] if profile and profile.get('role') else []
            except Exception:
                try:
                    roles = get_roles_by_user_id(user_id)
                except Exception:
                    roles = []
            
            cache.set(cache_key, roles, ROLE_CACHE_TTL)
        
        return SupabaseUser(
            sub=user_data.get('sub'),
            email=user_data.get('email'),
            roles=roles,
            raw_token_payload=user_data
        )
    return None

def get_current_user(request):
    """
    Get the current authenticated user from request
    """
    if hasattr(request, 'user') and isinstance(request.user, SupabaseUser):
        return request.user
    return None

# Decorators for role-based access control
def require_roles(*required_roles):
    """
    Decorator to require specific roles for a view
    Usage: @require_roles('admin', 'manager')
    """
    def decorator(view_func):
        from functools import wraps
        
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = get_current_user(request)
            if not user:
                raise exceptions.NotAuthenticated("Authentication required")
            
            if not user.has_any_role(required_roles):
                raise exceptions.PermissionDenied(
                    f"Requires one of these roles: {', '.join(required_roles)}"
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_verified_email(view_func):
    """
    Decorator to require verified email
    Usage: @require_verified_email
    """
    from functools import wraps
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            raise exceptions.NotAuthenticated("Authentication required")
        
        if not user.email_verified:
            raise exceptions.PermissionDenied("Email verification required")
        
        return view_func(request, *args, **kwargs)
    return wrapper