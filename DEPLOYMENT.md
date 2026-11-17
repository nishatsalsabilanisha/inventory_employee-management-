# Vercel Deployment

Vercel detects the root `manage.py`, reads `fms.settings.WSGI_APPLICATION`, and serves the project through its Python runtime. No custom API adapter, route rewrites, build command, or output directory is needed. `STATIC_ROOT` is configured so Vercel can collect static files and serve them from its CDN during the build.

The project pins Python 3.13 in `.python-version`. Dependencies are installed from `requirements.txt`.

## Easiest Deployment Workflow

1. **Push to GitHub**:
   Ensure all changes are pushed to your GitHub repository.
2. **Import into Vercel**:
   Import your repository. Leave the Build Command and Output Directory as default.
3. **Connect a Database (1 Click in Vercel)**:
   In your Vercel project dashboard, go to the **Storage** tab, click **Create Database** -> select **Neon (Postgres)**, and click **Connect**. Vercel will automatically inject `DATABASE_URL`!
4. **Run Initial Migrations**:
   Run migrations once against the new database from your machine using:
   ```powershell
   $env:DATABASE_URL="<your-neon-database-url>"
   python manage.py migrate
   python manage.py createsuperuser
   ```

## Automatic Smart Defaults

- `ALLOWED_HOSTS`: Automatically includes your Vercel project URLs and `*.vercel.app`.
- `CSRF_TRUSTED_ORIGINS`: Automatically allows `https://*.vercel.app`.
- `STATIC_ROOT`: Collected automatically by Vercel on build.
- `STORAGE`: Falls back gracefully to local storage if external S3 credentials are not yet configured.

## Optional Environment Variables

You can customize these in Vercel Project Settings > Environment Variables:

```text
DJANGO_SECRET_KEY=<long, random string>
DJANGO_DEBUG=False
DATABASE_URL=<PostgreSQL connection URL>
```

### Persistent Media Storage (Supabase S3)
To persist uploaded employee or product photos across serverless invocations, enable S3 on Supabase Storage and add:

```text
AWS_ACCESS_KEY_ID=<storage access key>
AWS_SECRET_ACCESS_KEY=<storage secret key>
AWS_STORAGE_BUCKET_NAME=media
AWS_S3_ENDPOINT_URL=https://<project-ref>.supabase.co/storage/v1/s3
```

## Verification

Before deploying, run:

```powershell
python manage.py check
python manage.py check --deploy
python manage.py migrate --plan
python manage.py collectstatic --noinput
```

Vercel runtime logs are available in the failed deployment's **Functions**
logs. If the deployment still returns `FUNCTION_INVOCATION_FAILED`, inspect
the first Python traceback there; the public HTTP response does not expose the
underlying exception.
