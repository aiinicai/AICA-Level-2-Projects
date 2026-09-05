"""
Supabase Configuration
Provides Supabase clients for the application
"""
import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")

# Client for user operations (respects RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Admin client for service operations (bypasses RLS)
# This is used by the Flask API for operations that need to bypass RLS
if SUPABASE_SERVICE_KEY and SUPABASE_SERVICE_KEY != "YOUR_SERVICE_ROLE_KEY_HERE_FROM_SUPABASE_DASHBOARD":
    supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
else:
    # Fallback to anon client if service key not configured
    # Note: This will respect RLS policies
    supabase_admin = supabase
    print("Warning: SUPABASE_SERVICE_KEY not configured. Using anon key. Some operations may fail.")
