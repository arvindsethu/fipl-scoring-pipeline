from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scores_message import get_scores_message
import time

# === CONFIGURATION ===

# Path to your Edge WebDriver executable
edge_driver_path = r"C:\Users\arvin\Code\fipl-scoring-pipeline\whatsapp_bot\edgedriver_win64\msedgedriver.exe"

# Path to your Edge user data (so you stay logged into WhatsApp Web)
edge_profile_path = r"C:\Users\arvin\AppData\Local\Microsoft\Edge\User Data"
profile_directory = "Default"  # Or "Profile 1", etc.

# Name of the WhatsApp group or contact
# group_name = "FIPL (M)"
group_name = "Arvind UK Sim (You)"

while True:
    try:
        # === SETUP EDGE OPTIONS ===
        options = Options()
        options.add_argument(f"user-data-dir={edge_profile_path}")
        options.add_argument(f"profile-directory={profile_directory}")
        options.add_argument("--start-maximized")

        # === LAUNCH EDGE ===
        driver = webdriver.Edge(service=Service(edge_driver_path), options=options)

        # === OPEN WHATSAPP WEB ===
        driver.get("https://web.whatsapp.com")

        print("Waiting for WhatsApp Web to load...")
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="side"]/div[1]/div/div[2]/div/div/div[1]'))
        )

        # === SEARCH AND OPEN GROUP ===
        search_box = driver.find_element(By.XPATH, '//*[@id="side"]/div[1]/div/div[2]/div/div/div[1]')
        search_box.click()
        search_box.send_keys(group_name)
        time.sleep(2)
        search_box.send_keys(Keys.ENTER)

        # === GET THE SCORES MESSAGE ===
        message = get_scores_message()
        # message = "Testing message"

        # === TYPE AND SEND MESSAGE (AS ONE BLOCK) ===
        message_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[3]/div[1]'))
        )

        # Split the message by newlines and send with Shift+Enter for in-bubble line breaks
        lines = message.split('\n')
        for idx, line in enumerate(lines):
            message_box.send_keys(line)
            if idx != len(lines) - 1:
                # Insert a newline without sending
                message_box.send_keys(Keys.SHIFT, Keys.ENTER)

        # Finally, send the entire block as one message
        message_box.send_keys(Keys.ENTER)

        print("✅ Message sent!")

        time.sleep(5)
        driver.quit()
        
        print("Waiting 10 minutes before next update...")
        time.sleep(600)  # 600 seconds = 10 minutes
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        try:
            driver.quit()
        except:
            pass
        print("Retrying in 10 minutes...")
        time.sleep(600)
