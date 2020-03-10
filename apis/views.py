import json
from datetime import datetime
import re

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse

# Create your views here.
from apis.models import UserInfo
from apis.services import login_web_bill, get_user_info, generate_token, find_user_by_name, get_auth_token, \
    find_user_by_token, send_loggedin_request

LOGIN_ERR_FAILED_LOGIN_MAINSITE = "Failed to login to main site"
LOGIN_ERR_CREDENTIAL_NOT_CORRECT = 'Username or password not correct'

ERR_NOT_AUTHORIZED = 'Session expired. Please login.'


def login(request):
    try:
        data = json.loads(request.body)
        username = data['username']
        password = data['password']
    except KeyError:
        return HttpResponseBadRequest("Missing Fields")

    # Login To WebBilling Site

    cre = login_web_bill()

    if cre is None:
        return HttpResponseBadRequest(LOGIN_ERR_FAILED_LOGIN_MAINSITE)

    ccid = cre[0]
    user_info = get_user_info(ccid, username)

    if user_info is None:
        return HttpResponseBadRequest(LOGIN_ERR_CREDENTIAL_NOT_CORRECT)

    if user_info['h323_password'] != password:
        return HttpResponseBadRequest(LOGIN_ERR_CREDENTIAL_NOT_CORRECT)

    if "blocked" in user_info.keys():
        return HttpResponseBadRequest("User blocked")

    if "expiration_date" not in user_info.keys():
        return HttpResponseBadRequest("User expired")

    expiration_date = datetime.strptime(user_info["expiration_date"], "%Y-%m-%d")

    print(expiration_date, datetime.now(), expiration_date > datetime.now())

    if expiration_date < datetime.now():
        return HttpResponseBadRequest("User expired")

    access_token = generate_token()

    user = find_user_by_name(username)

    if user is None:
        user = UserInfo.objects.create(user_name=username)

    user.ccid = ccid
    user.access_token = access_token
    user.save()

    return JsonResponse({"access_token": access_token})


def user_info(request):
    token = get_auth_token(request)

    if token is None:
        return HttpResponseBadRequest(ERR_NOT_AUTHORIZED)

    user = find_user_by_token(token)

    if user is None:
        return HttpResponseBadRequest(ERR_NOT_AUTHORIZED)

    user_info = get_user_info(user.ccid, user.user_name)

    if user_info is None:
        return HttpResponseBadRequest(ERR_NOT_AUTHORIZED)

    result = {
        'expiration_date': user_info['expiration_date'],
        'balance': user_info['custom_info']['balance'],
        'userid': user_info['tID'],
        'type': user_info['srv_cli'],
        'identity': '' if 'srv_centrex' not in user_info.keys() else user_info['srv_centrex'],
    }

    return JsonResponse(result)


OVERRIDE_DEFAULT = "def"
OVERRIDE_NO = "no"
OVERRIDE_CUSTOM = "cus"


def set_service_feature(request):
    data = json.loads(request.body)
    try:
        type = data['type']
    except KeyError:
        return HttpResponseBadRequest("Missing Fields")

    identity = ""

    if OVERRIDE_CUSTOM == type:
        try:
            identity = data['identity']
        except KeyError:
            return HttpResponseBadRequest("Missing Fields")

    token = get_auth_token(request)

    if token is None:
        return HttpResponseBadRequest(ERR_NOT_AUTHORIZED)

    user = find_user_by_token(token)

    if user is None:
        return HttpResponseBadRequest(ERR_NOT_AUTHORIZED)

    user_info = get_user_info(user.ccid, user.user_name)

    if user_info is None:
        return HttpResponseBadRequest(ERR_NOT_AUTHORIZED)

    if OVERRIDE_DEFAULT == type:
        user_info["srv_cli"] = "^"
        user_info.pop("srv_centrex")
    else:
        user_info["srv_cli"] = "Y"
        if OVERRIDE_NO == type:
            user_info["srv_centrex"] = "+"
        else:
            user_info["srv_centrex"] = identity

    user_info.pop("custom_info")

    user_info["Action"] = "Update"
    user_info["sip_status"] = "ANY"
    user_info["TAB"] = "PortaBilling_TabName_Call_Features"

    send_loggedin_request(user.ccid, "/account.html", user_info)

    return HttpResponse("Success")


def logout(request):
    token = get_auth_token(request)

    if token is None:
        return HttpResponse()

    user = find_user_by_token(token)

    if user is None:
        return HttpResponse()

    user.access_token = ""
    user.save()

    return HttpResponse()
