"""
Copyright 2018-present, Airbnb Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from collections import OrderedDict
import base64
import json

from stream_alert.alert_processor import LOGGER
from stream_alert.alert_processor.outputs.output_base import (
    OutputDispatcher,
    OutputProperty,
    OutputRequestFailure,
    StreamAlertOutput
)


@StreamAlertOutput
class GithubOutput(OutputDispatcher):
    """GithubOutput handles all alert dispatching for Github"""
    __service__ = 'github'

    @classmethod
    def get_user_defined_properties(cls):
        """Get properties that must be assigned by the user when configuring a new Github output."""
        return OrderedDict([
            ('descriptor',
             OutputProperty(description='a short and unique descriptor for this'
                                        ' Github integration')),
            ('repository',
             OutputProperty(description='the repository for this integration '
                                        'in the form :username/:repository',
                            cred_requirement=True,
                            mask_input=False)),
            ('labels',
             OutputProperty(description='a comma separated list of labels to '
                                        'apply to issues when they are created',
                            cred_requirement=True,
                            mask_input=False)),
            ('username',
             OutputProperty(description='the username for this integration',
                            cred_requirement=True,
                            mask_input=False)),
            ('access_token',
             OutputProperty(description='the access token for the integration',
                            cred_requirement=True,
                            mask_input=True))
        ])

    @classmethod
    def _get_default_properties(cls):
        """Get the standard url used for Github API. This value the same for
        everyone, so is hard-coded here and does not need to be configured by
        the user

        Returns:
            dict: Contains various default items for this output (ie: url)
        """
        return {'api': 'https://api.github.com'}

    def _dispatch(self, alert, descriptor):
        """Send alert to Github

        Args:
            alert (Alert): Alert instance which triggered a rule
            descriptor (str): Output descriptor

        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        credentials = self._load_creds(descriptor)
        if not credentials:
            return False

        username_password = "{}:{}".format(credentials['username'],
                                           credentials['access_token'])
        encoded_credentials = base64.b64encode(username_password)
        headers = {'Authorization': "Basic {}".format(encoded_credentials)}
        url = '{}/repos/{}/issues'.format(credentials['api'],
                                          credentials['repository'])

        title = "StreamAlert: {}".format(alert.rule_name)
        body_template = "### Description\n{}\n\n### Event data\n\n```\n{}\n```"
        body = body_template.format(
            alert.rule_description, json.dumps(alert.record, indent=2, sort_keys=True))
        issue = {'title': title, 'body': body, 'labels': credentials['labels'].split(',')}

        LOGGER.debug('sending alert to Github repository %s', credentials['repository'])

        try:
            self._post_request_retry(url, issue, headers)
        except OutputRequestFailure:
            return False

        return True
