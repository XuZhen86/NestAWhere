import os
from typing import List

from absl import app, flags, logging
from google.cloud import pubsub

from processmessage import dispatch_messages
from tokenutil import _TOKENS_JSON, init_refresh_token

_SERVICE_ACCOUNT_JSON = flags.DEFINE_string(name='service_account_json',
                                            default='secrets/service-account.json',
                                            help='path of service account privary key JSON')

_SUBSCRIPTION_NAME = flags.DEFINE_string(name='subscription_name',
                                         default=None,
                                         help='the subscription name shown on cloud console')


def main(_: List[str]) -> None:
  logging.get_absl_handler().use_absl_log_file()

  if not os.path.exists(_TOKENS_JSON.value):
    init_refresh_token()
    return

  subscriber_client = pubsub.SubscriberClient.from_service_account_json(_SERVICE_ACCOUNT_JSON.value)
  future = subscriber_client.subscribe(_SUBSCRIPTION_NAME.value, dispatch_messages)

  try:
    future.result()
  except Exception as e:
    subscriber_client.close()
    raise e


if __name__ == '__main__':
  app.run(main)
