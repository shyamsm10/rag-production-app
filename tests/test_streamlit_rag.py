import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


STREAMLIT_URL = "http://localhost:8501"


@pytest.fixture
def driver():

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    driver.get(STREAMLIT_URL)

    yield driver

    driver.quit()


def test_upload_and_chat(driver):

    wait = WebDriverWait(driver, 90)

    upload_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
    )

    upload_input.send_keys(
        r"C:\Users\Shyam\Downloads\DATA-STRUCTURE-AND-ALGORITHM-MERGE.pdf"
    )

    go_to_chat = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Chat')]")
        )
    )

    go_to_chat.click()

    chat_box = wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "textarea"))
    )

    chat_box.send_keys("tell me which week is today?")
    chat_box.send_keys(Keys.RETURN)

    assistant_messages = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//div[contains(@data-testid,'stChatMessage')]")
        )
    )

    assert len(assistant_messages) >= 2