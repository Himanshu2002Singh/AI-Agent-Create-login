import json
import random
import string
import time
from urllib.parse import urlparse
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fastapi import FastAPI
from pydantic import BaseModel


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
            elem = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
            elem.clear()
            elem.send_keys(value)
            print(f"[INFO] Sent value to element via {by}: {selector}")
            return True
        except:
            continue

    driver.save_screenshot(f"/tmp/{field_label}_not_found.png")
    print(f"[ERROR] '{field_label}' field not found. Screenshot saved.")
    return False


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
            element.click()
            return True
        except:
            continue

    return False


def get_chrome_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return uc.Chrome(options=options)


def process_user_bot(client_username, weburl):
    print(f"[START] Creating client '{client_username}' for '{weburl}'")

    site_data = find_user_by_weburl(weburl)
    if not site_data:
        print("[ERROR] Site data not found in users.json")
        return None

    driver = get_chrome_driver()
    new_password = generate_password()

    try:
        driver.get(site_data['weburl'])
        time.sleep(3)  # Let page load

        print("[INFO] Page loaded. Saving screenshot for debugging.")
        driver.save_screenshot("/tmp/page_loaded.png")

        if not smart_send_keys(driver, "username", site_data['username']):
            return None

        if not smart_send_keys(driver, "password", site_data['password']):
            return None

        if not click_login_button(driver):
            print("[ERROR] Login button not clickable")
            return None

        time.sleep(5)
        current_url = driver.current_url.lower()
        print(f"[INFO] Current URL after login: {current_url}")

        if not any(k in current_url for k in ["dashboard", "home", "panel", "client", "admin"]):
            print("[ERROR] Login failed — Not redirected to dashboard")
            driver.save_screenshot("/tmp/failed_login.png")
            return None

        if site_data.get("create_client_url"):
            driver.get(site_data["create_client_url"])
        else:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Clients')]"))
            ).click()
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Add Client') or contains(text(),'Create')]"))
            ).click()

        if not smart_send_keys(driver, "name", extract_name_from_username(client_username)):
            return None
        if not smart_send_keys(driver, "username", client_username):
            return None
        if not smart_send_keys(driver, "password", new_password):
            return None
        if not smart_send_keys(driver, "password_confirmation", new_password):
            return None

        for xpath in [
            "//button[normalize-space(text())='SUBMIT']",
            "//button[contains(text(),'Submit')]",
            "//input[@type='submit' and @value='Submit']"
        ]:
            try:
                WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
                print("[SUCCESS] Client submitted")
                break
            except:
                continue
        else:
            print("[ERROR] Submit button not found")
            return None

        print("[SUCCESS] Client creation completed.")
        return {
            "username": client_username,
            "password": new_password,
            "weburl": weburl
        }

    except Exception as e:
        print("[EXCEPTION]", str(e))
        driver.save_screenshot("/tmp/unexpected_exception.png")
        return None

    finally:
        driver.quit()


# FastAPI Setup
app = FastAPI()


class ClientData(BaseModel):
    client_username: str
    weburl: str


@app.post("/create-client")
def create_client(data: ClientData):
    result = process_user_bot(data.client_username, data.weburl)
    if result:
        return {"status": "success", "data": result}
    return {"status": "error", "message": "Failed to create client"}
