from flask import Flask, request
from flask.ext.login import current_user


class FlaskOpinewExt(Flask):
    def log_exception(self, exc_info):
        """...description omitted..."""
        self.logger.error(
            """
        Request:   {method} {path}
        IP:        {ip}

        Agent:     {agent_platform} | {agent_browser} {agent_browser_version}
        Raw Agent: {agent}

        Args:      {args}
        Form:      {form}
        User:      {current_user}

        Headers:   {headers}

            """.format(
                method=request.method,
                path=request.path,
                args=request.args,
                form=request.form,
                headers=request.headers,
                current_user=current_user,
                ip=request.remote_addr,
                agent_platform=request.user_agent.platform,
                agent_browser=request.user_agent.browser,
                agent_browser_version=request.user_agent.version,
                agent=request.user_agent.string,
            ), exc_info=exc_info
        )
