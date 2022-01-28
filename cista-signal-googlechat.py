#!/usr/bin/env python3
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
        return "2021/01/31 00:00:00"
    except Exception as e:
        print(e)
        raise e


def put_updated_at(filename):
    try:
        with open(filename, mode="w") as f:
            # YYYY-MM-DD hh:mm:ss
            f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        print(e)
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
        print(msg["id"], msg["tlp"], msg["created_at"], msg["priority"], msg["subject"])
        if msg["tlp"] == "RED":
            continue
        text = msg["body"].replace("\\r\\n", "\n")
        if msg["created_at"] == msg["updated_at"]:
            chat_text = f"*{msg['subject']}*\n_公開日時：{msg['created_at']}_\n\n{text}"
        else:
            chat_text = f"*{msg['subject']}*\n_~公開日時：{msg['created_at']}~　更新日時：{msg['updated_at']}_\n\n{text}"

        req = urllib.request.Request(
            url=webhook_url, data=json.dumps({"text": chat_text}).encode("utf-8")
        )
        req.add_header("Content-Type", "application/json; charset=UTF-8")
        try:
            with urllib.request.urlopen(req) as res:
                body = res.read().decode("utf-8")
        except Exception as e:
            raise e

    put_updated_at(config.get("cista", "updated_at")),


if __name__ == "__main__":
    cista_signal_googlechat()
