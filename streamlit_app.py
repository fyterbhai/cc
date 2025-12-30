import streamlit as st
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import database as db

st.set_page_config(page_title="📱 Instagram Auto DM Bot", layout="wide")

# Instagram URLs
INSTAGRAM_LOGIN = 'https://www.instagram.com/accounts/login/'
INSTAGRAM_DM = 'https://www.instagram.com/direct/inbox/'

# Beautiful CSS (Instagram Pink Theme)
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
.console-output { 
    background: #fff5f7; border: 2px solid #fed7e2; border-radius: 15px; 
    padding: 1.5rem; max-height: 400px; overflow-y: auto; font-family: 'Consolas';
    color: #be185d;
}
.success-box { background: linear-gradient(135deg, #dcfce7, #bbf7d0); color: #166534; padding: 1rem; border-radius: 12px; }
.error-box { background: linear-gradient(135deg, #fee2e2, #fecaca); color: #dc2626; padding: 1rem; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# Session State
for key in ['logged_in', 'user_id', 'username', 'logs', 'automation_state']:
    if key not in st.session_state:
        st.session_state[key] = False if 'logged_in' in key else {} if 'automation_state' in key else []

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0

if isinstance(st.session_state.automation_state, dict):
    st.session_state.automation_state = AutomationState()

def log_message(msg, state=None):
    timestamp = time.strftime("%H:%M:%S")
    log = f"[{timestamp}] {msg}"
    if state:
        state.logs.append(log)
    else:
        st.session_state.logs.append(log)
    if len(st.session_state.logs) > 50:
        st.session_state.logs = st.session_state.logs[-50:]

def setup_instagram_browser():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=390,844')
    options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def find_instagram_input(driver):
    selectors = [
        'div[contenteditable="true"][data-testid="conversation-compose-text-area"]',
        'div[contenteditable="true"][role="textbox"]',
        'div[aria-label*="Message"][contenteditable="true"]',
        '[contenteditable="true"]',
        'textarea'
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                if elem.is_displayed() and elem.size['height'] > 10:
                    return elem
        except:
            continue
    return None

def instagram_send_messages(config, state, user_id):
    driver = None
    try:
        log_message("🚀 Instagram DM Bot Starting...", state)
        driver = setup_instagram_browser()
        
        # Login with cookies
        driver.get(INSTAGRAM_LOGIN)
        time.sleep(8)
        
        if config['cookies'].strip():
            cookies = [c.strip() for c in config['cookies'].split(';') if '=' in c]
            for cookie in cookies:
                name, value = cookie.split('=', 1)
                driver.add_cookie({'name': name.strip(), 'value': value.strip(), 'domain': '.instagram.com'})
            driver.refresh()
            time.sleep(6)
        
        # Open chat
        chat_id = config['chat_id'].strip()
        if chat_id:
            driver.get(f'https://www.instagram.com/direct/t/{chat_id}/')
        else:
            driver.get(INSTAGRAM_DM)
        
        time.sleep(10)
        input_field = find_instagram_input(driver)
        
        if not input_field:
            log_message("❌ Message input not found!", state)
            return
        
        messages = [m.strip() for m in config['messages'].split('
') if m.strip()]
        if not messages: messages = ['Hi!']
        delay = max(15, int(config['delay']))
        
        while state.running:
            msg_idx = state.message_rotation_index % len(messages)
            message = messages[msg_idx]
            if config['name_prefix']:
                message = f"{config['name_prefix']} {message}"
            
            # Type message
            driver.execute_script("""
                const el = arguments[0]; const text = arguments[1];
                el.focus(); el.innerHTML = text; el.textContent = text;
                el.dispatchEvent(new Event('input', {bubbles: true}));
            """, input_field, message)
            time.sleep(2)
            
            # Send
            send_selectors = ['button[aria-label*="Send"]', 'div[aria-label*="Send"]']
            send_clicked = False
            for sel in send_selectors:
                try:
                    btns = driver.find_elements(By.CSS_SELECTOR, sel)
                    for btn in btns:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click();", btn)
                            send_clicked = True
                            break
                    if send_clicked: break
                except: pass
            
            if not send_clicked:
                driver.execute_script("""
                    const el = arguments[0];
                    const enter = new KeyboardEvent('keydown', {key: 'Enter', bubbles: true});
                    el.dispatchEvent(enter);
                """, input_field)
            
            state.message_count += 1
            state.message_rotation_index += 1
            log_message(f"✅ Message #{state.message_count} sent: '{message[:30]}...' | Next: {delay}s", state)
            time.sleep(delay)
            
    except Exception as e:
        log_message(f"❌ Error: {str(e)[:80]}", state)
    finally:
        if driver:
            driver.quit()
        state.running = False
        db.set_automation_running(user_id, False)

# MAIN UI
st.title("📱 Instagram Auto DM Bot")
st.markdown("### YKTI RAWAT | Secure • Fast • Unlimited DMs")

tab1, tab2, tab3 = st.tabs(["🔐 Login", "➕ Register", "⚙️ Dashboard"])

with tab1:
    col1, col2 = st.columns([3,1])
    with col1:
        with st.form("login"):
            username = st.text_input("👤 Username")
            password = st.text_input("🔑 Password", type="password")
            if st.form_submit_button("🚀 Login"):
                user_id = db.verify_user(username, password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = db.get_username(user_id)
                    st.success("✅ Login Successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")
    
    with col2:
        if st.button("🎮 Demo Mode"):
            st.session_state.logged_in = True
            st.session_state.user_id = 1
            st.session_state.username = "demo"
            st.rerun()

with tab2:
    with st.form("register"):
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.form_submit_button("➕ Create Account"):
            success, msg = db.create_user(new_user, new_pass)
            if success:
                st.success("✅ Account Created!")
            else:
                st.error(f"❌ {msg}")

if st.session_state.logged_in and st.session_state.user_id:
    with tab3:
        st.success(f"👋 Welcome **{st.session_state.username}**!")
        
        config = db.get_user_config(st.session_state.user_id) or {
            'chat_id': '', 'name_prefix': '', 'delay': 30, 'cookies': '', 'messages': 'Hi!
Hello!
Hey there!'
        }
        
        with st.form("config"):
            st.subheader("📱 Instagram Settings")
            
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("👥 Instagram Username", key="chat_id", value=config['chat_id'],
                            help="Username without @ (john_doe)")
                st.text_input("📝 Name Prefix", key="prefix", value=config['name_prefix'])
                delay = st.number_input("⏱️ Delay (seconds)", min_value=15, value=config['delay'])
            
            with col2:
                cookies = st.text_area("🍪 Instagram Cookies", key="cookies", value=config['cookies'], 
                                     height=120, help="F12 > Application > Cookies > Copy .instagram.com")
                messages = st.text_area("💬 Messages (one per line)", key="msgs", value=config['messages'], 
                                      height=120)
            
            if st.form_submit_button("💾 Save"):
                db.update_user_config(st.session_state.user_id, st.session_state.chat_id, 
                                    st.session_state.prefix, delay, st.session_state.cookies, st.session_state.msgs)
                st.success("✅ Settings Saved!")
        
        # Control Panel
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("▶️ START BOT", use_container_width=True):
                if not st.session_state.automation_state.running:
                    st.session_state.automation_state.running = True
                    db.set_automation_running(st.session_state.user_id, True)
                    thread = threading.Thread(target=instagram_send_messages, 
                                            args=(config, st.session_state.automation_state, st.session_state.user_id))
                    thread.daemon = True
                    thread.start()
                    st.success("🚀 Bot Started!")
        
        with col2:
            if st.button("⏹️ STOP BOT", use_container_width=True):
                st.session_state.automation_state.running = False
                db.set_automation_running(st.session_state.user_id, False)
                st.success("🛑 Bot Stopped!")
        
        with col3:
            st.metric("📨 Messages Sent", st.session_state.automation_state.message_count)
        
        # Live Logs
        st.subheader("📋 Live Console")
        for log in st.session_state.automation_state.logs[-15:] + st.session_state.logs[-15:]:
            st.markdown(f"• {log}")

st.markdown("---")
st.markdown("<p style='text-align:center;color:#E4405F;font-weight:700;'>Made with ❤️ by YKTI RAWAT</p>", unsafe_allow_html=True)
