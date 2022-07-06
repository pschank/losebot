#!/usr/bin/env python

import configparser
import datetime
import getpass
import os
from pydoc import classname
import shutil
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_setup import get_webdriver_for

# Program for downloading and parsing log data from the Loseit.com web site.


# Compute time range for weekly food log files that we want to download.
# We go BACKWARDS in time from "now".
# Start is a Monday 8am for most recent week with FULL data--in other words, skip this current week.
# Endpoint is where we left off last time -- initially  May 10, 2010 (start of all data)
EXPORT_WEEKLY_DATA_URL = "https://loseit.com/export/weekly?date=%s"
SETTINGS_URL = "https://www.loseit.com/#Settings:Subscription%5ESubscription"
WEEK_SECS = 604800  # 1 week in seconds
DOWNLOAD_DIR = os.path.dirname(os.path.abspath(__file__)) + "/downloaded_loseit_food_exercise/"
LOSE_IT_CREATION_DATE = datetime.datetime.strptime("2008-01-01", '%Y-%m-%d')

USER_AGENT= 'Mozilla/5.0 (Macintosh; Intel Mac OS X 12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
TMP_DOWNLOAD_FOLDER = "/tmp/loseit_downloads"

def main():
    start_date_from_properties = ""
    user = ""
    password = ""

    options = webdriver.ChromeOptions()

    options.add_argument('headless')
    options.add_argument(f'user-agent={USER_AGENT}')
    prefs = {"download.default_directory": TMP_DOWNLOAD_FOLDER}
    options.add_experimental_option("prefs", prefs);
    # options.add_argument(f"download.default_directory={DOWNLOAD_FOLDER}")
    browser = get_webdriver_for("chrome", options=options)
    if len(sys.argv) > 1:
        if not os.path.exists(sys.argv[1]):
            print("cannot find file: %s" % sys.argv[1])
            sys.exit(1)
        config = configparser.RawConfigParser()
        config.read(sys.argv[1])
        try:
            user = config.get('Losebot', 'username')
            password = config.get('Losebot', 'password')
            try:
                start_date_from_properties = config.get('Losebot', 'startdate')
            except Exception:
                pass # ok not to have startdate

        except Exception:
            print("""
Expected file to have a header and 2 required entries like:

[Losebot]
username=myemail@someserver.com
password=mysecretpassword
""")
            sys.exit(1)

    if user == "" or password == "":
        password, user = prompt_login()

    if not os.path.exists(TMP_DOWNLOAD_FOLDER):
        os.mkdir(TMP_DOWNLOAD_FOLDER)
    else:
        files = os.listdir(TMP_DOWNLOAD_FOLDER)
        for f in files:
            os.remove(os.path.join(TMP_DOWNLOAD_FOLDER, f))

    login(browser, "https://my.loseit.com/login/?r=https%3A%2F%2Floseit.com", user, password)

    if not is_logged_in(browser):
        print("login unsuccessful")
        sys.exit(1)

    # first case: check download dir to see what we have already, if any
    last_downloaded_timestamp = get_startdate_from_downloads()
    # print("last downloaded")
    # print(last_downloaded_timestamp)
    if last_downloaded_timestamp == 0:
        # user's first time; use start date from file or prompt for start date
        if start_date_from_properties == "":
            start_date_timestamp = prompt_start_date()
        else:
            start_date_timestamp = convert_nearest_monday_to_timestamp(start_date_from_properties)

            if start_date_timestamp < float(LOSE_IT_CREATION_DATE.strftime("%s")):
                raise Exception(
                    "start date in properties cannot be before {0}".format(LOSE_IT_CREATION_DATE.strftime('%Y-%m-%d')))

    # print("start date converted")
            # print(start_date_timestamp)

    else:
        # if start_date_from_properties and last_downloaded are both specified
        # warn & use last download
        if start_date_from_properties != "":
            print("Overriding specified start date because we found previous downloads; updating from there.")
        start_date_timestamp = last_downloaded_timestamp

    # print("start date for download")
    # print(start_date_timestamp)
    download_weekly_food_log_files(browser, start_date_timestamp)


def convert_nearest_monday_to_timestamp(year_month_day_string):
    start_date_parsed = datetime.datetime.strptime(year_month_day_string, '%Y-%m-%d')
    start_date = get_previous_monday(start_date_parsed)
    start_date_timestamp = float(start_date.strftime("%s"))
    return start_date_timestamp


def prompt_login():
    user = input("Username: ")
    password = getpass.getpass("Password: ")
    return password, user


def login(browser, url, user, password):
    print("attempting to log in...")
    browser.get(url)
    email = browser.find_element(By.ID, "email")
    email.send_keys(user)
    passwd = browser.find_element(By.ID, "password")
    passwd.send_keys(password)
    browser.find_element(By.XPATH, "//button[@type='submit']").click()
    WebDriverWait(browser, 15).until(EC.url_changes(browser.current_url))

def pretty_date(secs_since_epoch):
    value = datetime.datetime.fromtimestamp(secs_since_epoch)
    return value.strftime('%Y-%m-%d')


def content_is_ok(filename):
    with open(filename) as f:
        return "Date,Name,Icon,Type,Quantity,Units,Calories,Deleted,Fat" in f.readline()


def download_weekly_food_log_files(browser, start_date_timestamp):
    end_date_timestamp = get_last_monday_timestamp(datetime.datetime.now())
    print("start date timestamp")
    print(start_date_timestamp)
    # Prevent illogical situation where start is after the end
    if end_date_timestamp < start_date_timestamp:
        print("nothing to download: up to date")
        sys.exit(0)

    # sys.exit(0) # todo debugging

    weekly_timestamp = start_date_timestamp
    while weekly_timestamp <= end_date_timestamp:
        filename = DOWNLOAD_DIR + "%s_food.csv" % pretty_date(weekly_timestamp)
        url_timestamp_millis = int(round(weekly_timestamp * 1000))
        files = os.listdir(TMP_DOWNLOAD_FOLDER)
        if files:
            print("expected empty folder to begin with at: %s" % TMP_DOWNLOAD_FOLDER)
            sys.exit(1)
        browser.get(EXPORT_WEEKLY_DATA_URL % url_timestamp_millis)
        wait4download(TMP_DOWNLOAD_FOLDER, 10, 1)

        files = os.listdir(TMP_DOWNLOAD_FOLDER)
        shutil.move(os.path.join(TMP_DOWNLOAD_FOLDER, files[0]), filename)
        if not content_is_ok(filename):
            with open("/tmp/failed_export.html", 'w+') as f:
                f.write(browser.page_source)
            os.remove(filename)
            print("failed to retrieve " + EXPORT_WEEKLY_DATA_URL % url_timestamp_millis)
            sys.exit(1)
        else:
            print("saved file: %s" % filename)
            weekly_timestamp += WEEK_SECS

def wait4download(directory, timeout, nfiles=None):
    """
    Wait for downloads to finish with a specified timeout.

    Args
    ----
    directory : str
        The path to the folder where the files will be downloaded.
    timeout : int
        How many seconds to wait until timing out.
    nfiles : int, defaults to None
        If provided, also wait for the expected number of files.

    """
    seconds = 0
    dl_wait = True
    while dl_wait and seconds < timeout:
        time.sleep(1)
        dl_wait = False
        files = os.listdir(directory)
        if nfiles and len(files) != nfiles:
            dl_wait = True

        seconds += 1
    return seconds

def is_logged_in(browser):
    # a redirect to a page with a login means that you have NOT successfully logged in.
    # a page with a login has "Sign In" in text.
    result = "Log In" not in str(browser.page_source)
    if not result:
        with open('/tmp/loseit_login_result.html', 'w+') as f:
            f.write(browser.page_source)
    else:
        with open('/tmp/post_login_result.html', 'w+') as f:
            f.write(browser.page_source)

    return result


def get_last_monday_timestamp(timestamp):
    # For logs, want a full week of data ending on Mondays
    last_monday = get_previous_monday(timestamp)
    return float(last_monday.strftime("%s"))


def get_previous_monday(my_datetime):
    # Get last Monday by subtracting off the days of this week, at 8 am GMT
    last_monday = my_datetime + datetime.timedelta(days=-my_datetime.weekday())
    last_monday = last_monday.replace(hour=8, minute=0, second=0)   # start at 8am
    return last_monday


def get_startdate_from_downloads():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    all_files = os.listdir(DOWNLOAD_DIR)
    if len(all_files) == 0:
        return 0
    in_order = sorted(all_files)
    most_recent_file = in_order[-1]
    most_recent_date = datetime.datetime.strptime(most_recent_file, '%Y-%m-%d_food.csv')
    # Rewrite the last file because it could be incomplete, set to 8 am because midnight
    # could be confusing as to whether it belongs to current or previous day
    most_recent_date = most_recent_date.replace(hour=8, minute=0, second=0)
    return float(most_recent_date.strftime("%s"))


def get_start_date(br):
    br.open(SETTINGS_URL)
    text = br.response().read()
    print(text)


def prompt_start_date():
    one_year_ago = datetime.datetime.now() - datetime.timedelta(days=365)
    pretty_one_year_ago = pretty_date(float(one_year_ago.strftime("%s")))
    start_str = input(
        "Start date, in format YYYY-MM-DD, defaults to %s: " % pretty_one_year_ago) or pretty_one_year_ago
    # if start date is prior to when LoseIt began, use LoseIt creation date Jan 2008
    print("start date is: %s" % start_str)
    try:
        start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d')
        if start_date < LOSE_IT_CREATION_DATE:
            print("Your date is before LoseIt started collecting data in 2008, so using start date of January 2008")
            start_date = LOSE_IT_CREATION_DATE
    except:
        print("Bad format for start date: '%s'; using default of a year ago" % start_str)
        start_date = one_year_ago
    return float(start_date.strftime("%s"))


main()
