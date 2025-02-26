from flask import Flask
from plusplus.models import db
from plusplus.operations.slack_handler import process_incoming_message
from sentry_sdk.integrations.flask import FlaskIntegration
from slackeventsapi import SlackEventAdapter
import sentry_sdk


__all__ = ['create_app']


def create_app():
    app = Flask(__name__)

    app.config.from_object('plusplus.config')

    # Setup sentry
    sentry_sdk.init(
        dsn=app.config['SENTRY_URL'],
        integrations=[FlaskIntegration()]
    )

    # init slack event adaptor
    slack = SlackEventAdapter(app.config['SLACK_SIGNING_SECRET'], "/slack/events", app)

    # SQLAlchemy setup
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # blueprint setup

    from plusplus.slack_integration import slack as slack_blueprint
    from plusplus.views import views as views_blueprint
    app.register_blueprint(slack_blueprint, url_prefix='/slack')
    app.register_blueprint(views_blueprint)

    @slack.on("message")
    def handle_message(event_data):
        process_incoming_message(event_data)

    return app
