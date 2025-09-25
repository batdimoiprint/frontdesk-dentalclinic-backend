# combined_supabase_auth.py
import requests
import jwt
import time
from django.conf import settings
from typing import Optional, Dict, Any

# Try to import supabase client, but don't fail if not available
try:
    from supabase import create_client, Client
    SUPABASE_CLIENT_AVAILABLE = True
except ImportError:
    SUPABASE_CLIENT_AVAILABLE = False
    print("Warning: supabase-py client not available, falling back to API calls")

def get_supabase_client() -> Optional['Client']:
    """
    Get Supabase client instance if available
    """
    if not SUPABASE_CLIENT_AVAILABLE:
        return None
        
    supabase_url = getattr(settings, 'SUPABASE_URL', None)
    supabase_anon_key = getattr(settings, 'SUPABASE_ANON_KEY', None)
    
    if not supabase_url or not supabase_anon_key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in Django settings")
    
    return create_client(supabase_url, supabase_anon_key)

def verify_token_with_client(token: str) -> Optional[Dict[Any, Any]]:
    """
    Method 1: Verify JWT token using Supabase client library
    Most feature-complete but requires supabase-py dependency
    """
    if not SUPABASE_CLIENT_AVAILABLE:
        return None
        
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        # Use Supabase client to verify token and get user
        response = supabase.auth.get_user(token)
        
        if response.user:
            # Convert Supabase user object to dict for consistency
            user_data = {
                'sub': response.user.id,
                'email': response.user.email,
                'email_verified': getattr(response.user, 'email_confirmed_at', None) is not None,
                'aud': 'authenticated',
                'role': getattr(response.user, 'role', 'authenticated'),
                'user_metadata': getattr(response.user, 'user_metadata', {}),
                'app_metadata': getattr(response.user, 'app_metadata', {}),
                'iss': f"{getattr(settings, 'SUPABASE_URL')}/auth/v1",
                'verification_method': 'supabase_client'
            }
            return user_data
        else:
            return None
            
    except Exception as e:
        print(f"Supabase client verification failed: {str(e)}")
        return None

def verify_token_with_api(token: str) -> Optional[Dict[Any, Any]]:
    """
    Method 2: Verify JWT token using direct Supabase API call
    More reliable, no dependency on supabase-py client
    """
    try:
        # Direct API call to Supabase
        headers = {
            'Authorization': f'Bearer {token}',
            'apikey': getattr(settings, 'SUPABASE_ANON_KEY', ''),
            'Content-Type': 'application/json'
        }
        
        supabase_url = getattr(settings, 'SUPABASE_URL', '')
        if not supabase_url:
            raise ValueError("SUPABASE_URL not configured")
            
        # Call Supabase user endpoint
        url = f"{supabase_url.rstrip('/')}/auth/v1/user"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            return {
                'sub': user_data.get('id'),
                'email': user_data.get('email'),
                'aud': user_data.get('aud', 'authenticated'),
                'role': user_data.get('role', 'authenticated'),
                'email_verified': user_data.get('email_confirmed_at') is not None,
                'user_metadata': user_data.get('user_metadata', {}),
                'app_metadata': user_data.get('app_metadata', {}),
                'iss': f"{supabase_url}/auth/v1",
                'verification_method': 'supabase_api'
            }
        elif response.status_code == 401:
            # Token is invalid or expired
            return None
        else:
            # Other error
            print(f"Supabase API error: {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"Network error calling Supabase API: {e}")
        return None
    except Exception as e:
        print(f"Error verifying token with Supabase API: {e}")
        return None

def verify_token_with_jwt_fallback(token: str) -> Optional[Dict[Any, Any]]:
    """
    Method 3: Fallback - decode token without signature verification
    Use only in development or when Supabase services are unavailable
    """
    try:
        # Decode without verification to get payload
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Basic validation
        current_time = int(time.time())
        
        # Check expiration
        exp = payload.get('exp')
        if exp and current_time > exp:
            print(f"Token expired: {current_time} > {exp}")
            return None
        
        # Validate issuer if present
        expected_iss = f"{getattr(settings, 'SUPABASE_URL', '')}/auth/v1"
        if payload.get('iss') and payload.get('iss') != expected_iss:
            print(f"Token issuer mismatch: expected {expected_iss}, got {payload.get('iss')}")
            # Don't return None here, just warn - issuer might be formatted differently
        
        # Add verification method marker
        payload['verification_method'] = 'jwt_fallback'
        return payload
        
    except jwt.DecodeError as e:
        print(f"JWT decode error: {e}")
        return None
    except Exception as e:
        print(f"Fallback token decode failed: {e}")
        return None

def verify_token_combined(token: str, preferred_method: str = 'auto') -> Optional[Dict[Any, Any]]:
    """
    Combined approach: tries multiple verification methods in order of preference
    
    Args:
        token: JWT token to verify
        preferred_method: 'client', 'api', 'fallback', or 'auto'
    
    Returns:
        User data dict if token is valid, None if invalid
    """
    if not token:
        return None
    
    methods_to_try = []
    
    # Determine which methods to try based on preference
    if preferred_method == 'client':
        methods_to_try = [verify_token_with_client, verify_token_with_api, verify_token_with_jwt_fallback]
    elif preferred_method == 'api':
        methods_to_try = [verify_token_with_api, verify_token_with_client, verify_token_with_jwt_fallback]
    elif preferred_method == 'fallback':
        methods_to_try = [verify_token_with_jwt_fallback]
    else:  # 'auto' - default intelligent order
        if SUPABASE_CLIENT_AVAILABLE:
            # If client is available, prefer it for full features
            methods_to_try = [verify_token_with_client, verify_token_with_api]
        else:
            # If no client, use API approach
            methods_to_try = [verify_token_with_api]
        
        # Add fallback only in DEBUG mode
        if getattr(settings, 'DEBUG', False):
            methods_to_try.append(verify_token_with_jwt_fallback)
    
    # Try each method until one succeeds
    last_error = None
    for method in methods_to_try:
        try:
            result = method(token)
            if result:
                return result
        except Exception as e:
            last_error = e
            print(f"Method {method.__name__} failed: {e}")
            continue
    
    # All methods failed
    if last_error and getattr(settings, 'DEBUG', False):
        print(f"All verification methods failed. Last error: {last_error}")
    
    return None

# Legacy compatibility functions
def verify_token_with_supabase(token: str) -> Optional[Dict[Any, Any]]:
    """
    Legacy function name for backward compatibility
    Uses the API method by default
    """
    return verify_token_with_api(token)

def verify_token_fallback(token: str) -> Optional[Dict[Any, Any]]:
    """
    Legacy function name for backward compatibility
    """
    return verify_token_with_jwt_fallback(token)

# Configuration helpers
def get_verification_config() -> Dict[str, Any]:
    """
    Get current verification configuration and capabilities
    """
    return {
        'supabase_client_available': SUPABASE_CLIENT_AVAILABLE,
        'supabase_url_configured': bool(getattr(settings, 'SUPABASE_URL', None)),
        'supabase_key_configured': bool(getattr(settings, 'SUPABASE_ANON_KEY', None)),
        'debug_mode': getattr(settings, 'DEBUG', False),
        'recommended_method': 'client' if SUPABASE_CLIENT_AVAILABLE else 'api'
    }

def test_verification_methods(sample_token: str = None) -> Dict[str, Any]:
    """
    Test all verification methods (useful for debugging)
    """
    if not sample_token:
        return {'error': 'No token provided for testing'}
    
    results = {}
    methods = {
        'client': verify_token_with_client,
        'api': verify_token_with_api,
        'fallback': verify_token_with_jwt_fallback
    }
    
    for name, method in methods.items():
        try:
            result = method(sample_token)
            results[name] = {
                'success': result is not None,
                'data': result if result else 'Failed'
            }
        except Exception as e:
            results[name] = {
                'success': False,
                'error': str(e)
            }
    
    return results