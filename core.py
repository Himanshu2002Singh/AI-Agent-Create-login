import json
import random
import string
import time
import os
import shutil
from urllib.parse import urlparse
import undetected_chromedriver as uc  # use stealth browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===============================
# Utility Functions
# ===============================

def generate_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(chars) for _ in range(length))

def extract_name_from_username(username):
    return username[:4].capitalize()

def extract_base_domain(weburl):
    parsed = urlparse(weburl if weburl.startswith('http') else f'https://{weburl}')
    domain = parsed.netloc or parsed.path
    parts = domain.lower().strip().split('.')
    return '.'.join(parts[-2:]) if len(parts) > 2 else domain

def find_user_by_weburl(weburl, users_json='users.json'):
    base = extract_base_domain(weburl)
    with open(users_json, 'r', encoding='utf-8') as file:
        users = json.load(file)
        for u in users:
            if extract_base_domain(u['weburl']) == base:
                return u
    return None

# ===============================
# Chrome Driver Setup
# ===============================

import undetected_chromedriver as uc
import shutil

def get_driver(headless=False):
    options = uc.ChromeOptions()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    chrome_path = shutil.which("google-chrome") or shutil.which("chromium-browser")
    if not chrome_path:
        raise FileNotFoundError("Could not locate Chrome or Chromium on this machine.")

    # NOTE: uc.Chrome auto-detects Chrome, avoid passing browser_executable_path unless strictly needed
    driver = uc.Chrome(options=options)

    return driver


# ===============================
# Smart Input Handler
# ===============================

def smart_send_keys(driver, field_label, value, timeout=20):
    selectors = [
        (By.ID, field_label),
        (By.NAME, field_label),
        (By.XPATH, f"//input[@placeholder='{field_label}']"),
        (By.XPATH, f"//input[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{field_label.lower()}')]"),
        (By.XPATH, f"//input[contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{field_label.lower()}')]"),
        (By.XPATH, f"//label[contains(text(), '{field_label}')]/following-sibling::input"),
        (By.XPATH, f"//label[contains(text(), '{field_label}')]/../input"),
        (By.XPATH, "//input[@type='text']"),
        (By.XPATH, "//input[@type='email']"),
        (By.XPATH, "//input[@type='password']"),
    ]

    for by, selector in selectors:
        try:
            print(f"[DEBUG] Trying selector: {by} => {selector}")
            elem = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))
            elem.clear()
            elem.send_keys(value)
            print(f"[INFO] Sent value to element via {by}: {selector}")
            return True
        except Exception as e:
            print(f"[DEBUG] Selector failed: {by} => {selector} ({e.__class__.__name__}: {str(e)})")
            continue

    print(f"[ERROR] '{field_label}' field not found. Dumping visible input field info...")
    os.makedirs("debug_output", exist_ok=True)
    driver.save_screenshot(f"debug_output/{field_label}_not_found.png")

    try:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"[DEBUG] Total input fields found: {len(inputs)}")
        for i, input_elem in enumerate(inputs):
            print(f"  [{i}] id='{input_elem.get_attribute('id')}', name='{input_elem.get_attribute('name')}', placeholder='{input_elem.get_attribute('placeholder')}', type='{input_elem.get_attribute('type')}'")
    except Exception as e:
        print(f"[ERROR] Failed to dump input fields: {e}")

    return False

# ===============================
# Click Login Button
# ===============================

def click_login_button(driver):
    selectors = [
        (By.ID, "login_btn_admin"),
        (By.XPATH, "//button[normalize-space(text())='Login']"),
        (By.XPATH, "//button[normalize-space(text())='Sign In']"),
        (By.XPATH, "//button[contains(translate(text(), 'SIGNINLOGIN', 'signinlogin'), 'login')]"),
        (By.XPATH, "//input[@type='submit' and @value='Login']"),
        (By.XPATH, "//input[@type='submit' and @value='Sign In']"),
        (By.XPATH, "//button[@type='submit']"),
        (By.CSS_SELECTOR, "button.btn-submit")
    ]

    for by, selector in selectors:
        try:
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, selector)))
            try:
                element.click()
            except:
                driver.execute_script("arguments[0].click();", element)
            print(f"[INFO] Clicked login button using {by} - {selector}")
            return True
        except Exception as e:
            print(f"[WARN] Login button not found via {by} - {selector}: {e}")
            continue

    print("[ERROR] Login button not found")
    return False

# ===============================
# Navigate to 'Create User' Page
# ===============================

def navigate_to_create_user(driver):
    selectors = [
        (By.LINK_TEXT, "Create User"),
        (By.PARTIAL_LINK_TEXT, "Create"),
        (By.XPATH, "//a[contains(text(), 'Create User')]"),
        (By.XPATH, "//a[contains(text(), 'Create')]"),
        (By.XPATH, "//button[contains(text(), 'Create')]"),
        (By.XPATH, "//button[contains(text(), 'Add User')]"),
        (By.XPATH, "//button[contains(text(), 'Add Client')]"),
        (By.XPATH, "//span[contains(text(), 'Create')]"),
        (By.CSS_SELECTOR, "a.btn-create"),
        (By.CSS_SELECTOR, "button.btn-create"),
    ]

    for by, selector in selectors:
        try:
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, selector)))
            element.click()
            print(f"[INFO] Navigated to 'Create User' using {by} => {selector}")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"[DEBUG] Selector failed: {by} => {selector} ({e.__class__.__name__})")
            continue

    print("[ERROR] Could not find 'Create User' navigation button.")
    os.makedirs("debug_output", exist_ok=True)
    driver.save_screenshot("debug_output/create_user_not_found.png")
    return False

# ===============================
# Main Bot Logic
# ===============================

def process_user_bot(client_username, weburl):
    print(f"[START] Creating client '{client_username}' for '{weburl}'")

    site_data = find_user_by_weburl(weburl)
    if not site_data:
        print("[ERROR] Site data not found in users.json")
        return None

    driver = get_driver(headless=False)
    new_password = generate_password()

    try:
        # 1. Open login page
        driver.get(site_data['weburl'])
        time.sleep(10)

        os.makedirs("debug_output", exist_ok=True)
        driver.save_screenshot("debug_output/page_loaded.png")
        with open("debug_output/page_dump.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # 2. Switch iframe if username field not found
        if not driver.find_elements(By.ID, "username"):
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"[INFO] Found {len(iframes)} iframe(s)")
            for i, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    if driver.find_elements(By.ID, "username"):
                        print(f"[INFO] Switched to iframe #{i}")
                        break
                    driver.switch_to.default_content()
                except Exception as e:
                    print(f"[WARN] Failed to switch to iframe #{i}: {e}")
                    continue

        driver.switch_to.default_content()

        # 3. Fill login form
        if not smart_send_keys(driver, "username", site_data['username']):
            print("[ERROR] Username input not found.")
            return None

        if not smart_send_keys(driver, "password", site_data['password']):
            print("[ERROR] Password input not found.")
            return None

        if not click_login_button(driver):
            print("[ERROR] Login button not found.")
            return None

        time.sleep(5)
        print("[INFO] Login successful. Current URL:", driver.current_url)

        # 4. Navigate to 'Create Client' page using provided URL
        if 'client_creation_url' in site_data:
            create_url = site_data['client_creation_url']
            try:
                driver.get(create_url)
                print(f"[INFO] Navigated to create user page: {create_url}")
                time.sleep(3)
            except Exception as e:
                print(f"[ERROR] Failed to open client creation URL: {e}")
                return None
        else:
            print("[ERROR] client_creation_url not found in users.json for this website.")
            return None

        # 5. Fill and submit Create User form
        if not smart_send_keys(driver, "username", client_username):
            return None
        if not smart_send_keys(driver, "password", new_password):
            return None
        if not smart_send_keys(driver, "confirm_password", new_password):
            return None

        try:
            submit = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Create')]"))
            )
            submit.click()
            print("[INFO] Client creation submitted.")
            time.sleep(3)
            driver.save_screenshot("debug_output/client_created.png")
        except Exception as e:
            print(f"[ERROR] Failed to click create button: {e}")
            return None

        return {
            "username": client_username,
            "password": new_password,
            "weburl": weburl
        }

    except Exception as e:
        print(f"[EXCEPTION] An error occurred: {str(e)}")
        driver.save_screenshot("debug_output/exception.png")
        return None

    finally:
        driver.quit()
