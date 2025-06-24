import json
import random
import string
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================
# HELPER FUNCTIONS
# ==========================

def generate_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(chars) for _ in range(length))

def extract_name_from_username(username):
    return username[:4].capitalize()

def extract_base_domain(weburl):
    parsed = urlparse(weburl if weburl.startswith('http') else f'https://{weburl}')
    domain = parsed.netloc or parsed.path
    domain = domain.lower().strip()
    parts = domain.split('.')
    if len(parts) > 2:
        domain = '.'.join(parts[-2:])
    return domain

def find_user_by_weburl(weburl, users_json='users.json'):
    base = extract_base_domain(weburl)
    with open(users_json, 'r', encoding='utf-8') as file:
        users = json.load(file)
        for u in users:
            if extract_base_domain(u['weburl']) == base:
                return u
    return None

# ==========================
# SMART SEND KEYS
# ==========================

def smart_send_keys(driver, field_label, value, timeout=10):
    selectors = [
        (By.ID, field_label),
        (By.NAME, field_label),
        (By.XPATH, f"//input[@placeholder='{field_label}']"),
        (By.XPATH, f"//input[contains(@id, '{field_label.lower()}') or contains(@name, '{field_label.lower()}')]"),
        (By.XPATH, f"//label[contains(text(), '{field_label}')]/following-sibling::input"),
        (By.XPATH, "//input[@type='text']")
    ]
    for by, selector in selectors:
        try:
            elem = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
            elem.clear()
            elem.send_keys(value)
            print(f"[INFO] Sent value to field '{field_label}' using {by} - {selector}")
            return True
        except Exception as e:
            print(f"[WARN] Could not find '{field_label}' using {by} - {selector} → {e}")
            continue
    driver.save_screenshot(f"/tmp/{field_label}_not_found.png")
    print(f"[ERROR] Could not locate '{field_label}'. Screenshot saved.")
    return False

# ==========================
# CLICK LOGIN BUTTON
# ==========================

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
            element = WebDriverWait(driver, 6).until(EC.element_to_be_clickable((by, selector)))
            try:
                element.click()
            except:
                driver.execute_script("arguments[0].click();", element)
            print(f"[INFO] Clicked login button using {by} - {selector}")
            return True
        except Exception as e:
            print(f"[WARN] Login button not found via {by} - {selector} → {e}")
            continue
    print("[ERROR] Login button not found")
    return False

# ==========================
# GET HEADLESS DRIVER
# ==========================

from selenium.webdriver.chrome.options import Options

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=chrome_options)

# ==========================
# MAIN BOT LOGIC
# ==========================

def process_user_bot(client_username, weburl):
    print(f"[START] Creating client '{client_username}' for '{weburl}'")
    site_data = find_user_by_weburl(weburl)
    if not site_data:
        print("[ERROR] Site data not found in users.json")
        return None

    driver = get_driver()
    new_password = generate_password()

    try:
        driver.get(site_data['weburl'])
        time.sleep(2)

        # Save initial page state
        driver.save_screenshot("/tmp/page_loaded.png")
        with open("/tmp/page_dump.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("[DEBUG] Page loaded. Screenshot and HTML saved.")

        smart_send_keys(driver, "username", site_data['username'])
        smart_send_keys(driver, "password", site_data['password'])

        if not click_login_button(driver):
            print("[ERROR] Login failed")
            return None

        time.sleep(5)
        current_url = driver.current_url.lower()
        print(f"[DEBUG] Current URL after login: {current_url}")

        if not any(keyword in current_url for keyword in ["dashboard", "home", "panel", "client", "admin"]):
            print("[ERROR] Login didn't redirect to expected page")
            driver.save_screenshot("/tmp/login_failed.png")
            return None

        if site_data.get("create_client_url"):
            driver.get(site_data["create_client_url"])
        else:
            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Clients')]"))
                ).click()
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Add Client') or contains(text(),'Create')]"))
                ).click()
            except:
                print("[ERROR] Could not navigate to client creation page")
                return None

        smart_send_keys(driver, "name", extract_name_from_username(client_username))
        smart_send_keys(driver, "username", client_username)
        smart_send_keys(driver, "password", new_password)
        smart_send_keys(driver, "password_confirmation", new_password)

        for xpath in [
            "//button[normalize-space(text())='SUBMIT']",
            "//button[contains(text(),'Submit')]",
            "//input[@type='submit' and @value='Submit']"
        ]:
            try:
                WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
                print("[SUCCESS] Client submitted successfully")
                break
            except:
                continue
        else:
            print("[ERROR] Submit button not found")
            return None

        print("[SUCCESS] Client creation complete")
        return {
            "username": client_username,
            "password": new_password,
            "weburl": weburl
        }

    except Exception as e:
        print(f"[EXCEPTION] {str(e)}")
        driver.save_screenshot("/tmp/unexpected_exception.png")
        return None

    finally:
        time.sleep(2)
        driver.quit()
