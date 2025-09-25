import os
import requests
from django.conf import settings

SUPABASE_URL = settings.SUPABASE_URL.rstrip('/')
SERVICE_ROLE_KEY = settings.SUPABASE_SERVICE_ROLE_KEY
# Use the PostgREST endpoint to query tables:
POSTGREST = f"{SUPABASE_URL}/rest/v1"

def get_user_profile_by_id(user_id):
    """
    Query the profiles table by auth.users.id (UUID).
    Returns dict or None.
    """
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Accept": "application/json",
    }
    params = {
        "select": "id,email,full_name,role",  # adapt to your schema
    }
    url = f"{POSTGREST}/profiles?id=eq.{user_id}"
    resp = requests.get(url, headers=headers, params=params, timeout=8)
    if resp.status_code == 200:
        data = resp.json()
        if data:
            return data[0]
    return None

def get_roles_by_user_id(user_id):
    """
    If you use normalized user_roles/roles:
    Query user_roles with joins to roles.
    """
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Accept": "application/json",
    }
    # Example using PostgREST to join user_roles -> roles
    url = f"{POSTGREST}/user_roles?user_id=eq.{user_id}&select=role_id,roles(role_name)"
    resp = requests.get(url, headers=headers, timeout=8)
    if resp.status_code == 200:
        return [r.get('roles', {}).get('role_name') for r in resp.json()]
    return []
