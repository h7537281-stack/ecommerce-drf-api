from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import Category, Product


class Command(BaseCommand):
    help = 'تعبئة قاعدة البيانات ببيانات أولية تجريبية'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('جاري بدء تعبئة البيانات...'))

        # 1. إنشاء التصنيفات الرئيسية
        categories_data = [
            {'title': 'أدوية وفيتامينات', 'slug': 'medicines-vitamins'},
            {'title': 'العناية بالبشرة', 'slug': 'skincare'},
            {'title': 'مستلزمات طبية', 'slug': 'medical-supplies'},
            {'title': 'العناية بالأطفال', 'slug': 'baby-care'},
        ]

        categories = {}
        for cat in categories_data:
            category, _ = Category.objects.get_or_create(
                slug=cat['slug'],
                defaults={'title': cat['title']}
            )
            categories[cat['slug']] = category

        # 2. إنشاء المنتجات وتوزيعها على التصنيفات
        products_data = [
            {
                'title': 'فيتامين سي 1000 ملغ',
                'slug': 'vitamin-c-1000mg',
                'description': 'مكمل غذائي يومي لتعزيز المناعة.',
                'inventory': 50,
                'unit_price': 15.50,
                'category': categories['medicines-vitamins']
            },
            {
                'title': 'أوميغا 3 مكثف',
                'slug': 'omega-3-capsules',
                'description': 'كبسولات زيت السمك لدعم صحة القلب والتركيز.',
                'inventory': 40,
                'unit_price': 32.00,
                'category': categories['medicines-vitamins']
            },
            {
                'title': 'واقي شمس 50+',
                'slug': 'sunscreen-spf50',
                'description': 'حماية عالية من أشعة الشمس للبشرة الحساسة.',
                'inventory': 25,
                'unit_price': 28.00,
                'category': categories['skincare']
            },
            {
                'title': 'كريم مرطب طبي',
                'slug': 'moisturizing-cream',
                'description': 'ترطيب عميق للبشرة الجافة.',
                'inventory': 35,
                'unit_price': 22.50,
                'category': categories['skincare']
            },
            {
                'title': 'جهاز قياس الضغط',
                'slug': 'blood-pressure-monitor',
                'description': 'جهاز قياس ضغط الدم رقمي وسهل الاستخدام.',
                'inventory': 15,
                'unit_price': 85.00,
                'category': categories['medical-supplies']
            },
            {
                'title': 'ميزان حرارة عن بعد',
                'slug': 'digital-thermometer',
                'description': 'جهاز قياس الحرارة بالأشعة تحت الحمراء.',
                'inventory': 20,
                'unit_price': 45.00,
                'category': categories['medical-supplies']
            },
        ]

        for prod in products_data:
            Product.objects.get_or_create(
                slug=prod['slug'],
                defaults=prod
            )

        self.stdout.write(self.style.SUCCESS('تمت تعبئة البيانات التجريبية بنجاح!'))