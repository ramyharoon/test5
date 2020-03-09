import random
import re
import string

import requests
from bs4 import BeautifulSoup

from apis.models import UserInfo
from back_end.settings import WEB_BILL_URL, WEB_BILL_USER_NAME, WEB_BILL_PASSWORD


def get_auth_token(request):
    try:
        token = request.headers['Authorization']
    except KeyError:
        return None

    if "" == token:
        return None

    return token


def generate_token():
    group = string.ascii_lowercase + string.digits
    return ''.join(random.choice(group) for i in range(32))


def find_user_by_name(name):
    users = UserInfo.objects.filter(user_name=name)

    if 1 != len(users):
        return None

    return users[0]


def find_user_by_token(token):
    users = UserInfo.objects.filter(access_token=token)

    if 1 != len(users):
        return None

    return users[0]


def send_loggedin_request(ccid, url, data):
    headers = {"Cookie": "CCID=" + ccid}
    print("Data", data)
    return requests.post(WEB_BILL_URL + url, headers=headers, data=data, verify=False)


def get_token_secure_key(text):
    search = re.search("var token_secure_key = \"(.*)\";", text)

    if search is None:
        return None

    token_secure_key = search.group(1)

    if "" == token_secure_key:
        return None

    return token_secure_key


def get_user_info(ccid, username):
    response = send_loggedin_request(ccid, "/account.html", {})
    token = get_token_secure_key(response.text)

    if token is None:
        return None

    response = send_loggedin_request(ccid, "/account.html", {
        "token_secure_key": token,
        "tID": username,
        "Action": "Show numbers",
    })

    if -1 == response.text.find("h323_password"):
        print(username, " User not exist")
        return None

    search_text = response.text.replace("\n", "")

    search = re.search("(<form id=\"main_form\" name=\"main\".*>.*</form>)", search_text)

    if search is None:
        return None

    soup = BeautifulSoup(search.group(1), features="html.parser")

    arr = []
    arr += soup.find_all("input", {"type": "text"})
    arr += soup.find_all("input", {"type": "hidden"})

    result = {}

    for item in arr:
        if not item.has_attr("name") or item.has_attr("disabled"):
            continue

        try:
            value = item['value']
        except KeyError:
            value = ""

        name = item['name']
        if name not in result.keys() or "" != value:
            result[name] = value

    arr = soup.find_all('input', {"type": "checkbox"})

    for item in arr:
        if item.has_attr("id") or \
                not item.has_attr("name") or \
                not item.has_attr("value") or \
                not item.has_attr("checked"):
            continue
        result[item["name"]] = item["value"]

    selects = soup.find_all("select")

    for item in selects:
        if not item.has_attr('name') or item.has_attr("disabled"):
            continue

        name = item['name']
        value = ''
        options = item.findChildren("option", recursive=False)

        for option in options:
            if not option.has_attr('selected'):
                continue
            value = option['value']
            break

        result[name] = value

    textareas = soup.find_all("textarea")

    for item in textareas:
        if not item.has_attr("name"):
            continue

        result[item['name']] = "" if item.string is None else item.string

    radios = soup.find_all("input", {"type": "radio"})

    for item in radios:
        if not item.has_attr("name") or not item.has_attr("selected") or not item.has_attr("value"):
            continue

        result[item['name']] = item['value']

    search = re.search("UpdateTicket.value=\"([0-9]*)\";", response.text)

    if search is None or "" == search:
        return None

    result["UpdateTicket"] = search.group(1)

    result["custom_info"] = {}

    # Search For Balance

    search = re.search("var balance_value = ([0-9.]+);", response.text)

    if search is None:
        return None

    result["custom_info"]['balance'] = search.group(1)

    result['token_secure_key'] = token

    if "action" in result.keys():
        result.pop("action")

    return result


def login_web_bill():
    response = requests.post(WEB_BILL_URL + "/index.html", {
        "pb_auth_user": WEB_BILL_USER_NAME,
        "pb_auth_password": (WEB_BILL_PASSWORD if 1 == 1 else "rpass"),
    }, verify=False)

    try:
        cookie = response.headers['Set-Cookie']
    except KeyError:
        return None

    search = re.search("CCID=([a-z0-9]*);", cookie)

    if search is None:
        return None

    ccid = search.group(1)

    token_secure_key = get_token_secure_key(response.text)

    if token_secure_key is None:
        return None

    return [ccid, token_secure_key]
