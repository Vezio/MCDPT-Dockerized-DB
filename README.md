# MCDPT-Dockerized-DB
A dockerized services: flask server and postgresql database. The flask server 
is an interface to the postgresql server, providing the models and routes
required to query the database.

Authors: 
Tyler Rimaldi, 
Daniel Grossmann,
Dr. Donald Schwartz

## How to setup this repository
Create a `.env` file in the root of this directory and include the following:

```
POSTGRES_USER=yourusername
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=yourdbname
```

Create an instance folder in ./app/: `./app/instance
Inside of the instance folder add the following:
`__init__.py`
`config.py`

Inside the `config.py`, add the following:
```
DEBUG = boolean
SECRET_KEY = "secret"
DBNAME = "yourdbname"
DBUSER = "yourusername"
DBPASS = "yourpassword"
DBHOST = "db" # (this is based on the dockercompose service name)
DBPORT = "5432" # (this is the default postgres port)

SQLALCHEMY_DATABASE_URI = \
    'postgresql+psycopg2://{user}:{passwd}@{host}:{port}/{db}'.format(
        user=DBUSER,
        passwd=DBPASS,
        host=DBHOST,
        port=DBPORT,
        db=DBNAME)
```
## How to use this repository after setup
`docker-compose build` will build the services

`docker-compose up` will run the services

`localhost:5000` will be the the address to make calls to the database (ofcourse
these calls will be those that are defined by the flask server interface.)

## DB Routes Explained

### GET
- `localhost:5000/user/<cwid>`: cwid=integer
- `localhost:5000/user/login/<cwid>/<password>`: cwid=integer, password=alphanumeric string
- `localhost:5000/sessions/user/<cwid>`: cwid=integer
