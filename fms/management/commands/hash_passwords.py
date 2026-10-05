from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from fms.models import Employee, Customer


class Command(BaseCommand):
    help = "Hash all plaintext passwords in Employee and Customer tables"

    def handle(self, *args, **options):
        for label, model in [("Employee", Employee), ("Customer", Customer)]:
            count = 0
            for obj in model.objects.all():
                pw = str(obj.password) if obj.password else ""
                if pw and not (
                    pw.startswith("pbkdf2_")
                    or pw.startswith("bcrypt")
                    or pw.startswith("argon2")
                ):
                    obj.password = make_password(pw)
                    obj.save(update_fields=["password"])
                    count += 1
            self.stdout.write(f"{label}: hashed {count} passwords")