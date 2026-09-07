"""
IxlosJarimabot uchun FastAPI server:
- Telegram MiniApp uchun statik fayllarni beradi (/app, /admin)
- REST API: o'qituvchilar, jarima turlari, jarimalar, hisobotlar, adminlar
"""
import os
import sys
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from bot import database as db
from bot import reports
from webapp.telegram_auth import validate_init_data

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPER_ADMIN_IDS = [int(x) for x in os.getenv("SUPER_ADMIN_IDS", "").split(",") if x.strip().isdigit()]
DEV_MODE = os.getenv("DEV_MODE", "0") == "1"  # localda brauzerda sinash uchun (initData tekshiruvsiz)

app = FastAPI(title="IxlosJarimabot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")

db.init_db(super_admin_ids=SUPER_ADMIN_IDS)


# ------------------------------------------------------------- yordamchi: foydalanuvchini tekshirish
def get_auth_user(x_init_data: str = Header(default="")):
    if DEV_MODE:
        return {"id": SUPER_ADMIN_IDS[0] if SUPER_ADMIN_IDS else 0, "first_name": "Dev"}
    ok, user = validate_init_data(x_init_data, BOT_TOKEN)
    if not ok or not user:
        raise HTTPException(status_code=401, detail="Telegram autentifikatsiyasi muvaffaqiyatsiz")
    return user


def require_admin(x_init_data: str = Header(default="")):
    user = get_auth_user(x_init_data)
    if not db.is_admin(user["id"]):
        raise HTTPException(status_code=403, detail="Faqat administratorlar uchun")
    return user


# ------------------------------------------------------------- statik sahifalar
@app.get("/app")
async def serve_app():
    return FileResponse(os.path.join(STATIC_DIR, "app.html"))


@app.get("/admin")
async def serve_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ------------------------------------------------------------- Teachers
@app.get("/api/teachers")
async def api_list_teachers(x_init_data: str = Header(default="")):
    get_auth_user(x_init_data)
    return db.list_teachers(only_active=True)


class TeacherIn(BaseModel):
    full_name: str
    position: str = ""
    phone: str = ""


@app.post("/api/admin/teachers")
async def api_add_teacher(t: TeacherIn, x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    tid = db.add_teacher(t.full_name.strip(), t.position.strip(), t.phone.strip())
    return {"id": tid}


class TeacherUpdate(BaseModel):
    full_name: str | None = None
    position: str | None = None
    phone: str | None = None
    active: int | None = None


@app.put("/api/admin/teachers/{teacher_id}")
async def api_update_teacher(teacher_id: int, t: TeacherUpdate, x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    db.update_teacher(teacher_id, t.full_name, t.position, t.phone, t.active)
    return {"ok": True}


@app.delete("/api/admin/teachers/{teacher_id}")
async def api_delete_teacher(teacher_id: int, x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    db.delete_teacher(teacher_id)
    return {"ok": True}


@app.get("/api/admin/teachers")
async def api_admin_list_teachers(x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    return db.list_teachers(only_active=False)


# ------------------------------------------------------------- Fine types
@app.get("/api/fine-types")
async def api_list_fine_types(x_init_data: str = Header(default="")):
    get_auth_user(x_init_data)
    return db.list_fine_types(only_active=True)


class FineTypeIn(BaseModel):
    name: str
    amount: int


@app.post("/api/admin/fine-types")
async def api_add_fine_type(ft: FineTypeIn, x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    fid = db.add_fine_type(ft.name.strip(), ft.amount)
    return {"id": fid}


class FineTypeUpdate(BaseModel):
    name: str | None = None
    amount: int | None = None
    active: int | None = None


@app.put("/api/admin/fine-types/{ft_id}")
async def api_update_fine_type(ft_id: int, ft: FineTypeUpdate, x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    db.update_fine_type(ft_id, ft.name, ft.amount, ft.active)
    return {"ok": True}


@app.delete("/api/admin/fine-types/{ft_id}")
async def api_delete_fine_type(ft_id: int, x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    db.delete_fine_type(ft_id)
    return {"ok": True}


@app.get("/api/admin/fine-types")
async def api_admin_list_fine_types(x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    return db.list_fine_types(only_active=False)


# ------------------------------------------------------------- Fines (jarima kiritish)
class FineIn(BaseModel):
    teacher_id: int
    fine_type_id: int
    amount: int | None = None  # berilmasa fine_type default summasi olinadi
    comment: str = ""


@app.post("/api/fines")
async def api_add_fine(f: FineIn, x_init_data: str = Header(default="")):
    user = get_auth_user(x_init_data)
    ft = db.get_fine_type(f.fine_type_id)
    if not ft:
        raise HTTPException(status_code=404, detail="Jarima turi topilmadi")
    teacher = db.get_teacher(f.teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="O'qituvchi topilmadi")
    amount = f.amount if f.amount is not None else ft["amount"]
    fine_id = db.add_fine(f.teacher_id, f.fine_type_id, amount, user["id"], f.comment.strip())
    return {"id": fine_id, "amount": amount, "teacher_name": teacher["full_name"], "fine_type_name": ft["name"]}


@app.get("/api/fines/recent")
async def api_recent_fines(limit: int = 50, x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    return db.get_recent_fines(limit)


class FineUpdate(BaseModel):
    teacher_id: int | None = None
    fine_type_id: int | None = None
    amount: int | None = None
    comment: str | None = None


@app.put("/api/admin/fines/{fine_id}")
async def api_update_fine(fine_id: int, f: FineUpdate, x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    db.update_fine(fine_id, f.teacher_id, f.fine_type_id, f.amount, f.comment)
    return {"ok": True}


@app.delete("/api/admin/fines/{fine_id}")
async def api_delete_fine(fine_id: int, x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    db.delete_fine(fine_id)
    return {"ok": True}


# ------------------------------------------------------------- Admins
class AdminIn(BaseModel):
    chat_id: int
    full_name: str = ""


@app.get("/api/admin/admins")
async def api_list_admins(x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    return db.list_admins()


@app.post("/api/admin/admins")
async def api_add_admin(a: AdminIn, x_init_data: str = Header(default="")):
    user = get_auth_user(x_init_data)
    if not db.is_super_admin(user["id"]):
        raise HTTPException(status_code=403, detail="Faqat bosh administrator yangi admin qo'sha oladi")
    db.add_admin(a.chat_id, a.full_name)
    return {"ok": True}


@app.delete("/api/admin/admins/{chat_id}")
async def api_remove_admin(chat_id: int, x_init_data: str = Header(default="")):
    user = get_auth_user(x_init_data)
    if not db.is_super_admin(user["id"]):
        raise HTTPException(status_code=403, detail="Faqat bosh administrator admin huquqini olib tashlay oladi")
    db.remove_admin(chat_id)
    return {"ok": True}


@app.get("/api/me")
async def api_me(x_init_data: str = Header(default="")):
    user = get_auth_user(x_init_data)
    return {
        "id": user["id"],
        "first_name": user.get("first_name", ""),
        "is_admin": db.is_admin(user["id"]),
        "is_super_admin": db.is_super_admin(user["id"]),
    }


# ------------------------------------------------------------- Reports
@app.get("/api/admin/reports/summary")
async def api_report_summary(period: str, year: int | None = None, month: int | None = None,
                              x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    start, end, label = reports.period_range(period, year=year, month=month)
    summary = db.summary_by_teacher(start, end)
    total = sum(s["total"] for s in summary)
    count = sum(s["cnt"] for s in summary)
    return {"label": label, "summary": summary, "total": total, "count": count}


@app.get("/api/admin/reports/download")
async def api_report_download(period: str, year: int | None = None, month: int | None = None,
                                x_init_data: str = Header(default="")):
    require_admin(x_init_data)
    fpath, label, total, count = reports.build_excel_report(period, year=year, month=month)
    return FileResponse(fpath, filename=os.path.basename(fpath),
                         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
