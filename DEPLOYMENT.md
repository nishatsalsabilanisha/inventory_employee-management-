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
