import re
import streamlit as st
from supabase import create_client

# 學校代碼對照表（教育部學校代碼）
SCHOOL_CODE_MAP = {
    "010301":"國立華僑高級中等學校","011301":"私立淡江高中","011302":"私立康橋高中",
    "011306":"私立金陵女中","011307":"新北市裕德高級中等學校","011309":"財團法人南山高中",
    "011310":"財團法人恆毅高中","011311":"私立聖心女中","011312":"私立崇義高中",
    "011314":"新北市福瑞斯特高中","011315":"私立東海高中","011316":"私立格致高中",
    "011317":"私立醒吾高中","011318":"私立徐匯高中","011322":"新北市崇光高中",
    "011323":"私立光仁高中","011324":"私立竹林高中","011325":"私立中信高中",
    "011329":"財團法人辭修高中","011330":"新北市林口康橋國際高中","011399":"私立時雨高中",
    "011405":"私立樹人家商","011407":"私立復興商工","011408":"私立南強工商",
    "011413":"私立穀保家商","011420":"私立智光商工","011426":"私立能仁家商",
    "011427":"私立豫章工商","011431":"私立莊敬工家","011432":"私立中華商海",
    "013303":"市立泰山高中","013304":"市立板橋高中","013335":"市立新店高中",
    "013336":"市立中和高中","013337":"市立新莊高中","013338":"市立新北高中",
    "013339":"市立林口高中","013402":"市立瑞芳高工","013430":"市立三重商工",
    "013433":"市立新北高工","013434":"市立淡水商工","014302":"市立海山高中",
    "014311":"市立三重高中","014315":"市立永平高中","014322":"市立樹林高中",
    "014326":"市立明德高中","014332":"市立秀峰高中","014338":"市立金山高中",
    "014343":"市立安康高中","014347":"市立雙溪高中","014348":"市立石碇高中",
    "014353":"市立丹鳳高中","014356":"市立清水高中","014357":"市立三民高中",
    "014362":"市立錦和高中","014363":"市立光復高中","014364":"市立竹圍高中",
    "014381":"市立北大高級中學","014399":"市立豐珠中學","014439":"市立鶯歌工商",
    "014468":"市立樟樹國際實中","020301":"國立蘭陽女中","020302":"國立宜蘭高中",
    "020308":"國立羅東高中","020403":"國立宜蘭高商","020404":"國立羅東高商",
    "020405":"國立蘇澳海事","020407":"國立羅東高工","020409":"國立頭城家商",
    "021301":"私立慧燈高中","021310":"私立中道高中","024322":"縣立南澳高中",
    "024325":"縣立慈心華德福實中","030305":"國立中央大學附屬中壢高中",
    "030403":"國立北科大附屬桃園農工","031301":"桃園市路亞國際高中",
    "031309":"桃園市育達高中","031310":"私立六和高中","031311":"桃園市復旦高中",
    "031312":"桃園市治平高中","031313":"桃園市振聲高中","031317":"私立光啟高中",
    "031318":"桃園市啟英高中","031319":"桃園市清華高中","031320":"桃園市新興高中",
    "031323":"私立至善高中","031324":"桃園市大興高中","031326":"私立大華高中",
    "031414":"桃園市世紀綠能工商","031415":"私立方曙商工","031421":"私立永平工商",
    "033302":"市立龍潭高中","033304":"市立桃園高中","033306":"市立武陵高中",
    "033316":"市立楊梅高中","033325":"市立陽明高中","033327":"市立內壢高中",
    "033407":"市立中壢高商","033408":"市立中壢家商","034306":"市立南崁高中",
    "034312":"市立大溪高中","034314":"市立壽山高中","034319":"市立平鎮高中",
    "034332":"市立觀音高中","034335":"市立新屋高中","034347":"市立永豐高中",
    "034348":"市立羅浮高中","034399":"市立大園國際高中","040302":"國立竹東高中",
    "040304":"國立關西高中","040308":"國立陽明交大附中","041303":"私立義民高中",
    "041305":"私立忠信高中","041306":"私立東泰高中","041307":"私立仰德高中",
    "041401":"私立內思高工","044311":"縣立六家高級中學","044320":"縣立湖口高中",
    "050303":"國立苗栗高中","050310":"國立竹南高中","050314":"國立卓蘭高中",
    "050315":"國立苑裡高中","050401":"國立大湖農工","050404":"國立苗栗農工",
    "050407":"國立苗栗高商","051302":"私立君毅高中","051306":"私立建臺高中",
    "051307":"私立全人實驗高中","051408":"私立中興商工","051413":"私立龍德家商",
    "054308":"縣立三義高中","054309":"縣立苑裡高中","054317":"縣立興華高中",
    "054333":"縣立大同高中","060322":"國立興大附中","060323":"國立中科實驗高級中學",
    "061301":"財團法人常春藤高中","061306":"私立明台高中","061309":"私立致用高中",
    "061310":"臺中市大明高中","061311":"私立嘉陽高中","061313":"私立明道高中",
    "061314":"私立僑泰高中","061315":"私立華盛頓高中","061316":"私立青年高中",
    "061317":"私立弘文高中","061318":"私立立人高中","061319":"私立玉山高中",
    "061321":"私立慈明高中","061322":"華德福大地實驗學校","061323":"私立洛克威爾藝術實驗教育學校",
    "063303":"市立大甲高中","063305":"市立清水高中","063312":"市立豐原高中",
    "063401":"市立豐原高商","063402":"市立大甲高工","063404":"市立東勢高工",
    "063407":"市立沙鹿高工","063408":"市立霧峰農工","064308":"市立后綜高中",
    "064324":"市立大里高中","064328":"市立新社高中","064336":"市立長億高中",
    "064342":"市立中港高中","064350":"市立龍津高中","064406":"市立神岡高工",
    "070301":"國立彰化女中","070304":"國立員林高中","070307":"國立彰化高中",
    "070316":"國立鹿港高中","070319":"國立溪湖高中","070401":"國立彰師附工",
    "070402":"國立永靖高工","070403":"國立二林工商","070405":"國立秀水高工",
    "070406":"國立彰化高商","070408":"國立員林農工","070409":"國立員林崇實高工",
    "070410":"國立員林家商","070415":"國立北斗家商","071311":"私立精誠高中",
    "071317":"私立文興高中","071318":"財團法人正德高中","071414":"私立達德商工",
    "074308":"縣立彰化藝術高中","074313":"縣立二林高中","074323":"縣立和美高中",
    "074328":"縣立田中高中","074339":"縣立成功高中","080302":"國立南投高中",
    "080305":"國立中興高中","080307":"國立竹山高中","080308":"國立暨大附中",
    "080401":"國立仁愛高農","080403":"國立埔里高工","080404":"國立南投高商",
    "080406":"國立草屯商工","080410":"國立水里商工","081311":"私立五育高中",
    "081312":"私立三育高中","081313":"私立弘明實驗高中","081314":"私立普台高中",
    "081409":"南投縣同德高中","084309":"縣立旭光高中","090305":"國立斗六高中",
    "090306":"國立北港高中","090315":"國立虎尾高中","090401":"國立虎尾農工",
    "090402":"國立西螺農工","090403":"國立斗六家商","090404":"國立北港農工",
    "090413":"國立土庫商工","091307":"私立永年高中","091308":"私立正心高中",
    "091311":"私立文生高中","091312":"私立巨人高中","091316":"私立揚子高中",
    "091318":"財團法人義峰高中","091319":"福智高中","091320":"雲林縣維多利亞實驗高中",
    "091410":"私立大成商工","091414":"私立大德工商","094301":"縣立斗南高中",
    "094307":"縣立麥寮高中","094308":"縣立古坑華德福實驗高級中學","094326":"縣立蔦松藝術高中",
    "100301":"國立東石高中","100302":"國立新港藝術高中","100303":"國立嘉科實驗高中",
    "100402":"國立民雄農工","101304":"私立協同高中","101406":"私立萬能工商",
    "104319":"縣立竹崎高中","104326":"縣立永慶高中","110302":"國立新豐高中",
    "110308":"國立臺南大學附中","110311":"國立北門高中","110312":"國立新營高中",
    "110314":"國立後壁高中","110315":"國立善化高中","110317":"國立新化高中",
    "110328":"國立南科國際實驗高中","110401":"國立新化高工","110403":"國立白河商工",
    "110404":"國立北門農工","110405":"國立曾文家商","110406":"國立新營高工",
    "110407":"國立玉井工商","110409":"國立成大附屬南工","110410":"國立曾文農工",
    "111313":"私立南光高中","111320":"私立港明高中","111321":"臺南市中信國際高中",
    "111322":"私立明達高中","111323":"私立黎明高中","111326":"私立新榮高中",
    "111419":"私立陽明工商","111427":"私立育德工家","114306":"市立大灣高中",
    "114307":"市立永仁高中","114344":"市立沙崙國際高中","120303":"國立鳳山高中",
    "120304":"國立岡山高中","120311":"國立旗美高中","120319":"國立鳳新高中",
    "120320":"國立高科實驗高中","120401":"國立旗山農工","120402":"國立岡山農工",
    "120409":"國立鳳山商工","121302":"光禾華德福實驗學校","121306":"財團法人新光高中",
    "121307":"財團法人普門中學","121318":"私立正義高中","121320":"私立義大國際高中",
    "121405":"私立中山工商","121410":"私立旗美商工","121413":"私立高英工商",
    "121415":"私立華德工家","121417":"私立高苑工商","124302":"市立文山高中",
    "124311":"市立林園高中","124313":"市立仁武高中","124322":"市立路竹高中",
    "124333":"市立六龜高中","124340":"市立福誠高中","130302":"國立屏東女中",
    "130305":"國立屏東高中","130306":"國立潮州高中","130307":"國立屏科實驗高中",
    "130322":"國立屏北高中","130401":"國立內埔農工","130403":"國立屏東高工",
    "130404":"國立佳冬高農","130410":"國立東港海事","130417":"國立恆春工商",
    "131307":"財團法人屏榮高中","131308":"私立陸興高中","131311":"私立美和高中",
    "131409":"私立民生家商","134304":"縣立大同高中","134321":"縣立枋寮高中",
    "134324":"縣立東港高中","134334":"縣立來義高中","140301":"國立臺東大學附屬體育高中",
    "140302":"國立臺東女中","140303":"國立臺東高中","140404":"國立關山工商",
    "140405":"國立臺東高商","140408":"國立成功商水","141301":"臺東縣均一高中",
    "141307":"私立育仁高中","141406":"私立公東高工","144322":"縣立蘭嶼高中",
    "150302":"國立花蓮女中","150303":"國立花蓮高中","150309":"國立玉里高中",
    "150401":"國立花蓮高農","150404":"國立花蓮高工","150405":"國立花蓮高商",
    "150411":"國立光復商工","151306":"私立海星高中","151307":"私立四維高中",
    "151312":"財團法人慈濟大學附中","151410":"花蓮縣上騰工商","154301":"花蓮縣立體育高中",
    "154399":"縣立南平中學","160302":"國立馬公高中","160401":"國立澎湖海事水產",
    "170301":"國立基隆女中","170302":"國立基隆高中","170403":"國立海洋大學附屬基隆海事",
    "170404":"國立基隆商工","171306":"私立二信高中","171308":"輔大聖心高中",
    "171405":"私立光隆家商","171407":"私立培德工家","173304":"市立中山高中",
    "173306":"市立安樂高中","173307":"市立暖暖高中","173314":"市立八斗高中",
    "180301":"國立竹科實驗高級中等學校","180302":"國立新竹女中","180309":"國立新竹高中",
    "180403":"國立新竹高商","180404":"國立新竹高工","181305":"私立光復高中",
    "181306":"私立曙光女中","181307":"私立磐石高中","181308":"私立世界高中",
    "183306":"市立成德高中","183307":"市立香山高中","183313":"市立建功高中",
    "183314":"新竹市數位實驗高中","190406":"國立興大附農","191301":"私立東大附中",
    "191302":"私立葳格高中","191305":"臺中市新民高中","191308":"私立宜寧高中",
    "191309":"私立明德高中","191311":"私立衛道高中","191313":"私立曉明女中",
    "191314":"私立嶺東高中","191315":"私立磊川華德福實驗教育學校","191412":"財團法人光華高工",
    "193301":"市立臺中女中","193302":"市立臺中一中","193303":"市立忠明高中",
    "193313":"市立西苑高中","193315":"市立東山高中","193316":"市立惠文高中",
    "193404":"市立臺中家商","193407":"市立臺中高工","194303":"市立臺中二中",
    "194315":"市立文華高中","200302":"國立嘉義女中","200303":"國立嘉義高中",
    "200401":"國立華南高商","200405":"國立嘉義高工","200406":"國立嘉義高商",
    "200407":"國立嘉義家職","201304":"私立興華高中","201310":"私立嘉華高中",
    "201312":"私立輔仁高中","201313":"私立宏仁高中","201314":"私立立仁高中",
    "201408":"私立東吳工家","210303":"國立臺南二中","210305":"國立臺南一中",
    "210306":"國立臺南女中","210309":"國立家齊高中","210408":"國立臺南高商",
    "210416":"國立臺南海事","211301":"私立長榮高中","211302":"私立長榮女中",
    "211304":"財團法人聖功女中","211310":"臺南市光華高中","211314":"私立六信高中",
    "211315":"私立瀛海高中","211317":"臺南市崑山高中","211318":"私立德光高中",
    "211320":"財團法人慈濟高中","211407":"私立南英商工","211412":"私立亞洲餐旅",
    "211419":"私立慈幼工商","213303":"市立南寧高中","213316":"市立土城高中",
    "311401":"私立育達高中","313301":"市立西松高中","313302":"市立中崙高中",
    "321399":"私立協和祐德高中","323301":"市立松山高中","323302":"市立永春高中",
    "323401":"市立松山家商","323402":"市立松山工農","330301":"國立師大附中",
    "331301":"私立延平中學","331302":"私立金甌女中","331304":"私立復興實驗高中",
    "331402":"私立東方工商","331403":"私立喬治工商","331404":"私立開平餐飲",
    "333301":"市立和平高中","333304":"市立芳和實中","333401":"市立大安高工",
    "341302":"私立大同高中","341402":"私立稻江護家","343301":"市立中山女中",
    "343302":"市立大同高中","343303":"市立大直高中","351301":"臺北市新民高中",
    "351402":"臺北市開南高中","353301":"市立建國中學","353302":"市立成功中學",
    "353303":"市立北一女中","361301":"私立靜修高中","361401":"私立稻江高商",
    "363301":"市立明倫高中","363302":"市立成淵高中","373301":"市立華江高中",
    "373302":"市立大理高中","380301":"國立政大附中","381301":"私立東山高中",
    "381302":"私立滬江高中","381303":"私立大誠高中","381304":"私立再興中學",
    "381305":"私立景文高中","381306":"私立靜心高中","383301":"市立景美女中",
    "383302":"市立萬芳高中","383303":"臺北市數位實驗高中","383401":"市立木柵高工",
    "393301":"市立南港高中","393302":"市立育成高中","393401":"市立南港高工",
    "401303":"私立達人高中","403301":"市立內湖高中","403302":"市立麗山高中",
    "403303":"市立南湖高中","403401":"市立內湖高工","411301":"私立泰北高中",
    "411302":"私立衛理女中","411303":"私立華興中學","411401":"私立華岡藝校",
    "413301":"市立陽明高中","413302":"市立百齡高中","413401":"市立士林高商",
    "421301":"私立薇閣高中","421302":"臺北市幼華高中","421303":"私立奎山實驗高級中學",
    "421404":"私立惇敍工商","423301":"市立復興高中","423302":"市立中正高中",
    "521301":"天主教明誠高中","521303":"私立大榮高中","521401":"私立中華藝校",
    "523301":"市立鼓山高中","533301":"市立左營高中","533302":"市立新莊高中",
    "533401":"市立海青工商","533402":"市立三民家商","540301":"國立中山大學附屬國光高中",
    "543301":"市立中山高中","543302":"市立楠梓高中","551301":"私立立志高中",
    "551402":"私立樹德家商","553301":"市立高雄中學","553302":"市立三民高中",
    "553401":"市立高雄高工","563301":"市立新興高中","563401":"市立高雄高商",
    "573301":"市立高雄女中","580301":"國立高師大附中","581301":"私立復華高中",
    "581302":"天主教道明中學","581402":"私立三信家商","583301":"市立中正高中",
    "593301":"市立前鎮高中","593302":"市立瑞祥高中","593401":"市立中正高工",
    "610405":"國立高餐大附屬餐旅中學","613301":"市立小港高中",
    "710301":"國立金門高中","710401":"國立金門農工","720301":"國立馬祖高中",
    "011C71":"私立光華高商進修學校","351B09":"私立南華高中進修學校",
    "361B09":"私立志仁中學進修學校","400419":"國立臺灣戲曲學院附設高職部",
    "03C301":"敦品中學","04C301":"誠正中學","07C301":"勵志中學",
    "12C301":"明陽中學","12M301":"中正國防幹部預備學校",
}
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def is_valid_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(email) and re.match(pattern, email) is not None
from passlib.context import CryptContext
from datetime import datetime

# 密碼雜湊設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)

def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(raw_password, hashed_password)

PDF_BUCKET = "course-pdfs"
MAX_PDF_BYTES = 2 * 1024 * 1024  # 2 MB

def upload_pdf(uploaded_file, school_id) -> str | None:
    """上傳 PDF 至 Supabase Storage，回傳公開 URL；失敗時回傳 None。"""
    import time
    file_bytes = uploaded_file.read()
    if len(file_bytes) > MAX_PDF_BYTES:
        st.error("檔案超過 2MB 上限，請壓縮後再上傳。")
        return None
    path = f"{school_id}/{int(time.time())}.pdf"
    try:
        supabase.storage.from_(PDF_BUCKET).upload(
            path, file_bytes, {"content-type": "application/pdf"}
        )
        return supabase.storage.from_(PDF_BUCKET).get_public_url(path)
    except Exception as e:
        st.error(f"PDF 上傳失敗：{e}")
        return None

# 連鎖刪除函數
def delete_course_cascade(course_id):
    """刪除課程前，先刪除所有關聯的 matches，避免 FK 報錯"""
    supabase.table("matches").delete().eq("course_id", course_id).execute()
    supabase.table("courses").delete().eq("id", course_id).execute()

def delete_school_cascade(school_id):
    """刪除學校前，依序刪除 matches → courses → schools，避免 FK 報錯"""
    # 1. 找出該學校所有課程 id
    courses_res = supabase.table("courses").select("id").eq("host_school_id", school_id).execute()
    course_ids = [c["id"] for c in courses_res.data]

    # 2. 刪除這些課程的所有 matches
    for cid in course_ids:
        supabase.table("matches").delete().eq("course_id", cid).execute()

    # 3. 刪除該學校作為 partner 的 matches
    supabase.table("matches").delete().eq("partner_school_id", school_id).execute()

    # 4. 刪除該學校所有課程
    supabase.table("courses").delete().eq("host_school_id", school_id).execute()

    # 5. 刪除學校本身
    supabase.table("schools").delete().eq("id", school_id).execute()

# 權限控制函數
def require_login():
    """要求用戶登入，否則顯示警告並停止執行"""
    if not st.session_state.get("logged_in"):
        st.warning("⚠️ 請先登入學校帳號")
        st.stop()

def require_admin():
    """要求管理員權限，否則顯示錯誤並停止執行"""
    if not st.session_state.get("admin_logged_in"):
        st.error("🚫 您沒有管理權限，請以管理員身份登入")
        st.stop()

def is_admin():
    """檢查是否為管理員"""
    return st.session_state.get("admin_logged_in", False)

def is_logged_in():
    """檢查是否已登入"""
    return st.session_state.get("logged_in", False)

# 1. 連接 Supabase (建議將金鑰移至 secrets.toml)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="跨校課程媒合平台", layout="wide")

# --- 全域淺藍主題（同首頁色調，淺色調） ---
st.markdown("""
<style>
/* ── 背景：淺藍灰，與首頁 navy 同色系 ── */
.stApp {
    background: linear-gradient(160deg, #eef2fa 0%, #e8eef8 55%, #edf1f9 100%) !important;
}

/* ── 主文字 ── */
html, body, [class*="css"], .stMarkdown, .stText, p, li, label,
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: #1a2340 !important;
}

/* ── 標題 ── */
h1, h2, h3 { color: #1a2a4a !important; }

/* ── 側邊欄 ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #dce6f5 0%, #d0dcf0 100%) !important;
}
[data-testid="stSidebar"] * { color: #1a2a4a !important; }
[data-testid="stSidebar"] label { color: #2a3a60 !important; font-weight: 500 !important; }

/* ── Selectbox trigger ── */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] {
    background-color: #dce6f5 !important;
    border: 1px solid #b0c4e0 !important;
    color: #1a2340 !important;
}
[data-baseweb="select"] * { color: #1a2340 !important; }
[data-baseweb="select"] svg { fill: #1a2340 !important; }

/* ── Dropdown popover（body portal，手機和桌機通用） ── */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] > div > div {
    background-color: #dce6f5 !important;
    border: 1px solid #b0c4e0 !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 16px rgba(30,50,100,0.10) !important;
}
[data-baseweb="menu"] {
    background-color: #dce6f5 !important;
}
[data-baseweb="menu"] ul,
[data-baseweb="menu"] li {
    background-color: #dce6f5 !important;
    color: #1a2340 !important;
}
/* role="listbox" 是實際選項容器 */
[role="listbox"] {
    background-color: #dce6f5 !important;
    color: #1a2340 !important;
}
[role="option"] {
    background-color: #dce6f5 !important;
    color: #1a2340 !important;
}
[role="option"] * {
    background-color: transparent !important;
    color: #1a2340 !important;
}
[role="option"]:hover {
    background-color: #c4d4ec !important;
}
[role="option"][aria-selected="true"] {
    background-color: #dce6f5 !important;
    color: #1a2340 !important;
    font-weight: 600 !important;
}

/* ── 原生 <select>（Android WebView fallback） ── */
select {
    background-color: #ffffff !important;
    color: #1a2340 !important;
    border: 1px solid #b0c4e0 !important;
    border-radius: 6px !important;
}
select option {
    background-color: #ffffff !important;
    color: #1a2340 !important;
}

/* ── 手機版 sidebar overlay 容器 ── */
section[data-testid="stSidebar"] > div,
[data-testid="stSidebarNav"] {
    background: linear-gradient(180deg, #dce6f5 0%, #d0dcf0 100%) !important;
}

/* ── Text input / textarea ── */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    background-color: #ffffff !important;
    border: 1px solid #b0c4e0 !important;
    color: #1a2340 !important;
    border-radius: 6px !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder { color: #8098b8 !important; }

/* ── Buttons ── */
.stButton > button {
    background-color: #dce8f8 !important;
    color: #1a3060 !important;
    border: 1px solid #a0b8d8 !important;
    border-radius: 8px !important;
}
.stButton > button:hover {
    background-color: #c8d8f0 !important;
    border-color: #7a9cc8 !important;
}
/* Primary button — 用 data-testid 確保手機/桌機都生效 */
[data-testid="baseButton-primary"],
.stButton > button[kind="primary"] {
    background-color: #2563a8 !important;
    border-color: #2563a8 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
}
[data-testid="baseButton-primary"] p,
[data-testid="baseButton-primary"] span,
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span {
    color: #ffffff !important;
}
[data-testid="baseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover {
    background-color: #1e50a0 !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid #b0c4e0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    color: #4a6a9a !important;
    background-color: transparent !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #1a3060 !important;
    border-bottom: 2px solid #2563a8 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background-color: rgba(255, 255, 255, 0.75) !important;
    border: 1px solid #b0c4e0 !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: #1a2a4a !important;
}

/* ── Metric boxes ── */
[data-testid="stMetric"] {
    background-color: rgba(255, 255, 255, 0.8) !important;
    border: 1px solid #b0c4e0 !important;
    border-radius: 8px !important;
    padding: 0.8rem 1rem !important;
}
[data-testid="stMetricValue"] { color: #1a3060 !important; }
[data-testid="stMetricLabel"] { color: #4a6a9a !important; }

/* ── Info / Warning / Error / Success banners ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background-color: rgba(255, 255, 255, 0.7) !important;
    border: 1px dashed #90b0d8 !important;
    border-radius: 8px !important;
}

/* ── Dataframe / table ── */
[data-testid="stDataFrame"] { background-color: rgba(255, 255, 255, 0.8) !important; }

/* ── Radio / Checkbox ── */
.stRadio label, .stCheckbox label { color: #1a2a4a !important; }

/* ── Divider ── */
hr { border-color: #b0c4e0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #dce6f5; }
::-webkit-scrollbar-thumb { background: #90b0d8; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# 拒絕通知：僅對已登入的合作學校顯示
if st.session_state.get("logged_in") and st.session_state.get("school_info"):
    school = st.session_state.school_info
    if 'dismissed_rejections' not in st.session_state:
        st.session_state.dismissed_rejections = set()
    try:
        rejected_res = supabase.table("matches")\
            .select("id, course_id")\
            .eq("partner_school_id", school['id'])\
            .eq("status", "rejected")\
            .execute()
        for rm in rejected_res.data:
            if rm['id'] not in st.session_state.dismissed_rejections:
                course_res = supabase.table("courses")\
                    .select("id, title, max_schools")\
                    .eq("id", rm['course_id'])\
                    .execute()
                if course_res.data:
                    c = course_res.data[0]
                    st.warning(f"😔 **媒合申請通知**\n\n很遺憾，您對課程「**{c['title']}**」的媒合申請已被開課學校婉拒。")
                    if st.button("知道了", key=f"dismiss_{rm['id']}"):
                        st.session_state.dismissed_rejections.add(rm['id'])
                        st.rerun()
    except Exception:
        pass

# Email 發送函數
def send_email(to_email, to_name, subject, content):
    """發送 Email 給指定收件人"""
    try:
        # 修正：從 st.secrets 取得資訊並統一變數名稱
        gmail_user = st.secrets["GMAIL_USER"]
        gmail_password = st.secrets["GMAIL_PASSWORD"]
        
        # 建立郵件內容
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        body = f"""{content}

---
跨校課程媒合平台
https://your-app-url.com
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 發送郵件
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_password) # 使用正確的變數
            text = msg.as_string()
            server.sendmail(gmail_user, to_email, text)
        
        return True, "Email 發送成功"
        
    except Exception as e:
        return False, f"Email 發送失敗：{str(e)}"

# 初始化登入狀態
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.school_info = None

# --- 側邊欄選單 ---
if is_admin():
    # 管理員專用選單
    menu = ["課程大廳", "📊 系統管理", "登出"]
elif not is_logged_in():
    menu = ["課程大廳", "學校帳號登入"]
else:
    # 加入「配對情形」和「學校基本資料」
    menu = ["課程大廳", "管理中心 (我的課程)", "配對情形", "學校基本資料", "新增/修改課程", "登出"]

_default_index = 0
if st.session_state.get("force_login") and "學校帳號登入" in menu:
    _default_index = menu.index("學校帳號登入")
    st.session_state.force_login = False

choice = st.sidebar.selectbox("選單", menu, index=_default_index)

# --- 登出邏輯 ---
if choice == "登出":
    st.session_state.logged_in = False
    st.session_state.school_info = None
    st.session_state.entered_lobby = False
    st.session_state.admin_logged_in = False
    st.rerun()

# --- 頁面內容 ---
if choice == "課程大廳":

    # ── 首頁 Landing Page ──────────────────────────────────────
    if not st.session_state.get("entered_lobby", False):
        st.markdown("""
        <style>
        /* 隱藏 Streamlit 預設 UI */
        #MainMenu, footer, header { visibility: hidden; }
        [data-testid="stSidebar"] { display: none; }
        .stApp { background: linear-gradient(160deg, #10141f 0%, #172035 55%, #10141f 100%) !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; }

        /* Hero — 置中但不撐滿全頁，讓按鈕緊跟在下方 */
        .hero {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding-top: 18vh;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
        }
        .hero-eyebrow {
            font-size: 1rem;
            font-weight: 500;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #2997ff;
            margin-bottom: 1.4rem;
        }
        .hero-title {
            font-size: clamp(2.8rem, 7vw, 5.5rem);
            font-weight: 700;
            letter-spacing: -0.025em;
            line-height: 1.05;
            color: #f5f5f7;
            margin-bottom: 1.2rem;
        }
        .hero-subtitle {
            font-size: clamp(1rem, 2.5vw, 1.4rem);
            font-weight: 300;
            color: rgba(245,245,247,0.55);
            letter-spacing: 0.01em;
            margin-bottom: 0;
        }
        /* 分隔線 */
        .hero-divider {
            width: 60px;
            height: 1px;
            background: rgba(245,245,247,0.2);
            margin: 0 auto 2rem;
        }
        /* 首頁按鈕強制白字（高 specificity 覆蓋全域規則） */
        .stApp .stButton > button,
        .stApp [data-testid="baseButton-secondary"],
        .stApp [data-testid="baseButton-primary"],
        .stApp .stButton > button span,
        .stApp [data-testid="baseButton-secondary"] span,
        .stApp [data-testid="baseButton-primary"] span {
            color: #ffffff !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
        }
        </style>

        <div class="hero">
            <div class="hero-eyebrow">教育 × 合作 × 創新</div>
            <div class="hero-title">跨校課程<br>媒合平台</div>
            <div class="hero-divider"></div>
            <div class="hero-subtitle">Connecting everyone with curriculum</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("學校帳號 Sign in / Sign Up", use_container_width=True):
                st.session_state.entered_lobby = True
                st.session_state.force_login = True
                st.rerun()
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("進入課程大廳 →", use_container_width=True, type="primary"):
                st.session_state.entered_lobby = True
                st.rerun()
        st.stop()

    st.header("📚 現有跨校課程一覽")
    try:
        # 精確欄位查詢，含學校分區
        response = supabase.table("courses").select(
            "id, title, start_time, max_students, max_schools, syllabus, plan_pdf_url, host_school_id, "
            "sps_min, sps_max, req_1, req_2, req_3, "
            "schools(name, district, registrant_name, registrant_email, academic_director_email, principal_email)"
        ).execute()
        courses = response.data
        if not courses:
            st.info("目前尚無開課資訊。")
        else:
            # 一次批次撈所有課程的 matches，避免 N+1 查詢
            all_course_ids = [c['id'] for c in courses]
            all_matches_res = supabase.table("matches")\
                .select("course_id, status")\
                .in_("course_id", all_course_ids)\
                .in_("status", ["pending", "approved"])\
                .execute()
            matches_by_course = {}
            for m in all_matches_res.data:
                matches_by_course.setdefault(m['course_id'], []).append(m)

            # --- 篩選 UI ---
            all_districts = sorted({c['schools'].get('district', '其他') for c in courses if c.get('schools')})
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                selected_district = st.selectbox("🗺️ 篩選開課學校分區", ["全部"] + all_districts)
            with col_f2:
                time_keyword = st.text_input("🕐 搜尋時段關鍵字", placeholder="例：週三、14:00")

            filtered_courses = [
                c for c in courses
                if (selected_district == "全部" or c.get('schools', {}).get('district') == selected_district)
                and (not time_keyword or time_keyword in (c.get('start_time') or ''))
            ]
            st.caption(f"共 {len(filtered_courses)} 門課程")

            for c in filtered_courses:
                course_matches = matches_by_course.get(c['id'], [])
                approved_count = sum(1 for m in course_matches if m['status'] == 'approved')
                pending_count = sum(1 for m in course_matches if m['status'] == 'pending')
                total_active = approved_count + pending_count
                max_schools = c.get('max_schools', 2)

                with st.expander(f"📖 {c['title']} - {c['schools']['name']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**🗓️ 開課時間：** {c.get('start_time', '未設定')}")
                        st.write(f"**👥 跨校學生上限：** {c.get('max_students', 'N/A')} 人")
                        if c.get('sps_min') or c.get('sps_max'):
                            st.write(f"**🎓 每校希望學生人數：** {c.get('sps_min', '?')} ~ {c.get('sps_max', '?')} 人")
                    with col2:
                        st.write(f"**🏫 合作學校上限：** {max_schools} 所")
                        st.write(f"**📊 目前申請：** {total_active}/{max_schools} 所")
                        st.write(f"  - ✅ 已通過：{approved_count} 所")
                        st.write(f"  - ⏳ 待審核：{pending_count} 所")
                        if c.get('plan_pdf_url'):
                            st.link_button("📥 查看課程規劃表 (PDF)", c['plan_pdf_url'])
                    st.write(f"**📝 課程大綱：**\n{c['syllabus']}")

                    if f"show_matching_{c['id']}" not in st.session_state:
                        st.session_state[f"show_matching_{c['id']}"] = False

                    logged_in_school_id = st.session_state.school_info['id'] if st.session_state.get('logged_in') and st.session_state.get('school_info') else None
                    is_own_course = logged_in_school_id is not None and c.get('host_school_id') == logged_in_school_id

                    if is_own_course:
                        st.info("📌 此為您開設的課程，無法申請媒合。")
                    else:
                        button_disabled = total_active >= max_schools
                        button_text = "🚫 名額已滿" if button_disabled else "申請媒合"

                    if not is_own_course and st.button(button_text, key=f"btn_{c['id']}", disabled=button_disabled):
                        if not st.session_state.logged_in:
                            st.warning("⚠️ 老師請先登入後再進行媒合申請喔！")
                        else:
                            st.session_state[f"show_matching_{c['id']}"] = True
                            st.rerun()

                    if st.session_state[f"show_matching_{c['id']}"]:
                        st.subheader(f"📋 媒合確認事項 - {c['title']}")
                        st.write(f"**開課學校：** {c['schools']['name']}")
                        confirm_items = [
                            "確認授課時間段是否可以配合",
                            "確認是否課程計劃未來是否可以新增課程",
                            "確認合作學校端所準備之設備與環境是否可以安排妥當",
                            "未來如媒合成功基於誠信原則請與開課學校建立良好夥伴關係",
                        ]
                        for req_key in ["req_1", "req_2", "req_3"]:
                            req_val = c.get(req_key, "")
                            if req_val:
                                confirm_items.append(f"【開課學校要求】{req_val}")
                        all_confirmed = True
                        for i, item in enumerate(confirm_items, 1):
                            if not st.checkbox(f"{i}. {item}", key=f"confirm_{c['id']}_{i}"):
                                all_confirmed = False

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("取消申請", key=f"cancel_{c['id']}"):
                                st.session_state[f"show_matching_{c['id']}"] = False
                                st.rerun()
                        with col2:
                            if st.button("確定申請媒合", key=f"send_{c['id']}", disabled=not all_confirmed):
                                with st.spinner('🔄 正在處理媒合申請...'):
                                    try:
                                        existing_match = supabase.table("matches")\
                                            .select("id")\
                                            .eq("course_id", c['id'])\
                                            .eq("partner_school_id", st.session_state.school_info['id'])\
                                            .in_("status", ["pending", "approved"])\
                                            .execute()
                                        if existing_match.data:
                                            st.error("⚠️ 您已經申請過此課程的媒合，且申請正在處理中或已通過！")
                                        elif total_active >= max_schools:
                                            st.error(f"⚠️ 此課程合作學校已滿！最多接受 {max_schools} 所學校。")
                                        else:
                                            match_result = supabase.table("matches").insert({
                                                "course_id": c['id'],
                                                "partner_school_id": st.session_state.school_info['id'],
                                                "status": "pending"
                                            }).execute()
                                            match_id = match_result.data[0]['id']
                                            applicant_school = st.session_state.school_info
                                            host_school = c['schools']
                                            email_recipients = [
                                                {"email": host_school['registrant_email'], "name": host_school['registrant_name'], "type": "host"},
                                                {"email": host_school.get('academic_director_email'), "name": "承辦處室主任", "type": "host"},
                                                {"email": host_school.get('principal_email'), "name": "校長", "type": "host"},
                                                {"email": applicant_school['registrant_email'], "name": applicant_school['registrant_name'], "type": "applicant"},
                                                {"email": applicant_school.get('academic_director_email'), "name": "承辦處室主任", "type": "applicant"},
                                                {"email": applicant_school.get('principal_email'), "name": "校長", "type": "applicant"},
                                            ]
                                            email_success = True
                                            failed_emails = []
                                            for recipient in email_recipients:
                                                if is_valid_email(recipient['email']):
                                                    try:
                                                        if recipient['type'] == 'host':
                                                            subject = f"媒合申請通知：{applicant_school['name']} 申請您的課程「{c['title']}」"
                                                            content = f"親愛的 {recipient['name']}：\n\n您開設的課程「{c['title']}」收到來自 {applicant_school['name']} 的媒合申請。\n\n申請學校資訊：\n- 學校：{applicant_school['name']}\n- 承辦人：{applicant_school['registrant_name']}\n- 聯絡電話：{applicant_school['phone']}\n- 分機：{applicant_school.get('registrant_extension', '未提供')}\n\n請登入系統查看詳細資訊並處理此申請。\n\n跨校課程媒合平台"
                                                        else:
                                                            subject = f"媒合申請確認：已申請「{c['title']}」課程"
                                                            content = f"親愛的 {recipient['name']}：\n\n您的學校已成功遞交課程「{c['title']}」的媒合申請。\n\n申請資訊：\n- 申請課程：{c['title']}\n- 開課學校：{host_school['name']}\n- 申請編號：{match_id}\n\n我們將通知開課學校處理您的申請，請耐心等候回覆。\n\n跨校課程媒合平台"
                                                        success, msg = send_email(recipient['email'], recipient['name'], subject, content)
                                                        if not success:
                                                            email_success = False
                                                            failed_emails.append(f"{recipient['name']} ({recipient['email']})")
                                                    except Exception:
                                                        email_success = False
                                                        failed_emails.append(f"{recipient['name']} ({recipient['email']})")
                                            if email_success:
                                                st.success("✅ 媒合申請已成功提交！所有相關人員都會收到通知 Email。")
                                            else:
                                                st.warning(f"⚠️ 媒合申請已提交，但部分 Email 發送失敗：{', '.join(failed_emails)}")
                                            st.session_state[f"show_matching_{c['id']}"] = False
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 申請失敗：{e}")
                                        st.info("請稍後再試或聯繫管理員")
    except Exception as e:
        st.error(f"讀取資料失敗：{e}")

elif choice == "學校帳號登入":
    auth_mode = st.radio("請選擇操作", ["學校帳號登入", "註冊學校帳號", "管理人員登入"], horizontal=True)

    if auth_mode == "學校帳號登入":
        st.subheader("🔑 學校帳號登入")
        phone = st.text_input("帳號（學校電話）")
        pwd = st.text_input("密碼", type="password")
        if st.button("確認登入"):
            res = supabase.table("schools").select("*").eq("phone", phone).execute()
            if res.data:
                user = res.data[0]
                if verify_password(pwd, user['password_hash']):  # 使用統一的欄位名稱
                    st.session_state.logged_in = True
                    st.session_state.school_info = user
                    st.success(f"登入成功！歡迎 {user['name']}")
                    st.rerun()
                else:
                    st.error("密碼錯誤！")
            else:
                st.error("找不到此帳號！")
        
        # 忘記密碼功能
        st.divider()
        st.subheader("🔐 忘記密碼")
        st.write("如果您忘記密碼，可以透過以下方式重置為預設密碼")
        
        with st.expander("📋 重置密碼說明"):
            st.info("""
            **重置密碼流程：**
            1. 輸入學校帳號（電話號碼）
            2. 輸入承辦人姓名進行身分驗證
            3. 輸入承辦人 Email 進行驗證
            4. 驗證成功後，密碼將重置為預設密碼（電話號碼後4碼）
            5. 重置密碼會 Email 通知相關人員
            """)
        
        # 忘記密碼表單
        forgot_phone = st.text_input("學校帳號 (電話號碼)", key="forgot_phone")
        forgot_name = st.text_input("承辦人姓名", key="forgot_name")
        forgot_email = st.text_input("承辦人 Email", key="forgot_email")
        
        if st.button("🔄 重置密碼", key="reset_password"):
            if forgot_phone and forgot_name and forgot_email:
                with st.spinner("🔍 正在驗證身分資訊..."):
                    try:
                        # 查詢學校資料
                        school_res = supabase.table("schools").select("*").eq("phone", forgot_phone).execute()
                        
                        if not school_res.data:
                            st.error("❌ 找不到此帳號！請確認電話號碼正確。")
                        else:
                            school = school_res.data[0]
                            
                            # 驗證承辦人姓名
                            if school['registrant_name'] != forgot_name:
                                st.error("❌ 承辦人姓名不符！請確認輸入正確。")
                            # 驗證承辦人 Email
                            elif school['registrant_email'] != forgot_email:
                                st.error("❌ 承辦人 Email 不符！請確認輸入正確。")
                            else:
                                # 驗�通過，重置密碼
                                default_password = forgot_phone[-4:] if len(forgot_phone) >= 4 else "0000"
                                hashed_password = hash_password(default_password)
                                
                                # 更新密碼
                                supabase.table("schools").update({"password_hash": hashed_password}).eq("id", school['id']).execute()
                                
                                # 發送通知 Email
                                subject = "🔐 密碼重置通知 - 跨校課程媒合平台"
                                content = f"""
親愛的 {school['registrant_name']}：

您的密碼已成功重置。

重置資訊：
- 學校：{school['name']}
- 帳號：{school['phone']}
- 新密碼：{default_password}

**重要提醒：**
- 請使用新密碼登入系統
- 建議登入後立即修改密碼
- 如有問題請聯繫系統管理員

登入網址：[您的應用程式網址]

跨校課程媒合平台
                                """
                                
                                # 發送給承辦人
                                email_success, email_msg = send_email(
                                    school['registrant_email'], 
                                    school['registrant_name'], 
                                    subject, 
                                    content
                                )
                                
                                # 同時通知承辦處室主任和校長（如果有 Email）
                                additional_recipients = []
                                if is_valid_email(school.get('academic_director_email', '')):
                                    additional_recipients.append({
                                        'email': school['academic_director_email'],
                                        'name': '承辦處室主任'
                                    })
                                if is_valid_email(school.get('principal_email', '')):
                                    additional_recipients.append({
                                        'email': school['principal_email'],
                                        'name': '校長'
                                    })
                                
                                for recipient in additional_recipients:
                                    admin_content = f"""
親愛的 {recipient['name']}：

通知：{school['name']} 的承辦人 {school['registrant_name']} 已重置密碼。

重置時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

如非授權操作，請立即聯繫系統管理員。

跨校課程媒合平台
                                    """
                                    send_email(recipient['email'], recipient['name'], subject, admin_content)
                                
                                if email_success:
                                    st.success(f"✅ 密碼重置成功！")
                                    st.info(f"🔑 新密碼：{default_password}")
                                    st.info("📧 已發送通知 Email 給相關人員")
                                    st.balloons()
                                else:
                                    st.success(f"✅ 密碼重置成功！")
                                    st.info(f"🔑 新密碼：{default_password}")
                                    st.warning("⚠️ Email 發送失敗，請記錄新密碼")
                                
                    except Exception as e:
                        st.error(f"❌ 重置失敗：{e}")
            else:
                st.error("⚠️ 請填寫所有必填欄位！")
    
    elif auth_mode == "註冊學校帳號":
        # --- 註冊功能 (全新邏輯) ---
        st.subheader("📝 建立學校帳號")
        
        # 按分區分組的學校列表
        schools_by_district = {
            "北一區": [
                "國立羅東高級中學", "國立蘭陽女子高級中學", "國立花蓮高級中學", 
                "慈濟大學附屬高級中學", "國立基隆高級中學", "新北市立中和高級中學",
                "新北市立北大高級中學", "新北市立石碇高級中學", "新北市立板橋高中",
                "新北市立錦和高級中學", "新北市私立徐匯高級中學", "新北市金陵女子高級中學",
                "新北市南山高級中學"
            ],
            "北二區": [
                "國立臺灣師範大學附屬高級中學", "臺北市立中山女子高級中學",
                "臺北市立中正高級中學", "臺北市立中崙高級中學", "臺北市立內湖高級中學",
                "臺北市立永春高級中學", "臺北市立百齡高級中學", "臺北市立育成高級中學",
                "臺北市立松山高級中學", "臺北市立建國高級中學", "臺北市立第一女子高級中學",
                "臺北市立景美女子高級中學", "臺北市立陽明高級中學", "臺北市立萬芳高級中學",
                "臺北市立麗山高級中學", "臺北市數位實驗高級中等學校"
            ],
            "北三區": [
                "桃園市立內壢高級中等學校", "桃園市立桃園高級中等學校", "桃園市立陽明高級中等學校",
                "桃園市立楊梅高級中等學校", "桃園市立壽山高級中等學校", "國立新竹女子高級中學",
                "新竹市私立曙光女子高級中學"
            ],
            "中區": [
                "國立溪湖高級中學", "臺中市立大甲高級中等學校", "臺中市立中港高級中學",
                "臺中市立文華高級中學", "臺中市立清水高級中學", "臺中市立第一高級中學",
                "臺中市立第二高級中學", "臺中市立惠文高級中學", "臺中市立新社高級中學",
                "臺中市立臺中女子高級中等學校", "臺中市私立弘文高級中學", "國立竹山高級中學",
                "國立斗六高級中學", "國立嘉義女子高級中學", "國立嘉義高級中學",
                "嘉義縣立竹崎高級中學"
            ],
            "南區": [
                "國立臺南第一高級中學", "國立臺南第二高級中學", "臺南市天主教聖功女子高級中學",
                "臺南市立大灣高級中學", "臺南市立永仁高級中學", "臺南市光華高級中學",
                "臺南市私立南光高級中學", "臺南市德光高級中學", "高雄市立三民高級中學",
                "高雄市立中山高級中學", "高雄市立前鎮高級中學", "高雄市立高雄女子高級中學",
                "高雄市立路竹高級中學", "國立中山大學附屬國光高級中學", "國立屏東女子高級中學",
                "國立潮州高級中學", "國立臺東高級中學"
            ],
            "其他": [
                "新竹縣立竹北實驗高中"
            ]
        }
        
        # ── 1. 選擇學校名稱 ──
        st.write("### 1. 選擇學校名稱")

        # 代碼快速帶入
        code_input = st.text_input("輸入學校代碼（6碼英數字，可快速帶出學校）",
                                   max_chars=6, placeholder="例：183314")
        code_input = code_input.strip().upper()

        auto_district = None
        auto_school = None
        if len(code_input) == 6:
            matched = SCHOOL_CODE_MAP.get(code_input)
            if matched:
                # 反查是否在可選清單中
                for dist, school_list in schools_by_district.items():
                    if matched in school_list:
                        auto_district = dist
                        auto_school = matched
                        break
                if auto_school:
                    st.success(f"✅ 已找到：**{matched}**（{auto_district}）")
                else:
                    st.info(f"找到學校名稱：**{matched}**，請手動從下方選單選取。")
            else:
                st.error("找不到此代碼對應的學校，請確認代碼是否正確。")

        district_list = list(schools_by_district.keys())
        district_idx = district_list.index(auto_district) if auto_district else 0

        col_d, col_s = st.columns(2)
        with col_d:
            selected_district = st.selectbox("選擇分區", district_list, index=district_idx)
        with col_s:
            schools_in_district = schools_by_district[selected_district]
            school_idx = schools_in_district.index(auto_school) if auto_school and auto_school in schools_in_district else 0
            selected_school = st.selectbox("選擇學校", schools_in_district, index=school_idx)

        district = selected_district
        school_name = selected_school

        st.divider()

        # ── 2. 承辦人資訊 ──
        st.write("### 2. 承辦人資訊")
        col_n, col_ext = st.columns(2)
        with col_n:
            registrant_name = st.text_input("承辦人姓名", placeholder="例：王小明")
        with col_ext:
            registrant_extension = st.text_input("承辦人分機", placeholder="例：123", max_chars=10)

        school_phone = st.text_input("學校電話（作為登入帳號，請含區域號碼）",
                                     placeholder="例：073475181", max_chars=10)
        st.caption("⚠️ 請輸入含區域號碼的完整電話，例如高雄市為 07、台北市為 02")

        default_password = school_phone[-4:] if len(school_phone) >= 4 else ""
        hashed_password = hash_password(default_password) if default_password else ""
        st.info(f"🔒 預設密碼（電話後4碼）：{'**' + default_password + '**' if default_password else '請輸入完整電話號碼'}")

        st.divider()

        # ── 3. 學校重要聯絡人 Email ──
        st.write("### 3. 學校重要聯絡人 Email")
        registrant_email = st.text_input("承辦人 Email")
        academic_director_email = st.text_input("承辦處室主任 Email")
        principal_email = st.text_input("校長 Email")

        if st.button("確認註冊"):
            if not registrant_name:
                st.error("請填寫承辦人姓名")
            elif not school_phone or len(school_phone) < 4:
                st.error("請輸入完整的學校電話號碼（至少4碼）")
            elif not registrant_email or not academic_director_email or not principal_email:
                st.error("請填寫所有聯絡人 Email")
            elif not is_valid_email(registrant_email) or not is_valid_email(academic_director_email) or not is_valid_email(principal_email):
                st.error("請輸入正確的 Email 格式")
            else:
                # 檢查該學校是否已有帳號
                existing_school = supabase.table("schools")\
                    .select("*")\
                    .eq("name", school_name)\
                    .execute()

                if existing_school.data:
                    st.error(f"⚠️ 此學校「{school_name}」已經註冊過帳號了，每校限一個帳號。")
                else:
                    # 檢查電話號碼是否已被使用
                    existing_phone = supabase.table("schools")\
                        .select("*")\
                        .eq("phone", school_phone)\
                        .execute()

                    if existing_phone.data:
                        st.error("⚠️ 此電話號碼已被其他學校使用，請聯繫管理員。")
                    else:
                        new_school = {
                            "name": school_name,
                            "district": district,
                            "phone": school_phone,
                            "password_hash": hashed_password,  # 使用統一的欄位名稱
                            "registrant_name": registrant_name,
                            "registrant_extension": registrant_extension,
                            "registrant_email": registrant_email,  # 統一使用承辦人 Email
                            "academic_director_email": academic_director_email,
                            "principal_email": principal_email,
                            "identity": "學校承辦人",  # 新增身份欄位
                            "is_host": True,
                            "is_partner": True,
                            "is_admin": False
                        }
                        try:
                            data = supabase.table("schools").insert(new_school).execute()
                            st.success(f"🎉 註冊成功！歡迎 {school_name}。")
                            st.info(f"📞 帳號：{school_phone}")
                            st.info(f"🔐 預設密碼：{default_password}")
                            st.balloons()
                        except Exception as e:
                            st.error(f"註冊失敗：{e}")
    
    elif auth_mode == "管理人員登入":
        st.subheader("🔐 管理人員登入")
        admin_username = st.text_input("管理員帳號")
        admin_password = st.text_input("管理員密碼", type="password")
        
        if st.button("管理員登入"):
            try:
                # 從 st.secrets 獲取管理員憑證
                admin_user = st.secrets["ADMIN_USER"]
                admin_password_hash = st.secrets["ADMIN_PASSWORD_HASH"]
                
                if admin_username == admin_user and verify_password(admin_password, admin_password_hash):
                    st.session_state.admin_logged_in = True
                    st.success("🎉 管理員登入成功！")
                    st.rerun()
                else:
                    st.error("❌ 管理員帳號或密碼錯誤！")
            except Exception as e:
                st.error(f"❌ 登入失敗：{e}")
                st.info("⚠️ 請確認 st.secrets 中已設定 ADMIN_USER 和 ADMIN_PASSWORD_HASH")
        
        # 如果管理員已登入，顯示創建管理帳號功能
        if is_admin():
            st.divider()
            st.subheader("👨‍💼 創建管理帳號")
            
            admin_name = st.text_input("管理員姓名", key="admin_name")
            admin_email = st.text_input("管理員 Email", key="admin_email")
            admin_password = st.text_input("管理員密碼", type="password", key="admin_password")
            admin_role = st.selectbox("管理員角色", ["系統管理員", "課程管理員", "審核管理員"], key="admin_role")
            
            if st.button("創建管理帳號"):
                if admin_name and admin_email and admin_password:
                    try:
                        # 雜湊管理員密碼
                        hashed_admin_password = hash_password(admin_password)
                        
                        admin_data = {
                            "name": "管理部門",
                            "registrant_name": admin_name,
                            "registrant_email": admin_email,  # 使用統一的欄位名稱
                            "password_hash": hashed_admin_password,  # 使用統一的欄位名稱
                            "identity": admin_role,
                            "is_host": True,
                            "is_partner": True,
                            "is_admin": True
                        }
                        supabase.table("schools").insert(admin_data).execute()
                        st.success(f"✅ 管理帳號創建成功！{admin_name} ({admin_role})")
                        st.balloons()
                    except Exception as e:
                        st.error(f"創建失敗：{e}")
                else:
                    st.error("請填寫完整的管理員資訊！")
            
            if st.button("🚪 管理員登出"):
                st.session_state.admin_logged_in = False
                st.rerun()

# 修復此處名稱與選單一致
elif choice == "管理中心 (我的課程)":
    require_login()  # 要求登入權限
    st.title("⚙️ 學校管理中心")
    if st.session_state.school_info:
        school = st.session_state.school_info
        st.subheader(f"單位：{school['name']}")
        # 顯示該校已開設的課程
        res = supabase.table("courses").select("*").eq("host_school_id", school['id']).execute()
        if res.data:
            st.write("您已開設的課程：")
            st.table(res.data)
        else:
            st.info("您目前尚未開設任何課程。")

elif choice == "學校基本資料":
    require_login()  # 要求登入權限
    st.header("🏫 學校基本資料管理")
    if st.session_state.school_info:
        school = st.session_state.school_info
        st.subheader(f"學校：{school['name']}")
        
        # 顯示現有資訊
        st.write("### 📋 現有資訊")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"📞 帳號（電話）：{school['phone']}")
            st.info(f"🏫 學校：{school['name']}")
            st.info(f"🗺️ 分區：{school.get('district', '未設定')}")
            
        with col2:
            st.info(f"📧 承辦處室主任 Email：{school.get('academic_director_email', '未設定')}")
            st.info(f"📧 校長 Email：{school.get('principal_email', '未設定')}")
        
        st.divider()
        st.write("### ✏️ 修改資訊")
        
        with st.form("update_school_info"):
            st.write("#### 聯絡人資訊更新")
            new_academic_director_email = st.text_input("承辦處室主任 Email", value=school.get('academic_director_email', ''))
            new_principal_email = st.text_input("校長 Email", value=school.get('principal_email', ''))
            
            st.write("#### 密碼變更")
            current_password = st.text_input("目前密碼", type="password")
            new_password = st.text_input("新密碼", type="password")
            confirm_new_password = st.text_input("確認新密碼", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("更新聯絡資訊"):
                    if new_academic_director_email and new_principal_email:
                        if is_valid_email(new_academic_director_email) and is_valid_email(new_principal_email):
                            try:
                                update_data = {
                                    "academic_director_email": new_academic_director_email,
                                    "principal_email": new_principal_email
                                }
                                supabase.table("schools").update(update_data).eq("id", school['id']).execute()
                                st.success("✅ 聯絡資訊更新成功！")
                                # 更新 session_state
                                st.session_state.school_info.update(update_data)
                                st.rerun()
                            except Exception as e:
                                st.error(f"更新失敗：{e}")
                        else:
                            st.error("請輸入正確的 Email 格式")
                    else:
                        st.error("請填寫所有 Email 欄位")
            
            with col2:
                if st.form_submit_button("更新密碼"):
                    if current_password and new_password and confirm_new_password:
                        # 驗證目前密碼
                        if verify_password(current_password, school['password_hash']):  # 使用統一的欄位名稱
                            if new_password == confirm_new_password:
                                if len(new_password) >= 4:
                                    try:
                                        # 將新密碼雜湊後儲存
                                        hashed_new_password = hash_password(new_password)
                                        supabase.table("schools").update({"password_hash": hashed_new_password}).eq("id", school['id']).execute()  # 使用統一的欄位名稱
                                        st.success("✅ 密碼更新成功！")
                                        st.session_state.school_info['password_hash'] = hashed_new_password  # 更新 session_state
                                    except Exception as e:
                                        st.error(f"密碼更新失敗：{e}")
                                else:
                                    st.error("新密碼至少需要4個字元")
                            else:
                                st.error("新密碼與確認密碼不一致")
                        else:
                            st.error("目前密碼錯誤")
                    else:
                        st.error("請填寫所有密碼欄位")

elif choice == "新增/修改課程":
    require_login()
    st.header("✍️ 管理您的課程")
    if st.session_state.school_info:
        school = st.session_state.school_info
        st.write(f"開課單位：**{school['name']}**")

        tab_add, tab_edit = st.tabs(["➕ 新增課程", "✏️ 修改／刪除課程"])

        # ── 新增課程 ──
        with tab_add:
            with st.form("course_form_add"):
                c_title    = st.text_input("課程名稱")
                c_time     = st.text_input("開課時間", placeholder="例：每週三 14:00-16:00")
                c_students  = st.number_input("跨校學生人數上限", min_value=0, value=20)
                c_schools   = st.number_input("跨校學校數目上限", min_value=0, value=2)
                st.write("**🎓 每校希望學生人數範圍（選填）**")
                col_sps1, col_sps2 = st.columns(2)
                with col_sps1:
                    c_sps_min = st.number_input("最少人數", min_value=0, max_value=5, value=0, key="add_sps_min")
                with col_sps2:
                    c_sps_max = st.number_input("最多人數", min_value=0, max_value=5, value=0, key="add_sps_max")
                c_pdf_file  = st.file_uploader("課程規劃表 PDF（2MB 以內）", type=["pdf"])
                c_syllabus  = st.text_area("課程大綱／內容說明")
                st.write("**📋 開課學校合作要求（選填，最多三點）**")
                c_req1 = st.text_input("要求一", placeholder="例：合作學校需自備視訊設備")
                c_req2 = st.text_input("要求二")
                c_req3 = st.text_input("要求三")
                if st.form_submit_button("確認新增課程"):
                    if not c_title:
                        st.error("請填寫課程名稱。")
                    else:
                        pdf_url = ""
                        if c_pdf_file:
                            pdf_url = upload_pdf(c_pdf_file, school['id']) or ""
                        if c_pdf_file and not pdf_url:
                            pass  # upload_pdf 已顯示錯誤，停止
                        else:
                            try:
                                supabase.table("courses").insert({
                                    "host_school_id": school['id'],
                                    "title": c_title,
                                    "start_time": c_time,
                                    "max_students": c_students,
                                    "max_schools": c_schools,
                                    "sps_min": c_sps_min if c_sps_min > 0 else None,
                                    "sps_max": c_sps_max if c_sps_max > 0 else None,
                                    "plan_pdf_url": pdf_url,
                                    "syllabus": c_syllabus,
                                    "req_1": c_req1 or None,
                                    "req_2": c_req2 or None,
                                    "req_3": c_req3 or None,
                                }).execute()
                                st.success("🎉 課程新增成功！已同步顯示於課程大廳。")
                            except Exception as e:
                                st.error(f"新增失敗：{e}")

        # ── 修改／刪除課程 ──
        with tab_edit:
            try:
                my_courses = supabase.table("courses")\
                    .select("id, title, start_time, max_students, max_schools, syllabus, plan_pdf_url")\
                    .eq("host_school_id", school['id'])\
                    .execute()
                if not my_courses.data:
                    st.info("您目前尚無開設任何課程。")
                else:
                    for c in my_courses.data:
                        with st.expander(f"📖 {c['title']}"):
                            with st.form(f"edit_form_{c['id']}"):
                                e_title    = st.text_input("課程名稱", value=c['title'])
                                e_time     = st.text_input("開課時間", value=c.get('start_time', ''))
                                e_students  = st.number_input("跨校學生人數上限", min_value=0, value=c.get('max_students', 20))
                                e_schools   = st.number_input("跨校學校數目上限", min_value=0, value=c.get('max_schools', 2))
                                st.write("**🎓 每校希望學生人數範圍（選填）**")
                                col_sps1, col_sps2 = st.columns(2)
                                with col_sps1:
                                    e_sps_min = st.number_input("最少人數", min_value=0, max_value=5, value=c.get('sps_min') or 0, key=f"sps_min_{c['id']}")
                                with col_sps2:
                                    e_sps_max = st.number_input("最多人數", min_value=0, max_value=5, value=c.get('sps_max') or 0, key=f"sps_max_{c['id']}")
                                if c.get('plan_pdf_url'):
                                    st.markdown(f"📄 目前 PDF：[查看現有檔案]({c['plan_pdf_url']})")
                                e_pdf_file  = st.file_uploader("更換課程規劃表 PDF（2MB 以內，不上傳則保留原檔）", type=["pdf"], key=f"pdf_{c['id']}")
                                e_syllabus  = st.text_area("課程大綱／內容說明", value=c.get('syllabus', '') or '')
                                st.write("**📋 開課學校合作要求（選填）**")
                                e_req1 = st.text_input("要求一", value=c.get('req_1', '') or '', key=f"req1_{c['id']}")
                                e_req2 = st.text_input("要求二", value=c.get('req_2', '') or '', key=f"req2_{c['id']}")
                                e_req3 = st.text_input("要求三", value=c.get('req_3', '') or '', key=f"req3_{c['id']}")
                                col_save, col_del = st.columns(2)
                                with col_save:
                                    if st.form_submit_button("💾 儲存修改"):
                                        if not e_title:
                                            st.error("課程名稱不得為空。")
                                        else:
                                            new_pdf_url = c.get('plan_pdf_url', '') or ''
                                            if e_pdf_file:
                                                uploaded = upload_pdf(e_pdf_file, school['id'])
                                                if not uploaded:
                                                    st.stop()
                                                new_pdf_url = uploaded
                                            try:
                                                supabase.table("courses").update({
                                                    "title": e_title,
                                                    "start_time": e_time,
                                                    "max_students": e_students,
                                                    "max_schools": e_schools,
                                                    "sps_min": e_sps_min if e_sps_min > 0 else None,
                                                    "sps_max": e_sps_max if e_sps_max > 0 else None,
                                                    "plan_pdf_url": new_pdf_url,
                                                    "syllabus": e_syllabus,
                                                    "req_1": e_req1 or None,
                                                    "req_2": e_req2 or None,
                                                    "req_3": e_req3 or None,
                                                }).eq("id", c['id']).execute()
                                                st.success("✅ 修改已儲存！")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"修改失敗：{e}")
                                with col_del:
                                    if st.form_submit_button("🗑️ 刪除此課程", type="secondary"):
                                        confirm_key = f"del_confirm_{c['id']}"
                                        st.session_state[confirm_key] = True

                            # 刪除二次確認（在 form 外）
                            confirm_key = f"del_confirm_{c['id']}"
                            if st.session_state.get(confirm_key):
                                st.warning(f"⚠️ 確定刪除「{c['title']}」？此操作將同時刪除所有媒合記錄，且**無法復原**。")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("✅ 確認刪除", key=f"yes_del_{c['id']}", type="primary"):
                                        try:
                                            delete_course_cascade(c['id'])
                                            st.session_state[confirm_key] = False
                                            st.success(f"已刪除「{c['title']}」。")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"刪除失敗：{e}")
                                with col_no:
                                    if st.button("❌ 取消", key=f"no_del_{c['id']}"):
                                        st.session_state[confirm_key] = False
                                        st.rerun()
            except Exception as e:
                st.error(f"讀取課程失敗：{e}")

elif choice == "配對情形":
    require_login()  # 要求登入權限
    st.header("🤝 課程配對進度追蹤")
    school = st.session_state.school_info
    
    # 分成兩個區塊：我是開課端 / 我是申請端
    tab1, tab2 = st.tabs(["我是開課學校 (收到的申請)", "我是合作學校 (寄出的申請)"])
    
    with tab1:
        st.subheader("📩 收到其他學校的配對請求")
        try:
            # Step 1: 取得我開的所有課程
            my_courses_res = supabase.table("courses")\
                .select("id, title, max_schools")\
                .eq("host_school_id", school['id'])\
                .execute()
            my_course_ids = [c['id'] for c in my_courses_res.data]
            my_course_map = {c['id']: c for c in my_courses_res.data}

            if my_course_ids:
                # Step 2: 查詢這些課程收到的申請
                incoming = supabase.table("matches")\
                    .select("id, status, course_id, partner_school_id")\
                    .in_("course_id", my_course_ids)\
                    .execute()

                # Step 3: 批次取得申請學校名稱
                partner_ids = list({m['partner_school_id'] for m in incoming.data})
                partner_map = {}
                if partner_ids:
                    schools_res = supabase.table("schools")\
                        .select("id, name, registrant_name, registrant_email, academic_director_email, principal_email")\
                        .in_("id", partner_ids)\
                        .execute()
                    partner_map = {s['id']: s for s in schools_res.data}

                if incoming.data:
                    for m in incoming.data:
                        course = my_course_map.get(m['course_id'], {})
                        course_title = course.get('title', '未知課程')
                        max_schools = course.get('max_schools', 2)
                        partner_info = partner_map.get(m['partner_school_id'], {})
                        partner_name = partner_info.get('name', '未知學校') if isinstance(partner_info, dict) else partner_info
                        status = m['status']

                        status_label = {"pending": "⏳ 待審核", "approved": "✅ 媒合成功", "rejected": "😔 媒合被婉拒"}.get(status, status)

                        with st.container(border=True):
                            st.write(f"**{partner_name}** 申請了「{course_title}」　{status_label}")

                            if status == "pending":
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ 確認正式合作", key=f"approve_{m['id']}"):
                                        approved_count = len([x for x in incoming.data
                                                              if x['course_id'] == m['course_id'] and x['status'] == 'approved'])
                                        if approved_count >= max_schools:
                                            st.error(f"已達合作學校上限（{max_schools} 所），無法再核准。")
                                        else:
                                            supabase.table("matches").update({"status": "approved"}).eq("id", m['id']).execute()
                                            # 寄信給申請學校三位收件人
                                            for recipient_email, recipient_name in [
                                                (partner_info.get('registrant_email'), partner_info.get('registrant_name', '承辦人')),
                                                (partner_info.get('academic_director_email'), '承辦處室主任'),
                                                (partner_info.get('principal_email'), '校長'),
                                            ]:
                                                if is_valid_email(recipient_email):
                                                    send_email(
                                                        recipient_email, recipient_name,
                                                        f"媒合成功通知：您的課程申請「{course_title}」已被核准",
                                                        f"親愛的 {recipient_name}：\n\n恭喜！{partner_name} 對課程「{course_title}」的媒合申請已獲得開課學校「{school['name']}」正式核准，雙方合作正式成立。\n\n【開課學校聯絡資訊】\n- 承辦人姓名：{school.get('registrant_name', '未提供')}\n- 承辦人 Email：{school.get('registrant_email', '未提供')}\n- 承辦處室主任 Email：{school.get('academic_director_email', '未提供')}\n- 學校電話：{school.get('phone', '未提供')}\n- 承辦人分機：{school.get('registrant_extension', '未提供')}\n\n請盡快與開課學校聯繫，確認後續合作細節。\n\n跨校課程媒合平台"
                                                    )
                                            st.success(f"已確認與 {partner_name} 正式合作，通知 Email 已發送！")
                                            st.rerun()
                                with col2:
                                    if st.button("❌ 拒絕", key=f"reject_{m['id']}"):
                                        supabase.table("matches").update({"status": "rejected"}).eq("id", m['id']).execute()
                                        # 寄信給申請學校三位收件人
                                        for recipient_email, recipient_name in [
                                            (partner_info.get('registrant_email'), partner_info.get('registrant_name', '承辦人')),
                                            (partner_info.get('academic_director_email'), '承辦處室主任'),
                                            (partner_info.get('principal_email'), '校長'),
                                        ]:
                                            if is_valid_email(recipient_email):
                                                send_email(
                                                    recipient_email, recipient_name,
                                                    f"媒合申請通知：「{course_title}」申請未獲通過",
                                                    f"親愛的 {recipient_name}：\n\n很遺憾，{partner_name} 對課程「{course_title}」的媒合申請已被開課學校「{school['name']}」婉拒。\n\n跨校課程媒合平台"
                                                )
                                        st.warning(f"已婉拒 {partner_name} 的申請，通知 Email 已發送。")
                                        st.rerun()
                else:
                    st.write("目前尚無收到申請。")
            else:
                st.write("目前尚無收到申請。")
        except Exception as e:
            st.error(f"讀取失敗（Tab1）：{e}")

    with tab2:
        st.subheader("📤 已寄出的配對請求")
        try:
            # Step 1: 查詢我申請的 matches（含 course_id）
            outgoing = supabase.table("matches")\
                .select("id, status, course_id")\
                .eq("partner_school_id", school['id'])\
                .execute()

            if outgoing.data:
                # Step 2: 批次取得課程與開課學校名稱
                course_ids = list({m['course_id'] for m in outgoing.data})
                courses_res = supabase.table("courses")\
                    .select("id, title, host_school_id")\
                    .in_("id", course_ids)\
                    .execute()
                course_map = {c['id']: c for c in courses_res.data}

                host_ids = list({c['host_school_id'] for c in courses_res.data})
                host_res = supabase.table("schools")\
                    .select("id, name")\
                    .in_("id", host_ids)\
                    .execute()
                host_map = {s['id']: s['name'] for s in host_res.data}

                for m in outgoing.data:
                    course = course_map.get(m['course_id'], {})
                    host_name = host_map.get(course.get('host_school_id'), '未知學校')
                    status_label = {"pending": "⏳ 審核中", "approved": "🎉 媒合成功", "rejected": "😔 媒合被婉拒"}.get(m['status'], m['status'])
                    if m['status'] == 'approved':
                        st.success(f"🎉 **媒合成功**　您與 **{host_name}** 的「{course.get('title', '未知課程')}」合作已確認！")
                    elif m['status'] == 'rejected':
                        st.warning(f"😔 **媒合被婉拒**　您向 **{host_name}** 申請的「{course.get('title', '未知課程')}」未獲通過。")
                    else:
                        st.info(f"⏳ **審核中**　您向 **{host_name}** 申請了「{course.get('title', '未知課程')}」，請等候回覆。")
            else:
                st.write("您尚未申請任何課程。")
        except Exception as e:
            st.error(f"讀取失敗（Tab2）：{e}")

# 管理員專用頁面
elif choice == "📊 系統管理":
    require_admin()
    st.title("📊 系統管理")

    ALL_SCHOOLS_BY_DISTRICT = {
        "北一區": ["國立羅東高級中學","國立蘭陽女子高級中學","國立花蓮高級中學","慈濟大學附屬高級中學","國立基隆高級中學","新北市立中和高級中學","新北市立北大高級中學","新北市立石碇高級中學","新北市立板橋高中","新北市立錦和高級中學","新北市私立徐匯高級中學","新北市金陵女子高級中學","新北市南山高級中學"],
        "北二區": ["國立臺灣師範大學附屬高級中學","臺北市立中山女子高級中學","臺北市立中正高級中學","臺北市立中崙高級中學","臺北市立內湖高級中學","臺北市立永春高級中學","臺北市立百齡高級中學","臺北市立育成高級中學","臺北市立松山高級中學","臺北市立建國高級中學","臺北市立第一女子高級中學","臺北市立景美女子高級中學","臺北市立陽明高級中學","臺北市立萬芳高級中學","臺北市立麗山高級中學","臺北市數位實驗高級中等學校"],
        "北三區": ["桃園市立內壢高級中等學校","桃園市立桃園高級中等學校","桃園市立陽明高級中等學校","桃園市立楊梅高級中等學校","桃園市立壽山高級中等學校","國立新竹女子高級中學","新竹市私立曙光女子高級中學"],
        "中區": ["國立溪湖高級中學","臺中市立大甲高級中等學校","臺中市立中港高級中學","臺中市立文華高級中學","臺中市立清水高級中學","臺中市立第一高級中學","臺中市立第二高級中學","臺中市立惠文高級中學","臺中市立新社高級中學","臺中市立臺中女子高級中等學校","臺中市私立弘文高級中學","國立竹山高級中學","國立斗六高級中學","國立嘉義女子高級中學","國立嘉義高級中學","嘉義縣立竹崎高級中學"],
        "南區": ["國立臺南第一高級中學","國立臺南第二高級中學","臺南市天主教聖功女子高級中學","臺南市立大灣高級中學","臺南市立永仁高級中學","臺南市光華高級中學","臺南市私立南光高級中學","臺南市德光高級中學","高雄市立三民高級中學","高雄市立中山高級中學","高雄市立前鎮高級中學","高雄市立高雄女子高級中學","高雄市立路竹高級中學","國立中山大學附屬國光高級中學","國立屏東女子高級中學","國立潮州高級中學","國立臺東高級中學"],
        "其他": ["新竹縣立竹北實驗高中"],
    }

    tab1, tab2 = st.tabs(["🏫 學校帳號基本資訊", "🤝 配對狀況"])

    # ── Tab 1：學校帳號基本資訊 ──
    with tab1:
        try:
            all_schools_res = supabase.table("schools").select("*").execute()
            registered = [s for s in all_schools_res.data if not s.get("is_admin", False)]
            registered_names = {s["name"] for s in registered}

            district_options = ["全部"] + list(ALL_SCHOOLS_BY_DISTRICT.keys())
            sel_district = st.selectbox("🗺️ 篩選分區", district_options, key="admin_district_filter")

            st.subheader("✅ 已註冊學校")
            filtered_registered = [
                s for s in registered
                if sel_district == "全部" or s.get("district") == sel_district
            ]
            if filtered_registered:
                for account in filtered_registered:
                    with st.expander(f"🏫 {account['name']}　（{account.get('district','未分區')}）"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**📋 基本資料**")
                            st.write(f"帳號（電話）：{account.get('phone','—')}")
                            st.write(f"分機：{account.get('registrant_extension','—')}")
                            st.write(f"承辦人：{account.get('registrant_name','—')}")
                            st.write(f"承辦人 Email：{account.get('registrant_email','—')}")
                        with col2:
                            st.write("**📧 主管信箱**")
                            st.write(f"承辦處室主任：{account.get('academic_director_email','—')}")
                            st.write(f"校長：{account.get('principal_email','—')}")
                            st.write("**🎓 權限**")
                            st.write(f"開課：{'✅' if account.get('is_host') else '❌'}　合作：{'✅' if account.get('is_partner') else '❌'}")
                        st.divider()
                        delete_key = f"confirm_delete_school_{account['id']}"
                        if delete_key not in st.session_state:
                            st.session_state[delete_key] = False
                        if not st.session_state[delete_key]:
                            if st.button(f"🗑️ 刪除「{account['name']}」", key=f"del_school_{account['id']}", type="secondary"):
                                st.session_state[delete_key] = True
                                st.rerun()
                        else:
                            st.warning(f"⚠️ 確定要刪除「{account['name']}」？將同時刪除所有課程與媒合記錄，且**無法復原**。")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("✅ 確認刪除", key=f"yes_school_{account['id']}", type="primary"):
                                    try:
                                        delete_school_cascade(account["id"])
                                        st.success(f"已刪除「{account['name']}」。")
                                        st.session_state[delete_key] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"刪除失敗：{e}")
                            with col_no:
                                if st.button("❌ 取消", key=f"no_school_{account['id']}"):
                                    st.session_state[delete_key] = False
                                    st.rerun()
            else:
                st.info("此分區尚無已註冊學校。")

            st.subheader("⬜ 尚未註冊學校")
            unregistered_found = False
            for district, names in ALL_SCHOOLS_BY_DISTRICT.items():
                if sel_district != "全部" and district != sel_district:
                    continue
                missing = [n for n in names if n not in registered_names]
                if missing:
                    unregistered_found = True
                    st.write(f"**{district}**：" + "、".join(missing))
            if not unregistered_found:
                st.info("所有學校皆已註冊帳號。")

        except Exception as e:
            st.error(f"讀取失敗：{e}")

    # ── Tab 2：配對狀況 ──
    with tab2:
        try:
            courses_res = supabase.table("courses")                .select("id, title, max_schools, host_school_id, schools(name)")                .execute()

            matches_res = supabase.table("matches")                .select("id, course_id, partner_school_id, status")                .execute()
            all_matches = matches_res.data

            partner_ids = list({m["partner_school_id"] for m in all_matches})
            partner_map = {}
            if partner_ids:
                p_res = supabase.table("schools").select("id, name").in_("id", partner_ids).execute()
                partner_map = {s["id"]: s["name"] for s in p_res.data}

            st.subheader("📤 開課學校配對狀況")
            if courses_res.data:
                host_courses: dict = {}
                for c in courses_res.data:
                    sname = c["schools"]["name"]
                    host_courses.setdefault(sname, []).append(c)

                for school_name, courses_list in host_courses.items():
                    st.write(f"**🏫 {school_name}**")
                    for c in courses_list:
                        c_matches = [m for m in all_matches if m["course_id"] == c["id"]]
                        approved = sum(1 for m in c_matches if m["status"] == "approved")
                        pending  = sum(1 for m in c_matches if m["status"] == "pending")
                        max_s    = c.get("max_schools", 2)
                        if approved >= max_s:
                            badge = f"🔴 {approved}/{max_s} 已配對額滿"
                        elif approved > 0:
                            badge = f"🟡 {approved}/{max_s} 仍有配對名額"
                        else:
                            badge = f"⚪ 0/{max_s} 尚無配對學校"
                        st.write(f"　　📖 {c['title']}　{badge}　⏳待審核 {pending} 所")
                    st.divider()
            else:
                st.info("目前尚無任何課程。")

            st.subheader("📥 申請學校配對狀況")
            if all_matches:
                from collections import defaultdict
                stats: dict = defaultdict(lambda: {"total": 0, "approved": 0})
                for m in all_matches:
                    stats[m["partner_school_id"]]["total"] += 1
                    if m["status"] == "approved":
                        stats[m["partner_school_id"]]["approved"] += 1
                for pid, s in stats.items():
                    sname = partner_map.get(pid, f"學校 {pid}")
                    st.write(f"**{sname}**　共送出 {s['total']} 次申請，已成功配對 {s['approved']} 次")
            else:
                st.info("目前尚無任何媒合申請記錄。")

        except Exception as e:
            st.error(f"讀取配對資料失敗：{e}")
