# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import base64
import contextlib
import os
import re
import shutil
import time
from datetime import datetime
from urllib.parse import quote

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By

from ..Config import Config
from ..core.managers import edit_or_reply


def _resolve_chrome_bin():
    """Find Chrome/Chromium binary even when Config.CHROME_BIN is missing."""
    configured = getattr(Config, "CHROME_BIN", None)
    if configured and os.path.isfile(configured):
        return configured

    env_bin = os.environ.get("CHROME_BIN")
    if env_bin and os.path.isfile(env_bin):
        return env_bin

    for candidate in (
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/app/.apt/usr/bin/google-chrome",
    ):
        if os.path.isfile(candidate):
            return candidate

    return (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
    )


class chromeDriver:
    @staticmethod
    def start_driver():
        chrome_bin = _resolve_chrome_bin()
        if not chrome_bin:
            return None, "Chrome/Chromium not installed on this server."
        try:
            chrome_options = ChromeOptions()
            chrome_options.binary_location = chrome_bin
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument("--test-type")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920x1080")
            chrome_options.add_argument("--disable-gpu")
            prefs = {"download.default_directory": "./"}
            chrome_options.add_experimental_option("prefs", prefs)
            driver = webdriver.Chrome(options=chrome_options)
            return driver, None
        except Exception as err:
            return None, str(err)

    @staticmethod
    def _screenshot_via_api(inputstr):
        """Fallback screenshot when local Chrome/Chromium is unavailable."""
        errors = []

        try:
            resp = requests.get(
                "https://api.microlink.io/",
                params={
                    "url": inputstr,
                    "screenshot": "true",
                    "meta": "false",
                },
                timeout=60,
            )
            resp.raise_for_status()
            payload = resp.json()
            shot_url = (payload.get("data") or {}).get("screenshot", {}).get("url")
            if shot_url:
                img_resp = requests.get(shot_url, timeout=60)
                img_resp.raise_for_status()
                if img_resp.content:
                    return img_resp.content, f"**url : **{inputstr}"
        except Exception as err:
            errors.append(f"microlink: {err}")

        try:
            thumb_url = f"https://image.thum.io/get/width/1280/noanimate/{quote(inputstr, safe='')}"
            img_resp = requests.get(thumb_url, timeout=60)
            img_resp.raise_for_status()
            content_type = img_resp.headers.get("content-type", "")
            if img_resp.content and content_type.startswith("image"):
                return img_resp.content, f"**url : **{inputstr}"
        except Exception as err:
            errors.append(f"thum.io: {err}")

        detail = errors[-1] if errors else "unknown error"
        return None, (
            "Could not capture screenshot. Chrome/Chromium is not installed here "
            f"and the online fallback failed ({detail})."
        )

    @staticmethod
    def bypass_cache(inputstr, driver=None):
        if driver is None:
            driver, error = chromeDriver.start_driver()
            if not driver:
                return None, error
        driver.get(inputstr)
        if "google" in inputstr:
            with contextlib.suppress(Exception):
                driver.find_element(By.ID, "L2AGLb").click()
            with contextlib.suppress(Exception):
                driver.find_element(
                    By.XPATH, "//button[@aria-label='Accept all']"
                ).click()
        return driver, None

    @staticmethod
    def get_html(inputstr):
        driver, error = chromeDriver.bypass_cache(inputstr)
        if not driver:
            return None, error
        html = driver.page_source
        driver.close()
        return html, None

    @staticmethod
    def get_rayso(
        inputstr, file_name="Rayso.png", title="CatUB", theme="crimson", darkMode=True
    ):
        url = f'https://ray.so/#code={base64.b64encode(inputstr.encode()).decode().replace("+","-")}&title={title}&theme={theme}&padding=64&darkMode={darkMode}&language=python'
        driver, error = chromeDriver.start_driver()
        if error:
            return None, error
        driver.set_window_size(2000, 20000)
        driver.get(url)
        element = driver.find_element(By.CLASS_NAME, "Controls_controls__kwzcE")
        driver.execute_script("arguments[0].style.display = 'none';", element)
        frame = driver.find_element(By.CLASS_NAME, "Frame_frame__Dmfe9")
        frame.screenshot(file_name)
        driver.quit()
        return file_name, None

    @staticmethod
    async def get_screenshot(inputstr, event=None):
        start = datetime.now()
        driver, error = None, None
        if _resolve_chrome_bin():
            driver, error = chromeDriver.bypass_cache(inputstr)
        if driver:
            try:
                if event:
                    await edit_or_reply(
                        event, "`Calculating Page Dimensions with Google Chrome BIN`"
                    )
                height = driver.execute_script(
                    "return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);"
                )
                width = driver.execute_script(
                    "return Math.max(document.body.scrollWidth, document.body.offsetWidth, document.documentElement.clientWidth, document.documentElement.scrollWidth, document.documentElement.offsetWidth);"
                )
                driver.set_window_size(width + 100, height + 100)
                im_png = driver.get_screenshot_as_png()
                end = datetime.now()
                ms = (end - start).seconds
                return im_png, f"**url : **{inputstr} \n**Time :** `{ms} seconds`"
            finally:
                with contextlib.suppress(Exception):
                    driver.quit()

        if event:
            await edit_or_reply(
                event, "`Chrome unavailable, using online screenshot fallback...`"
            )
        image, response = chromeDriver._screenshot_via_api(inputstr)
        if image:
            end = datetime.now()
            ms = (end - start).seconds
            return image, f"{response}\n**Time :** `{ms} seconds`"
        return None, response or error or "Could not capture screenshot."


class GooglePic:
    def __init__(self, image, site):
        self.image = image
        self.site = site

    def __hash__(self):
        return hash(self.image + self.site)

    @staticmethod
    def __title_fetch__(html):
        title = ""
        pattern1 = re.compile(r"Image search ([^\"]+)")
        pattern2 = re.compile(r"\],\"(.*?)(?=\",null,\[\[\"ROSTI\")")
        if match := pattern1.search(html):
            title = match[1]
        elif match := pattern2.search(html):
            title = match[1]
        return "Visual matches" if (len(title) > 100 or not title) else title

    @staticmethod
    def reverse_data(image_filename, flag=False):
        data = {
            "title": None,
            "lens": None,
            "google": None,
            "image_set": None,
            "error": None,
        }
        with open(image_filename, mode="rb") as f:
            url = f"https://lens.google.com/upload?ep=ccm&s=&st={int(time.time())}"
            try:
                res1 = requests.post(url, files={"encoded_image": f})
                if res1.ok:
                    data["lens"] = re.search(r"https?://[^\"]+", res1.text).group()
                    res2 = requests.get(data["lens"])
                    if res2.ok:
                        html = res2.text.encode().decode("unicode_escape")
                        with contextlib.suppress(Exception):
                            data["google"] = re.search(
                                r"https://www.google.com/search\?tbs.+?(?=\")", html
                            ).group()
                        if not data["google"]:
                            html, data["error"] = chromeDriver.get_html(data["lens"])
                            html = html.encode().decode("unicode_escape")
                            data["google"] = re.search(
                                r"https://www.google.com/search\?tbs.+?(?=\")", html
                            ).group()
                    if html:
                        if flag:
                            data["image_set"] = set()
                            for link in re.findall(
                                r"https://www.google.com/imgres\?imgurl.+?(?=\")", html
                            ):
                                image = re.search(r"imgurl=(.+?)&", link)[1]
                                site = re.search(r"imgrefurl=(.+?)&", link)[1]
                                if image.endswith(
                                    (".jpg", ".jpeg", ".png", ".gif")
                                ) or site.endswith((".jpg", ".jpeg", ".png", ".gif")):
                                    data["image_set"].add(GooglePic(image, site))
                        data["title"] = GooglePic.__title_fetch__(html)
            except Exception as error:
                data["error"] = str(error)
        return data
