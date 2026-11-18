import mimetypes
import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class Command(BaseCommand):
    help = "Upload all local media files from MEDIA_ROOT to Supabase Storage (S3 bucket)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--bucket",
            type=str,
            default="",
            help="Override bucket name (default: AWS_STORAGE_BUCKET_NAME from settings)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing files in the bucket",
        )

    def handle(self, *args, **options):
        access_key = getattr(settings, "AWS_ACCESS_KEY_ID", "") or os.environ.get("AWS_ACCESS_KEY_ID", "")
        secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "") or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", "") or os.environ.get("AWS_S3_ENDPOINT_URL", "")
        bucket_name = options["bucket"] or getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") or os.environ.get("AWS_STORAGE_BUCKET_NAME", "media")
        region_name = getattr(settings, "AWS_S3_REGION_NAME", "us-east-1") or os.environ.get("AWS_S3_REGION_NAME", "us-east-1")

        if not access_key or not secret_key or not endpoint_url:
            self.stderr.write(
                self.style.ERROR(
                    "Missing Supabase Storage S3 credentials!\n"
                    "Please ensure the following environment variables are set in .env:\n"
                    "  AWS_ACCESS_KEY_ID=<your-supabase-storage-access-key>\n"
                    "  AWS_SECRET_ACCESS_KEY=<your-supabase-storage-secret-key>\n"
                    "  AWS_STORAGE_BUCKET_NAME=media\n"
                    "  AWS_S3_ENDPOINT_URL=https://<your-project-ref>.supabase.co/storage/v1/s3\n"
                )
            )
            return

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            raise CommandError(f"MEDIA_ROOT directory does not exist: {media_root}")

        self.stdout.write(self.style.NOTICE(f"Connecting to Supabase Storage at: {endpoint_url}"))
        self.stdout.write(self.style.NOTICE(f"Target Bucket: {bucket_name}"))

        session = boto3.session.Session()
        s3_client = session.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

        # Collect all files to upload
        files_to_upload = [p for p in media_root.rglob("*") if p.is_file()]
        total_files = len(files_to_upload)

        if total_files == 0:
            self.stdout.write(self.style.WARNING(f"No media files found in {media_root}."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {total_files} media files to upload.\n"))

        uploaded_count = 0
        skipped_count = 0
        failed_count = 0

        for idx, file_path in enumerate(files_to_upload, start=1):
            rel_path = file_path.relative_to(media_root).as_posix()
            content_type, _ = mimetypes.guess_type(str(file_path))
            content_type = content_type or "application/octet-stream"

            extra_args = {"ContentType": content_type}

            try:
                if not options["overwrite"]:
                    try:
                        s3_client.head_object(Bucket=bucket_name, Key=rel_path)
                        skipped_count += 1
                        self.stdout.write(f"[{idx}/{total_files}] Skipped (exists): {rel_path}")
                        continue
                    except ClientError:
                        pass

                s3_client.upload_file(
                    Filename=str(file_path),
                    Bucket=bucket_name,
                    Key=rel_path,
                    ExtraArgs=extra_args,
                )
                uploaded_count += 1
                self.stdout.write(self.style.SUCCESS(f"[{idx}/{total_files}] Uploaded: {rel_path}"))
            except Exception as e:
                failed_count += 1
                self.stderr.write(self.style.ERROR(f"[{idx}/{total_files}] Failed {rel_path}: {e}"))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Summary: {uploaded_count} uploaded, {skipped_count} skipped, {failed_count} failed."
            )
        )
