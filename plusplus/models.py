from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import aggregated
from slack_sdk import WebClient
import datetime

db = SQLAlchemy()


class SlackTeam(db.Model):
    __tablename__ = 'SlackTeam'
    id = db.Column(db.String, primary_key=True)
    bot_user_id = db.Column(db.String)
    bot_access_token = db.Column(db.String)
    things = db.relationship("Thing", backref="team")
    last_request = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    banned = db.Column(db.Boolean, default=False)
    team_name = db.Column(db.String)
    team_domain = db.Column(db.String)
    team_email_domain = db.Column(db.String)
    midterm_pool_points = db.Column(db.Integer, default=0)

    def __init__(self, request_json):
        self.update(request_json)

    def update(self, request_json):
        self.id = request_json['team']['id']
        self.bot_user_id = request_json['bot_user_id']
        self.bot_access_token = request_json['access_token']
        self.get_team_metadata()

    @property
    def slack_client(self):
        return WebClient(self.bot_access_token)

    def update_last_access(self):
        self.last_request = datetime.datetime.utcnow()

    def get_team_metadata(self):
        sc = self.slack_client
        response = sc.team_info()
        self.team_name = response['team']['name']
        self.team_domain = f"https://{response['team']['domain']}.slack.com"
        self.team_email_domain = response['team']['email_domain']
    
    def add_to_midterm_pool(self, pts):
        if self.midterm_pool_points is None:
            self.midterm_pool_points = pts
        else:
            self.midterm_pool_points += pts

class Thing(db.Model):
    __tablename__ = 'Thing'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item = db.Column(db.String)
    ta_id = db.Column(db.String)

    @aggregated('points', db.Column(db.Integer))
    def total_points(self):
        return db.func.sum(Point.value)
    #def total_all_time_points(self):
    #    return db.func.sum(Point.query.filter(Point.value > 0))
    points = db.relationship("Point", primaryjoin="and_(Thing.id==Point.awardee_id)")
    user = db.Column(db.Boolean)
    team_id = db.Column(db.String, db.ForeignKey('SlackTeam.id'))
    show_in_global_leaderboard = db.Column(db.Boolean, default=True)
    last_modified = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def increment(self, num_pts, reason):
        point = Point(num_pts, None, reason)
        point.awardee_id = self.id
        point.time_added = datetime.datetime.utcnow()
        return point

    def decrement(self, num_pts, reason):
        point = Point(-num_pts, None, reason)
        point.awardee_id = self.id
        point.time_added = datetime.datetime.utcnow()
        return point


class Point(db.Model):
    __tablename__ = 'Point'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    awardee_id = db.Column(db.Integer, db.ForeignKey('Thing.id'))
    value = db.Column(db.Integer, default=0)
    reason = db.Column(db.String, default="None Provided")
    #awarder_id = db.Column(db.Integer, db.ForeignKey('Thing.id'))
    time_added = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, value, awardee_id, reason):
        self.value = value
        #self.awarder_id = awarder_id
        self.awardee_id = awardee_id
        self.reason = reason
