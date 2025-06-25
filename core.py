import json
import random
import string
import time
import os
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

def get_driver(headless=False):
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return uc.Chrome(options=options)


# ===============================
# Smart Input Handler
# ===============================

def smart_send_keys(driver, field_label, value, timeout=20):
    selectors = [
        (By.ID, field_label),
        (By.NAME, field_label),
        (By.XPATH, f"//input[@placeholder='{field_label}']"),
        (By.XPATH, f"//input[contains(@id, '{field_label.lower()}') or contains(@name, '{field_label.lower()}')]"),
        (By.XPATH, f"//label[contains(text(), '{field_label}')]/following-sibling::input"),
        (By.XPATH, "//*[@id='username']"),
        (By.XPATH, "//input[@type='text']")
    ]

    for by, selector in selectors:
        try:
            print(f"[DEBUG] Trying selector: {by} => {selector}")
            elem = WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, selector)))
            elem.clear()
            elem.send_keys(value)
            print(f"[INFO] Sent value to element via {by}: {selector}")
            return True
        except Exception as e:
            print(f"[DEBUG] Selector failed: {by} => {selector} ({str(e)})")
            continue

    print(f"[ERROR] '{field_label}' field not found. Dumping input field info.")
    os.makedirs("debug_output", exist_ok=True)
    driver.save_screenshot(f"debug_output/{field_label}_not_found.png")

    try:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"\n[DEBUG] Total input fields found: {len(inputs)}")
        for i, input_elem in enumerate(inputs):
            print(f"  [{i}] id='{input_elem.get_attribute('id')}', name='{input_elem.get_attribute('name')}', placeholder='{input_elem.get_attribute('placeholder')}'")
    except Exception as e:
        print("[ERROR] Could not extract input element info:", str(e))

    return False


# ===============================
# Login Button Click
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
# Main Bot Logic
# ===============================

def process_user_bot(client_username, weburl):
    print(f"[START] Creating client '{client_username}' for '{weburl}'")

    site_data = find_user_by_weburl(weburl)
    if not site_data:
        print("[ERROR] Site data not found in users.json")
        return None

    driver = get_driver(headless=False)  # disable headless for real site debugging
    new_password = generate_password()

    try:
        driver.get(site_data['weburl'])
        time.sleep(10)

        os.makedirs("debug_output", exist_ok=True)
        driver.save_screenshot("debug_output/page_loaded.png")
        with open("debug_output/page_dump.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        #print('html==>', driver.page_source[:1000])  # First 1000 characters



        # Try switching to iframe if input fields not found
        if not driver.find_elements(By.ID, "username"):
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"[INFO] Found {len(iframes)} iframe(s)")
            for i, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    if driver.find_elements(By.ID, "username"):
                        print(f"[INFO] Switched to iframe #{i} to access username field")
                        break
                    driver.switch_to.default_content()
                except Exception as e:
                    print(f"[WARN] Failed to switch to iframe #{i}: {e}")
                    continue

        if not smart_send_keys(driver, "username", site_data['username']):
            return None
        if not smart_send_keys(driver, "password", site_data['password']):
            return None
        if not click_login_button(driver):
            return None

        time.sleep(5)
        print("[INFO] Login action completed, current URL:", driver.current_url)

        return {
            "username": client_username,
            "password": new_password,
            "weburl": weburl
        }

    except Exception as e:
        print("[EXCEPTION] An error occurred:", str(e))
        driver.save_screenshot("debug_output/exception.png")
        return None

    finally:
        driver.quit()
