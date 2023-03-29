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
import logging
import argparse
import re


class cista_signal:
    def __init__(self):
        args = self.parse_arguments()
        # parse log level
        numeric_level = getattr(logging, args.log.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError("Invalid log level: %s" % loglevel)
        logging.basicConfig(
            level=numeric_level,
            format="%(name)s:%(lineno)s %(funcName)s [%(levelname)s]: %(message)s",
        )
        self.logger = logging.getLogger("cista-signal-googlechat")
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")
        self.signal_api_key = self.config.get("cista", "signal_api_key")
        self.signal_base_url = self.config.get("cista", "signal_base_url")
        self.webhook_url = self.config.get("cista", "webhook_url")
        self.organization_id = self.config.get("cista", "organization_id", fallback="")
        self.filename = self.config.get("cista", "updated_at")
        self.updated_at = self.get_updated_at()
        self.signal_api_method = self.config.get(
            "cista", "signal_api_method", fallback="threads"
        )

    def set_parser_args(self, parser):
        LOG_LEVEL = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        USER_CHOICE = LOG_LEVEL + list(map(lambda w: w.lower(), LOG_LEVEL))
        parser.add_argument(
            "--log", help="set log level", choices=USER_CHOICE, default="WARNING"
        )

    def parse_arguments(self):
        parser = argparse.ArgumentParser()
        self.set_parser_args(parser)
        return parser.parse_args()

    def get_updated_at(self):
        try:
            with open(self.filename) as f:
                # chop \r \n
                dt = f.read().strip()
                self.logger.debug(dt)
                return dt
        except FileNotFoundError as e:
            self.logger.error(e)
            return "2022/01/31 00:00:00"
        except Exception as e:
            self.logger.error(e)
            raise e

    def put_updated_at(self):
        try:
            with open(self.filename, mode="w", newline="\n") as f:
                # YYYY/MM/DD hh:mm
                dt = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
                self.logger.debug(dt)
                f.write(dt + "\n")
        except Exception as e:
            self.logger.error(f)
            raise e

    def googlechat(self, text, thread=None):
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

        req = urllib.request.Request(
            url=self.webhook_url, data=data.encode("utf-8"), method="POST"
        )
        req.add_header("Content-Type", "application/json; charset=UTF-8")
        try:
            with urllib.request.urlopen(req) as res:
                body = res.read().decode("utf-8")
                j = json.loads(body)
                thread = j["thread"]
                if is_long is True:
                    self.googlechat(text[lastlf:], thread)
        except Exception as e:
            self.logger.critical(res)
            raise e

    def threads_googlechat(self):
        params = {
            "OID": self.organization_id,
            "provide_category": "all",
            "status": "all",
            "q[predicate]": "range",
            "q[start]": self.updated_at,
            "q[attribute]": "updated_at",
            "order": "ASC",
        }
        self.logger.debug(params)

        p = urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url=self.signal_base_url + "/api/v2/provide/threads.json?" + p, method="GET"
        )
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("x-api-key", self.signal_api_key)
        try:
            with urllib.request.urlopen(req) as res:
                body = res.read().decode("utf-8")
                json_dict = json.loads(body)
                self.logger.debug(f'HIT : {json_dict["total"]}')
        except Exception as e:
            self.logger.critical(e)
            raise e

        msgs = sorted(json_dict["provide_threads"], key=lambda x: x["id"])
        for msg in msgs:
            if msg["tlp"] == "RED":
                continue
            title = msg["title"].replace("\\t", "")
            self.logger.info(
                f'{msg["id"]} {msg["created_at"]} {msg["updated_at"]} {msg["priority"]} {len(msg["body"])} {msg["title"]}'
            )
            text = (
                msg["body"].replace("\\r", "").replace("\\n", "\n").replace("\\t", "\t")
            )
            if msg["created_at"] == msg["updated_at"]:
                chat_text = f"*{title}*\n_公開日時：{msg['created_at']}_\n\n{text}"
            else:
                chat_text = f"*{title}*\n_~公開日時：{msg['created_at']}~　更新日時：{msg['updated_at']}_\n\n{text}"
            self.googlechat(chat_text)

        if json_dict["total"] > 0:
            self.put_updated_at()
        else:
            self.logger.debug("No Hit, No Update.")

    def messages_googlechat(self):
        params = {
            "OID": self.organization_id,
            "TID": "",
            "q[predicate]": "range",
            "q[start]": self.updated_at,
            "q[attribute]": "updated_at",
            "order": "ASC",
        }

        self.logger.debug(params)
        p = urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url=self.signal_base_url + "/api/v2/provide/messages.json?" + p,
            method="GET",
        )
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("x-api-key", self.signal_api_key)
        try:
            with urllib.request.urlopen(req) as res:
                body = res.read().decode("utf-8")
                json_dict = json.loads(body)
                self.logger.debug(f'HIT : {json_dict["total"]}')
        except Exception as e:
            self.logger.critical(e)
            raise e

        msgs = sorted(json_dict["provide_messages"], key=lambda x: x["id"])
        for msg in msgs:
            if msg["tlp"] == "RED":
                continue
            subject = msg["subject"].replace("\\t", "").strip()
            self.logger.info(
                f'{msg["id"]} {msg["created_at"]} {msg["updated_at"]} {msg["priority"]} {len(msg["body"])} {msg["subject"]}'
            )
            text = (
                msg["body"].replace("\\r", "").replace("\\n", "\n").replace("\\t", "\t")
            )
            text = re.sub(r"-----BEGIN PGP SIGNATURE-----([\r\n\S]*)-----END PGP SIGNATURE-----", "-----PGP署名省略-----", text, re.MULTILINE)

            if msg["created_at"] == msg["updated_at"]:
                chat_text = f"*{subject}*\n_公開日時：{msg['created_at']}_\n\n{text}"
            else:
                chat_text = f"*{subject}*\n_~公開日時：{msg['created_at']}~　更新日時：{msg['updated_at']}_\n\n{text}"
            self.googlechat(chat_text)

        if json_dict["total"] > 0:
            self.put_updated_at()
        else:
            self.logger.debug("No Hit, No Update.")

    def run(self):
        if self.signal_api_method == "messages":
            self.messages_googlechat()
        else:
            self.threads_googlechat()


if __name__ == "__main__":
    cs = cista_signal()
    cs.run()
