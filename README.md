# UZT Cargo Platform

UZT Cargo uchun yangi alohida platforma:

- Public sayt
- Custom web admin dashboard
- Telegram bot
- Django backend va API uchun tayyor asos

## Ishga tushirish

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Sayt: http://127.0.0.1:8000/

Web admin: http://127.0.0.1:8000/dashboard/

Django admin vaqtincha mavjud: http://127.0.0.1:8000/django-admin/

## Telegram bot

`.env` ichida `TELEGRAM_BOT_TOKEN` ni to'ldiring:

```powershell
python manage.py runbot
```

Bot e'lonlarni guruh yoki kanalga chiqarishi uchun `.env` ichida shu qiymatlarni qo'ying:

```env
TELEGRAM_BOT_TOKEN=123456:bot-token
TELEGRAM_ANNOUNCEMENT_CHAT_ID=-1001234567890
```

Botdagi asosiy flow:

- `/register` - yuk egasi, haydovchi yoki logist sifatida ro'yxatdan o'tish.
- `/newload` - yuk egasi yoki logist yangi yuk joylaydi.
- `/loads` - aktiv yuklar.
- `/nearloads` - haydovchi lokatsiya yuboradi va yaqin yuklarni ko'radi.
- Guruh/kanaldagi `Qabul qilish` tugmasini birinchi bosgan ro'yxatdan o'tgan haydovchiga yuk biriktiriladi.
