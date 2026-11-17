# Vercel Deployment

Vercel detects the root `manage.py`, reads `fms.settings.WSGI_APPLICATION`, and serves the project through its Python runtime. No custom API adapter, route rewrites, build command, or output directory is needed. `STATIC_ROOT` is configured so Vercel can collect static files and serve them from its CDN during the build.

The project pins Python 3.13 in `.python-version`. Dependencies are installed from `requirements.txt`.

## Simple Deployment Workflow (GitHub + Supabase + Vercel)

1. **Push to GitHub**:
   Ensure all changes are pushed to your GitHub repository:
   ```powershell
   git add .
   git commit -m "Configure Vercel and Supabase deployment"
   git push origin main
   ```

2. **Get Supabase Database URL**:
   In your Supabase project under **Project Settings** → **Database** → **Connection string (URI)**, copy your PostgreSQL URL:
   ```text
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

3. **Run Migrations Once Locally**:
   Before deploying, apply database migrations to your Supabase database:
   ```powershell
   $env:DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Import into Vercel**:
   - Go to Vercel, click **Add New...** → **Project**, and import your GitHub repository.
   - Leave Build and Output settings at defaults.
   - Under **Environment Variables**, add:
     - `DATABASE_URL`: your Supabase connection string
     - `DJANGO_SECRET_KEY`: a random secret key string
   - Click **Deploy**.

## Automatic Smart Defaults

- `ALLOWED_HOSTS`: Automatically includes your Vercel project URLs and `*.vercel.app`.
- `CSRF_TRUSTED_ORIGINS`: Automatically allows `https://*.vercel.app`.
- `STATIC_ROOT`: Collected automatically by Vercel on build.
- `STORAGE`: Falls back gracefully to local storage if external S3 credentials are not yet configured.

## Optional: Supabase S3 Media Storage
If you want uploaded images (buyer/employee photos) to persist in Supabase Storage, enable S3 on your Supabase Storage bucket (`media`) and add:

```text
USE_SUPABASE_STORAGE=True
AWS_ACCESS_KEY_ID=<your-storage-access-key>
AWS_SECRET_ACCESS_KEY=<your-storage-secret-key>
AWS_STORAGE_BUCKET_NAME=media
AWS_S3_ENDPOINT_URL=https://<your-project-ref>.supabase.co/storage/v1/s3
```
