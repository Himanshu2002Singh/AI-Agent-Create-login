import json
import random
import string
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from selenium.webdriver.chrome.options import Options
import shutil 
import tempfile
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

def smart_send_keys(driver, field_label, value, timeout=10):
    selectors = [
        (By.ID, field_label),
        (By.NAME, field_label),
        (By.XPATH, f"//input[@placeholder='{field_label}']"),
        (By.XPATH, f"//input[contains(@id, '{field_label.lower()}') or contains(@name, '{field_label.lower()}')]"),
        (By.XPATH, f"//label[contains(text(), '{field_label}')]/following-sibling::input")
    ]
    for by, selector in selectors:
        try:
            elem = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
            elem.clear()
            elem.send_keys(value)
            return True
        except:
            continue
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
            try:
                element.click()
            except:
                driver.execute_script("arguments[0].click();", element)
            return True
        except:
            continue
    return False
def get_driver(options=None):
    if options is None:
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless")  # Optional
        options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
    
    driver = webdriver.Chrome(options=options)
    return driver, options.arguments[-1].split('=')[1]  # returning driver and profile path

def  process_user_bot(client_usernamever,weburl):
    options = Options()

                     # Create a unique temporary profile to avoid --user-data-dir conflict
    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless")  # Optional: Remove if you want GUI

    site_data = find_user_by_weburl(weburl)
    if not site_data:
        return None
    driver, profile_path = get_driver(options)

    #driver = webdriver.Chrome()
    new_password = generate_password()

    try:
        driver.get(site_data['weburl'])
        smart_send_keys(driver, "username", site_data['username'])
        smart_send_keys(driver, "password", site_data['password'])    new_password = generate_password()

    try:
        driver.get(site_data['weburl'])
        smart_send_keys(driver, "username", site_data['username'])
        smart_send_keys(driver, "password", site_data['password'])
        click_login_button(driver)
        time.sleep(5)

        current_url = driver.current_url.lower()
        if not any(keyword in current_url for keyword in ["dashboard", "home", "panel", "client", "admin"]):
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
                return None

        smart_send_keys(driver, "name", extract_name_from_username(client_username))
        smart_send_keys(driver, "username", client_username)
        smart_send_keys(driver, "password", new_password)
        smart_send_keys(driver, "password_confirmation", new_password)

        # Submit
        for xpath in [
            "//button[normalize-space(text())='SUBMIT']",
            "//button[contains(text(),'Submit')]",
            "//input[@type='submit' and @value='Submit']"
        ]:
            try:
                WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
                break
            except:
                continue
        else:
            return None

        return {
            "username": client_username,
            "password": new_password,
            "weburl": weburl
        }

    except Exception as e:
        return None

    finally:
        time.sleep(3)
        driver.quit()
