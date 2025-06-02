from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# === CONFIGURATION ===
edge_driver_path = r"C:\Users\arvin\Code\testing_playground\whatsapp_automation\edgedriver_win64\msedgedriver.exe"
edge_profile_path = r"C:\Users\arvin\AppData\Local\Microsoft\Edge\User Data"
profile_directory = "Default"  # Or "Profile 1" etc.

group_name = "Arvind UK Sim (You)"  # Change this
message = "This is a test message sent by a bot"  # Your message

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

# === TYPE AND SEND MESSAGE ===
message_box = WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[3]/div[1]'))
)
message_box.send_keys(message + Keys.ENTER)

print("✅ Message sent!")

time.sleep(5)
driver.quit()
