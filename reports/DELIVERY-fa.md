# تحویل: کمپین هشت‌مرحله‌ای NEON GAUNTLET

تاریخ: ۲۰۲۶-۱۰-۱۹ — شاخه: `arena/118e3734-fd`

## ۱. چه چیزی اضافه شد

| مورد | قبل | بعد |
|---|---|---|
| مرحله | ۱ | **۸** (`config/stages.json`، تولیدشده با `tools/stage_pipeline/make_stages.py`) |
| موج | ۳ | ۳ تا ۴ موج در هر مرحله (۲۹ موج) |
| دشمن | ۲ آرکی‌تایپ (ریوِت، ریوِت نخبه) | **۴** آرکی‌تایپ (`rivet`, `runner`, `rivet_elite`, `overlord` به‌عنوان باس) |
| تایمر | ثابت ۹۹ ثانیه | ۹۹ تا ۱۳۴ ثانیه، وابسته به مرحله |
| مقیاس سختی | ندارد | `enemyHealthMul` تا ۱٫۷۰ و `enemyDamageMul` تا ۱٫۴۲ |
| جریان صفحه | مرحله → results | مرحله → بنر «NEXT: …» → مرحله بعد؛ نتایج فقط بعد از مرحله ۸ |
| تست‌ها | ۲۳ | **۲۵** |

## ۲. مکانیک کمپین

* `FD.stageList()` فایل `config/stages.json` را می‌خواند؛ `FD.setStage(i)` یک
  کپی عمیق از مرحلهٔ `i` را در `FD.assets.dataRef.currentStage` می‌گذارد و
  `FD.cfg.stage` همان را برمی‌گرداند. هیچ ماژول دیگری نمی‌داند چند مرحله وجود دارد.
* پس از پاک‌کردن هر مرحله، `onStageClear()` نتیجه را می‌سازد و
  `stageClearNext` را ست می‌کند؛ بعد از ۲۶۰ تیک نگه‌داشتن صفحهٔ «STAGE CLEAR»،
  `startStage(stageIndex + 1)` اجرا می‌شود.
* HUD شمارهٔ مرحله را نشان می‌دهد (`STAGE n / 8`) و صفحهٔ نتایج جمع کل کمپین
  (مراحل پاک‌شده، امتیاز، ضربه‌ها، آسیب دریافتی) را نشان می‌دهد.
* باس هر مرحله (۲ تا ۸) در موج آخر ظاهر می‌شود: `overlord` با ۱۸۰ HP پایه،
  مقیاس رسم ۱٫۲۵ و شعاع تهاجم ۳۴۰ پیکسل، همراه دو محافظ.

## ۳. تکرارپذیری

```bash
python3 tools/stage_pipeline/make_stages.py            # ساخت config/stages.json
python3 tools/stage_pipeline/make_stages.py --check    # خطا اگر فایل قدیمی باشد
python3 tools/asset_pipeline/bundle_data.py            # data.js
python3 tools/build_standalone.py                      # dist/neon-gauntlet.html
npm test                                               # ۲۵ تست
node tools/tests/playtest.js                           # پلی‌تست مرحله ۱
node tools/tests/standalone.js                         # کل کمپین روی فایل تک‌فایلی
node tools/capture/screenshots.js                      # ۱۴ اسکرین‌شات
```

## ۴. وضعیت تفکیک‌شده

### COMPLETED-AND-VERIFIED
* تولید قطعی `config/stages.json` و بررسی هم‌زمانی با `--check` (تست `config: stages.json …`).
* ۸ مرحله، ۲۹ موج، ۱۰۱ دشمن، ۷ باس؛ همهٔ انواع دشمن در `combat.json` تعریف شده‌اند.
* اجرای کامل کمپین تا صفحهٔ نتایج: تست `flow: all eight stages clear in sequence and reach the results screen`
  با autopilot و invincibility؛ همچنین `standalone.js` روی فایل `dist` با
  «campaign CLEARED (8/8 stages)».
* انتقال مرحله به مرحله با حفظ HP بازیکن و صفر شدن وضعیت موج‌ها.
* ۲۵/۲۵ تست سبز؛ بیلد تک‌فایلی ۵۰۲٬۳۷۲ بایت با ۱۰۲ تصویر و صفر ارجاع خارجی.
* ۱۴ اسکرین‌شات تازه و ۱۱ فریم اثبات پلی‌تست مرحله ۱.

### IMPLEMENTED-BUT-NOT-FULLY-VERIFIED
* تعادل سختی مراحل ۲ تا ۸: اعداد از منحنی خطی تولید می‌شوند اما با بازیکن انسانی
  تست نشده‌اند (فقط autopilot).
* باس `overlord`: همان اسپرایت `rivet_elite` با مقیاس ۱٫۲۵ و نوار جان متفاوت؛
  انیمیشن اختصاصی ندارد.
* تم رنگی مراحل: فقط رنگ‌آمیزی (wash) روی همان پنج لایهٔ پارالاکس است.

### BLOCKED-OR-NOT-IMPLEMENTED
* موسیقی و افکت صوتی جداگانه برای هر مرحله (همان لوپ رویه‌ای).
* لایه‌های پس‌زمینهٔ اختصاصی برای هر مرحله.
* ویدیوی گیم‌پلی دوباره رندر نشد؛ `artifacts/video/gameplay.mp4` هنوز مرحله ۱ را نشان می‌دهد.

## ۵. محدودیت‌ها

* چهار آرکی‌تایپ از یک شیت اسپرایت استفاده می‌کنند (تفاوت: آمار، مقیاس، تینت، AI).
* `stages.json` را دستی ویرایش نکنید؛ منبع حقیقت `make_stages.py` است.
