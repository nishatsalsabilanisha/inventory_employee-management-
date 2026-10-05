from django.db import migrations


def rename_or_add_payment_customer(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    with schema_editor.connection.cursor() as cur:
        if vendor == 'postgresql':
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'fms_paymenttransaction' AND column_name IN ('buyer_id', 'customer_id');
            """)
            cols = [r[0] for r in cur.fetchall()]
            if 'buyer_id' in cols:
                cur.execute("ALTER TABLE fms_paymenttransaction RENAME COLUMN buyer_id TO customer_id;")
            elif 'customer_id' not in cols:
                cur.execute("ALTER TABLE fms_paymenttransaction ADD COLUMN customer_id bigint NULL REFERENCES fms_customer(id) ON DELETE SET NULL;")
        else:
            cur.execute("PRAGMA table_info(fms_paymenttransaction);")
            cols = [r[1] for r in cur.fetchall()]
            if 'buyer_id' in cols:
                cur.execute("ALTER TABLE fms_paymenttransaction RENAME COLUMN buyer_id TO customer_id;")
            elif 'customer_id' not in cols:
                cur.execute("ALTER TABLE fms_paymenttransaction ADD COLUMN customer_id integer NULL REFERENCES fms_customer(id) ON DELETE SET NULL;")


class Migration(migrations.Migration):

    dependencies = [
        ("fms", "0026_salarypayment"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Buyer",
            new_name="Customer",
        ),
        migrations.RenameField(
            model_name="cancellationrequest",
            old_name="buyer",
            new_name="customer",
        ),
        migrations.RenameField(
            model_name="cart",
            old_name="buyer",
            new_name="customer",
        ),
        migrations.RenameField(
            model_name="order",
            old_name="buyer",
            new_name="customer",
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name="paymenttransaction",
                    old_name="buyer",
                    new_name="customer",
                ),
            ],
            database_operations=[
                migrations.RunPython(rename_or_add_payment_customer, migrations.RunPython.noop),
            ],
        ),
    ]

