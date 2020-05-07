from flask import Flask, make_response, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import bcrypt
import hashlib
import base64
import time

app = Flask(__name__, instance_relative_config=True)

# load configuration file
app.logger.info("Loading configuration file")
app.config.from_pyfile("config.py")
app.logger.info("Finished loading configuration file")

# setup database
db = SQLAlchemy(app)

# route to fetch a user's name from their cwid
@app.route("/user/<cwid>", methods=["GET"])
def findUser(cwid):
    try:
        # query for the user
        user = User.query.filter_by(cwid=cwid).first()
        return make_response(jsonify(cwid=user.cwid, name=user.name), 200, {"Content-Type": "application/json"})       
    except:
        return make_response(jsonify(message="No user with cwid: " + cwid), 404, {"Content-Type": "application/json"})

# verify that the given password is correct for the given cwid
@app.route("/user/login/<cwid>/<password>", methods=["GET"])
def verifyUser(cwid, password):
    try:
        # query for the user
        user = User.query.filter_by(cwid=cwid).first()

        shaHash = hashlib.sha256()
        shaHash.update(password.encode())

        if bcrypt.checkpw(base64.b64encode(shaHash.digest()), bytes.fromhex(user.password)):
            return make_response(jsonify(message="User's password is correct"), 200, {"Content-Type": "application/json"})
        else:
            return make_response(jsonify(message="User's password is incorrect"), 401, {"Content-Type": "application/json"})
    except:
        return make_response(jsonify(message="No user with cwid: " + cwid), 404, {"Content-Type": "application/json"})


# route to get a list of all the user's sessions
@app.route("/sessions/user/<cwid>", methods=["GET"])
def listSessions(cwid):
    try:
        # query for the user
        user = User.query.filter_by(cwid=cwid).first()

        if user is not None:
            # user exists
            if len(user.sessions) > 0:
                # user has sessions
                # create a list of the session information to return as json
                sessionData = []
                for session in user.sessions:
                    sessionData.append({"cwid": session.cwid, "sessionNumber": session.sessionNumber, "description": session.description})
                return make_response(jsonify(sessionData), 200, {"Content-Type": "application/json"})
            else:
                # user has not made a session
                return make_response(jsonify(message="User has no sessions"), 404, {"Content-Type": "application/json"})
        else:
            # user was not found
            return make_response(jsonify(message="No user with cwid: " + cwid), 404, {"Content-Type": "application/json"})
    except:
        return make_response(jsonify(message="Unexpected server error"), 500, {"Content-Type": "application/json"})


# route to get a list of all the sessions that have been shared with the user
@app.route("/sessions/shared/user/<cwid>", methods=["GET"])
def listSharedSessions(cwid):
    try:
        # find the user the sessions have been shared with
        user = User.query.filter_by(cwid=cwid).first()
        
        # get the information about the sessions that have been shared with the user
        if len(user.sharedSessions) > 0:
            sessions = []
            for sharedSession in user.sharedSessions:
                session = sharedSession.session
                sessions.append({"cwid": session.cwid, "sessionNumber": session.sessionNumber, "description": session.description})

            return make_response(jsonify(sessions), 200, {"Content-Type": "application/json"})
        else:
            return make_response(jsonify(message="User has not had a session shared with them"), 204, {"Content-Type": "application/json"})
    except IntegrityError as error:
        return make_response(jsonify(message="There is no user with that cwid"), 404, {"Content-Type": "application/json"})
    except:
        return make_response(jsonify(message="Unexpected server error"), 500, {"Content-Type": "application/json"})


# route to get the data from a session
@app.route("/getSession/<cwid>/<sessionNumber>", methods=["GET"])
def getSession(cwid, sessionNumber):
    try:
        # find the session that has been requested
        session = Session.query.filter_by(cwid=cwid, sessionNumber=sessionNumber).first()

        # add the session data to a list by times
        sessionData = []
        for sessionTime in session.sessionTimes:
            sessionData.append({"time": str(sessionTime.time), "values": [0] * len(sessionTime.sessionValues)})
            for sessionValue in sessionTime.sessionValues:
                sessionData[-1]["values"][sessionValue.sensorNumber] = sessionValue.sensorValue

        return make_response(jsonify(data=sessionData, length=session.length, width=session.width), 200, {"Content-Type": "application/json"})
    except IntegrityError as error:
        app.logger.error(error)
        return make_response(jsonify(message="There is no session with the given cwid and session number"), 404, {"Content-Type": "application/json"})
    except:
        return make_response(jsonify(message="Unexpected server error"), 500, {"Content-Type": "application/json"})

# route to create a user
@app.route("/create/user/<cwid>/<name>/<password>", methods=["POST"])
def createUser(cwid, name, password):
    shaHash = hashlib.sha256()
    shaHash.update(password.encode())
    hashedPassword = bcrypt.hashpw(base64.b64encode(shaHash.digest()), bcrypt.gensalt())

    # create the new user
    newUser = User(cwid=cwid, name=name, password=hashedPassword.hex())
    try:
        # add the new user to the database
        db.session.add(newUser)
        db.session.commit()
        return make_response(jsonify(message="Successfully created user"), 201, {"Content-Type": "application/json"})
    except IntegrityError as error:
        return make_response(jsonify(message="There is already a user with that cwid"), 409, {"Content-Type": "application/json"})
    except:
        return make_response(jsonify(message="Unexpected server error"), 500, {"Content-Type": "application/json"})

# route to create a session
@app.route("/create/session", methods=["POST"])
def createSession():
    data = request.get_json()
    if data is not None:
        try:
            # determine what the next session number should be
            newSessionNumber = len(Session.query.filter_by(cwid=data["cwid"]).all()) + 1

            # create the new session and add it
            newSession = Session(cwid=data["cwid"], sessionNumber=newSessionNumber, description=data["description"], length=data["length"], width=data["width"])
            db.session.add(newSession)

            # add new session times and values
            sessionTimes = []
            sessionValues = []
            # for each time create a SessionTime
            for time in data["data"]:
                sessionTimes.append(SessionTime(cwid=data["cwid"], sessionNumber=newSessionNumber, time=time["time"]))
                if len(time["values"]) == newSession.length * newSession.width:
                    # for each sensor value at that time create a SessionValue
                    for sensor in range(len(time["values"])):
                        sessionValues.append(SessionValue(cwid=data["cwid"], sessionNumber=newSessionNumber, time=time["time"], sensorNumber=sensor, sensorValue=time["values"][sensor]))
                else:
                    return make_response(jsonify(message="The number of sensors did not match the length and width"), 400, {"Content-Type": "application/json"})

            # add the session times and values to the database
            db.session.add_all(sessionTimes)
            db.session.add_all(sessionValues)

            # commit new session information
            db.session.commit()
            return make_response(jsonify(message="Successfully created session"), 201, {"Content-Type": "application/json"})
        except:
            return make_response(jsonify(message="Unexpected server error"), 500, {"Content-Type": "application/json"})
    else:
        return make_response(jsonify(message="No data received or not interpreted"), 400, {"Content-Type": "application/json"})

# route to share a session
@app.route("/create/sharedSession/<sessionCWID>/<sessionNumber>/<shareToCWID>", methods=["POST"])
def shareSession(sessionCWID, sessionNumber, shareToCWID):
    # check the session isn't being shared to the user who made it
    if sessionCWID == shareToCWID:
        return make_response(jsonify(message="Cannot share a session with yourself"), 400, {"Content-Type": "application/json"})
    else:
        # create the shared session
        sharedSession = SharedSession(sessionCWID=sessionCWID, sessionNumber=sessionNumber, shareToCWID=shareToCWID)

        # attempt to put it into the database
        try:
            db.session.add(sharedSession)
            db.session.commit()
            return make_response(jsonify(message="Successfully shared the session"), 201, {"Content-Type": "application/json"})
        except IntegrityError as error:
            return make_response(jsonify(message="Session has already been shared to that user or the session or cwid does not exist"), 409, {"Content-Type": "application/json"})
        except:
            return make_response(jsonify(message="Unexpected server error"), 500, {"Content-Type": "application/json"})

class User(db.Model):
    __tablename__ = "user"
    cwid = db.Column(db.Integer, primary_key = True, autoincrement = False)
    name = db.Column(db.String(), nullable = False)
    password = db.Column(db.String(), nullable = False)
    sessions = db.relationship("Session", back_populates="user")
    sharedSessions = db.relationship("SharedSession", back_populates="user")

class SharedSession(db.Model):
    __tablename__ = "shared_session"
    __table_args__ = (db.ForeignKeyConstraint(["sessionCWID", "sessionNumber"], ["session.cwid", "session.sessionNumber"]), db.ForeignKeyConstraint(["shareToCWID"], ["user.cwid"]))
    sessionCWID = db.Column(db.Integer, primary_key = True)
    sessionNumber = db.Column(db.Integer, primary_key = True)
    shareToCWID = db.Column(db.Integer, primary_key = True)
    user = db.relationship("User", back_populates="sharedSessions")
    session = db.relationship("Session", back_populates="sharedTo")

class SessionValue(db.Model):
    __tablename__ = "session_value"
    __table_args__ = (db.ForeignKeyConstraint(["cwid", "sessionNumber", "time"], ["session_time.cwid", "session_time.sessionNumber", "session_time.time"]),)
    cwid = db.Column(db.Integer, primary_key = True)
    sessionNumber = db.Column(db.Integer, primary_key = True)
    time = db.Column(db.DateTime, primary_key = True)
    sensorNumber = db.Column(db.Integer, primary_key = True)
    sensorValue = db.Column(db.Integer, nullable = False)
    sessionTime = db.relationship("SessionTime", back_populates="sessionValues")

class SessionTime(db.Model):
    __tablename__ = "session_time"
    __table_args__ = (db.ForeignKeyConstraint(["cwid", "sessionNumber"], ["session.cwid", "session.sessionNumber"]),)
    cwid = db.Column(db.Integer, primary_key = True)
    sessionNumber = db.Column(db.Integer, primary_key = True)
    time = db.Column(db.DateTime, primary_key = True)
    sessionValues = db.relationship("SessionValue", back_populates="sessionTime")
    session = db.relationship("Session", back_populates="sessionTimes")

class Session(db.Model):
    __tablename__ = "session"
    __table_args__ = (db.ForeignKeyConstraint(["cwid"], ["user.cwid"]),)
    cwid = db.Column(db.Integer, primary_key = True)
    sessionNumber = db.Column(db.Integer, primary_key = True)
    description = db.Column(db.String(), nullable = False)
    length = db.Column(db.Integer, nullable = False)
    width = db.Column(db.Integer, nullable = False)
    sessionTimes = db.relationship("SessionTime", back_populates="session")
    sharedTo = db.relationship("SharedSession", back_populates="session")
    user = db.relationship("User", back_populates="sessions")

if __name__ == '__main__':
    dbstatus = False
    while dbstatus == False:
        try:
            db.create_all()
        except:
            time.sleep(2)
        else:
            dbstatus = True
    db.create_all()
    app.run(debug=True, host='0.0.0.0', port='5000')