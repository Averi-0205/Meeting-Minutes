import hashlib
import json
import os
import re
import base64
from pathlib import Path
from datetime import datetime
import calendar

import streamlit as st
import requests

st.set_page_config(page_title="经营例会看板", layout="wide")

SUPABASE_URL = "https://fkqmidohkperokttcbjx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZrcW1pZG9oa3Blcm9rdHRjYmp4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE1NTEyNTAsImV4cCI6MjA5NzEyNzI1MH0.Ywh57DQpZ49OjPpvqpaqzY2jOEgPVbh6QB9Tw-AdP3k"
SB_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZrcW1pZG9oa3Blcm9rdHRjYmp4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTU1MTI1MCwiZXhwIjoyMDk3MTI3MjUwfQ.p2DXY5NVhBX7Qs77bbyoV9mRL155-6QWd3ADG9ZvznY"
STORAGE_HEADERS = {"apikey": SB_SERVICE_KEY, "Authorization": "Bearer " + SB_SERVICE_KEY}
SB_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY, "Content-Type": "application/json"}
SALT = "meeting_board_2026"

def _hash_pw(pw):
    return hashlib.sha256((SALT + pw).encode()).hexdigest()

def get_user(account):
    try:
        r = requests.get(SUPABASE_URL + "/rest/v1/users", headers=SB_HEADERS, params={"account": "eq." + account}, timeout=10)
        if r.status_code == 200 and r.json():
            return r.json()[0]
    except Exception:
        pass
    return None

def verify_password(account, password):
    user = get_user(account)
    if not user:
        return None
    if _hash_pw(password) == user["password_hash"]:
        return user
    return None

def change_pw(account, new_password):
    try:
        r = requests.patch(SUPABASE_URL + "/rest/v1/users", headers=SB_HEADERS, params={"account": "eq." + account}, json={"password_hash": _hash_pw(new_password)}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def get_all_users():
    try:
        r = requests.get(SUPABASE_URL + "/rest/v1/users", headers=SB_HEADERS, params={"select": "account,name,is_admin,can_delete,can_download,categories"}, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

MEETINGS_DIR = Path(__file__).parent / "meetings"

def scan_meeting_files():
    if not MEETINGS_DIR.exists():
        return []
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.html$")
    files = []
    for fi in MEETINGS_DIR.iterdir():
        if fi.is_file():
            m = pattern.match(fi.name)
            if m:
                files.append({"date": m.group(1), "category": m.group(2), "filename": fi.name})
    files.sort(key=lambda x: x["date"])
    return files

def load_html_content_raw(filename):
    fp = MEETINGS_DIR / filename
    return fp.read_text(encoding="utf-8") if fp.exists() else None

def delete_from_github(filename):
    try:
        r = requests.delete(SUPABASE_URL.replace("https://", "https://") + "/storage/v1/object/meetings/" + filename, headers=STORAGE_HEADERS, timeout=30)
        if r.status_code in (200, 204):
            return True, "已删除"
        return False, "Supabase 删除失败: " + str(r.status_code)
    except Exception as e:
        return False, "网络错误: " + str(e)

def upload_to_github(filename, content_bytes):
    try:
        r = requests.post(SUPABASE_URL.replace("https://", "https://") + "/storage/v1/object/meetings/" + filename,
            headers={"apikey": SB_SERVICE_KEY, "Authorization": "Bearer " + SB_SERVICE_KEY, "Content-Type": "text/html"},
            data=content_bytes, timeout=60)
        if r.status_code in (200, 201):
            return True, "已同步到 Supabase"
        return False, "Supabase 上传失败: " + str(r.status_code)
    except Exception as e:
        return False, "网络错误: " + str(e)

def sync_from_github():
    try:
        MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
        r = requests.post(SUPABASE_URL.replace("https://", "https://") + "/storage/v1/object/list/meetings",
            headers=STORAGE_HEADERS, json={"prefix": ""}, timeout=30)
        if r.status_code != 200:
            return 0
        files = r.json()
        if not isinstance(files, list):
            return 0
        count = 0
        for item in files:
            fn = item.get("name", "")
            if not fn.endswith(".html"):
                continue
            lp = MEETINGS_DIR / fn
            if lp.exists():
                continue
            encoded = urllib.parse.quote(fn, safe="-_.")
            dr = requests.get(SUPABASE_URL.replace("https://", "https://") + "/storage/v1/object/public/meetings/" + filename, timeout=30)
            if dr.status_code == 200:
                lp.write_bytes(dr.content)
                count += 1
        return count
    except Exception:
        return 0

st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    * {font-size: 18px !important; line-height: 1.6 !important;}
    h1 {font-size: 48px !important;}
    h2 {font-size: 36px !important;}
    h3 {font-size: 28px !important;}
    h4 {font-size: 24px !important;}
    h5 {font-size: 20px !important;}
    .stButton button {font-size: 16px !important; padding: 10px 20px !important; border-radius: 8px !important;}
    .stButton button {min-width: 60px !important; white-space: nowrap !important; letter-spacing: 0 !important;}
    [data-testid="stVerticalBlock"] > div {min-height: 40px !important;}
    .cal-day {display:flex;align-items:center;justify-content:center;min-height:36px;padding:6px 0;font-size:14px;}
    .cal-day-empty {display:flex;align-items:center;justify-content:center;min-height:36px;}
    .stButton button {min-width: 60px !important; white-space: nowrap !important; letter-spacing: 0 !important;}
    .stTabs [data-baseweb="tab"] {font-size: 18px !important; padding: 10px 18px !important;}
    .stTabs [data-baseweb="tab-highlight"] {height: 4px !important;}
    .block-container {padding: 1rem 1.5rem 0.5rem 1.5rem !important;}
    .stColumns {gap: 0.25rem !important;}
    .element-container {margin: 0rem !important; padding: 0rem !important;}
    section[data-testid="stSidebar"] * {font-size: 16px !important;}
    .main-title {font-size: 48px; font-weight: 700; color: #1a202c; margin-bottom: 0.5rem;}
    .login-box {max-width: 500px; margin: 60px auto; padding: 30px; background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);}
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    st.markdown('<div class="main-title" style="text-align:center; margin-top:40px;">经营例会看板</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            account = st.text_input("账号", placeholder="???jenny")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录", type="primary", use_container_width=True)
            if submitted:
                user = verify_password(account.strip().lower(), password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_account = account.strip().lower()
                    st.session_state.user_name = user["name"]
                    st.session_state.user_categories = user.get("categories", ["经营管理"])
                    st.session_state.can_delete = user.get("can_delete", False)
                    st.session_state.can_download = user.get("can_download", False)
                    st.session_state.is_admin = user.get("is_admin", False)
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

with st.sidebar:
    st.markdown("### 👤 " + st.session_state.get("user_name", ""))
    if st.session_state.get("is_admin"):
        st.markdown("👑 **总管理员**")
    st.divider()
    if st.button("🚪 退出登录", use_container_width=True):
        for k in ["logged_in","user_account","user_name","user_categories","can_delete","can_download","is_admin","sync_done","preview_cal_file","preview_cal_date","preview_file"]:
            st.session_state.pop(k, None)
        st.rerun()

user_name = st.session_state.get("user_name", "")
allowed_categories = st.session_state.get("user_categories", [])

if not st.session_state.get("sync_done"):
    with st.spinner("正在同步最新数据..."):
        synced = sync_from_github()
        if synced > 0:
            st.session_state.sync_msg = "已同步 " + str(synced) + " 个文件"
    st.session_state.sync_done = True

all_files = scan_meeting_files()
visible_files = [fi for fi in all_files if fi["category"] in allowed_categories]


# Build tabs
tab_names = ["📅 会议日历", "🔑 修改密码", "📤 上传记录"]
if st.session_state.get("can_download"):
    tab_names.append("📥 下载记录")
if st.session_state.get("is_admin"):
    tab_names.append("⚙️ 管理面板")
tabs = st.tabs(tab_names)
ti = 0

# ===== TAB 1: Calendar =====
with tabs[ti]:
    if "calendar_year" not in st.session_state:
        if visible_files:
            last_date = datetime.strptime(visible_files[-1]["date"], "%Y-%m-%d")
            st.session_state.calendar_year = last_date.year
            st.session_state.calendar_month = last_date.month
        else:
            st.session_state.calendar_year = datetime.now().year
            st.session_state.calendar_month = datetime.now().month

    year = st.session_state.calendar_year
    month = st.session_state.calendar_month

    # Build meeting date lookup
    meeting_dates = {}
    for fi in all_files:
        if fi["category"] in allowed_categories:
            meeting_dates[fi["date"]] = fi["filename"]

    # Navigation
    nav_l, nav_t, nav_r = st.columns([1, 4, 1])
    if nav_l.button("◀", key="cal_prev"):
        if month == 1:
            st.session_state.calendar_year = year - 1
            st.session_state.calendar_month = 12
        else:
            st.session_state.calendar_month = month - 1
        st.rerun()
    nav_t.markdown(f"<h3 style='text-align:center;margin:0'>{year}年 {month}月</h3>", unsafe_allow_html=True)
    if nav_r.button("▶", key="cal_next"):
        if month == 12:
            st.session_state.calendar_year = year + 1
            st.session_state.calendar_month = 1
        else:
            st.session_state.calendar_month = month + 1
        st.rerun()

    # Calendar grid + Preview side by side
    cal_col, preview_col = st.columns([1, 3])

    with cal_col:
        # Weekday headers
        cols = st.columns(7)
        for i, wd in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
            cols[i].markdown(f"<div style='text-align:center;font-weight:600;color:#718096;font-size:11px'>{wd}</div>", unsafe_allow_html=True)

        # Calculate calendar layout
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
        days_in_month = (last_day - first_day).days
        start_weekday = (first_day.weekday())  # Monday=0

        # Build rows
        current_col = 0
        cols = st.columns(7)
        # Empty cells before first day
        for _ in range(start_weekday):
            cols[current_col].markdown("<div class='cal-day-empty'>&nbsp;</div>", unsafe_allow_html=True)
            current_col += 1

        for day in range(1, days_in_month + 1):
            if current_col >= 7:
                cols = st.columns(7)
                current_col = 0
            date_str = f"{year}-{month:02d}-{day:02d}"
            if date_str in meeting_dates:
                if cols[current_col].button(f"{day}", key=f"day_{date_str}", use_container_width=True, type="primary"):
                    st.session_state.preview_cal_file = meeting_dates[date_str]
                    st.session_state.preview_cal_date = date_str
                    st.rerun()
            else:
                cols[current_col].markdown(f"<div class='cal-day' style='color:#a0aec0'>{day}</div>", unsafe_allow_html=True)
            current_col += 1

        # Fill remaining cells
        while current_col < 7 and current_col > 0:
            cols[current_col].markdown("<div class='cal-day-empty'>&nbsp;</div>", unsafe_allow_html=True)
            current_col += 1

    with preview_col:
        if st.session_state.get("preview_cal_file"):
            pf = st.session_state.preview_cal_file
            pd = st.session_state.get("preview_cal_date", "")
            st.markdown(f"#### 📄 {pd} 会议纪要")
            raw = load_html_content_raw(pf)
            if raw:
                st.components.v1.html(raw, height=1000, scrolling=True)
            else:
                st.error("无法读取文件")
        else:
            st.markdown("<div style='display:flex;align-items:center;justify-content:center;height:400px;color:#a0aec0;text-align:center'><div><div style='font-size:48px;margin-bottom:12px'>👈</div><div>点击左侧日历中的蓝色日期<br>即可在此处预览会议纪要</div></div></div>", unsafe_allow_html=True)
ti += 1

# ===== TAB 2: Password =====
with tabs[ti]:
    st.markdown("### 🔑 修改密码")
    st.markdown("修改您的登录密码，修改后下次登录生效。")
    old_pw = st.text_input("当前密码", type="password", key="old_pw")
    new_pw = st.text_input("新密码", type="password", key="new_pw")
    new_pw2 = st.text_input("确认新密码", type="password", key="new_pw2")
    if st.button("💾 保存新密码", type="primary"):
        acct = st.session_state.get("user_account", "")
        if not verify_password(acct, old_pw):
            st.error("当前密码不正确")
        elif new_pw != new_pw2:
            st.error("两次输入的新密码不一致")
        elif len(new_pw) < 4:
            st.error("新密码至少 4 位")
        elif change_pw(acct, new_pw):
            st.success("密码已修改，下次登录请使用新密码")
ti += 1

# ===== TAB 3: Upload =====
with tabs[ti]:
    st.markdown("### 📤 上传会议纪要")
    st.markdown("上传经营管理会议纪要文件（HTML格式），按日期自动命名并加入看板。")
    if "upload_key" not in st.session_state:
        st.session_state.upload_key = 0
    up_date = st.date_input("会议日期", value=datetime.now(), key="up_date")
    up_file = st.file_uploader("选择 HTML 文件", type=["html"], key="up_file")
    if up_file is not None:
        if st.button("📤 确认上传", type="primary"):
            date_str = up_date.strftime("%Y-%m-%d")
            filename = date_str + "-经营管理.html"
            filepath = MEETINGS_DIR / filename
            file_bytes = up_file.getvalue()
            try:
                head = file_bytes[:2048].decode("utf-8", errors="ignore").lower()
            except Exception:
                head = ""
            if "<html" not in head and "<!doctype" not in head and "<head" not in head:
                st.error("❌ 上传的文件不是有效的 HTML 文件")
                st.stop()
            MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(file_bytes)
            with st.spinner("正在同步到 GitHub..."):
                ok, msg = upload_to_github(filename, file_bytes)
            if ok:
                st.success("✅ 已保存并同步：" + filename)
            else:
                st.warning("⚠️ 已本地保存：" + filename + "，但 GitHub 同步失败（" + msg + "）")
            st.session_state.upload_key += 1
            st.rerun()
ti += 1

# ===== TAB 4: Download =====
if st.session_state.get("can_download"):
    with tabs[ti]:
        st.markdown("### 📥 下载会议纪要")
        dl_files = scan_meeting_files()
        if not dl_files:
            st.info("暂无可下载的会议纪要。")
        else:
            for df in dl_files:
                col_info, col_btn = st.columns([4, 1])
                col_info.markdown("`" + df["date"] + "` · " + df["category"])
                local_path = MEETINGS_DIR / df["filename"]
                if local_path.exists():
                    file_bytes = local_path.read_bytes()
                    col_btn.download_button("⬇️ 下载", data=file_bytes, file_name=df["filename"], mime="text/html", key="dl_" + df["filename"])
    ti += 1

# ===== TAB 5: Admin =====
if st.session_state.get("is_admin"):
    with tabs[ti]:
        st.markdown("### ⚙️ 管理面板")

        st.markdown("#### 🔐 重置成员密码")
        all_users = get_all_users()
        for u in all_users:
            acct = u["account"]
            if acct == st.session_state.get("user_account"):
                continue
            col_name, col_input, col_btn = st.columns([2, 3, 1])
            col_name.markdown("**" + u["name"] + "** (`" + acct + "`)")
            new_reset = col_input.text_input("新密码", key="reset_" + acct, placeholder="输入新密码", label_visibility="collapsed")
            if col_btn.button("🔄 重置", key="resetbtn_" + acct):
                if new_reset and len(new_reset) >= 4:
                    change_pw(acct, new_reset)
                    st.success(u["name"] + " 密码已重置为: " + new_reset)
                    st.rerun()
                else:
                    st.error("密码至少 4 位")

        st.divider()

        st.markdown("#### 🗑️ 删除会议纪要")
        del_files = scan_meeting_files()
        if not del_files:
            st.info("暂无可删除的会议纪要。")
        else:
            for df in del_files:
                col_info, col_btn = st.columns([4, 1])
                col_info.markdown("`" + df["date"] + "` · " + df["category"])
                if col_btn.button("🗑️ 删除", key="del_" + df["filename"], type="secondary"):
                    local_path = MEETINGS_DIR / df["filename"]
                    if local_path.exists():
                        local_path.unlink()
                    with st.spinner("正在删除 " + df["filename"] + " ..."):
                        ok, msg = delete_from_github(df["filename"])
                    if ok:
                        st.success("✅ 已删除：" + df["filename"])
                    else:
                        st.warning("⚠️ 本地已删除，但 GitHub 删除失败（" + msg + "）")
                    st.rerun()

        st.divider()

        st.markdown("#### ✏️ 修改会议纪要")
        mod_files = scan_meeting_files()
        if not mod_files:
            st.info("暂无可修改的会议纪要。")
        else:
            mod_select = st.selectbox("选择要修改的记录", options=[df["filename"] for df in mod_files], key="mod_select")
            mod_file = st.file_uploader("上传替换文件（HTML）", type=["html"], key="mod_file")
            if mod_file is not None:
                if st.button("✏️ 确认替换", type="primary"):
                    file_bytes = mod_file.getvalue()
                    try:
                        head = file_bytes[:2048].decode("utf-8", errors="ignore").lower()
                    except Exception:
                        head = ""
                    if "<html" not in head and "<!doctype" not in head and "<head" not in head:
                        st.error("❌ 文件不是有效的 HTML。")
                        st.stop()
                    filepath = MEETINGS_DIR / mod_select
                    filepath.write_bytes(file_bytes)
                    with st.spinner("正在同步到 GitHub..."):
                        ok, msg = upload_to_github(mod_select, file_bytes)
                    if ok:
                        st.success("✅ 已替换并同步：" + mod_select)
                    else:
                        st.warning("⚠️ 已本地替换，但 GitHub 同步失败（" + msg + "）")
                    st.rerun()
