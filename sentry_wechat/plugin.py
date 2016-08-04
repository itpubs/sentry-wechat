# -*- coding: utf-8 -*-

import logging
import json
import requests
from django import forms
from sentry.plugins.bases import NotificationPlugin

TOKEN_ENDPOINT = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
NOTIFICATION_ENDPOINT = "https://qyapi.weixin.qq.com/cgi-bin/message/send"
MESSAGE_TEMPLATE = '''
{team_name}/{project_name}\t{level}
{message}
{url}
'''

logger = logging.getLogger("sentry.plugins.wechat")


class WechatOptionsForm(forms.Form):

    agent_id = forms.IntegerField(help_text="Agent ID")
    access_key = forms.CharField(help_text="Access key")
    secret_key = forms.CharField(help_text="Secret key")
    target_users = forms.CharField(
        help_text="Target users (multiple values should separated with \"|\")", required=False)
    target_parties = forms.CharField(
        help_text="Target parties (multiple values should separated with \"|\")", required=False)
    target_tags = forms.CharField(
        help_text="Target tags (multiple values should separated with \"|\")", required=False)
    is_safe = forms.BooleanField(help_text="Safe or not", required=False)


class WechatMessage(NotificationPlugin):

    title = "wechat"
    slug = "wechat"
    conf_title = title
    conf_key = "wechat"

    project_conf_form = WechatOptionsForm

    def is_configured(self, project):
        return False

    def notify_users(self, group, event, fail_silently=False):
        project = event.project
        team = project.team

        agent_id = self.get_option("agent_id", project)
        access_key = self.get_option("access_key", project)
        secret_key = self.get_option("secret_key", project)
        target_users = self.get_option("target_users", project)
        target_parties = self.get_option("target_parties", project)
        target_tags = self.get_option("target_tags", project)
        is_safe = self.get_option("is_safe", project)

        message = {
            "msgtype": "text",
            "touser": target_users,
            "toparty": target_parties,
            "totag": target_tags,
            "agentid": agent_id,
            "text": {
                "content": MESSAGE_TEMPLATE.format(**{
                    "team_name": team.name,
                    "project_name": project.name,
                    "level": event.get_tag('level').capitalize(),
                    "message": event.get_legacy_message(),
                    "url": group.get_absolute_url(),
                }),
            },
            "safe": "1" if is_safe else "0"
        }
        return self._push_notification(access_key, secret_key, message)

    def _get_token(self, access_key, secret_key):
        resp = requests.get(TOKEN_ENDPOINT, params={
                            "corpid": access_key, "corpsecret": secret_key})
        token = None
        try:
            token = resp.json().get("access_token")
        except:
            pass
        return token

    def _push_notification(self, access_key, secret_key, message):
        info = "Failed"
        access_token = self._get_token(access_key, secret_key)
        if access_token is None:
            info = "No valid token"
        else:
            resp = requests.post(NOTIFICATION_ENDPOINT, params={
                                 "access_token": access_token}, data=json.dumps(message))
            try:
                erro_code = resp.json().get("error", None)
                if erro_code is not None:
                    info = "Successful" if erro_code == 0 else resp.text
            except:
                pass

        return info
