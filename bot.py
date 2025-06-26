import json
import time
import os
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ✅ Load admin credentials from users.json
def load_admin_credentials(filepath='users.json'):
    credentials = {}
    with open(filepath, mode='r') as file:
        users = json.load(file)
        for user in users:
            credentials[user['weburl'].strip()] = (user['username'], user['password'])
    return credentials

# ✅ Login to the admin panel
def login(driver, url, username, password):
    driver.get(url)
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//input[@name='username']"))).send_keys(username)
    driver.find_element(By.XPATH, "//input[@name='password']").send_keys(password)
    driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()

# ✅ Navigate to Client List → Down-line
def navigate_to_downline(driver):
    try:
        print("🧭 Navigating to 'Down-line' section...")
        client_list_trigger = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Client List')] | //span[normalize-space()='Client List']"))
        )
        time.sleep(0.5)
        client_list_trigger.click()
        print("✅ Clicked on 'Client List'")

        downline_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//ul[@id='listUser']//a[contains(., 'Down-line')] | //span[contains(text(), 'Down Line')]"))
        )
        time.sleep(0.3)
        downline_link.click()
        print("✅ Clicked on 'Down-line'")

    except TimeoutException:
        print("❌ Timeout waiting for 'Client List' or 'Down-line'")
        os.makedirs("errors", exist_ok=True)
        driver.save_screenshot("errors/timeout_error.png")
        with open("errors/page_source_on_timeout.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise

# ✅ Search for client
def search_client(driver, username):
    try:
        print(f"🔍 Searching for client: {username}")
        search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "search-user")))
        search_box.clear()
        search_box.send_keys(username)
        search_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Search')]")))
        search_button.click()
        print("🔎 Search button clicked.")
        time.sleep(2)

        candidates = driver.find_elements(By.XPATH, f"//*[contains(text(), '{username}')]")
        for element in candidates:
            if username.lower() in element.text.lower():
                print(f"✅ Found client '{username}'")
                return True

        raise Exception("Client not matched in visible elements.")

    except Exception as e:
        print(f"❌ Client search failed: {e}")
        os.makedirs("errors", exist_ok=True)
        driver.save_screenshot(f"errors/error_{username}.png")
        with open(f"errors/page_source_{username}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return False

# ✅ Perform deposit or withdrawal
def perform_transaction(driver, client_username, amount, action_type):
    os.makedirs("errors", exist_ok=True)
    try:
        print(f"⚙️ Performing {action_type} for {client_username}...")
        rows = driver.find_elements(By.XPATH, "//table//tr")
        found = False

        for row in rows:
            if client_username.lower() in row.text.lower():
                found = True
                try:
                    if action_type == "deposit":
                        button = row.find_element(By.XPATH, ".//a[contains(@class, 'btn_deposit') and contains(text(), 'Bank Deposit')] | .//a[normalize-space(text())='Deposit']")
                    elif action_type == "withdraw":
                        button = row.find_element(By.XPATH, ".//a[contains(@class, 'btn_withdraw') and contains(text(), 'Bank Withdraw')] | .//a[normalize-space(text())='Withdraw']")
                    else:
                        raise ValueError(f"Invalid action type: {action_type}")

                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(button))
                    button.click()
                    print(f"✅ Clicked {action_type} button for {client_username}")
                except Exception as e:
                    raise Exception(f"Failed to click {action_type} button: {e}")
                break

        if not found:
            print(f"❌ Client '{client_username}' not found.")
            return

        input_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
            By.XPATH, "//input[(@id='amount' and contains(@placeholder, 'Chips')) or contains(@placeholder, 'Deposit') or contains(@placeholder, 'Withdraw') or contains(@id, 'deposit_chips') or contains(@id, 'withdraw_chips')]"
        )))
        input_box.clear()
        input_box.send_keys(str(amount))

        update_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((
            By.XPATH, "//button[@type='submit' and contains(text(), 'Update')]"
        )))
        update_button.click()

        print(f"✅ {action_type.capitalize()} ₹{amount} → {client_username}")

    except Exception as e:
        print(f"❌ Failed to {action_type} → {client_username}: {e}")
        driver.save_screenshot(f"errors/failed_{client_username}_{action_type}.png")
        with open(f"errors/page_source_{client_username}_{action_type}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

# ✅ MAIN FUNCTION with Unique User Data Dir
def process_transaction_request(request_data):
    credentials = load_admin_credentials()

    url = request_data.get('url')
    username = request_data.get('username')
    amount = request_data.get('amount')
    action_type = request_data.get('type').lower()

    if action_type not in ['deposit', 'withdraw']:
        return {"status": "error", "message": f"Invalid action type: {action_type}"}

    if url not in credentials:
        return {"status": "error", "message": f"Admin credentials not found for URL: {url}"}

    # Setup Chrome Options with unique user-data-dir
    options = Options()
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    unique_dir = f"/tmp/selenium_profile_{uuid.uuid4()}"
   

    service = Service()  # You can specify chromedriver path if needed

    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()

    try:
        login(driver, url, *credentials[url])
        navigate_to_downline(driver)
        time.sleep(1)

        if search_client(driver, username):
            perform_transaction(driver, username, amount, action_type)
            return {"status": "success", "message": f"{action_type.capitalize()} ₹{amount} for {username} complete"}
        else:
            return {"status": "error", "message": f"Client '{username}' not found"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

    finally:
        driver.quit()
        try:
            if os.path.exists(unique_dir):
                import shutil
                shutil.rmtree(unique_dir)
        except Exception as cleanup_error:
            print(f"⚠️ Failed to clean up user data dir: {cleanup_error}")
