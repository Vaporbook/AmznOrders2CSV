import time
import json
import re
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# The purpose of this script is to sum up the taxes paid for a set of Amazon orders 

# This script uses selenium to browse to amazon, authenticate,
# then retrieve the list of orders specified in the order_ids.txt file. After retrieving
# order details for each from the pages, it generates a ledger.json file which contains
# each order id along with the details of the order including sales tax to be collected.

# So far it recognizes two types of page: regular and fresh. At the end it outputs the
# total tax summed from all order details.

# Authenticating: create the file `.creds` in the root with email and password on separate lines.
# If you don't want to use that method, make sure the file exists, and the script will prompt you
# You will be prompted for the OTP after login as well, so have your 2fa ready.

DETAIL_URL_PREFIX='https://www.amazon.com/gp/your-account/order-details/ref=ppx_yo_dt_b_order_details_o02?ie=UTF8&orderID='
ORDER_IDS_FILENAME = 'order_ids.txt'
CREDS_FILENAME = '.creds'
LEDGER_FILENAME = 'ledger.json'
HEADLESS_MODE = True
LOGIN_URL = 'https://www.amazon.com/gp/css/homepage.html/ref=nav_bb_ya'
ELID_FOR_SIGNIN_BUTTON = 'nav-link-accountList'
ELID_FOR_EMAIL_FIELD = 'ap_email'
ELID_FOR_PASSWORD_FIELD = 'ap_password'
ELID_FOR_OTP_BUTTON = 'auth-send-code'
ELID_FOR_OTP_FIELD = 'auth-mfa-otpcode'
ELID_FOR_ORDER_DETAILS = 'od-subtotals'
ELID_FOR_FRESH_ORDER_DETAILS = 'order-summary'

request_list = {}
ledger = []
browser = None
running_tax_total = 0
raw_text = ''

def open_browser():
    global browser
    options = Options()
    if HEADLESS_MODE:
        options.add_argument("-headless")
    browser = webdriver.Firefox(options=options)

def load_ids():
    urlfile = open(ORDER_IDS_FILENAME, 'r')
    id_list = urlfile.readlines()
    urlfile.close()
    for str_id in id_list:
        raw_id = str_id.strip()
        url = f'{DETAIL_URL_PREFIX}{raw_id}'
        request_list[raw_id] = urlparse(url)

def login():

    creds_file = open(CREDS_FILENAME, 'r')
    email, password = creds_file.readlines()

    if not email or not password:
        email = input('Enter Email:')
        password = input('Enter Password:')

    login1 = LOGIN_URL
    browser.get(login1)
    sign_in = browser.find_element(By.ID, ELID_FOR_SIGNIN_BUTTON)

    sign_in.click()

    email_input = browser.find_element(By.ID, ELID_FOR_EMAIL_FIELD)
    email_input.send_keys(email)
    email_input.send_keys(Keys.ENTER)

    time.sleep(1)

    pw_input = browser.find_element(By.ID, ELID_FOR_PASSWORD_FIELD)
    pw_input.send_keys(password)
    pw_input.send_keys(Keys.ENTER)

    time.sleep(1)

    try:
        send_otp_button = browser.find_element(By.ID, ELID_FOR_OTP_BUTTON)
        print('Found extra step - clicking...')
        send_otp_button.click()
    except:
        print('Error or no click needed')

    otp = input('Enter OTP:')

    otp_input = browser.find_element(By.ID, ELID_FOR_OTP_FIELD)
    otp_input.send_keys(otp)
    otp_input.send_keys(Keys.ENTER)

def fetch(raw_id, url):
    print(url.geturl())
    browser.get(url.geturl())
    
    time.sleep(1)
    
    order_detail_subtotals = None
    snippet = ''

    try:
        # two page types known so far - the usual order, and a fresh order
        order_detail_subtotals = browser.find_elements(By.ID, ELID_FOR_ORDER_DETAILS) #order-summary
        order_detail_subtotals_fresh = browser.find_elements(By.ID, ELID_FOR_FRESH_ORDER_DETAILS)

        if len(order_detail_subtotals) > 0:
            snippet = order_detail_subtotals[0].text
        elif len(order_detail_subtotals_fresh) > 0:
            snippet = order_detail_subtotals_fresh[0].text
    except:
        # new edge case
        print('Err: No anchor elements were found')
        print(f'This is likely a new edge case to handle. The order id on this one is {raw_id}')
    return snippet

def get_all():
    login()
    time.sleep(1)
    for raw_id in request_list:
        print(f'fetching details for order #{raw_id}')
        url = request_list[raw_id]
        details = fetch(raw_id, url)
        ledger.append((raw_id, details))
        time.sleep(1)

def test_urls():
    for url in request_list:
        print(url.geturl())

def persist_ledger():
    ledger_file = open(LEDGER_FILENAME, 'w')
    json.dump(ledger, ledger_file)
    ledger_file.close()

def parse_raw_text(id, raw):
    # things get ugly here, as you'd expect
    global running_tax_total
    working_str = re.sub('Order Summary', '', raw, flags=re.IGNORECASE)

    # remove newlines appearing after :
    working_str = re.sub(':\n', ': ', working_str).strip()

    working_parts = []
    working_parts.append(id)
    col_values = working_str.split('\n')
    for keyval in col_values:
        if keyval.find(':') > -1:
            label, value =  keyval.split(':')
            if label == 'Estimated tax to be collected' or label == 'Est. Tax':
                tax = float(value.strip().strip('$'))
                running_tax_total += tax
    working_parts.append(col_values)
    return working_parts

def format_ledger():
    ledger_file = open(LEDGER_FILENAME, 'r')
    ledger = json.load(ledger_file)
    for line_item in ledger:
        id = line_item[0]
        raw_text = line_item[1]
        column_values = parse_raw_text(id, raw_text)
        print(column_values)

print('loading ids...')

load_ids()

print('opening browser...')

open_browser()
get_all()
browser.close()

print('done browsing.')

persist_ledger()
format_ledger()

print('saved ledger.')
print('------------------------------------')
print(f'${running_tax_total} total tax paid')