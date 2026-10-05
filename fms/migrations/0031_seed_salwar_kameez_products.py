from django.db import migrations

# Inspired by Le Reve Craze salwar kameez collection.
# [Color] [Fabric] [Style] Salwar Kameez
PRODUCTS = [
    ("Green Cotton Jacquard Salwar Kameez",
     "Elegant green cotton jacquard three-piece with embroidered dupatta. Premium cotton jacquard weave with a matching dupatta.",
     "4691.00", 25),
    ("Golden Viscose A-Line Salwar Kameez",
     "Golden viscose A-line kameez with churidar and printed dupatta. Lightweight, flowy and comfortable for daily wear.",
     "4091.00", 30),
    ("White Viscose A-Line Salwar Kameez",
     "White viscose A-line kameez with straight churidar and soft dupatta. Classic and breathable all-weather wear.",
     "3991.00", 30),
    ("Green Georgette Salwar Kameez",
     "Green georgette three-piece with delicate work on the neckline and matching dupatta.",
     "7091.00", 20),
    ("Green Georgette Straight Salwar Kameez",
     "Green georgette straight-cut kameez with churidar and contrast dupatta. Graceful drape for formal occasions.",
     "6591.00", 20),
    ("Red Georgette A-line Salwar Kameez",
     "Red georgette A-line kameez with embroidered accents and matching dupatta. Festive yet understated.",
     "6091.00", 25),
    ("Red Blended A-line Salwar Kameez",
     "Red blended fabric A-line kameez with churidar and dupatta. All-day comfort with a rich colour.",
     "5591.00", 25),
    ("Red Satin Georgette Party Salwar Kameez",
     "Red satin georgette party-wear three-piece with subtle sheen and premium finish.",
     "5491.00", 15),
    ("Burgundy Blended A-line Salwar Kameez",
     "Burgundy blended A-line kameez with matching dupatta. Deep festive tone for evening events.",
     "7041.00", 20),
    ("Gray Joom Salwar Kameez",
     "Gray joom fabric three-piece with minimalist elegance and matching dupatta.",
     "4241.00", 25),
    ("Green Joom Salwar Kameez",
     "Green joom kameez with churidar and dupatta. Crisp texture with a comfortable drape.",
     "7091.00", 20),
    ("Beige Blended Gown Style Salwar Kameez",
     "Beige blended gown-style kameez with flared silhouette and dupatta. Modern take on classic salwar.",
     "8191.00", 18),
    ("Beige Satin Georgette Salwar Kameez",
     "Beige satin georgette three-piece with elegant fall and matching dupatta.",
     "5691.00", 22),
    ("Brown Viscose Shrug Style Salwar Kameez",
     "Brown viscose kameez with a shrug-style overlay and dupatta. Trendy layered look.",
     "5691.00", 20),
    ("Brown Muslin Shrug Style Salwar Kameez",
     "Brown muslin kameez with shrug-style overlay and dupatta. Soft, breathable premium muslin.",
     "10891.00", 12),
    ("Pink Muslin Exclusive Salwar Kameez",
     "Pink muslin exclusive three-piece with fine detailing. Premium hand-feel fabric for special occasions.",
     "12891.00", 10),
    ("Pink Silk & Viscose Blend Exclusive Salwar Kameez",
     "Pink silk and viscose blend exclusive three-piece with rich drape and matching dupatta.",
     "10991.00", 10),
    ("Pastel Brown Silk & Viscose Blend Exclusive Salwar Kameez",
     "Pastel brown silk and viscose blend exclusive set. Soft pastel tone with a luxurious finish.",
     "14991.00", 8),
    ("Black Muslin and Crepe Exclusive Salwar Kameez",
     "Black muslin and crepe exclusive three-piece with contrasting texture panels and dupatta.",
     "9891.00", 12),
]


def seed_products(apps, schema_editor):
    Product = apps.get_model("fms", "Product")
    for name, description, price, stock in PRODUCTS:
        Product.objects.get_or_create(
            name=name,
            defaults={
                "description": description,
                "price": price,
                "stock": stock,
                "low_stock_threshold": 10,
                "category": "Womenswear",
                "subcategory": "Salwar Kameez",
            },
        )


def unseed_products(apps, schema_editor):
    Product = apps.get_model("fms", "Product")
    Product.objects.filter(name__in=[p[0] for p in PRODUCTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("fms", "0030_seed_departments_job_positions"),
    ]

    operations = [
        migrations.RunPython(seed_products, unseed_products),
    ]
