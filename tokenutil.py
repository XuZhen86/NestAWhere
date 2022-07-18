import json
from urllib.parse import parse_qs, urlparse

import requests
from absl import flags, logging

# https://developers.google.com/nest/device-access/authorize
_OAUTH2_JSON = flags.DEFINE_string(name='oauth2_json',
                                   default='secrets/oauth2.json',
                                   help='path of OAuth 2.0 web application client JSON')

_TOKENS_JSON = flags.DEFINE_string(name='tokens_json',
                                   default='secrets/tokens.json',
                                   help='path of saved tokens')

_DEVICE_ACCESS_PROJECT_ID = flags.DEFINE_string(
    name='device_access_project_id',
    default=None,
    help='the Project ID shown on Device Access Console')


def _check_response_status_code(response: requests.Response) -> None:
  if response.status_code != 200:
    raise ValueError(f'status_code is {response.status_code}, expected 200')


# https://developers.google.com/nest/device-access/authorize#link_your_account
def _prompt_authorization_code(oauth2_client_id: str, device_access_project_id: str) -> str:
  params = {
      'redirect_uri': 'https://www.google.com',
      'access_type': 'offline',
      'prompt': 'consent',
      'client_id': oauth2_client_id,
      'response_type': 'code',
      'scope': 'https://www.googleapis.com/auth/sdm.service'
  }
  request = requests.Request(
      method='GET',
      url=f'https://nestservices.google.com/partnerconnections/{device_access_project_id}/auth',
      params=params)

  print(request.prepare().url)
  redirect_url = input('redirect_url = ')

  authorization_code = parse_qs(urlparse(redirect_url).query)['code'][0]
  return authorization_code


# https://developers.google.com/nest/device-access/authorize#get_an_access_token
def _get_refresh_token(oauth2_client_id: str, oauth2_client_secret: str, authorization_code: str,
                       device_access_project_id: str) -> str:
  params = {
      'client_id': oauth2_client_id,
      'client_secret': oauth2_client_secret,
      'redirect_uri': 'https://www.google.com',
      'grant_type': 'authorization_code',
      'code': authorization_code,
  }

  response = requests.post('https://www.googleapis.com/oauth2/v4/token', params=params)
  _check_response_status_code(response)

  response_json = json.loads(response.text)
  refresh_token = response_json['refresh_token']
  access_token = response_json['access_token']

  # https://developers.google.com/nest/device-access/authorize#make_a_device_list_call
  headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {access_token}'}
  response = requests.get(
      f'https://smartdevicemanagement.googleapis.com/v1/enterprises/{device_access_project_id}/devices',
      headers=headers)
  _check_response_status_code(response)

  return refresh_token


def init_refresh_token() -> None:
  with open(_OAUTH2_JSON.value, 'r') as fp:
    oauth2_json = json.load(fp)
    oauth2_client_id: str = oauth2_json['web']['client_id']
    oauth2_client_secret: str = oauth2_json['web']['client_secret']

  authorization_code = _prompt_authorization_code(oauth2_client_id, _DEVICE_ACCESS_PROJECT_ID.value)
  print('authorization_code = ' + authorization_code)

  refresh_token = _get_refresh_token(oauth2_client_id, oauth2_client_secret, authorization_code,
                                     _DEVICE_ACCESS_PROJECT_ID.value)
  print('refresh_token = ' + refresh_token)

  with open(_TOKENS_JSON.value, 'w') as fp:
    json.dump({'refresh_token': refresh_token}, fp)
  print('successful')


# https://developers.google.com/nest/device-access/authorize#how_to_use_a_refresh_token
def get_access_token() -> str:
  with open(_OAUTH2_JSON.value, 'r') as fp:
    j = json.load(fp)
    oauth2_client_id: str = j['web']['client_id']
    oauth2_client_secret: str = j['web']['client_secret']

  with open(_TOKENS_JSON.value, 'r') as fp:
    j = json.load(fp)
    refresh_token: str = j['refresh_token']

  params = {
      'client_id': oauth2_client_id,
      'client_secret': oauth2_client_secret,
      'grant_type': 'refresh_token',
      'refresh_token': refresh_token,
  }
  response = requests.post('https://www.googleapis.com/oauth2/v4/token', params=params)
  _check_response_status_code(response)

  response_json = json.loads(response.text)
  access_token: str = response_json['access_token']
  logging.debug(f'access_token = {access_token}')
  return access_token
