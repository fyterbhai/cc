# FILE 1: database.py (COPY YOUR ORIGINAL DATABASE FILE - NO CHANGES NEEDED)
# Yeh bilkul same rahega jo tumne diya tha

# FILE 2: instagram_bot.py (COMPLETE INSTAGRAM VERSION)
import sqlite3
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet
import os
import streamlit as st
import streamlit.components.v1 as components
import time
import threading
import uuid
import json
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import database as db

# Instagram specific constants
INSTAGRAM_LOGIN_URL = 'https://www.instagram.com/accounts/login/'
INSTAGRAM_MESSAGES_URL = 'https://www.instagram.com/direct/inbox/'
ADMIN_USERNAME = "your_instagram_admin_username"  # Yahan admin ka username daalo

st.set_page_config(
    page_title="Instagram Auto DM Bot - YKTI RAWAT",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tumhara same beautiful CSS
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

* { font-family: 'Outfit', sans-serif !important; }

.stApp {
    background: linear-gradient(135deg, #f4f9ff 0%, #e9f3ff 40%, #e1f0ff 100%);
    background-attachment: fixed;
    color: #333 !important;
}

.main .block-container {
    background: rgba(255, 255, 255, 0.85);
    border-radius: 28px;
    padding: 40px;
    border: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 10px 40px rgba(0,0,0,0.08);
    animation: smoothFade 0.5s ease;
}

@keyframes smoothFade {
    from {opacity: 0; transform: translateY(12px);}
    to {opacity: 1; transform: translateY(0);}
}

.main-header {
    background: linear-gradient(135deg, #ffffff, #f0f8ff, #e7f3ff);
    border-radius: 25px;
    padding: 50px 25px;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0, 140, 255, 0.12);
    border: 1px solid rgba(0, 140, 255, 0.15);
}

.main-header h1 {
    color: #E4405F;
    font-size: 3rem;
    font-weight: 900;
}

.main-header p {
    color: #D32F2F;
    font-size: 1.2rem;
    opacity: 0.85;
}

.stTextInput>div>div>input, .stTextArea>div>div>textarea {
    background: #ffffff;
    border-radius: 12px;
    padding: 14px;
    border: 1.5px solid #fee;
    color: #333;
    font-size: 1rem;
    transition: 0.2s ease;
}

.stTextInput>div>div>input:focus {
    border-color: #E4405F;
    box-shadow: 0 0 12px rgba(228, 64, 95, 0.3);
}

label { color: #C13584 !important; font-weight: 700 !important; }

.stButton>button {
    background: linear-gradient(135deg, #E4405F 0%, #C13584 100%);
    color: white;
    font-weight: 700;
    font-size: 1.1rem;
    padding: 1rem 2rem;
    border-radius: 14px;
    border: none;
    transition: 0.3s ease;
    box-shadow: 0 10px 20px rgba(228, 64, 95, 0.25);
}

.stButton>button:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 28px rgba(228, 64, 95, 0.35);
}

.console-output {
    background: #ffffff;
    border: 2px solid #fee;
    border-radius: 15px;
    padding: 20px;
    font-family: "Consolas";
    max-height: 400px;
    color: #D32F2F;
    overflow-y: auto;
    box-shadow: 0 10px 25px rgba(228, 64, 95, 0.15);
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Session state (same as original)
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'username' not in st.session_state: st.session_state.username = None
if 'automation_running' not in st.session_state: st.session_state.automation_running = False
if 'logs' not in st.session_state: st.session_state.logs = []
if 'message_count' not in st.session_state: st.session_state.message_count = 0

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

ADMIN_UID = "your_instagram_admin_id"

def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state:
        automation_state.logs.append(formatted_msg)
    else:
        st.session_state.logs.append(formatted_msg)

def find_instagram_message_input(driver, process_id, automation_state=None):
    """Instagram DM input field find karne ke liye"""
    log_message(f'{process_id}: 📱 Finding Instagram DM input...', automation_state)
    time.sleep(8)
    
    # Instagram specific selectors
    selectors = [
        'div[contenteditable="true"][data-testid="conversation-compose-text-area"]',
        'div[contenteditable="true"][role="textbox"]',
        'div[aria-label*="Message *"][contenteditable="true"]',
        'div[aria-label*="message"][contenteditable="true"]',
        'textarea[placeholder*="Message"]',
        'div[data-block="true"][contenteditable="true"]',
        '[contenteditable="true"][tabindex="0"]',
        'div[spellcheck="true"]'
    ]
    
    for idx, selector in enumerate(selectors):
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            log_message(f'{process_id}: Selector {idx+1}: {len(elements)} elements', automation_state)
            
            for element in elements:
                try:
                    if element.is_displayed() and element.size['height'] > 20:
                        element.click()
                        time.sleep(0.5)
                        
                        placeholder = driver.execute_script(
                            "return arguments[0].getAttribute('aria-placeholder') || arguments[0].getAttribute('placeholder') || '';", 
                            element
                        )
                        
                        if 'message' in placeholder.lower() or idx < 3:
                            log_message(f'{process_id}: ✅ Found input: {placeholder[:50]}', automation_state)
                            return element
                except:
                    continue
        except:
            continue
    
    log_message(f'{process_id}: ❌ No input found!', automation_state)
    return None

def setup_instagram_browser(automation_state=None):
    """Instagram ke liye stealth browser"""
    log_message('🔧 Setting up Instagram browser...', automation_state)
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=375,812')  # Mobile view
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_window_size(375, 812)
    return driver

def get_next_message(messages, automation_state=None):
    if not messages: return 'Hi!'
    if automation_state:
        msg = messages[automation_state.message_rotation_index % len(messages)]
        automation_state.message_rotation_index += 1
        return msg
    return messages[0]

def instagram_send_messages(config, automation_state, user_id, process_id='IG-AUTO-1'):
    driver = None
    try:
        log_message(f'{process_id}: 🚀 Starting Instagram DM automation...', automation_state)
        driver = setup_instagram_browser(automation_state)
        
        # Instagram open karo
        log_message(f'{process_id}: Going to Instagram...', automation_state)
        driver.get(INSTAGRAM_LOGIN_URL)
        time.sleep(10)
        
        # Cookies add karo (Instagram format: sessionid=abc; csrftoken=xyz)
        if config['cookies'] and config['cookies'].strip():
            log_message(f'{process_id}: Adding {len(config["cookies"])} Instagram cookies...', automation_state)
            cookie_array = [c.strip() for c in config['cookies'].split(';') if c.strip()]
            for cookie in cookie_array:
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    try:
                        driver.add_cookie({
                            'name': name.strip(),
                            'value': value.strip(),
                            'domain': '.instagram.com',
                            'path': '/'
                        })
                    except:
                        pass
            driver.refresh()
            time.sleep(5)
        
        # Specific chat open karo ya DM inbox
        if config['chat_id']:
            chat_username = config['chat_id'].strip()
            chat_url = f'https://www.instagram.com/direct/t/{chat_username}/'
            log_message(f'{process_id}: Opening chat: {chat_username}', automation_state)
            driver.get(chat_url)
        else:
            log_message(f'{process_id}: Opening DM inbox...', automation_state)
            driver.get(INSTAGRAM_MESSAGES_URL)
        
        time.sleep(12)
        
        message_input = find_instagram_message_input(driver, process_id, automation_state)
        if not message_input:
            log_message(f'{process_id}: ❌ Message input not found!', automation_state)
            return 0
        
        delay = int(config['delay'] or 30)
        messages_list = [msg.strip() for msg in config['messages'].split('
') if msg.strip()]
        if not messages_list: messages_list = ['Hi there!']
        
        messages_sent = 0
        while automation_state.running:
            base_message = get_next_message(messages_list, automation_state)
            message_to_send = f"{config['name_prefix']} {base_message}" if config['name_prefix'] else base_message
            
            # Message type karo
            driver.execute_script("""
                const element = arguments[0];
                const message = arguments[1];
                element.focus();
                element.click();
                element.innerHTML = message;
                element.textContent = message;
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'}));
            """, message_input, message_to_send)
            
            time.sleep(2)
            
            # Send button dhundo aur click karo
            send_selectors = [
                'button[aria-label*="Send"]',
                'div[aria-label*="Send"]',
                'svg[aria-label*="Send"]',
                '[data-testid="send-button"]'
            ]
            
            send_clicked = False
            for selector in send_selectors:
                try:
                    send_btns = driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in send_btns:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click();", btn)
                            send_clicked = True
                            break
                    if send_clicked: break
                except:
                    continue
            
            if not send_clicked:
                # Enter key bhejo
                driver.execute_script("""
                    const element = arguments[0];
                    const enterEvent = new KeyboardEvent('keydown', {
                        key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
                    });
                    element.dispatchEvent(enterEvent);
                """, message_input)
            
            messages_sent += 1
            automation_state.message_count = messages_sent
            log_message(f'{process_id}: ✅ Message #{messages_sent} sent: "{message_to_send[:40]}..." | Next: {delay}s', automation_state)
            time.sleep(delay)
        
        return messages_sent
        
    except Exception as e:
        log_message(f'{process_id}: ❌ Error: {str(e)[:100]}', automation_state)
        return 0
    finally:
        if driver:
            try:
                driver.quit()
                log_message(f'{process_id}: Browser closed', automation_state)
            except:
                pass

# ================ STREAMLIT UI (SAME LOGIN SYSTEM) ================
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📱 Instagram Auto DM Bot</h1>
        <p>YKTI RAWAT | Secure • Fast • Reliable</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Login/Register Tab
    tab1, tab2, tab3 = st.tabs(["🔐 Login", "➕ Register", "⚙️ Dashboard"])
    
    with tab1:
        if st.button("🔑 Login as Demo User", key="demo"):
            st.session_state.logged_in = True
            st.session_state.user_id = 1
            st.session_state.username = "demo_user"
            st.rerun()
        
        with st.form("login_form"):
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
                    st.error("❌ Invalid credentials!")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password", type="password")
            if st.form_submit_button("Create Account"):
                success, msg = db.create_user(new_username, new_password)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # Dashboard
    if st.session_state.logged_in and st.session_state.user_id:
        with tab3:
            st.markdown(f"👋 Welcome, **{st.session_state.username}**!")
            
            config = db.get_user_config(st.session_state.user_id)
            if config:
                # Config form
                with st.form("config_form"):
                    st.subheader("📱 Instagram Configuration")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        chat_id = st.text_input("Instagram Username (chat_id)", value=config['chat_id'])
                        name_prefix = st.text_input("Name Prefix", value=config['name_prefix'])
                        delay = st.number_input("Delay (seconds)", min_value=10, value=config['delay'])
                    
                    with col2:
                        cookies = st.text_area("Instagram Cookies", value=config['cookies'], height=150,
                                             help="F12 → Application → Cookies → Copy .instagram.com cookies")
                        messages = st.text_area("Messages (one per line)", value=config['messages'], height=150)
                    
                    if st.form_submit_button("💾 Save Config"):
                        db.update_user_config(
                            st.session_state.user_id, chat_id, name_prefix, delay, cookies, messages
                        )
                        st.success("✅ Config saved!")
                
                # Control buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("▶️ Start Automation", use_container_width=True):
                        if not st.session_state.automation_state.running:
                            st.session_state.automation_state.running = True
                            db.set_automation_running(st.session_state.user_id, True)
                            
                            # Thread mein start karo
                            thread = threading.Thread(
                                target=instagram_send_messages,
                                args=(config, st.session_state.automation_state, st.session_state.user_id)
                            )
                            thread.daemon = True
                            thread.start()
                            st.success("🚀 Automation started!")
                
                with col2:
                    if st.button("⏹️ Stop Automation", use_container_width=True):
                        st.session_state.automation_state.running = False
                        db.set_automation_running(st.session_state.user_id, False)
                        st.success("🛑 Automation stopped!")
                
                with col3:
                    st.metric("Messages Sent", st.session_state.automation_state.message_count)
                
                # Logs
                st.subheader("📋 Live Logs")
                for log in st.session_state.automation_state.logs[-20:]:
                    st.markdown(f'<div class="console-line">{log}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    db.init_db()
    main()
