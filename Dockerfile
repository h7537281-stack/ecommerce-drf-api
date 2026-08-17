# 1. استخدام نسخة بايثون رسمية وخفيفة
FROM python:3.11-slim

# 2. تعيين بيئة العمل
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# 4. تثبيت المكتبيات النظامية المساعدة
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. نسخ ملف المكتبيات وتثبيتها
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 6. نسخ بقية كود المشروع إلى الحاوية
COPY . /app/

# 7. المنفذ الذي سيعمل عليه Django
EXPOSE 8000

# 8. أمر التشغيل الافتراضي
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]