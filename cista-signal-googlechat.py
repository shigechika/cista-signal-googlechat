#!/usr/bin/env python3
#
#   Copyright ©︎2022 AIKAWA Shigechika
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import urllib.request, urllib.parse
import json
import configparser
import datetime
import os


def get_updated_at(filename):
    try:
        with open(filename) as f:
            # chop \r \n
            return f.read().strip()
    except FileNotFoundError as e:
        print(e)
        return "2022/01/31 00:00:00"
    except Exception as e:
        print(e)
        raise e


def put_updated_at(filename):
    try:
        with open(filename, mode="w", newline='\n') as f:
            # YYYY/MM/DD hh:mm
            f.write(datetime.datetime.now().strftime("%Y/%m/%d %H:%M") + '\n')
    except Exception as e:
        print(e)
        raise e


def googlechat(webhook_url, text, thread=None):
    if len(text) >= 4000:
        is_long = True
        lastlf = text[0:3997].rindex("\n\n")
        chat_text = text[0:lastlf] + "\n↕️️"
    else:
        is_long = False
        chat_text = text

    if thread is None:
        data = json.dumps({"text": chat_text})
    else:
        data = json.dumps({"text": chat_text, "thread": thread})

    req = urllib.request.Request(url=webhook_url, data=data.encode("utf-8"))
    req.add_header("Content-Type", "application/json; charset=UTF-8")
    try:
        with urllib.request.urlopen(req) as res:
            body = res.read().decode("utf-8")
            j = json.loads(body)
            thread = j["thread"]
            if is_long is True:
                googlechat(webhook_url, text[lastlf:], thread)
    except Exception as e:
        raise e


def cista_signal_googlechat():
    config = configparser.ConfigParser()
    config.read("config.ini")
    signal_api_key = config.get("cista", "signal_api_key")
    signal_base_url = config.get("cista", "signal_base_url")
    webhook_url = config.get("cista", "webhook_url")

    params = {
        "OID": "",
        "TID": "",
        "q[predicate]": "range",
        "q[start]": get_updated_at(config.get("cista", "updated_at")),
        "q[attribute]": "updated_at",
        "order": "ASC",
    }

    p = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url=signal_base_url + "/api/v2/provide/messages.json?" + p
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("x-api-key", signal_api_key)
    try:
        with urllib.request.urlopen(req) as res:
            body = res.read().decode("utf-8")
            json_dict = json.loads(body)
    except Exception as e:
        raise e

    msgs = sorted(json_dict["provide_messages"], key=lambda x: x["id"])
    for msg in msgs:
        print(
            msg["id"],
            msg["created_at"],
            msg["priority"],
            len(msg["body"]),
            msg["subject"],
        )
        if msg["tlp"] == "RED":
            continue
        subject = msg["subject"].replace("\\t", "")
        text = msg["body"].replace("\\r", "").replace("\\n", "\n").replace("\\t", "\t")
        if msg["created_at"] == msg["updated_at"]:
            chat_text = f"*{subject}*\n_公開日時：{msg['created_at']}_\n\n{text}"
        else:
            chat_text = f"*{subject}*\n_~公開日時：{msg['created_at']}~　更新日時：{msg['updated_at']}_\n\n{text}"
        googlechat(webhook_url, chat_text)

    put_updated_at(config.get("cista", "updated_at")),


if __name__ == "__main__":
    cista_signal_googlechat()
