<<<<<<< HEAD
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

=======
# Vercel deployment

Vercel's current Django integration detects the root `manage.py`, reads
`fms.settings.WSGI_APPLICATION`, and serves the project through its Python
runtime. No custom API adapter, route rewrites, build command, or output
directory is needed. `STATIC_ROOT` is configured so Vercel can collect static
files and serve them from its CDN during the build.

In Vercel Project Settings, use the repository root as the Root Directory and
remove any legacy Build Command, Output Directory, or Install Command
overrides so automatic Django detection can run.

The project pins Python 3.13 in `.python-version`. Dependencies are installed
from `requirements.txt`.

## Required Vercel environment variables

Set these for Production (and Preview if previews should use the database):

```text
DJANGO_SECRET_KEY=<long, random, private value>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=inventory-employee-management.vercel.app
CSRF_TRUSTED_ORIGINS=https://inventory-employee-management.vercel.app
DATABASE_URL=<PostgreSQL connection URL>
DB_SSLMODE=require
```

Alternatively, omit `DATABASE_URL` and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
`DB_HOST`, and `DB_PORT` to the persistent PostgreSQL provider's values. Never
commit the actual values. `DATABASE_URL` takes precedence when both forms are
present.

Create a long random secret locally, for example with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

The project uses PostgreSQL, not the untracked local `db.sqlite3`. Vercel's
function filesystem is ephemeral, so SQLite is not a suitable production
database. Create a persistent PostgreSQL database (for example, Supabase), add
its connection URL or individual credentials to Vercel, then run migrations
once against that database from a trusted local environment:

```powershell
python manage.py migrate
```

Do not run migrations against production until the database is provisioned and
backed up. The repository's migration files are under `fms/migrations/`.

## Static files and uploads

Vercel collects Django static assets from `STATIC_ROOT` and serves them at
`/static/`. Product and employee uploads need persistent object storage because
Vercel's local filesystem is ephemeral. This project supports Supabase's
S3-compatible storage. Create a bucket and configure:

```text
USE_SUPABASE_STORAGE=True
AWS_ACCESS_KEY_ID=<storage access key>
AWS_SECRET_ACCESS_KEY=<storage secret key>
AWS_STORAGE_BUCKET_NAME=media
AWS_S3_REGION_NAME=us-east-1
AWS_S3_ENDPOINT_URL=https://<project-ref>.supabase.co/storage/v1/s3
AWS_S3_SIGNATURE_VERSION=aws4
AWS_S3_ADDRESSING_STYLE=path
AWS_S3_FILE_OVERWRITE=False
AWS_S3_USE_SSL=True
```

The bucket must permit the read access expected by the application's image
URLs. Keep all storage credentials private. Existing tracked media files are
not automatically uploaded to the bucket; migrate them separately if they
must remain available after deployment.

On Vercel, HTTPS redirects, secure cookies, and HSTS default to enabled. You
can explicitly set:

```text
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

The `.env.example` file contains placeholders only. Copy it to an ignored
`.env` for local development and never commit `.env`.

>>>>>>> bfe3dde3035582d7ff3128ca784822b006540202
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
