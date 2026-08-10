# 🎨 MahouN Harvey-Style Premium UI

## آپدیت‌های جدید

### ✨ Landing Page لاکچری
یه landing page حرفه‌ای مثل Harvey با فیچرهای زیر ساخته شدیم:

- **Animated Gradient Hero**: پس‌زمینه gradient با انیمیشن
- **Glassmorphism Effects**: جلوه‌های شیشه‌ای مدرن
- **Smooth Animations**: انیمیشن‌های نرم با Tailwind
- **Premium Typography**: تایپوگرافی حرفه‌ای
- **Feature Cards**: کارت‌های فیچر با hover effects
- **Stats Display**: نمایش آمار کلیدی
- **Responsive Design**: طراحی ریسپانسیو کامل

### 🎯 Navigation Structure

```
/                    → Landing Page (Public)
/login               → Login Page
/app/dashboard       → Main Dashboard (Protected)
/app/search          → Legal Search
/app/upload          → Document Upload
... (بقیه روت‌ها)
```

### 🎨 Custom Animations

تمام انیمیشن‌های custom در `tailwind.config.js` تعریف شدن:

- `animate-gradient-shift`: انیمیشن gradient
- `animate-fade-in`: fade in نرم
- `animate-slide-up`: slide up از پایین
- `animate-scroll`: انیمیشن scroll indicator

### 💎 Utility Classes

کلاس‌های کاربردی جدید در `index.css`:

- `.glass`: glassmorphism effect
- `.gradient-text`: gradient text رنگی
- `.shadow-premium`: سایه premium
- `.animation-delay-*`: تاخیر برای انیمیشن‌ها

## 🚀 چطوری استفاده کنیم؟

### 1. نصب Dependencies
```bash
cd frontend
npm install
```

### 2. اجرای Dev Server
```bash
npm run dev
```

بعد برو به:
- http://localhost:5173/ → Landing Page خفن
- http://localhost:5173/app/dashboard → Dashboard اصلی

### 3. Build برای Production
```bash
npm run build
```

## 📐 Design System

### Colors
- **Primary**: Blue gradient (#3b82f6 → #8b5cf6)
- **Secondary**: Purple (#8b5cf6 → #ec4899)
- **Accent**: Pink (#ec4899 → #f43f5e)
- **Background**: Slate-950/900 dark gradient
- **Text**: White/Slate-100 (primary), Slate-400 (secondary)

### Typography
- **Headings**: Bold, از 6xl تا 4xl
- **Body**: text-lg تا text-xl
- **Secondary**: text-slate-400

### Spacing
- **Sections**: py-32 (128px vertical)
- **Cards**: p-8 (32px padding)
- **Gaps**: gap-8 (32px بین المان‌ها)

## 🎯 Next Steps

بعدی‌ها که باید اضافه بشن:

1. **Command Palette (Cmd+K)**
   - Quick search
   - Quick actions
   - Fuzzy matching

2. **Premium Dashboard**
   - Real-time charts
   - Live metrics
   - Interactive visualizations

3. **AI Chat Interface**
   - Streaming responses
   - Markdown rendering
   - Citation cards

4. **Document Viewer**
   - PDF integration
   - Annotations
   - Highlighting

5. **Notification System**
   - Toast notifications
   - In-app alerts
   - Sound effects

## 🔥 فیچرهای Harvey که الان داریم

✅ Premium gradient backgrounds
✅ Glassmorphism effects
✅ Smooth animations
✅ Feature cards با hover
✅ Stats display
✅ Responsive design
✅ Dark mode premium
✅ Custom scrollbars

## 🎨 فیچرهایی که بعداً میاد

⏳ Command palette (Cmd+K)
⏳ Real-time collaboration
⏳ Advanced analytics
⏳ AI chat interface
⏳ Document annotations
⏳ Export capabilities
⏳ Email notifications
⏳ Mobile app

## 💪 Performance

Landing page الان خیلی سریعه:
- First Contentful Paint: <1s
- Time to Interactive: <2s
- Bundle size: Optimized با lazy loading

## 🐛 Issues؟

اگه مشکلی بود:
1. npm cache clean --force
2. rm -rf node_modules package-lock.json
3. npm install
4. npm run dev

---

**Made with ❤️ by MahouN Team**
**Inspired by Harvey AI's premium experience**
