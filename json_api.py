#!/usr/bin/env python2
# -*- encoding: utf-8 -*-

""" Bukkit JSONAPI v2 for Python

Python implementation utilizing the second version of the API.
Needs 'requests' library installed (pip install requests)

Usage:

>>> import API2
>>> conn = API2.Connection(<parameters>)
>>> api = API2.JSONAPI(conn)
Then you can use the calls like described in <http://mcjsonapi.com/apidocs/>
like this:

Let's say you want to ban player "abc" for a reason "griefing"
API function name is players.name.ban with 2 parameters.
In this API, you will then call:
>>> api.players.name.ban("abc", "griefing") # api is the JSONAPI object

Do not try to dir() on the JSONAPI object as it does not store any info
about the methods. The API's method name is derived dynamically from
what you've written after `api.`

Feel free to post any suggestions or improvements.

@author: Milan Falešník <milan@falesnik.net>
"""

import hashlib
import json
import urllib
import requests
import re


class JSONAPIException(Exception):
    pass


class PageNotFoundException(JSONAPIException):
    pass


class InvalidJSONException(JSONAPIException):
    pass


class ServerOfflineException(JSONAPIException):
    pass


class APIErrorException(JSONAPIException):
    pass


class InvocationTargetException(JSONAPIException):
    pass


class OtherCaughtException(JSONAPIException):
    pass


class MethodNotExistException(JSONAPIException):
    pass


class WrongAPIKeyException(JSONAPIException):
    pass


class NotAllowedAPIKeyException(JSONAPIException):
    pass


class MissingUsernameException(JSONAPIException):
    pass


exception_mapping = {
    1: PageNotFoundException,
    2: InvalidJSONException,
    3: ServerOfflineException,
    4: APIErrorException,
    5: InvocationTargetException,
    6: OtherCaughtException,
    7: MethodNotExistException,
    8: WrongAPIKeyException,
    9: NotAllowedAPIKeyException,
    10: MissingUsernameException,
}


class API:
    def __init__(self, host, port, username, password):
        if not (host and port and username and password):
            raise ValueError("Your arguments are wrong!")
        self.connection = {
            "host": host,
            "port": int(port),
            "username": username,
            "password": password,
        }
        self.command_stack = []
        self.url = "http://{host}:{port}/api/2/call?json={json}"

    def add(self, method_name, *args):
        """ Add a command to the command stack
            method_name => the JSONAPI supported method name
            args => any additional ORDERED arguments required by the API
        """
        self.command_stack.append(
            dict(
                name=method_name,
                username=self.connection["username"],
                key=self.generate_key(method_name),
                arguments=args,
            )
        )

    def send_all(self, is_verbose=False):
        """ Send all commands added to the command stack and make a request
            is_verbose => true if we want more information about the response
        """
        self.make_request(json.dumps(self.command_stack), is_verbose)
        del self.command_stack[:]

    def make_request(self, payload, is_verbose):
        """ Request the server API to process our command and handle the response
            payload => the json formatted data
            is_verbose => true if we want more information about the response
        """

        raw_response = requests.get(
            self.url.format(
                host=self.connection["host"],
                port=self.connection["port"],
                json=urllib.parse.quote(payload),
            )
        ).json()

        if not is_verbose:
            return [Response(item) for item in raw_response]
        else:
            return [Response(item).response for item in raw_response]

    def generate_key(self, method_name):
        """ Generates a SHA-256 hash as required by JSON API for the request
            method_name => a string with the name of the JSON API supported method
        """
        sha = hashlib.sha256()
        sha.update(bytes(self.connection["username"], "utf-8"))
        sha.update(bytes(method_name, "utf-8"))
        sha.update(bytes(self.connection["password"], "utf-8"))
        return sha.hexdigest()


class Response(object):
    """ Ported from API2
    """

    arg_regexp = re.compile(
        r"Incorrect number of args: gave ([0-9]+) \([^)]*\), expected ([0-9]+)"
    )

    def __init__(self, data):
        self.is_success = data["is_success"]
        self.source = data["source"]
        self.tag = data.get("tag", None)
        self.result = data[data["result"]]
        self.return_code = 0 if self.is_success else self.result["code"]
        self.raise_exception_if_failed()

    def raise_exception_if_failed(self):
        if self.return_code > 0:
            if self.return_code == 6:
                match = self.arg_regexp.search(self.result["message"])
                if match:
                    given, expected = [int(x) for x in match.groups()]
                    # Mimic the pythonic one.
                    raise TypeError(
                        "%s() takes exactly %d arguments (%d given)"
                        % (self.source, expected, given)
                    )
                else:
                    raise exception_mapping[self.return_code]
                (self.result["message"])
            else:
                raise exception_mapping[self.return_code]
            (self.result["message"])

    def __nonzero__(self):
        return self.is_success is True
