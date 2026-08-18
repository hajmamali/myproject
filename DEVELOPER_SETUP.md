# مرجع سریع برای توسعه‌دهندگان MahouN

## 🚀 شروع سریع

### 1. اجرای فرانت‌اند توسعه‌دهنده

```bash
cd frontend
npm run dev:developer
```

**پورت:** http://localhost:3001

### 2. ورود به سیستم

**روش‌های ورود:**

#### الف) دسترسی سریع برای development:
- **نام کاربری:** `haji`
- **رمز عبور:** `haji`
- **نقش:** ADMIN (تمام دسترسی‌ها)

#### ب) درخواست account جدید (production):
- برای محیط production، از تیم infrastructure سوال کنید

---

## 📋 منوی توسعه‌دهنده

بعد از ورود، شما دسترسی کامل به این بخش‌ها دارید:

| بخش | URL | توضیح |
|---|---|---|
| **Dashboard** | `/` | مرجع کنترل و یکجا سازی داده‌ها |
| **Monitoring** | `/monitoring` | پایش عملیات real-time |
| **Delay Analysis** | `/delay-analysis` | تحلیل تأخیرات و bottlenecks |
| **Timeline** | `/timeline` | نمایش سرعت و جدول زمانی |
| **Training** | `/training` | مدیریت مدل‌های یادگیری |
| **A/B Testing** | `/ab-testing` | آزمایش‌های تجربی و optimization |
| **Fine-tuning** | `/fine-tuning` | تنظیق دقیق مدل‌ها |
| **Governance** | `/governance` | قوانین و تدقیق دسترسی |
| **Knowledge Graph** | `/knowledge-graph` | دید گراف دانش حقوقی |

---

## 🔐 امنیت و Sessions

### Session Expiry
- **مدت**: 8 ساعت
- **به‌روزرسانی خودکار**: تا زمان استفاده

### دسترسی‌های ADMIN (شما)
- ✅ مطالعه (`READ`)
- ✅ نوشتن (`WRITE`)
- ✅ حذف (`DELETE`)
- ✅ مدیریت (`ADMIN`)
- ✅ خروجی‌گیری (`EXPORT`)
- ✅ بدون نام‌کردن (`ANONYMIZE`)

---

## 🛠️ API Integration (Backend Connection)

### محیط Development
```bash
# فرانت‌اند: localhost:3001
# بک‌اند: localhost:8000

# proxy خودکار از Vite:
# /v1/* → localhost:8000/v1/*
# /api/* → localhost:8000/api/*
```

### محیط Production
- Nginx proxy (نیاز به پیکربندی)
- Environment variable: `VITE_API_URL`

### بررسی اتصال API
```bash
# از developer console:
curl -X GET http://localhost:8000/health
```

---

## 📝 Governance و Audit Logging

هر فعالیت شما ثبت می‌شود برای تدقیق:
- **Request ID**: شناسه منحصر برای تتبع
- **Trace ID**: چین تراکنش
- **Audit Reference**: ارجاع برای سوابق

---

## 🐛 عیب‌یابی

### مشکل: صفحه login می‌ماند
**حل:**
1. `npm run dev:developer` را دوباره شروع کنید
2. Cache را پاک کنید: `localStorage.clear()`
3. صفحه را refresh کنید (Ctrl+Shift+R)

### مشکل: خطای API / backend غیرفعال
**حل:**
1. بک‌اند را بررسی کنید: `python api/main.py`
2. ثبت کردن پورت: `lsof -i :8000`
3. درخواست صحیح: `curl http://localhost:8000/health`

### مشکل: پیام دسترسی رد شده
- شما ADMIN هستید و تمام دسترسی‌ها را دارید
- اگر همچنان رد شد، sessionتان منقضی شده است
- دوباره login کنید

---

## 🔧 توسعه‌ای و تغییر

### اضافه کردن route جدید
```tsx
// developer/App.tsx میں:
<Route path="/new-page" element={
  <ProtectedRoute>
    <NewComponent />
  </ProtectedRoute>
} />
```

### اضافه کردن permission جدید
```ts
// shared/stores/authStore.ts میں:
export enum Permission {
  // ... موجود
  MY_NEW_PERMISSION = 'my_new_permission',
}
```

### تست auth locally
```bash
cd frontend
npm test -- authStore.test.ts
```

---

## 📞 سوالات و درخواست کمک

اگر مشکل داریتد:
1. **Logs بررسی کنید**: Browser console (F12)
2. **Backend logs**: `python -u api/main.py`
3. **Network tab**: DevTools → Network → API calls
4. **AuthStore state**: DevTools → Redux/Zustand extension

---

## ✅ Checklist اول

- [ ] `npm run dev:developer` اجرا کنید
- [ ] صفحه login را مشاهده کنید
- [ ] `haji/haji` را وارد کنید
- [ ] Dashboard ظاهر شود
- [ ] حداقل یک page دیگر کلیک کنید
- [ ] Governance page ببینید
- [ ] F12 Developer Console را بررسی کنید - هیچ error نباید باشد

---

**نسخه:** MahouN 2026-08-18  
**آخرین به‌روزرسانی:** امروز  
**Status:** ✅ Ready for Development
