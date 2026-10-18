#!/usr/bin/env python3
"""شبیه‌سازی مقایسه‌ای: فرمول نهایی v2.2 (ظرفیت‌محور) در برابر فرمول اصلی رتبه‌لند (۴۷ ساعت/۴۹۵ تست ثابت).

مدل (ساده، شفاف، قطعی با نویز seed دار):
- ۴ درس تجربی با ضرایب w: زیست ۱۲، شیمی ۹، ریاضی ۸، فیزیک ۶.
- هر درس استخر لقمه دارد (از راهبردی ماز، فرض ۳۳ هفته تا کنکور تیر ۱۴۰۶).
- تسلط هر لقمه m∈[0,1]: مطالعهٔ تازه m0=0.55؛ زنگ تست +0.22؛ مرور m→m+0.45(1−m).
- فراموشی: بدون تماس، m *= exp(-Δt/S)، S با هر مرور/تست رشد می‌کند (فاصله‌گذاری).
- درصد درس = میانگین m روی لقمه‌های بودجهٔ آزمون × مهارت تست (لجستیک با تجمع تست).
- پایبندی: اگر برنامه > ظرفیت موجود، adherence افت می‌کند و خستگی انباشته ظرفیت را ۵٪/هفته کم می‌کند.
- رتبه‌لند: تخصیص ثابت (زیست ۱۵/ریاضی ۱۱/فیزیک ۱۲/شیمی ۹ ساعت؛ ۱۲۰/۱۵۰/۱۵۰/۷۵ تست)،
  بدون مرور فاصله‌دار صریح، بدون بافر، بدون رمپ.
- v2.2: H_core از ظرفیت با رمپ ≤+۵ ساعت/هفته، تخصیص C'×S با S بازخوردی از درصد آزمون،
  مرور صریح (هفتهٔ بعد + ۳ هفته بعد)، بافر/جبرانی، تست ۱۵/۲۰ هر زنگ.

خروجی: جدول سناریوها به stdout + markdown.
"""
import math
import random
import json

W = {"زیست": 12, "شیمی": 9, "ریاضی": 8, "فیزیک": 6}
SUBS = list(W)
WEEKS = 33
LOQME = {"زیست": 44, "ریاضی": 40, "فیزیک": 40, "شیمی": 42}   # فرض از راهبردی ۹صفحه‌ای ماز
BUDGET_SHARE = [i / WEEKS for i in range(1, WEEKS + 1)]       # بودجهٔ تجمعی خطی راهبردی


def make_state():
    return {s: {"m": [0.0] * LOQME[s], "stab": [2.0] * LOQME[s],
                "seen": [0] * LOQME[s], "tests": 0, "touched_week": [-99] * LOQME[s]}
            for s in SUBS}


def decay(st, wk):
    for s in SUBS:
        d = st[s]
        for i in range(LOQME[s]):
            if d["m"][i] > 0:
                d["m"][i] *= math.exp(-1.0 / max(0.3, d["stab"][i]))
            # لقمه‌های دیده‌نشده دست‌نخورده


def touch(d, i, kind, wk):
    if kind == "new":
        d["m"][i] = max(d["m"][i], 0.55)
        d["seen"][i] = max(d["seen"][i], 1)
    elif kind == "test":
        if d["seen"][i] == 0:
            d["m"][i] = max(d["m"][i], 0.55); d["seen"][i] = 1
        d["m"][i] = min(1.0, d["m"][i] + 0.22)
    elif kind == "rev":
        if d["seen"][i]:
            d["m"][i] = min(1.0, d["m"][i] + 0.45 * (1 - d["m"][i]))
    d["stab"][i] = min(16.0, d["stab"][i] + (1.5 if kind == "rev" else 0.9))
    d["touched_week"][i] = wk


def skill(d):
    t = d["tests"]
    return 0.60 + 0.40 * (1 - math.exp(-t / 900.0))


def exam_scores(st, wk):
    out = {}
    for s in SUBS:
        d = st[s]
        upto = min(LOQME[s], int(math.ceil(LOQME[s] * (wk / WEEKS))))  # بودجهٔ آزمون تا هفتهٔ wk
        ms = [d["m"][i] for i in range(upto)]
        cov = sum(1 for x in d["seen"][:upto] if x) / max(1, upto)
        out[s] = 100.0 * (sum(ms) / max(1, upto)) * skill(d) * (0.5 + 0.5 * cov)
    return out


def weighted(scores):
    return sum(W[s] * scores[s] for s in SUBS) / sum(W.values())


def adherence_model(planned, available, fatigue):
    if planned <= available * 1.02:
        return 0.95, fatigue
    over = planned / max(1e-6, available) - 1
    adh = max(0.45, 1 - 0.6 * over)
    fat = min(0.30, fatigue + 0.05)   # خستگی انباشته
    return adh, fat


def run(policy, F_week_raw, school_cut, lag_weeks=0, seed=7):
    rnd = random.Random(seed)
    st = make_state()
    fatigue = 0.0
    prev_H = 15.0                             # پایهٔ رمپ = H_core هفتهٔ قبل (شروع سبک)
    log = []
    for wk in range(1, WEEKS + 1):
        available = F_week_raw * (1 - school_cut) * (1 - fatigue)
        eff_wk = max(0, wk - lag_weeks)
        # ---- تولید برنامه ----
        if policy == "rankland":
            plan_h = {"زیست": 15, "ریاضی": 11, "فیزیک": 12, "شیمی": 9}
            plan_t = {"زیست": 120, "ریاضی": 150, "فیزیک": 150, "شیمی": 75}
            review_hours = {}
        else:
            net = max(0.0, 0.90 * (available - 4.0))           # T_finals اول کسر می‌شود
            H_core = min(prev_H + 5.0, math.floor(net / 1.25) * 1.25)  # رمپ ≤ +۵ روی هدف خالص
            levels = {}
            if wk > 1:
                sc = exam_scores(st, wk - 1)
                for s in SUBS:
                    levels[s] = 1.25 if sc[s] < 35 else (0.75 if sc[s] > 65 else 1.0)
            else:
                levels = {s: 1.0 for s in SUBS}
            Cp = {s: W[s] * levels[s] for s in SUBS}
            tot = sum(Cp.values())
            plan_h = {s: H_core * Cp[s] / tot for s in SUBS}
            plan_t = {}
            review_hours = {}
            for s in SUBS:
                bells = plan_h[s] / 1.25
                rev = sum(1 for i in range(LOQME[s])
                          if st[s]["seen"][i] and 0 < wk - st[s]["touched_week"][i] <= 3 and (wk - i % 3) % 2 == 0)
                rev_b = min(bells * 0.30, rev * 1.0)           # سقف ۳۰٪ زنگ‌ها مرور
                new_b = bells - rev_b
                review_hours[s] = rev_b * 1.25
                plan_t[s] = int((new_b * 15 + rev_b * 20) * 0.6)  # نسبت ۲:۳ → ۶۰٪ زنگ‌ها تست‌دار
        # کف تخصیص: هر درس حداقل ۲ زنگ در هفته (رفع starvation کم‌ساعت‌ها)
        if policy == "v2":
            for s_ in SUBS:
                plan_h[s_] = max(plan_h[s_], 2.5)
            tot_h = sum(plan_h.values())
            if tot_h > available * 0.95:      # کف را با ظرفیت آشتی بده
                k = (available * 0.95) / tot_h
                plan_h = {s_: v * k for s_, v in plan_h.items()}
        planned_total = sum(plan_h.values())
        adh, fatigue = adherence_model(planned_total, available, fatigue)
        exec_h = planned_total * adh * (0.97 + 0.06 * rnd.random())
        if policy == "v2":
            prev_H = sum(plan_h.values())
        # ---- اجرای هفته: تزریق زنگ‌ها به لقمه‌ها ----
        scale = exec_h / max(1e-6, planned_total)
        for s in SUBS:
            d = st[s]
            upto = min(LOQME[s], int(math.ceil(LOQME[s] * (eff_wk / WEEKS)))) if eff_wk > 0 else 0
            h_s = plan_h[s] * scale
            bells = h_s / 1.25
            rev_b = 0.0
            if policy == "v2":
                rev_b = (review_hours[s] / 1.25) * scale
                # مرور لقمه‌های تازه‌دیده‌شده
                cand = [i for i in range(upto) if d["seen"][i] and wk - d["touched_week"][i] >= 1]
                cand.sort(key=lambda i: d["m"][i])
                for k in range(int(rev_b)):
                    if cand:
                        touch(d, cand[k % len(cand)], "rev", wk)
            new_b = bells - rev_b
            fresh = [i for i in range(upto) if not d["seen"][i]]
            n_new = min(len(fresh), max(0, round(new_b / 2)))   # هر لقمهٔ تازه ≈ ۲ زنگ (مطالعه+تست)
            for i in fresh[:n_new]:
                touch(d, i, "new", wk)
                touch(d, i, "test", wk)
            extra_tests = int(new_b - 2 * n_new + (0 if policy == "v2" else bells))
            done_idx = [i for i in range(upto) if d["seen"][i]]
            if policy == "rankland":
                # تست ثابت هفتگی رتبه‌لند روی مباحث بودجه (بدون مرور فاصله‌دار)
                nt = int(plan_t[s] * scale)
                d["tests"] += nt
                if done_idx:
                    for k in range(nt):
                        i = done_idx[k % len(done_idx)]
                        d["m"][i] = min(1.0, d["m"][i] + 0.02 * (1 - d["m"][i]))
                        d["stab"][i] = min(16.0, d["stab"][i] + 0.03)
                        d["touched_week"][i] = wk
            else:
                nt = int(plan_t[s] * scale)
                d["tests"] += nt
                if done_idx:
                    for k in range(nt):
                        i = done_idx[rnd.randrange(len(done_idx))]
                        d["m"][i] = min(1.0, d["m"][i] + 0.02 * (1 - d["m"][i]))
                        d["stab"][i] = min(16.0, d["stab"][i] + 0.03)
                        d["touched_week"][i] = wk
        decay(st, wk)
        sc = exam_scores(st, wk)
        log.append({"week": wk, "exec_h": round(exec_h, 1), "adh": round(adh, 2),
                    "fat": round(fatigue, 2), "wscore": round(weighted(sc), 1),
                    "tests": sum(st[s]["tests"] for s in SUBS),
                    "pct": {s: round(sc[s], 1) for s in SUBS}})
    fin = exam_scores(st, WEEKS)
    cov = {s: round(100 * sum(1 for x in st[s]["seen"] if x) / LOQME[s], 1) for s in SUBS}
    return {"final_pct": {s: round(fin[s], 1) for s in SUBS},
            "weighted_score": round(weighted(fin), 2), "coverage": cov,
            "total_tests": sum(st[s]["tests"] for s in SUBS),
            "burnout_weeks": sum(1 for r in log if r["fat"] > 0.05),
            "avg_exec_h": round(sum(r["exec_h"] for r in log) / WEEKS, 1),
            "log": log}


SCENARIOS = [
    ("مدرسه‌ای (۸٫۵ س/روز، کسر ۲۵٪ مدرسه/عمومی)", 59.5, 0.25, 0),
    ("پشت‌کنکوری (۱۳٫۵ س/روز، کسر ۱۰٪)", 94.5, 0.10, 0),
    ("مدرسه‌ای با یک ماه تأخیر از راهبردی", 59.5, 0.25, 4),
    ("ضعیف (۵ س/روز واقعی، مدرسه‌ای خسته)", 42.0, 0.25, 0),
]

rows = []
for name, F, cut, lag in SCENARIOS:
    a = run("rankland", F, cut, lag)
    b = run("v2", F, cut, lag)
    rows.append((name, a, b))
    print(f"\n=== {name} ===")
    for tag, r in (("رتبه‌لند", a), ("v2.2", b)):
        print(f"{tag:8s} score={r['weighted_score']:6.2f}  tests={r['total_tests']:6d}  "
              f"exec={r['avg_exec_h']:5.1f}h/wk  burnout={r['burnout_weeks']:2d}  "
              f"pct={r['final_pct']}")
        print(f"         coverage={r['coverage']}")

json.dump({n: {"rankland": {k: v for k, v in a.items() if k != 'log'},
               "v2": {k: v for k, v in b.items() if k != 'log'}} for n, a, b in rows},
          open("outputs/validation-sim.json", "w"), ensure_ascii=False, indent=1)
print("\nsaved -> outputs/validation-sim.json")
