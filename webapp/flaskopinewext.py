import traceback
from flask import Flask, request
from flask.ext.login import current_user


def build_curl():
    return "curl -I {headers}{data}{method}{url}".format(
            method=" -X %s " % request.method,
            headers="-H " + " -H ".join(["'%s: %s'" % (h[0], h[1]) for h in request.headers]) + " ",
            data=("--data '%s'" % request.data) if not request.method == "GET" else '',
            url=request.base_url)


def error_string(ex=None):
    return """
ERROR: {ex}

CURL:
-----
{curl}

REQUEST:
--------
{method} {path}
base_url: {base_url}

HEADERS:
--------
{headers}

BODY:
-----
{body}

TRACEBACK:
----------
{traceback}

From IP   : {ip}
Args      : {args}
Form      : {form}
User      : {current_user}
""".format(
        ex=ex,
        base_url=request.base_url,
        method=request.method,
        path=request.path,
        body=request.data,
        args=request.args,
        form=request.form,
        headers=request.headers,
        current_user=current_user,
        ip=request.remote_addr,
        curl=build_curl(),
        traceback=traceback.format_exc()
    )


class FlaskOpinewExt(Flask):
    def log_exception(self, exc_info):
        """...description omitted..."""
        self.logger.error(error_string(), exc_info=exc_info)
