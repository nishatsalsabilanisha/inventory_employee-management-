"""
Helper script to upload all local media files (products, employee photos, buyer photos)
to your Supabase Storage bucket so they appear live in your deployment.

Usage:
    python upload_media_to_supabase.py
"""
import mimetypes
import os
import sys
from pathlib import Path

# Load settings and environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fms.settings")

try:
    import django
    django.setup()
    from django.core.management import call_command
except Exception as e:
    print(f"Error loading Django environment: {e}")
    sys.exit(1)

if __name__ == "__main__":
    print("=======================================================")
    print("  Supabase Media Uploader (Product & Employee Photos)")
    print("=======================================================\n")
    call_command("upload_media")
