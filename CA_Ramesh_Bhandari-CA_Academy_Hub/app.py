import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from PIL import Image
import io
import pypdf
import time
from google import genai
from google.genai import types
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="CA Academy Mentorship Hub", page_icon="🎓", layout="wide")

# ==============================================================================
# PROFESSIONAL STYLING & INSTITUTIONAL THEME INJECTION
# ==============================================================================
st.markdown("""
<style>
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .academy-header-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #F8FAFC;
        padding: 24px 32px;
        border-radius: 12px;
        border-left: 6px solid #D97706;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .academy-header-title {
        font-size: 26px;
        font-weight: 700;
        margin-bottom: 4px;
        color: #FFFFFF;
    }
    .academy-header-sub {
        font-size: 14px;
        color: #94A3B8;
        letter-spacing: 0.3px;
    }
    .hero-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        color: #FFFFFF;
        padding: 40px 36px;
        border-radius: 16px;
        border-bottom: 5px solid #D97706;
        margin-bottom: 28px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .hero-title {
        font-size: 32px;
        font-weight: 800;
        color: #FFFFFF;
        margin-bottom: 8px;
    }
    .hero-subtitle {
        font-size: 16px;
        color: #CBD5E1;
        line-height: 1.6;
    }
    .feature-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.06);
    }
    .feature-title {
        font-weight: 700;
        font-size: 17px;
        color: #0F172A;
        margin-bottom: 6px;
    }
    .feature-desc {
        font-size: 13px;
        color: #64748B;
        line-height: 1.5;
    }
    div.stButton > button:first-child {
        background: linear-gradient(180deg, #1E3A8A 0%, #172554 100%);
        color: #FFFFFF;
        font-weight: 600;
        border-radius: 8px;
        border: 1px solid #1E3A8A;
        padding: 8px 18px;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:first-child:hover {
        background: #1D4ED8;
        border-color: #1D4ED8;
        color: #FFFFFF;
        box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25);
        transform: translateY(-1px);
    }
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
        color: #0F172A;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #E2E8F0;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        font-weight: 600;
        font-size: 14px;
        color: #64748B;
        border-radius: 8px 8px 0px 0px;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        color: #1E3A8A !important;
        border-bottom: 3px solid #D97706 !important;
    }
    [data-testid="stForm"], [data-testid="stExpander"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# OFFICIAL CA SYLLABUS MAPPING (Foundation: 4, Inter: 6, Final: 6)
# ==============================================================================
CA_SYLLABUS = {
    "CA Foundation": [
        "Paper 1: Accounting",
        "Paper 2: Business Laws",
        "Paper 3: Quantitative Aptitude (Maths, Stats & LR)",
        "Paper 4: Business Economics"
    ],
    "CA Intermediate": [
        "Paper 1: Advanced Accounting",
        "Paper 2: Corporate and Other Laws",
        "Paper 3: Taxation (Direct Tax & GST)",
        "Paper 4: Cost and Management Accounting",
        "Paper 5: Auditing and Ethics",
        "Paper 6: Financial Management and Strategic Management (FM & SM)"
    ],
    "CA Final": [
        "Paper 1: Financial Reporting (FR)",
        "Paper 2: Advanced Financial Management (AFM)",
        "Paper 3: Advanced Auditing, Assurance and Professional Ethics",
        "Paper 4: Direct Tax Laws and International Taxation",
        "Paper 5: Indirect Tax Laws (GST & Customs)",
        "Paper 6: Integrated Business Solutions (Multi-Disciplinary Case Study)"
    ]
}

# ==============================================================================
# SQLITE PERSISTENT DATABASE SETUP
# ==============================================================================
DB_FILE = "ca_academy.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            name TEXT,
            email TEXT,
            level TEXT,
            status TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            test_id TEXT PRIMARY KEY,
            level TEXT,
            subject TEXT,
            topic TEXT,
            max_marks INTEGER,
            time_allowed_mins INTEGER,
            questions TEXT,
            suggested_solution TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            sub_id TEXT PRIMARY KEY,
            test_id TEXT,
            student_username TEXT,
            subject TEXT,
            topic TEXT,
            student_answer TEXT,
            has_image INTEGER,
            image_blob BLOB,
            max_marks INTEGER,
            score INTEGER,
            eval_feedback TEXT,
            status TEXT,
            submission_time TEXT,
            graded_date TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS student_doubts (
            doubt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_username TEXT,
            student_name TEXT,
            level TEXT,
            subject TEXT,
            question TEXT,
            ai_response TEXT,
            teacher_remark TEXT,
            created_at TEXT
        )
    ''')
    
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        seed_users = [
            ("admin", "123", "Teacher", "Prof. Ramesh Bhandari", "admin@academy.com", "Faculty", "Active"),
            ("stu101", "123", "Student", "Aarav Sharma", "aarav@academy.com", "CA Intermediate", "Active"),
            ("stu102", "123", "Student", "Priya Verma", "priya@academy.com", "CA Final", "Pending"),
            ("stu103", "123", "Student", "Rohan Gupta", "rohan@academy.com", "CA Foundation", "Active")
        ]
        c.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", seed_users)
        
        seed_tests = [
            ("TEST101", "CA Intermediate", "Paper 2: Corporate and Other Laws", "Board Meetings & Quorum", 20, 30,
             "Question 1 (10 Marks):\nExplain the provisions regarding convening of Board Meetings via Video Conferencing under Section 173 of the Companies Act, 2013 read with relevant rules.\n\nQuestion 2 (10 Marks):\nState the statutory quorum requirements under Section 174 of the Companies Act, 2013 for a public limited company having 9 directors.",
             "Suggested Solution (TEST101):\n1. Section 173(2) allows video conferencing provided roll call, audio-visual recording, and security measures are maintained.\n2. Section 174 requires 1/3rd of total strength (3 directors) or 2 directors, whichever is higher. Therefore, quorum is 3 directors."),
            ("TEST102", "CA Intermediate", "Paper 1: Advanced Accounting", "Consolidation of Financial Statements", 20, 30,
             "Question 1 (20 Marks):\nExplain the accounting treatment of Unrealized Profit on intra-group inventory transfers between Parent and Subsidiary under Ind AS 110.",
             "Suggested Solution (TEST102):\nEliminate 100% of the unrealized profit from consolidated financial statements by debiting parent/subsidiary retained earnings (depending on upstream/downstream) and crediting consolidated inventory balance.")
        ]
        c.executemany("INSERT INTO tests VALUES (?, ?, ?, ?, ?, ?, ?, ?)", seed_tests)
        
        seed_submissions = [
            ("SUB001", "TEST101", "stu101", "Paper 2: Corporate and Other Laws", "Board Meetings & Quorum",
             "Board meetings can be held via video conferencing. Quorum requires at least 2 directors or one-third.",
             0, None, 20, 14, "Good fundamental understanding. Cite Section 173 and 174 specifically next time for full marks.", "Graded", "2026-08-20 10:30:00", "2026-08-20"),
            ("SUB002", "TEST102", "stu101", "Paper 1: Advanced Accounting", "Consolidation of Financial Statements",
             "Unrealized profit on inventory must be fully eliminated against consolidated profits.",
             0, None, 20, 9, "Needs thorough revision of intra-group transaction eliminations under Ind AS 110.", "Graded", "2026-08-25 14:15:00", "2026-08-25")
        ]
        c.executemany("INSERT INTO submissions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", seed_submissions)
        
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_FILE)

if "current_user" not in st.session_state:
    st.session_state.current_user = None

# ==============================================================================
# AI HELPER FUNCTION
# ==============================================================================
def call_gemini(prompt, system_instruction, api_key, image=None):
    if not api_key:
        return "ERROR: Missing Gemini API Key. Please provide a valid key in the sidebar."
    
    try:
        client = genai.Client(api_key=api_key)
        contents = []
        if image is not None:
            contents.append(image)
        contents.append(prompt)
        
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2
                    )
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                if attempt == 0 and ("503" in str(e) or "429" in str(e)):
                    time.sleep(2)
                    continue
                return f"ERROR: {str(e)}"
        return "⚠️ Service currently busy. Please try again."
    except Exception as e:
        return f"ERROR: {str(e)}"

# ==============================================================================
# SIDEBAR AUTHENTICATION & ACCESS
# ==============================================================================
with st.sidebar:
    st.title("🎓 CA Academy Portal")
    api_key = st.text_input("Gemini API Key", type="password", help="Enter free key from Google AI Studio")
    st.markdown("---")

    if st.session_state.current_user is None:
        auth_mode = st.radio("Access Portal", ["Sign In", "Sign Up (New Member)", "Forgot / Reset Password"])

        # 1. Sign In
        if auth_mode == "Sign In":
            st.subheader("Login Credentials")
            with st.form("signin_form", clear_on_submit=False):
                uname = st.text_input("Username").strip()
                pwd = st.text_input("Password", type="password").strip()
                role_login = st.selectbox("Role", ["Student", "Teacher"])
                
                submitted_login = st.form_submit_button("Sign In", use_container_width=True)

                if submitted_login:
                    if not uname or not pwd:
                        st.error("Please enter both username and password.")
                    else:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("SELECT username, password, role, name, email, level, status FROM users WHERE LOWER(username) = ? AND password = ? AND role = ?", (uname.lower(), pwd, role_login))
                        row = c.fetchone()
                        conn.close()

                        if row:
                            user_dict = {"username": row[0], "password": row[1], "role": row[2], "name": row[3], "email": row[4], "level": row[5], "status": row[6]}
                            if user_dict["status"] == "Pending":
                                st.warning("⏳ Your application is pending approval from the Head Administrator.")
                            elif user_dict["status"] == "Disabled":
                                st.error("🚫 Your account has been suspended by the administrator.")
                            else:
                                st.session_state.current_user = user_dict
                                st.success(f"Welcome back, {user_dict['name']}!")
                                st.rerun()
                        else:
                            st.error("Invalid credentials or role selected.")

        # 2. Sign Up
        elif auth_mode == "Sign Up (New Member)":
            st.subheader("Academy Registration")
            with st.form("signup_form", clear_on_submit=True):
                signup_role = st.selectbox("Registering As:", ["Student", "Teacher"])
                new_uname = st.text_input("Choose Username").strip()
                new_name = st.text_input("Full Name").strip()
                new_email = st.text_input("Email Address").strip()
                new_pwd = st.text_input("Create Password", type="password").strip()
                
                if signup_role == "Student":
                    new_level = st.selectbox("CA Program Level", list(CA_SYLLABUS.keys()))
                else:
                    new_level = "Faculty"
                
                submitted_signup = st.form_submit_button("Submit Registration", use_container_width=True)
                if submitted_signup:
                    if not (new_uname and new_name and new_email and new_pwd):
                        st.error("Please fill in all registration fields.")
                    else:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE LOWER(username) = ?", (new_uname.lower(),))
                        if c.fetchone():
                            st.error("Username already registered. Choose another.")
                        else:
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", (new_uname, new_pwd, signup_role, new_name, new_email, new_level, "Pending"))
                            conn.commit()
                            st.success("✅ Application submitted! Please wait for Head Admin approval before logging in.")
                        conn.close()

        # 3. Forgot Password
        elif auth_mode == "Forgot / Reset Password":
            st.subheader("Reset Password")
            with st.form("forgot_password_form", clear_on_submit=False):
                reset_uname = st.text_input("Registered Username").strip()
                reset_email = st.text_input("Registered Email").strip()
                new_pass = st.text_input("Enter New Password", type="password").strip()
                confirm_pass = st.text_input("Confirm New Password", type="password").strip()
                
                submitted_reset = st.form_submit_button("Update Password", use_container_width=True)
                if submitted_reset:
                    if not (reset_uname and reset_email and new_pass and confirm_pass):
                        st.error("Please fill in all fields.")
                    elif new_pass != confirm_pass:
                        st.error("Passwords do not match.")
                    else:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE LOWER(username) = ? AND LOWER(email) = ?", (reset_uname.lower(), reset_email.lower()))
                        row = c.fetchone()
                        if not row:
                            st.error("No account matching that username and registered email address.")
                        else:
                            c.execute("UPDATE users SET password = ? WHERE LOWER(username) = ?", (new_pass, reset_uname.lower()))
                            conn.commit()
                            st.success("✅ Password updated successfully! You can now select 'Sign In' to log in.")
                        conn.close()

    else:
        st.success(f"👤 **{st.session_state.current_user['name']}**")
        st.caption(f"Role: **{st.session_state.current_user['role']}** | User: `{st.session_state.current_user['username']}`")
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()
        st.markdown("---")

# ==============================================================================
# MAIN APPLICATION INTERFACES
# ==============================================================================

# ------------------------------------------------------------------------------
# 0. PUBLIC / UN-AUTHENTICATED LANDING PAGE
# ------------------------------------------------------------------------------
if st.session_state.current_user is None:
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🎓 CA Academy Mentorship & Examination Hub</div>
        <div class="hero-subtitle">
            An advanced institutional AI platform for Chartered Accountancy coaching institutes and candidates.
            Built with multimodal vision evaluation, structured test management, and real-time faculty-student mentorship.
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">📚 Official ICAI Alignment</div>
            <div class="feature-desc">Dynamic syllabus mapping across CA Foundation (4 Papers), CA Intermediate (6 Papers), and CA Final (6 Papers).</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">✍️ Multimodal Paper Grading</div>
            <div class="feature-desc">Students upload physical handwritten answer sheet scans; multimodal AI evaluates working notes with step marking.</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">🎯 Exemption & Gap Analytics</div>
            <div class="feature-desc">Dynamic tracking against 40% passing cutoffs and 60% exemption benchmarks with interactive aggregate visualization.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_info1, col_info2 = st.columns([3, 2])
    with col_info1:
        st.markdown("### 🏛️ Academy Workflow & Governance Architecture")
        st.markdown("""
        * **Faculty-Controlled Admissions:** New registrations remain pending until vetted and activated by faculty.
        * **Confidential Model Solutions:** Exam suggested solutions remain locked until after faculty evaluations are finalized.
        * **Two-Way Doubt Clearing:** Real-time synchronization where student questions answered by the AI mentor are logged for faculty endorsement.
        * **Persistent Storage:** All student rosters, tests, answer sheets, and grades are permanently saved to a persistent SQLite database.
        """)
    with col_info2:
        st.info("""
        **👉 Getting Started:**
        1. Select **Sign In** from the sidebar to access pre-seeded accounts:
           * **Teacher:** `admin` / `123`
           * **Student:** `stu101` / `123`
        2. Or submit a new admission application via **Sign Up (New Member)**.
        3. Enter your Gemini API Key in the sidebar to activate AI capabilities.
        """)

# ------------------------------------------------------------------------------
# 1. TEACHER / ADMIN DASHBOARD
# ------------------------------------------------------------------------------
elif st.session_state.current_user["role"] == "Teacher":
    st.markdown(f"""
    <div class="academy-header-card">
        <div class="academy-header-title">👨‍🏫 Academy Faculty & Administration Hub</div>
        <div class="academy-header-sub">Faculty In-Charge: <b>{st.session_state.current_user['name']}</b> | Status: <b>Active Administrator</b></div>
    </div>
    """, unsafe_allow_html=True)
    
    t_tabs = st.tabs([
        "👥 Admissions & Faculty Roster", 
        "📝 Create Test Paper (AI or PDF)", 
        "⚖️ Evaluate Submissions (Text/OCR)", 
        "💬 Student Doubts & Mentorship Q&A", 
        "📊 Academy Analytics", 
        "🔒 Change Password"
    ])

    # 1. Admissions & Faculty Roster
    with t_tabs[0]:
        st.subheader("👥 Admissions & Staff Management")
        with st.expander("➕ Register a New Faculty Member / Teacher Directly", expanded=False):
            with st.form("add_faculty_form", clear_on_submit=True):
                f_uname = st.text_input("Teacher Username").strip()
                f_name = st.text_input("Teacher Full Name (e.g., Prof. Sharma)").strip()
                f_email = st.text_input("Teacher Email").strip()
                f_pwd = st.text_input("Temporary Password", type="password").strip()
                f_submit = st.form_submit_button("Induct Faculty Member Immediately")
                
                if f_submit:
                    if not (f_uname and f_name and f_email and f_pwd):
                        st.error("Please fill in all faculty fields.")
                    else:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE LOWER(username) = ?", (f_uname.lower(),))
                        if c.fetchone():
                            st.error("Username already registered.")
                        else:
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", (f_uname, f_pwd, "Teacher", f_name, f_email, "Faculty", "Active"))
                            conn.commit()
                            st.success(f"✅ Faculty member '{f_name}' has been created with Active status! They can now log in.")
                            st.rerun()
                        conn.close()

        st.markdown("---")
        conn = get_db_connection()
        members_df = pd.read_sql_query("SELECT username, name, email, role, level, status FROM users WHERE username != 'admin'", conn)
        conn.close()
        
        st.write("### 📋 Academy User Registry (Students & Teachers)")
        for idx, row in members_df.iterrows():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            c1.write(f"**{row['name']}** (`{row['username']}`)")
            c2.write(f"Role: **{row['role']}** ({row['level']})")
            c3.write(f"Status: `{row['status']}`")
            with c4:
                if row["status"] == "Pending":
                    if st.button(f"Approve {row['role']}", key=f"app_{idx}"):
                        conn = get_db_connection()
                        conn.execute("UPDATE users SET status = 'Active' WHERE username = ?", (row["username"],))
                        conn.commit()
                        conn.close()
                        st.rerun()
                elif row["status"] == "Active":
                    if st.button("Disable Access", key=f"dis_{idx}"):
                        conn = get_db_connection()
                        conn.execute("UPDATE users SET status = 'Disabled' WHERE username = ?", (row["username"],))
                        conn.commit()
                        conn.close()
                        st.rerun()
                elif row["status"] == "Disabled":
                    if st.button("Re-enable Access", key=f"en_{idx}"):
                        conn = get_db_connection()
                        conn.execute("UPDATE users SET status = 'Active' WHERE username = ?", (row["username"],))
                        conn.commit()
                        conn.close()
                        st.rerun()
            st.divider()

    # 2. Test Paper Creator
    with t_tabs[1]:
        st.subheader("Create Academy Test Paper")
        create_mode = st.radio("Choose Test Paper Creation Method:", ["✨ Generate Automatically with AI", "📄 Upload Custom PDF / Type Own Test Paper"], horizontal=True)
        
        col1, col2 = st.columns(2)
        with col1:
            t_lvl = st.selectbox("Course Level", list(CA_SYLLABUS.keys()), key="t_gen_lvl")
            available_subjects = CA_SYLLABUS[t_lvl]
            t_sub = st.selectbox("Select Subject", available_subjects, key="t_gen_sub")
            t_top = st.text_input("Topic / Chapter Name", "Audit and Auditors (Sec 139-148)")
            t_m = st.number_input("Maximum Marks", 10, 100, 20, step=5)
            t_mins = st.number_input("Allotted Exam Time (Minutes)", 15, 180, 30, step=5)

        if create_mode == "✨ Generate Automatically with AI":
            with col2:
                st.info("AI will generate real ICAI-standard case study & numerical questions along with a faculty model answer key.")
                if st.button("🚀 Generate & Publish AI Test Paper"):
                    if not api_key:
                        st.error("Please enter your Gemini API Key in the left sidebar to generate tests.")
                    else:
                        with st.spinner("Drafting comprehensive questions and step-wise marking scheme..."):
                            sys_prompt = f"You are a master faculty member teaching {t_lvl} - {t_sub} at a premier CA Coaching Academy. Draft realistic, challenging exam questions and an exact internal suggested answer key."
                            user_p = f"""Create an official coaching academy test paper of {t_m} marks for {t_lvl} on the subject '{t_sub}' and topic '{t_top}'.
Include 2 to 3 realistic examination questions (case-studies/practical numericals).
Separate the questions and suggested solution using the exact delimiter strings below:

===QUESTIONS===
(Write the question paper here)
===SOLUTION===
(Write the step-by-step suggested solution with marks breakdown here)"""

                            ai_out = call_gemini(user_p, sys_prompt, api_key)
                            
                            if ai_out.startswith("ERROR:") or ai_out.startswith("⚠️"):
                                st.error(ai_out)
                            else:
                                if "===SOLUTION===" in ai_out:
                                    parts = ai_out.split("===SOLUTION===")
                                    q_part = parts[0].replace("===QUESTIONS===", "").strip()
                                    a_part = parts[1].strip()
                                else:
                                    q_part = ai_out.replace("===QUESTIONS===", "").strip()
                                    a_part = "Faculty Model Solution & Step Marking Key generated."
                                
                                conn = get_db_connection()
                                c = conn.cursor()
                                c.execute("SELECT COUNT(*) FROM tests")
                                count = c.fetchone()[0]
                                new_test_id = f"TEST{count + 101}"
                                c.execute("INSERT INTO tests VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (new_test_id, t_lvl, t_sub, t_top, t_m, t_mins, q_part, a_part))
                                conn.commit()
                                conn.close()
                                st.success(f"✅ AI Test Paper `{new_test_id}` successfully created and assigned to {t_lvl} students!")
                                st.rerun()

        else:
            with col2:
                st.info("Upload your own institution's Question Paper PDF or paste manual questions.")
                pdf_upload = st.file_uploader("Upload Question Paper PDF", type=["pdf"])
                extracted_pdf_text = ""
                
                if pdf_upload:
                    try:
                        reader = pypdf.PdfReader(pdf_upload)
                        for page in reader.pages:
                            extracted_pdf_text += (page.extract_text() or "") + "\n"
                        st.success(f"✅ Extracted text from {len(reader.pages)} PDF page(s).")
                    except Exception as e:
                        st.error(f"Error reading PDF: {e}")
                
                manual_q = st.text_area("Question Paper Content:", value=extracted_pdf_text if extracted_pdf_text else "", height=150, placeholder="Paste or type question paper text here...")
                manual_sol = st.text_area("Faculty Model Solution / Key (Confidential):", height=100, placeholder="Type model answer and marks distribution...")
                
                if st.button("📤 Publish Custom Test Paper"):
                    if not manual_q.strip():
                        st.error("Question paper content cannot be empty.")
                    else:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM tests")
                        count = c.fetchone()[0]
                        new_test_id = f"TEST{count + 101}"
                        c.execute("INSERT INTO tests VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (new_test_id, t_lvl, t_sub, t_top, t_m, t_mins, manual_q.strip(), manual_sol.strip() if manual_sol else "Official Academy Answer Key on file."))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Custom Test Paper `{new_test_id}` published successfully for {t_lvl}!")
                        st.rerun()

        st.markdown("---")
        conn = get_db_connection()
        tests_df = pd.read_sql_query("SELECT test_id, level, subject, topic, max_marks, time_allowed_mins FROM tests", conn)
        conn.close()
        st.write("### Published Academy Tests (Active in Database)")
        st.dataframe(tests_df, use_container_width=True)

    # 3. Answer Sheet Evaluation (Text & Handwritten OCR)
    with t_tabs[2]:
        st.subheader("Review & Grade Submissions (Text or Handwritten Scan)")
        conn = get_db_connection()
        pending_subs = pd.read_sql_query("SELECT * FROM submissions WHERE status = 'Pending Evaluation'", conn)
        conn.close()

        if pending_subs.empty:
            st.info("No pending student submissions waiting for evaluation.")
        else:
            for _, sub in pending_subs.iterrows():
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT suggested_solution FROM tests WHERE test_id = ?", (sub["test_id"],))
                sol_row = c.fetchone()
                model_sol = sol_row[0] if sol_row else "Standard faculty answer key."
                conn.close()
                
                st.write(f"#### Submission `{sub['sub_id']}`: `{sub['subject']} - {sub['topic']}`")
                st.write(f"**Student:** {sub['student_username']} | **Max Marks:** {sub['max_marks']} | **Submitted:** {sub['submission_time']}")
                
                uploaded_img_obj = None
                if sub["has_image"] == 1 and sub["image_blob"]:
                    st.write("**Handwritten Answer Sheet Scan Attached:**")
                    uploaded_img_obj = Image.open(io.BytesIO(sub["image_blob"]))
                    st.image(uploaded_img_obj, caption="Student Handwritten Paper", width=450)
                
                if sub["student_answer"]:
                    st.markdown(f"**Typed Notes / Answer:**\n> {sub['student_answer']}")
                
                with st.expander("🔍 View Academy Model Solution (Faculty Confidential)"):
                    st.markdown(model_sol)

                if st.button(f"Draft AI Evaluation for {sub['sub_id']}"):
                    sys_eval = "You are a CA Academy Professor. Evaluate the student's answer against the suggested solution with step marking. Award marks and highlight missing provisions."
                    p_eval = f"Suggested Solution:\n{model_sol}\n\nStudent Typed Text:\n{sub['student_answer']}\nMax Marks: {sub['max_marks']}"
                    res_eval = call_gemini(p_eval, sys_eval, api_key, image=uploaded_img_obj)
                    st.session_state[f"ai_eval_{sub['sub_id']}"] = res_eval
                
                if f"ai_eval_{sub['sub_id']}" in st.session_state:
                    st.info(st.session_state[f"ai_eval_{sub['sub_id']}"])

                with st.form(f"grade_form_{sub['sub_id']}"):
                    awarded_marks = st.number_input("Final Marks to Award", 0, int(sub["max_marks"]), 10)
                    feedback = st.text_area("Teacher Remarks & Feedback", "Well attempted. Work on statutory citations.")
                    if st.form_submit_button("Approve Marks & Publish Result"):
                        conn = get_db_connection()
                        conn.execute("UPDATE submissions SET score = ?, eval_feedback = ?, status = 'Graded', graded_date = ? WHERE sub_id = ?",
                                     (awarded_marks, feedback, datetime.now().strftime("%Y-%m-%d"), sub["sub_id"]))
                        conn.commit()
                        conn.close()
                        st.success("Result published! The student can now view their marks and the model solution.")
                        st.rerun()
                st.divider()

    # 4. Student Doubts & Mentorship Q&A Synchronization
    with t_tabs[3]:
        st.subheader("💬 Student Doubt Inquiries & Mentorship Forum")
        conn = get_db_connection()
        doubts_df = pd.read_sql_query("SELECT * FROM student_doubts ORDER BY doubt_id DESC", conn)
        conn.close()

        if doubts_df.empty:
            st.info("No student questions asked to the Academy Tutor yet.")
        else:
            for _, d in doubts_df.iterrows():
                with st.expander(f"📌 [{d['level']}] {d['subject']} — Asked by {d['student_name']} ({d['created_at']})", expanded=True):
                    st.markdown(f"**Student's Question:**\n> {d['question']}")
                    st.markdown(f"**AI Tutor's Immediate Guidance:**\n{d['ai_response']}")
                    
                    if d["teacher_remark"]:
                        st.success(f"**Current Teacher Endorsement / Note:** {d['teacher_remark']}")
                    
                    with st.form(f"endorse_form_{d['doubt_id']}"):
                        f_note = st.text_input("Add / Edit Faculty Endorsement or Clarification:", value=d["teacher_remark"] if d["teacher_remark"] else "")
                        if st.form_submit_button("Save Faculty Endorsement"):
                            conn = get_db_connection()
                            conn.execute("UPDATE student_doubts SET teacher_remark = ? WHERE doubt_id = ?", (f_note, d["doubt_id"]))
                            conn.commit()
                            conn.close()
                            st.success("Faculty remark saved! Visible in student's tutor panel.")
                            st.rerun()

    # 5. Batch Analytics
    with t_tabs[4]:
        st.subheader("Academy-Wide Performance Overview")
        conn = get_db_connection()
        graded_df = pd.read_sql_query("SELECT * FROM submissions WHERE status = 'Graded'", conn)
        conn.close()
        if not graded_df.empty:
            fig_inst = px.bar(graded_df, x="subject", y="score", color="student_username", title="Score Distribution across Academy Subjects", barmode="group")
            st.plotly_chart(fig_inst, use_container_width=True)
        else:
            st.info("Performance charts will populate once test results are graded.")

    # 6. Password Reset
    with t_tabs[5]:
        st.subheader("Update Account Password")
        with st.form("t_pwd_form"):
            curr_p = st.text_input("Current Password", type="password")
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Change Password"):
                if curr_p != st.session_state.current_user["password"]:
                    st.error("Current password is incorrect.")
                elif not new_p or new_p != conf_p:
                    st.error("New passwords do not match or are empty.")
                else:
                    conn = get_db_connection()
                    conn.execute("UPDATE users SET password = ? WHERE username = ?", (new_p, st.session_state.current_user["username"]))
                    conn.commit()
                    conn.close()
                    st.session_state.current_user["password"] = new_p
                    st.success("✅ Password successfully updated!")

# ------------------------------------------------------------------------------
# 2. STUDENT DASHBOARD
# ------------------------------------------------------------------------------
else:
    current_student = st.session_state.current_user
    student_level = current_student.get('level', 'CA Intermediate')
    st.markdown(f"""
    <div class="academy-header-card">
        <div class="academy-header-title">👨‍🎓 Student Learning & Examination Hub</div>
        <div class="academy-header-sub">Candidate: <b>{current_student['name']}</b> | Stream: <b>{student_level}</b> | Roll No: <b>{current_student['username'].upper()}</b></div>
    </div>
    """, unsafe_allow_html=True)
    
    s_tabs = st.tabs([
        "🤖 Academy AI Tutor", 
        "✍️ Take Timed Test (Text / Handwritten)", 
        "🎯 ICAI Exemption & Gap Analytics", 
        "📑 Graded Results & Model Answers", 
        "🔒 Reset Password"
    ])

    # 1. AI Concept Tutor
    with s_tabs[0]:
        st.subheader(f"24x7 Conceptual Mentorship ({student_level})")
        student_subjects = CA_SYLLABUS.get(student_level, CA_SYLLABUS["CA Intermediate"])
        sel_subj = st.selectbox("Select Subject to Ask", student_subjects, key="s_tutor_sub")
        doubt = st.text_area(f"Ask any doubt or practical question for {sel_subj}:", placeholder="e.g., Explain the difference between AS 9 and Ind AS 115 revenue recognition principles.")
        
        if st.button("Ask Academy Mentor"):
            if not doubt.strip():
                st.error("Please enter a question.")
            else:
                with st.spinner("Consulting Academy study notes..."):
                    sys_inst = f"You are a master faculty mentor teaching {student_level} - {sel_subj} at a CA Coaching Academy. Provide point-wise explanations, journal entries, and statutory citations."
                    ai_reply = call_gemini(doubt, sys_inst, api_key)
                    
                    conn = get_db_connection()
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    conn.execute('''
                        INSERT INTO student_doubts (student_username, student_name, level, subject, question, ai_response, teacher_remark, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (current_student["username"], current_student["name"], student_level, sel_subj, doubt, ai_reply, "", now_str))
                    conn.commit()
                    conn.close()
                    
                    st.markdown(ai_reply)
                    st.success("✅ Doubt answered and logged to the Teacher's Mentorship Q&A tab for faculty review!")

        st.markdown("---")
        st.write("### 📜 My Recent Doubt Q&A History")
        conn = get_db_connection()
        my_doubts = pd.read_sql_query("SELECT * FROM student_doubts WHERE student_username = ? ORDER BY doubt_id DESC", conn, params=(current_student["username"],))
        conn.close()
        
        if my_doubts.empty:
            st.caption("No past questions on record yet.")
        else:
            for _, md in my_doubts.iterrows():
                with st.expander(f"Question: {md['subject']} ({md['created_at']})"):
                    st.markdown(f"**My Question:** {md['question']}")
                    st.markdown(f"**Mentor Answer:**\n{md['ai_response']}")
                    if md["teacher_remark"]:
                        st.info(f"👨‍🏫 **Faculty Note:** {md['teacher_remark']}")

    # 2. Take Test
    with s_tabs[1]:
        st.subheader("Assigned Academy Tests (Timed Exam Mode)")
        conn = get_db_connection()
        tests_df = pd.read_sql_query("SELECT * FROM tests WHERE level = ?", conn, params=(student_level,))
        conn.close()
        
        if tests_df.empty:
            st.info(f"No tests currently published for {student_level}.")
        else:
            test_choices = {f"{row['test_id']} - {row['subject']} ({row['topic']})": row for _, row in tests_df.iterrows()}
            selected_label = st.selectbox("Select Test to Attempt", list(test_choices.keys()))
            active_test = test_choices[selected_label]
            
            st.markdown(f"### Questions (Max Marks: {active_test['max_marks']} | Time Allowed: {active_test['time_allowed_mins']} Mins)")
            st.warning("⚠️ Note: Suggested solutions are locked until the faculty reviews and grades your paper.")
            
            st.markdown("#### 📄 Test Paper:")
            st.code(active_test["questions"], language="markdown")
            
            c_ans1, c_ans2 = st.columns(2)
            with c_ans1:
                stu_response = st.text_area("Type Answer Here (Optional if uploading scan):", height=180)
            with c_ans2:
                uploaded_file = st.file_uploader("Upload Handwritten Answer Paper Scan (JPG/PNG)", type=["jpg", "jpeg", "png"])
                if uploaded_file:
                    st.image(uploaded_file, caption="Handwritten Sheet Preview", width=250)
            
            if st.button("Submit Test Paper for Evaluation"):
                if not stu_response.strip() and uploaded_file is None:
                    st.error("Please type an answer or upload a handwritten answer sheet scan.")
                else:
                    img_bytes = uploaded_file.read() if uploaded_file else None
                    has_img = 1 if img_bytes else 0
                    
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM submissions")
                    sub_count = c.fetchone()[0]
                    new_sub_id = f"SUB{sub_count + 1:03d}"
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    c.execute('''
                        INSERT INTO submissions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (new_sub_id, active_test["test_id"], current_student["username"], active_test["subject"], active_test["topic"],
                          stu_response, has_img, img_bytes, active_test["max_marks"], 0, "", "Pending Evaluation", now_str, None))
                    conn.commit()
                    conn.close()
                    st.success("🎉 Test submitted successfully! Your teacher will evaluate your paper shortly.")

    # 3. ICAI Exemption Predictor & Graphical Analytics
    with s_tabs[2]:
        st.subheader(f"🎯 ICAI Exemption Predictor & Gap Analytics ({student_level})")
        conn = get_db_connection()
        my_graded_df = pd.read_sql_query("SELECT * FROM submissions WHERE student_username = ? AND status = 'Graded'", conn, params=(current_student["username"],))
        conn.close()
        
        if not my_graded_df.empty:
            total_obtained = my_graded_df["score"].sum()
            total_max = my_graded_df["max_marks"].sum()
            agg_percentage = (total_obtained / total_max) * 100 if total_max > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Overall Aggregate Score", f"{agg_percentage:.1f}%", delta="Target: >= 50%")
            
            exemptions = my_graded_df[my_graded_df["score"] >= 0.6 * my_graded_df["max_marks"]]["subject"].count()
            m2.metric("Subjects with Exemption (>= 60%)", f"{exemptions} Papers")
            
            at_risk = my_graded_df[my_graded_df["score"] < 0.4 * my_graded_df["max_marks"]]["subject"].count()
            m3.metric("Critical Risk Subjects (< 40%)", f"{at_risk} Papers", delta_color="inverse")
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                my_graded_df["pct_score"] = (my_graded_df["score"] / my_graded_df["max_marks"]) * 100
                fig_bar = px.bar(my_graded_df, x="subject", y="pct_score", color="pct_score", range_y=[0, 100],
                                 title="Subject Mastery (40% Passing | 60% Exemption)",
                                 color_continuous_scale=["red", "yellow", "green"])
                fig_bar.add_hline(y=40, line_dash="dot", annotation_text="Min 40% Pass", line_color="orange")
                fig_bar.add_hline(y=60, line_dash="dash", annotation_text="60% Exemption Goal", line_color="green")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with col2:
                fig_trend = px.line(my_graded_df.sort_values("graded_date"), x="graded_date", y="score", markers=True,
                                    title="Score Trajectory Over Time")
                st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Performance charts and aggregate statistics will unlock once your test submissions are evaluated.")

    # 4. Results & Suggested Answers
    with s_tabs[3]:
        st.subheader("📑 Graded Results & Model Suggested Answers")
        conn = get_db_connection()
        my_graded_df = pd.read_sql_query("SELECT * FROM submissions WHERE student_username = ? AND status = 'Graded'", conn, params=(current_student["username"],))
        conn.close()
        
        if my_graded_df.empty:
            st.info("No evaluated results available yet.")
        else:
            for _, item in my_graded_df.iterrows():
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT suggested_solution FROM tests WHERE test_id = ?", (item["test_id"],))
                sol = c.fetchone()
                model_sol = sol[0] if sol else "Standard faculty answer key."
                conn.close()
                
                with st.expander(f"📊 {item['subject']} - {item['topic']} | Score: {item['score']} / {item['max_marks']}"):
                    st.write(f"**Teacher Feedback:** {item['eval_feedback']}")
                    if item["has_image"] == 1 and item["image_blob"]:
                        st.write("**Your Submitted Handwritten Paper:**")
                        st.image(Image.open(io.BytesIO(item["image_blob"])), width=350)
                    if item["student_answer"]:
                        st.markdown(f"**Your Typed Notes:**\n> {item['student_answer']}")
                    st.markdown("---")
                    st.markdown("### 🔑 Academy Suggested Solution (Unlocked):")
                    st.success(model_sol)

    # 5. Password Reset
    with s_tabs[4]:
        st.subheader("Update Account Password")
        with st.form("s_pwd_form"):
            curr_p_s = st.text_input("Current Password", type="password")
            new_p_s = st.text_input("New Password", type="password")
            conf_p_s = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Change Password"):
                if curr_p_s != st.session_state.current_user["password"]:
                    st.error("Current password is incorrect.")
                elif not new_p_s or new_p_s != conf_p_s:
                    st.error("New passwords do not match or are empty.")
                else:
                    conn = get_db_connection()
                    conn.execute("UPDATE users SET password = ? WHERE username = ?", (new_p_s, st.session_state.current_user["username"]))
                    conn.commit()
                    conn.close()
                    st.session_state.current_user["password"] = new_p_s
                    st.success("✅ Password successfully updated!")