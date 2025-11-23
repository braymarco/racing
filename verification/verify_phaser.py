from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8000")

        # Wait for the voting screen to be visible (which is the default state)
        page.wait_for_selector("#voting-screen")

        # Also wait for canvas to be present (Phaser initialized)
        page.wait_for_selector("canvas")

        # Wait a bit for Phaser to render the initial state (black background)
        time.sleep(2)

        page.screenshot(path="/home/jules/verification/phaser_init.png")
        browser.close()

if __name__ == "__main__":
    run()
