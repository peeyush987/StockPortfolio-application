from flask_migrate import Migrate
from flask_moment import Moment
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate(compare_type=True)
moment = Moment()
sess = Session()
