from django.db import migrations


DEPARTMENTS = [
    ("Merchandising", "Order planning, costing and buyer communication."),
    ("Design", "Fashion design, pattern making and sampling support."),
    ("Cutting", "Fabric cutting according to approved markers."),
    ("Garments Production", "Main sewing and assembly production lines."),
    ("Finishing & Packing", "Trimming, ironing, folding and final packing."),
    ("Quality Control", "Inspection and quality assurance at every stage."),
    ("Sampling", "Development and production of sample garments."),
    ("Dyeing & Printing", "Fabric dyeing, washing and printing operations."),
    ("Fabric Store", "Raw material receiving, storing and issuing."),
    ("Warehouse & Logistics", "Finished goods storage and shipment handling."),
    ("Human Resources & Admin", "Recruitment, attendance, leave and admin affairs."),
    ("Accounts & Finance", "Salary, costing, payment and financial records."),
    ("Sales & Marketing", "Customer relations, sales and promotions."),
    ("IT", "Software, network and hardware support."),
    ("Maintenance", "Machine servicing and factory maintenance."),
]

POSITIONS = [
    ("General Manager", "Merchandising"),
    ("Production Manager", "Garments Production"),
    ("Line Supervisor", "Garments Production"),
    ("Machine Operator", "Garments Production"),
    ("Senior Merchandiser", "Merchandising"),
    ("Merchandiser", "Merchandising"),
    ("Assistant Merchandiser", "Merchandising"),
    ("Fashion Designer", "Design"),
    ("Pattern Master", "Design"),
    ("Sample Maker", "Sampling"),
    ("Cutting Master", "Cutting"),
    ("Fabric Cutter", "Cutting"),
    ("Quality Inspector (QC)", "Quality Control"),
    ("Quality Assurance Officer", "Quality Control"),
    ("Finishing Supervisor", "Finishing & Packing"),
    ("Ironing Operator", "Finishing & Packing"),
    ("Packing Operator", "Finishing & Packing"),
    ("Dyeing Operator", "Dyeing & Printing"),
    ("Printing Operator", "Dyeing & Printing"),
    ("Store Keeper", "Fabric Store"),
    ("Fabric Store Assistant", "Fabric Store"),
    ("Warehouse Officer", "Warehouse & Logistics"),
    ("Dispatch Executive", "Warehouse & Logistics"),
    ("HR Executive", "Human Resources & Admin"),
    ("Admin Assistant", "Human Resources & Admin"),
    ("Accountant", "Accounts & Finance"),
    ("Junior Accountant", "Accounts & Finance"),
    ("Cashier", "Accounts & Finance"),
    ("Marketing Executive", "Sales & Marketing"),
    ("Sales Representative", "Sales & Marketing"),
    ("Data Entry Operator", "IT"),
    ("IT Support Officer", "IT"),
    ("Maintenance Technician", "Maintenance"),
    ("Security Guard", "Human Resources & Admin"),
    ("Housekeeping Staff", "Human Resources & Admin"),
]


def seed_catalog(apps, schema_editor):
    Department = apps.get_model("fms", "Department")
    JobPosition = apps.get_model("fms", "JobPosition")

    dept_map = {}
    for name, description in DEPARTMENTS:
        dept, created = Department.objects.get_or_create(
            name=name,
            defaults={"description": description, "is_active": True},
        )
        dept_map[name] = dept

    for title, dept_name in POSITIONS:
        dept = dept_map.get(dept_name)
        if dept:
            JobPosition.objects.get_or_create(
                title=title,
                department=dept,
                defaults={"is_active": True},
            )


def unseed_catalog(apps, schema_editor):
    JobPosition = apps.get_model("fms", "JobPosition")
    Department = apps.get_model("fms", "Department")
    JobPosition.objects.filter(title__in=[t for t, _ in POSITIONS]).delete()
    Department.objects.filter(name__in=[n for n, _ in DEPARTMENTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("fms", "0029_department_product_low_stock_threshold_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, unseed_catalog),
    ]
