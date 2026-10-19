# گزارش پیشرفت — فاز ۱ (تحلیل استاتیک مرحلهٔ ۱)

**کامیت:** `af9e498` روی شاخهٔ `arena/118e3734-fd` (پوش‌شده)
**مبنا:** `21cd1d8` به‌عنوان baseline پذیرفته‌شده؛ هیچ فایل یا ادعای آن حذف نشده است.

---

## Phase
Phase 1 — تحلیل استاتیک دایرکتوری مرجع (Stage 1)، تسک‌های ۱ تا ۵.

## Research Question
1. آیا چهار بلوکِ دیکد‌شدهٔ مرحلهٔ ۱ از یک مسیر معمولی (wave pipeline) می‌آیند یا بلوک ۴ مسیر boss است؟
2. دنبالهٔ boss/final-wave در هشت راند چه ساختاری دارد و آیا یک cursor واحد ELC آن را ادامه می‌دهد؟
3. جدول‌های palette descriptor چه اندازه و چه منطق انتخابی دارند (فقط index، بدون RGB)؟
4. آیا می‌توان regression test نوشت که حذف خاموش بایت‌ها را fail کند؟

## Sources
- `gsaurus/sor-disassemblies` → `Assemblies/Streets of Rage (JUE) (REV 00) [!].asm` (۷۲٬۹۲۰ خط) — منبع اصلی.
- `RuiNelson/StreetsOfRageRecompilation` → `ai-analysis/game-engine-and-levels.md` (شاهد ثانویهٔ runtime، MIT).
- `RuiNelson/StreetsOfRageProject` (بدون license) — فقط ارجاع متقابل.
- `Dandaman955` Redux استفاده **نشد** (Bare Knuckle J؛ cross-reference ممنوع).

## Tools
- `tools/research/nemesis.py` (دیکدر)، `listing.py` (استخراج `dc.b/dc.w`)،
  `elc.py` (`parse_stream`, `walk_stream`, `parse_tail`)،
  `extract_stage01.py`، **جدید:** `stage01_tables.py`، **جدید:** `test_stage01.py` (۲۲ تست).

## Files
تولید/به‌روزرسانی‌شده:
`reports/stage01-control-flow.md`، `reports/stage01-elc-records.json` (۳۲۷ KB)،
`reports/stage01-boss-tail-analysis.md`، `reports/stage01-palette-descriptors.md` + `.json`،
`reports/stage01-evidence-ledger.json` (۲۰ ادعا + ۴ فرضیهٔ اصلاح‌شده)،
به‌روزرسانی `reports/reference-stage-01.md` (بخش ۱۲) و
`reports/reference-stage-01-evidence-ledger.json` (revision 2).

## Static Evidence
- `sub_436` (L595) → جدول ۱۲‌وردهٔ `off_44C` (L610)؛ چون lookup اول **byte** و جدول **word** است:
  `state = 2 × index`. نگاشت: `0`=EnemySpawn_Scene، `2`=loc_6A6، `4`=loc_784 (timed)،
  `6`/`8`/`A`=زنجیرهٔ deferred، `C`=loc_C28، **`E`=loc_59C (ورود boss)**، `10`=loc_748،
  `12`=Write_Art، `14`=loc_4CA، `16`=loc_464.
- `EnemySpawn_Scene` (L777): palette slot = `Scene+1` (L790‑793)؛ برای راندهای ۱–۴
  guard در `Scene >= 3` (L825) → `loc_646` → `$FFFB14 = $E`.
- `Load_Enemy_Into_RAM` (L1779) در شروع مرحله با `Scene = 0` سه ستون بلوک ۱ را spawn می‌کند؛
  در نتیجه بلوک‌های ۲/۳/۴ در Scene های 0/1/2 و بلوک ۴ آخرین wave معمولی است.
- تأیید مستقل: جدول descriptor هر راند ۵/۵/۵/۵/۷/۷/۷/۷ slot دارد = `guard + 2` و با تعداد
  بلوک‌های دیکد‌شده (۴/۴/۴/۴/۶/۶/۵/۶) هم‌خوان است.
- تأیید محتوایی: slot سوم راند ۱ تنها slotی است که palette set 9 را انتخاب می‌کند و فقط
  بلوک ۴ دارای type `$26` (Nora) است.
- **X:** `add.b d2,($FFFFFB12).w` روی *high byte* اثر می‌گذارد (big-endian)؛ پایه‌ها
  `$0300,$0400,…, $0E00` برای ۱۲ ستون. مدل قدیمی (ریست پایه در هر بلوک) رد شد.
- **Tail:** در راندهای ۱–۶ دنباله با گرامر timed آغاز می‌شود
  (`word delay + 6-byte record` … `$0099`) و اولین جفتِ هر راند delay=16 و type منطبق با
  boss همان راند در `$1C378` دارد. سپس یک section طول‌دار (مثل deferred) می‌آید.
- راند ۲ تنها دنباله‌ای است که کل بافر را دقیقاً مصرف می‌کند (۴۲ بایت).
- راند ۱: `00 10 → $56`، `00 10 → $D6`، `$0099`، `00 02 99 00` (section خالی)، سپس
  `6a 00` که **هیچ‌کدام از هشت مصرف‌کنندهٔ `Cur_ELC_Adr` آن را نمی‌خوانند** → UNKNOWN صریح.

## Runtime Evidence
هیچ اجرای واقعی انجام نشد (ROM/emulator در دسترس نیست). تنها شاهد runtime، **ثانویه** است:
یادداشت‌های autoplay در `RuiNelson/StreetsOfRageRecompilation` که دو غرفهٔ type‑`$11` را در
x = **2016** و **2920** ثبت کرده‌اند. مدل X این دو عدد را بدون استفاده از آن‌ها به‌عنوان ورودی
بازتولید می‌کند:
- `2016 = $7E0` → بلوک ۲، byte4 `$E0` (0x0700 | 0xE0)
- `2920 = $B68` → بلوک ۳، byte4 `$68` (0x0B00 | 0x68)

## Findings
1. **مسیر چهار بلوک روشن شد:** ۱ بلوک در شروع مرحله + ۳ بلوک با `EnemySpawn_Scene`
   در Scene های 0/1/2؛ guard در Scene=3 به state 7 می‌رود. بلوک ۴ معمولی است.
2. **`$E` یک state است، نه flag:** index 7 = `loc_59C` (palette/art مربوط به boss).
3. **مدل X اصلاح و اعتبارسنجی شد** (بالا).
4. **مکانیزم boss:** boss یک رکورد ۶‌بایتی عادی در یک timed list است که بعد از `loc_59C`
   با همان `loc_784` خوانده می‌شود؛ پارسر جداگانه‌ای وجود ندارد.
5. **جدول‌های palette:** ۸ root، اندازه‌های 46/46/46/46/62/62/50/62 بایت،
   منطق انتخاب از byte 4 (bit 7 = boss table، high nibble + 8 → `Pal_ID_Enemy`) و
   low nibble از byte 5 → `$FFFFFA6A`؛ بدون هیچ ادعای RGB.

## Confidence
| ادعا | کلاس |
| --- | --- |
| نگاشت state → target | VERIFIED_DIRECT |
| guard و مسیر بلوک ۴ | VERIFIED_DIRECT (کد) + STRONG_INFERENCE (مقدار Scene در زمان spawn) |
| مدل X | VERIFIED_DIRECT |
| تطابق 2016/2920 | VERIFIED_AGAINST_SECONDARY_RUNTIME |
| boss = timed record | STRONG_INFERENCE |
| tail راندهای ۷ و ۸ | UNKNOWN |
| RGB / sprite / انیمیشن | BLOCKED |

## Contradictions
- ادعای قبلی «byte 4 انتخاب‌کنندهٔ لبه است» **باطل** شد: byte 5 لبه را انتخاب می‌کند و
  byte 4 به `+$15` می‌رود (E012).
- ادعای قبلی «`$E` یک boss flag است» باطل شد (E005/E006).
- ادعای قبلی «بلوک ۴ نامشخص است چون guard در Scene>=3 است» حل شد: guard گذارها را می‌شمارد.
- **باقی‌ماندهٔ واقعی:** راند ۸ geometry index ۴ را انتخاب می‌کند در حالی که `word_1C1BC`
  فقط دو ورودی دارد؛ slotهای ۱ و ۶ راند ۷ alias هستند؛ دنبالهٔ راند ۷ با `FF FF…` شروع می‌شود.

## Blocked
- اجرای ROM/emulator → همهٔ ادعاهای runtime (به‌جز شاهد ثانویه) BLOCKED.
- مقادیر RGB و رنگ‌ها: عمداً تفسیر نشد.
- sprite/animation: نیازمند دادهٔ گرافیکی و اجرا.

## Next Experiment
1. اگر emulator/ROM فراهم شد: trace مقدار `Scene` در فریم spawn هر بلوک + خواندن `$FFFB12`.
2. حل ابهام geometry index ۴ در راند ۸ (بررسی توسعهٔ جدول یا مسیر جایگزین).
3. تلاش برای یافتن مصرف‌کنندهٔ `$6A`/دنبالهٔ راند ۷ و ۸ (احتمالاً مسیر ویژهٔ Level 7).
4. استخراج محتوای ۱۲ ورودی `Pal_Alt_Enemy` و اتصال type → palette به‌صورت کامل.
5. ساخت `reports/stage01/timeline.csv` نهایی از `stage01-elc-records.json`.

## Acceptance
- هر بایت راند ۱ یا parse شده یا صریحاً unresolved است: **PASS**
  (`walk_stream` + `segments_cover` + `leftover` در تست‌ها).
- نگاشت Scene/block قابل ردیابی یا صریحاً unresolved: **PASS** (با برچسب STRONG_INFERENCE).
- چارچوب boss-tail تا حد پشتیبانی‌شده برقرار است: **PASS** (راندهای ۱–۶؛ ۷/۸ UNKNOWN).
- تست‌های decoded-data قبلی و جدید: **PASS** (`22 tests OK`).
- بدون ادعای runtime/RGB/sprite: **PASS**.

## وضعیت تفکیک‌شده
**COMPLETED-AND-VERIFIED:** state machine؛ block→scene؛ مدل X؛ اندازه و slotهای جدول‌های palette؛
byte-accounting هر هشت stream؛ تست‌ها.
**IMPLEMENTED-BUT-NOT-FULLY-VERIFIED:** نگاشت boss type ↔ boss art (STRONG_INFERENCE)؛
معنای semantic فیلد `Pal_Correct`.
**BLOCKED-OR-NOT-IMPLEMENTED:** تأیید runtime مقدار Scene؛ RGB؛ گرافیک؛ دنبالهٔ راندهای ۷ و ۸.
