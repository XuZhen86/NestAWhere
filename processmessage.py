import json
import os
from datetime import datetime
from typing import Any, Dict

import requests
from absl import flags
from google.cloud import pubsub_v1

from tokenutil import _check_response_status_code, get_access_token

ACK_MESSAGES = flags.DEFINE_bool(name='ack_messages',
                                 default=False,
                                 help='ack messages after processing them')


def _local_date(timestamp: str) -> str:
  return datetime.fromisoformat(timestamp[:-1] + '+00:00').astimezone().strftime('%Y%m%d')


def _local_file_name(timestamp: str, event_thread_id: str) -> str:
  local_date_time = datetime.fromisoformat(timestamp[:-1] +
                                           '+00:00').astimezone().strftime('%Y%m%d-%H%M%S')
  return f'{local_date_time}_{event_thread_id}'


def _local_path(body: Dict[str, Any]) -> str:
  timestamp: str = body['timestamp']
  event_thread_id: str = body['eventThreadId']

  local_date = _local_date(timestamp)
  local_file_name = _local_file_name(timestamp, event_thread_id)

  local_path = os.path.join(local_date, local_file_name)
  return local_path


def _write_messages_json(body: Dict[str, Any]) -> None:
  file_name = os.path.join('messages', _local_path(body) + f'.{body["eventThreadState"]}.json')

  os.makedirs(os.path.dirname(file_name), exist_ok=True)
  with open(file_name, 'w') as fp:
    json.dump(body, fp, indent=2)


def _started(body: Dict[str, Any]) -> None:
  pass


def _updated(body: Dict[str, Any]) -> None:
  pass


def _ended(body: Dict[str, Any]) -> None:
  try:
    preview_url: str = body['resourceUpdate']['events'][
        'sdm.devices.events.CameraClipPreview.ClipPreview']['previewUrl']
  except:
    return

  access_token = get_access_token()
  headers = {'Authorization': f'Bearer {access_token}'}
  response = requests.get(preview_url, headers=headers, stream=True)
  try:
    _check_response_status_code(response)
  except:
    return

  file_name = os.path.join('clips', _local_path(body) + '.mp4')
  os.makedirs(os.path.dirname(file_name), exist_ok=True)
  with open(file_name, 'wb') as fp:
    for chunk in response.iter_content():
      fp.write(chunk)


def dispatch_messages(message: 'pubsub_v1.subscriber.message.Message') -> None:
  body: Dict[str, Any] = json.loads(message.data)
  event_thread_state: str = body['eventThreadState']

  _write_messages_json(body)

  # TODO: update to use match-case when yapf supports it.
  if event_thread_state == 'STARTED':
    _started(body)
  elif event_thread_state == 'UPDATED':
    _updated(body)
  elif event_thread_state == 'ENDED':
    _ended(body)
  else:
    raise ValueError(f'unexpected event_thread_state {event_thread_state}')

  if ACK_MESSAGES.value:
    message.ack()
