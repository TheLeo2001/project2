from flask import Flask, make_response, jsonify, request
from pymongo import MongoClient
#from bson import objectid
import jwt
import datetime
from functools import wraps
import bcrypt

app = Flask(__name__)

app.config['SECRET_KEY'] = 'mysecret'


# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['footballDB']
leaguesCollection = db['leagues']
users = db['users']
blacklist = db['blacklist']

@app.route('/api/v1.0/leaguesCollection/<int:_id>/reviews/<int:reviewID>', methods=['PUT'])
#@jwt_required
def edit_review(_id, reviewID):
    edited_review = {
        "reviews.$.username" : request.form["username"],
        "reviews.$.comment" : request.form["comment"],
        "reviews.$.stars" : request.form["stars"],
    }
    leaguesCollection.update_one(
        { "reviews.id" : reviewID },
        { "$set" : edited_review}
    )
    edit_review_url = "http://localhost:5000/leaguesCollection/" + id + "/reviews/" + reviewID
    return make_response( jsonify( { "url" : edit_review_url } ), 200)