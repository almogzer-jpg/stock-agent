# העלאת הלוח לענן (גישה מכל טלפון בעולם)

מדריך צעד‑אחר‑צעד להעלאת **Stock Agent Pro** ל‑Streamlit Community Cloud (חינמי).
התוצאה: קישור קבוע כמו `https://stock-agent-XXXX.streamlit.app` שעובד מכל טלפון,
בלי תלות במחשב שלך.

> הכל כבר מוכן בצד הקוד: הלוח מייצר את הנתונים בעצמו בענן, וסיסמת המייל מוחרגת
> ולא תעלה לאינטרנט.

---

## שלב 1 — צור מאגר (repository) ב‑GitHub
1. היכנס ל‑https://github.com → לחץ **New repository** (כפתור ירוק / סימן +).
2. שם: למשל `stock-agent`.
3. בחר **Private** (מומלץ — שהקוד יישאר פרטי).
4. **אל תסמן** "Add a README" (כבר יש לנו קבצים).
5. לחץ **Create repository**. תקבל כתובת כמו:
   `https://github.com/USERNAME/stock-agent.git` — העתק אותה.

## שלב 2 — העלה את הקוד (פעם אחת)
פתח טרמינל בתיקייה `C:\claude\stock-agent` והרץ (החלף את הכתובת בשלך):
```bash
git remote add origin https://github.com/USERNAME/stock-agent.git
git push -u origin main
```
ייתכן שתתבקש להתחבר ל‑GitHub (חלון דפדפן / שם משתמש + טוקן). זה חד‑פעמי.

> 💡 אני יכול להריץ עבורך את שלב 2 — רק תן לי את כתובת המאגר שיצרת, ואשר לי לדחוף.

## שלב 3 — חבר ל‑Streamlit Cloud
1. היכנס ל‑https://share.streamlit.io
2. לחץ **Sign in with GitHub** ואשר את ההרשאה.
3. לחץ **Create app** → **Deploy a public app from GitHub** (גם עבור repo פרטי).
4. מלא:
   - **Repository:** `USERNAME/stock-agent`
   - **Branch:** `main`
   - **Main file path:** `dashboard/app.py`  ← חשוב!
5. לחץ **Deploy**. ההתקנה לוקחת 1–3 דקות.
6. בפתיחה הראשונה הלוח מריץ סריקה ראשונית (~דקה) ואז מציג הכל.

## שלב 4 — הגבלת גישה (פרטיות)
ב‑Streamlit Cloud → **Settings → Sharing** אפשר להגדיר שרק כתובות מייל
מאושרות (שלך) יוכלו לצפות. מומלץ.

## שלב 5 — פתח בטלפון
העתק את הקישור (`https://...streamlit.app`) ושלח לעצמך. שמור אותו כסימנייה /
"הוסף למסך הבית" — והלוח זמין כמו אפליקציה. 📱

---

## הערות
- **מיילים ותזמון יומי נשארים במחשב שלך** (התזמון של 09:00). הענן הוא לצפייה +
  כפתור "רענן נתונים".
- כפתור **🔄 רענן נתונים** עובד גם בענן — מושך מחירים עדכניים מ‑Yahoo.
- סיסמת המייל **לא** מועלית (מוחרגת ב‑`.gitignore`). אם תרצה מיילים גם מהענן,
  שמים את הפרטים תחת **Settings → Secrets** (לא בקוד).
