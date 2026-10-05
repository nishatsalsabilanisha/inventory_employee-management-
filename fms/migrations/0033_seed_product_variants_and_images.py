import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import migrations
from PIL import Image, ImageDraw


# demo variants per product: (color, size, textile, price_multiplier, stock)
VARIANT_BLUEPRINTS = [
    ("Green", "M", "Cotton", "1.00", 18),
    ("Green", "L", "Cotton", "1.00", 14),
    ("Green", "XL", "Cotton", "1.00", 10),
    ("White", "S", "Cotton", "1.00", 12),
    ("White", "M", "Cotton", "1.00", 16),
    ("White", "L", "Cotton", "1.00", 12),
    ("Black", "M", "Georgette", "1.10", 8),
    ("Black", "L", "Georgette", "1.10", 6),
    ("Black", "XL", "Georgette", "1.10", 5),
    ("Pink", "S", "Silk & Viscose", "1.25", 6),
    ("Pink", "M", "Silk & Viscose", "1.25", 8),
    ("Pink", "L", "Silk & Viscose", "1.25", 6),
    ("Brown", "M", "Muslin", "1.30", 5),
    ("Brown", "L", "Muslin", "1.30", 4),
    ("Red", "M", "Satin Georgette", "1.15", 9),
    ("Red", "L", "Satin Georgette", "1.15", 7),
    ("Beige", "S", "Viscose", "0.95", 10),
    ("Beige", "M", "Viscose", "0.95", 12),
    ("Beige", "L", "Viscose", "0.95", 9),
    ("Gray", "M", "Joom", "0.90", 11),
    ("Gray", "L", "Joom", "0.90", 8),
]

PALETTE = {
    "Green": (34, 139, 34),
    "White": (245, 245, 245),
    "Black": (30, 30, 30),
    "Pink": (231, 84, 128),
    "Brown": (121, 85, 61),
    "Red": (220, 50, 47),
    "Beige": (214, 197, 166),
    "Gray": (128, 128, 128),
    "Burgundy": (128, 0, 32),
    "Pastel Brown": (194, 152, 118),
    "Golden": (218, 165, 32),
    "Pastel Pink": (250, 190, 210),
}


def make_image(name, color_rgb):
    img = Image.new("RGB", (600, 800), color_rgb)
    draw = ImageDraw.Draw(img)
    for i in range(0, 800, 40):
        shade = tuple(min(255, c + 18) for c in color_rgb)
        draw.line([(0, i), (600, i)], fill=shade, width=2)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return ContentFile(buf.getvalue(), name=f"{name}.jpg")


def seed_demo(apps, schema_editor):
    Product = apps.get_model("fms", "Product")
    ProductColor = apps.get_model("fms", "ProductColor")
    ProductSize = apps.get_model("fms", "ProductSize")
    ProductTextile = apps.get_model("fms", "ProductTextile")
    ProductVariant = apps.get_model("fms", "ProductVariant")
    ProductImage = apps.get_model("fms", "ProductImage")

    products = list(Product.objects.filter(subcategory="Salwar Kameez"))

    for product in products:
        color_names = sorted({b[0] for b in VARIANT_BLUEPRINTS})[:5]
        size_names = ["S", "M", "L", "XL"]
        textile_names = sorted({b[2] for b in VARIANT_BLUEPRINTS})

        for c in color_names:
            ProductColor.objects.get_or_create(product=product, name=c)
        for s in size_names:
            ProductSize.objects.get_or_create(product=product, name=s)
        for t in textile_names:
            ProductTextile.objects.get_or_create(product=product, name=t)

        base_price = float(product.price)
        for color, size, textile, mult, stock in VARIANT_BLUEPRINTS:
            ProductVariant.objects.get_or_create(
                product=product,
                color=color,
                size=size,
                textile=textile,
                defaults={
                    "price": round(base_price * float(mult), 2),
                    "stock": stock,
                },
            )

        key = next((k for k in PALETTE if k in product.name), "Beige")
        color_rgb = PALETTE[key]
        for i in range(3):
            f = make_image(f"{product.sl}_img{i+1}", color_rgb)
            ProductImage.objects.get_or_create(
                product=product,
                is_primary=(i == 0),
                defaults={"image": f},
            )


def unseed_demo(apps, schema_editor):
    ProductColor = apps.get_model("fms", "ProductColor")
    ProductSize = apps.get_model("fms", "ProductSize")
    ProductTextile = apps.get_model("fms", "ProductTextile")
    ProductVariant = apps.get_model("fms", "ProductVariant")
    ProductImage = apps.get_model("fms", "ProductImage")
    ProductImage.objects.all().delete()
    ProductVariant.objects.all().delete()
    ProductColor.objects.all().delete()
    ProductSize.objects.all().delete()
    ProductTextile.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("fms", "0032_product_brand_product_discount_price_product_sku_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_demo, unseed_demo),
    ]
