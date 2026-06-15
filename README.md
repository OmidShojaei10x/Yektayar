# یکتایار — ربات تلگرام Exchange

ربات تلگرامی برای اتصال به سرور Exchange داخلی یکتانت.

## امکانات

| قابلیت | توضیح |
|--------|-------|
| 🔐 احراز هویت | ورود با نام کاربری و پسورد Exchange (رمزنگاری‌شده) |
| 📧 ایمیل | مشاهده صندوق ورودی، خواندن ایمیل، ارسال ایمیل |
| 📅 تقویم | مشاهده رویدادها، ایجاد جلسه جدید |
| 👥 مخاطبان | جستجو در دفترچه آدرس سازمان |
| 🏢 رزرو اتاق | رزرو اتاق جلسه با کمک هوش مصنوعی |
| 🤖 AI | گفت‌وگوی فارسی با Claude برای رزرو هوشمند اتاق |

## راه‌اندازی

### پیش‌نیازها

- Python 3.12+
- دسترسی به سرور Exchange (EWS فعال)
- توکن ربات تلگرام از @BotFather
- کلید API آنتروپیک (Claude)

### نصب

```bash
git clone ...
cd Yektayar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### تنظیمات

```bash
cp .env.example .env
```

فایل `.env` را ویرایش کن:

```env
TELEGRAM_BOT_TOKEN=xxx
EXCHANGE_SERVER=mail.yektanet.com
EXCHANGE_DOMAIN=yektanet
ANTHROPIC_API_KEY=sk-ant-xxx
ENCRYPTION_KEY=<کلید Fernet تولیدشده>
```

برای تولید کلید رمزنگاری:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

اگر سرور Exchange از Autodiscover پشتیبانی نمی‌کند، آدرس EWS را مستقیم بده:
```env
EXCHANGE_EWS_URL=https://mail.yektanet.com/EWS/Exchange.asmx
```

### اجرا

```bash
python main.py
```

### Docker

```bash
docker-compose up -d
```

> **نکته:** در `docker-compose.yml` شبکه `yektanet_internal` باید از قبل موجود باشد تا ربات به سرور Exchange داخلی دسترسی داشته باشد.

## ساختار پروژه

```
Yektayar/
├── main.py                  # نقطه ورود، ثبت Handler‌ها
├── config.py                # خواندن متغیرهای محیطی
├── bot/
│   ├── handlers/
│   │   ├── auth.py          # ورود/خروج
│   │   ├── email.py         # ایمیل
│   │   ├── calendar.py      # تقویم
│   │   ├── contacts.py      # مخاطبان
│   │   └── rooms.py         # رزرو اتاق + AI
│   ├── keyboards.py         # کیبوردهای تلگرام
│   └── middleware.py        # بررسی احراز هویت
├── exchange/
│   └── client.py            # کلاینت EWS با exchangelib
├── ai/
│   └── booking_agent.py     # Agent رزرو اتاق با Claude
├── storage/
│   └── session_store.py     # ذخیره رمزنگاری‌شده با SQLite
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## امنیت

- پسورد کاربران با **Fernet symmetric encryption** رمزنگاری می‌شود
- پیام حاوی پسورد بلافاصله از چت پاک می‌شود
- هر کاربر فقط به داده‌های خودش دسترسی دارد
