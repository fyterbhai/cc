import streamlit as st
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import database as db

st.set_page_config(page_title="Instagram Auto DM Bot", layout="wide")

INSTAGRAM_LOGIN = 'https://www.instagram.com/accounts/login/'
INSTAGRAM_DM = 'https://www.instagram.com/direct/inbox/'

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
* { font-family: 'Poppins', sans-serif !important; }
.stApp { background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 50%, #f9a8d4 100%); }
.main .block-container { 
    background: rgba(255,255,255,0.95); border-radius: 25px; padding: 3rem; 
    box-shadow: 0 20px 60px rgba(228,64,95,0.2); border: 1px solid rgba(228,64,95,0.1);
}
h1 { color: #E4405F !important; font-weight: 800 !important; font-size: 3rem !important; }
.stButton > button { 
    background: linear-gradient(135deg, #E4405F, #F585B7); color: white; 
    border-radius: 15px; font-weight: 600; padding: 1rem 2rem; border: none;
    box-shadow: 0 10px 30px rgba(228,64,95,0.3);
}
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 15px 40px rgba(228,64,95,0.4); }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'username' not in st.session_state: st.session_state.username = None
if 'logs' not in st.session_state: st.session_state.logs = []

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

def log_message(msg, state=None):
    timestamp = time.strftime("%H:%M:%S")
    log = f"[{timestamp}] {msg}"
    if state:
        state.logs.append(log)
    else:
        st.session_state.logs.append(log)

def setup_browser():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15')
    driver = webdriver.Chrome(options=options)
    return driver

def find_input(driver):
    selectors = [
        'div[contenteditable="true"]',
        'textarea',
        '[role="textbox"]'
    ]
    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for elem in elements:
            if elem.is_displayed():
                return elem
    return None

def send_messages(config, state, user_id):
    driver = None
    try:
        log_message("🚀 Starting Instagram bot...", state)
        driver = setup_browser()
        
        driver.get(INSTAGRAM_LOGIN)
        time.sleep(8)
        
        if config['cookies']:
            for cookie in config['cookies'].split(';'):
                cookie = cookie.strip()
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    driver.add_cookie({'name': name.strip(), 'value': value.strip(), 'domain': '.instagram.com'})
            driver.refresh()
            time.sleep(5)
        
        chat_id = config['chat_id'].strip()
        if chat_id:
            driver.get(f'https://www.instagram.com/direct/t/{chat_id}/')
        else:
            driver.get(INSTAGRAM_DM)
        
        time.sleep(10)
        input_field = find_input(driver)
        
        if not input_field:
            log_message("❌ Input not found", state)
            return
        
        messages_list = []
        if config['messages']:
            messages_list = [m.strip() for m in config['messages'].split('\
') if m.strip()]
        if not messages_list:
            messages_list = ['Hi!']
        
        delay = max(15, int(config['delay']))
        
        while state.running:
            msg_idx = state.message_rotation_index % len(messages_list)
            message = messages_list[msg_idx]
            if config['name_prefix']:
                message = config['name_prefix'] + ' ' + message
            
            driver.execute_script("arguments[0].innerHTML=arguments[1];", input_field, message)
            time.sleep(2)
            
            send_btns = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label*="Send"]')
            if send_btns:
                driver.execute_script("arguments[0].click();", send_btns[0])
            else:
                driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'}));", input_field)
            
            state.message_count += 1
            state.message_rotation_index += 1
            log_message(f"✅ Sent #{state.message_count}: {message[:30]}", state)
            time.sleep(delay)
            
    except Exception as e:
        log_message(f"❌ Error: {str(e)}", state)
    finally:
        if driver:
            driver.quit()
        state.running = False
        db.set_automation_running(user_id, False)

st.title("📱 Instagram Auto DM Bot")
tab1, tab2, tab3 = st.tabs(["🔐 Login", "➕ Register", "⚙️ Dashboard"])

with tab1:
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user_id = db.verify_user(username, password)
            if user_id:
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.username = db.get_username(user_id)
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Wrong credentials!")

with tab2:
    with st.form("register"):
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.form_submit_button("Register"):
            success, msg = db.create_user(new_username, new_password)
            if success:
                st.success("✅ Account created!")
            else:
                st.error(f"❌ {msg}")

if st.session_state.logged_in and st.session_state.user_id:
    with tab3:
        st.success(f"Welcome {st.session_state.username}!")
        
        config = db.get_user_config(st.session_state.user_id) or {
            'chat_id': '', 'name_prefix': '', 'delay': 30, 'cookies': '', 'messages': 'Hi!
Hello!'
        }
        
        with st.form("config"):
            col1, col2 = st.columns(2)
            with col1:
                chat_id = st.text_input("Instagram Username", value=config['chat_id'])
                prefix = st.text_input("Name Prefix", value=config['name_prefix'])
                delay = st.number_input("Delay (seconds)", value=config['delay'], min_value=15)
            
            with col2:
                cookies = st.text_area("Instagram Cookies", value=config['cookies'], height=100)
                messages_text = st.text_area("Messages", value=config['messages'], height=100)
            
            if st.form_submit_button("Save"):
                db.update_user_config(st.session_state.user_id, chat_id, prefix, delay, cookies, messages_text)
                st.success("✅ Saved!")
                st.rerun()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("▶️ START"):
                if not st.session_state.automation_state.running:
                    st.session_state.automation_state.running = True
                    thread = threading.Thread(target=send_messages, args=(config, st.session_state.automation_state, st.session_state.user_id))
                    thread.daemon = True
                    thread.start()
                    st.success("🚀 Started!")
        
        with col2:
            if st.button("⏹️ STOP"):
                st.session_state.automation_state.running = False
                st.success("🛑 Stopped!")
        
        with col3:
            st.metric("Messages", st.session_state.automation_state.message_count)
        
        st.subheader("Logs")
        for log in st.session_state.automation_state.logs[-10:]:
            st.text(log)
