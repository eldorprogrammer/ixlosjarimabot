"""
Hisobotlarni (kunlik/haftalik/oylik/yillik) hisoblash va Excel fayl sifatida
generatsiya qilish moduli.
"""
import os
import calendar
from datetime import datetime, date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from . import database as db

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)


def period_range(period: str, ref: date = None, year: int = None, month: int = None):
    """
    period: 'today' | 'week' | 'month' | 'year' | 'month_pick' (year+month berilganda)
    Qaytaradi: (start_dt, end_dt, label)
    """
    ref = ref or date.today()
    if period == "today":
        start = datetime(ref.year, ref.month, ref.day)
        end = start + timedelta(days=1)
        label = f"{ref.strftime('%d.%m.%Y')} — kunlik hisobot"
    elif period == "week":
        start_day = ref - timedelta(days=ref.weekday())
        start = datetime(start_day.year, start_day.month, start_day.day)
        end = start + timedelta(days=7)
        label = f"{start_day.strftime('%d.%m.%Y')} - {(start_day + timedelta(days=6)).strftime('%d.%m.%Y')} — haftalik hisobot"
    elif period == "month":
        start = datetime(ref.year, ref.month, 1)
        last_day = calendar.monthrange(ref.year, ref.month)[1]
        end = datetime(ref.year, ref.month, last_day) + timedelta(days=1)
        label = f"{ref.strftime('%B %Y')} — oylik hisobot"
    elif period == "month_pick":
        y, m = year, month
        start = datetime(y, m, 1)
        last_day = calendar.monthrange(y, m)[1]
        end = datetime(y, m, last_day) + timedelta(days=1)
        label = f"{start.strftime('%B %Y')} — oylik hisobot"
    elif period == "year":
        y = year or ref.year
        start = datetime(y, 1, 1)
        end = datetime(y + 1, 1, 1)
        label = f"{y} — yillik hisobot"
    else:
        raise ValueError("Noto'g'ri period turi")
    return start, end, label


UZ_MONTHS = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
    7: "Iyul", 8: "Avgust", 9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr",
}


def build_excel_report(period: str, ref: date = None, year: int = None, month: int = None) -> str:
    start, end, label = period_range(period, ref=ref, year=year, month=month)
    fines = db.get_fines_between(start, end)
    summary = db.summary_by_teacher(start, end)

    wb = Workbook()

    # ---- Sheet 1: umumiy (o'qituvchi bo'yicha jamlama) ----
    ws1 = wb.active
    ws1.title = "Jamlama"
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    title_font = Font(bold=True, size=14, color="1F4E78")
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws1.merge_cells("A1:D1")
    ws1["A1"] = f"IxlosJarimabot — {label}"
    ws1["A1"].font = title_font
    ws1["A1"].alignment = Alignment(horizontal="center")

    headers = ["№", "O'qituvchi / Xodim", "Jarimalar soni", "Umumiy summa (so'm)"]
    for col, h in enumerate(headers, start=1):
        c = ws1.cell(row=3, column=col, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center")
        c.border = border

    total_all = 0
    row = 4
    for i, s in enumerate(summary, start=1):
        ws1.cell(row=row, column=1, value=i).border = border
        ws1.cell(row=row, column=2, value=s["teacher_name"]).border = border
        ws1.cell(row=row, column=3, value=s["cnt"]).border = border
        ws1.cell(row=row, column=4, value=s["total"]).border = border
        total_all += s["total"]
        row += 1

    row += 1
    ws1.cell(row=row, column=2, value="JAMI:").font = Font(bold=True)
    ws1.cell(row=row, column=4, value=total_all).font = Font(bold=True)

    widths = [5, 34, 16, 20]
    for i, w in enumerate(widths, start=1):
        ws1.column_dimensions[get_column_letter(i)].width = w

    # ---- Sheet 2: batafsil ro'yxat ----
    ws2 = wb.create_sheet("Batafsil")
    headers2 = ["№", "Sana", "O'qituvchi / Xodim", "Lavozim", "Jarima turi", "Summa (so'm)", "Izoh"]
    for col, h in enumerate(headers2, start=1):
        c = ws2.cell(row=1, column=col, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center")
        c.border = border

    for i, f in enumerate(fines, start=1):
        dt = datetime.fromisoformat(f["created_at"])
        ws2.cell(row=i + 1, column=1, value=i).border = border
        ws2.cell(row=i + 1, column=2, value=dt.strftime("%d.%m.%Y %H:%M")).border = border
        ws2.cell(row=i + 1, column=3, value=f["teacher_name"]).border = border
        ws2.cell(row=i + 1, column=4, value=f.get("teacher_position") or "").border = border
        ws2.cell(row=i + 1, column=5, value=f["fine_type_name"]).border = border
        ws2.cell(row=i + 1, column=6, value=f["amount"]).border = border
        ws2.cell(row=i + 1, column=7, value=f.get("comment") or "").border = border

    widths2 = [5, 18, 30, 18, 22, 16, 24]
    for i, w in enumerate(widths2, start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    fname = f"hisobot_{period}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx"
    fpath = os.path.join(EXPORTS_DIR, fname)
    wb.save(fpath)
    return fpath, label, total_all, len(fines)
