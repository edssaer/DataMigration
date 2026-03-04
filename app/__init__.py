from flask import Flask
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

from app.routes.api_v2 import api
app.register_blueprint(api)
