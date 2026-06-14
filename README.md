# סוכן מניות (Stock Agent)

סוכן **חינמי** לסריקת מניות אמריקאיות, בנוי במודולים. סורק רשימת מעקב מדי יום,
מעניק לכל מניה ציון 0–100, מזהה מועמדים לפריצה, מייצא ל‑CSV/Excel, שולח התראות
ומגיש לוח בקרה ב‑Streamlit. הנתונים מגיעים מ‑yfinance (Yahoo Finance) — **ללא
ממשקי API בתשלום**. הפלט למשתמש בעברית; תאריכים בפורמט DD/MM/YYYY.

## ארכיטקטורה

```
stock-agent/
├── run.py              # תזמורת יומית (נקודת כניסה)
├── config.py           # כל הספים, הנתיבים, דגלי תכונות ותוויות עברית
├── data_loader.py      # טעינת OHLCV משותפת מ‑yfinance
├── watchlist.txt       # מניות, אחת בכל שורה
├── data/               # פלטים: results.csv/.xlsx (אחרון), alerts.log
│   └── outputs/         # סט קבצים מתוארך + "latest" מכל הרצה (ראו "קבצי פלט")
├── market.py           # מדדי שוק, ETF סקטורים, ציון מצב שוק (yfinance)
├── charts.py           # גרפי sparkline למייל/דוחות (matplotlib)
├── indicators/         # ממוצעים, RSI, נפח, מדדי שיא 52 שבועות
├── scanners/           # מזהי תבניות (פריצה)
├── ranking_engine/     # ניקוד 0–100 + פרשנות + תתי-ציונים (factor_scores)
├── fundamentals/       # נתונים פונדמנטליים (כבוי כברירת מחדל)
├── news/               # כותרות חדשות + ציון סנטימנט
├── alerts/             # התראות למסוף/לוג + מייל
├── backtesting/        # בדיקת אות היסטורית (תשואה עתידית)
├── proprietary.py      # מדדים קנייניים מחושבים (Fear&Greed, Breadth, Capital Flow, Upside, Confidence)
├── portfolio.py        # ניתוח תיק (Phase 7) + portfolio.csv (ההחזקות שלך)
├── explain.py          # הסברי הזדמנות (למה כן/לא, קטליזטורים, סיכונים)
├── events.py           # אירועים (דוחות, שינויי דירוג) מ-yfinance
├── insights.py         # תובנות AI יומיות בעברית (מבוסס כללים)
├── alerts/center.py    # מרכז התראות (פריצה/נפח/דוחות/דירוג/רוטציה)
├── assistant.py        # עוזר חכם חינמי (שו"ת בעברית על הנתונים, ללא API)
└── dashboard/          # ממשק Streamlit Pro (תֵמה כהה, Plotly, RTL)
    ├── app.py          #   הלוח האינטראקטיבי (כולל עמוד "🤖 עוזר" + כפתור רענון)
    ├── theme.py        #   CSS כהה + עזרי Plotly
    └── index.html      #   תמונת מצב סטטית (נוצרת בכל הרצה)
```

זרימת הנתונים בכיוון אחד: `data_loader → indicators → scanners + ranking_engine
→ ייצוא → התראות`. כל מודול עצמאי וניתן לייבוא בנפרד.

## קבצי פלט

כל הרצה כותבת ל‑`data/outputs/` סט קבצים מלא עם חותמת זמן (`YYYY-MM-DD_HHMM`):

| קובץ | מה הוא מכיל |
|---|---|
| `daily_report_<ts>.html` | הדוח המלא בעברית, עצמאי (גרפים מוטמעים) — נפתח בכל דפדפן |
| `daily_report_<ts>.xlsx` | כל תוצאות הסריקה כטבלת Excel |
| `opportunities_<ts>.csv` | רק המניות החיוביות (🟢) — ההזדמנויות של היום |
| `alerts_<ts>.csv` | ההתראות שנשלחו באותה הרצה |
| `backtest_summary_<ts>.xlsx` | ביצועי אות הפריצה בעבר (אחוז הצלחה, תשואה ממוצעת) |

בנוסף, `data/results.csv` ו‑`data/results.xlsx` תמיד מכילים את הסריקה **האחרונה**
(לוח הבקרה קורא מהם).

## התקנה

```bash
cd stock-agent
pip install -r requirements.txt
```

## שימוש

**סריקה יומית** (כותבת `data/results.csv` + `.xlsx`, רושמת התראות, מדפיסה סיכום
בעברית):
```bash
python run.py
```

**לוח בקרה** — קליק כפול על **"סוכן מניות"** בשולחן העבודה (קיצור דרך), או:
```bash
streamlit run dashboard/app.py
```
הלוח מציג כל מניה עם סטטוס צבעוני (🟢/🟡/🔴), הסבר בעברית פשוטה, גרף מחיר,
ושורה תחתונה — מקובץ לפי חיוביות / למעקב / להימנעות.

**בדיקת אות הפריצה (Backtest)** על מניות נבחרות:
```bash
python backtesting/backtester.py AAPL MSFT NVDA
```

## התראות מייל (Gmail)

כשמתגלה מועמד לפריצה, הסוכן שולח **מייל סיכום ב‑HTML (RTL)** עם טבלת המועמדים
וחמשת המובילים. אם המייל לא מוגדר — השליחה פשוט מדלגת, והסריקה ממשיכה כרגיל.

**הגדרה (Gmail):**

1. ב‑Google: הפעל אימות דו‑שלבי, ואז צור **App Password** ב‑
   *Google Account → Security → App passwords* (16 תווים).
2. מלא את הפרטים ב‑[email_config.json](email_config.json):
   ```json
   {
     "smtp_host": "smtp.gmail.com",
     "smtp_port": 587,
     "sender": "you@gmail.com",
     "app_password": "סיסמת-האפליקציה-בת-16-התווים",
     "recipient": "you@gmail.com"
   }
   ```
   הקובץ מוחרג ב‑`.gitignore` כדי שהסיסמה לא תישמר בגרסאות.
   לחלופין אפשר משתני סביבה: `STOCK_AGENT_EMAIL_SENDER`,
   `STOCK_AGENT_EMAIL_PASSWORD`, `STOCK_AGENT_EMAIL_RECIPIENT`.

**בדיקת שליחה** (שולח מייל בדיקה אם ההגדרות תקינות):
```bash
python -c "import sys; sys.path.insert(0,'.'); from alerts.email_notifier import EmailNotifier; EmailNotifier().send('בדיקה — סוכן מניות', '<div dir=rtl>זו הודעת בדיקה ✔</div>', 'בדיקה')"
```

ההרצה האוטומטית היומית כבר משתמשת ב‑`run.py`, אז ברגע שתגדיר את המייל —
ההתראות יישלחו אוטומטית בכל בוקר שבו יימצא מועמד לפריצה.

## הרצה אוטומטית יומית (Windows Task Scheduler)

הוגדרה משימה בשם **`StockAgentDaily`** שמריצה את הסוכן אוטומטית **שני–שישי
בשעה 09:00** (שעון ישראל). היא מריצה את [run_daily.bat](run_daily.bat), שמתעד
כל ריצה עם חותמות זמן אל `data/daily_run.log`.

פקודות ניהול (PowerShell):
```powershell
# צפייה במצב המשימה
Get-ScheduledTask -TaskName "StockAgentDaily"

# הרצה ידנית עכשיו (בדיקה)
Start-ScheduledTask -TaskName "StockAgentDaily"

# השבתה / הפעלה מחדש
Disable-ScheduledTask -TaskName "StockAgentDaily"
Enable-ScheduledTask  -TaskName "StockAgentDaily"

# שינוי שעת ההרצה (למשל ל‑08:00)
$t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 8:00am
Set-ScheduledTask -TaskName "StockAgentDaily" -Trigger $t

# מחיקת המשימה
Unregister-ScheduledTask -TaskName "StockAgentDaily" -Confirm:$false
```

> הערה: המשימה רצה כשהמחשב דולק והמשתמש מחובר. אם המחשב היה כבוי בשעת היעד,
> ההגדרה `StartWhenAvailable` תריץ אותה בהזדמנות הראשונה לאחר מכן.

## הגדרות

כל מה שניתן לכוונן נמצא ב‑[config.py](config.py):

- ספי פריצה (`NEAR_HIGH_PCT`, `VOLUME_SPIKE`, `RSI_MIN/MAX`)
- `ENABLE_FUNDAMENTALS` — כבוי כברירת מחדל (קריאות `.info` לכל מניה איטיות);
  הפעלה מוסיפה עמודות שווי שוק / מכפיל / שולי רווח / צמיחה / סקטור לייצוא.
- `ENABLE_NEWS` — כותרות חדשות עבור מועמדי הפריצה בלוג ההתראות.

## תבחיני פריצה

מניה מסומנת כמועמדת לפריצה כאשר **כל** התנאים מתקיימים:

- מחיר מעל ממוצע 50 יום
- מחיר מעל ממוצע 200 יום
- בטווח 10% משיא 52 השבועות
- נפח גבוה פי 1.5 לפחות מהנפח הממוצע ל‑20 יום
- RSI בין 50 ל‑75

## הערות

- הנתונים משקפים את **יום המסחר הנוכחי** כשהוא זמין (Yahoo כולל את הנר האחרון,
  גם אם חלקי, כל עוד השוק פתוח).
- תאריכים בפורמט DD/MM/YYYY.
- לצרכי מידע בלבד — אין לראות בכך ייעוץ השקעות.
