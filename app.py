from flask import Flask, make_response, jsonify, request
from pymongo import MongoClient
#from bson import objectid
import jwt
import datetime
from functools import wraps
import bcrypt
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'mysecret'

#app.config['SECRET_KEY'] = 'iiwctehv9269vcdeqio2947tmvncfe629rvbxk2937nc'


# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['footballDB']
leaguesCollection = db['leagues']
users = db['users']
blacklist = db['blacklist']

#############################################################################################################################


def jwt_required(func):
    @wraps(func)
    def jwt_required_wrapper(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return jsonify( { 'message' : 'token is missing'} ), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except:
            return jsonify( { 'message' : 'token is invalid'} ), 401
        
        bl_token = blacklist.find_one( { "token" : token } )
        if bl_token is not None:
            return make_response( jsonify( { 'message' : 'token has been cancelled'} ), 401)
        return func(*args, **kwargs)
    
    return jwt_required_wrapper
        

def admin_required(func):
    @wraps(func)
    def admin_required_wrapper(*args, **kwargs):
        token = request.headers['x-access-token']
        data = jwt.decode( token, app.config['SECRET_KEY'], algorithms=['HS256'] )
        if data["admin"]:
            return func(*args, **kwargs)
        else:
            return make_response( jsonify( { 'message' : 'Admin access required'} ), 401)
        
    return admin_required_wrapper


############################################################################################################################################

@app.route('/api/v1.0/leaguesCollection', methods=['GET'])
def show_all_leagues():
    page_num, page_size = 1, 10
    if request.args.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))

    page_start = (page_size * (page_num - 1))

    leagues_list = list(leaguesCollection.find({}))
    data_to_return = leagues_list[page_start:page_start + page_size]

    return make_response(jsonify(data_to_return), 200)

############################################################################################################################################

@app.route('/api/v1.0/leaguesCollection/<int:_id>', methods=['GET'])
#@jwt_required
def show_one_league(_id):
    try:
        # Use find_one to retrieve the document by _id
        league = leaguesCollection.find_one({'_id': _id})

        if league is not None:
            league['_id'] = str(league['_id'])
            for review in league['reviews']:
                review['id'] = str(review['id'])
            return make_response(jsonify( [league] ), 200)
        else:
            return make_response(jsonify({'error': 'League not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'error': str(e)}), 400)
    
###########################################################################################################################################
    

###########################################################################################################################################
    
@app.route('/api/v1.0/leaguesCollection/search', methods=['GET'])
def search_leagues():
    query = request.args.get('query')
    if not query:
        return make_response(jsonify({'error': 'Query parameter is required'}), 400)                                      #########
                                                                                                                        # search attempt leagues #
    # Perform a MongoDB query to search for leagues based on the query parameter                                           #########
    # Example: leagues_list = list(leaguesCollection.find({"title": {"$regex": query, "$options": "i"}}))
    leagues_list = list(leaguesCollection.find({"title": {"$regex": query, "$options": "i"}}))

    return make_response(jsonify(leagues_list), 200)


###########################################################################################################################################
    
@app.route('/api/v1.0/leaguesCollection/searchTeams', methods=['GET'])
def search_teams_in_leagues():
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'Query parameter "query" is required'}), 400

    # Construct MongoDB aggregation pipeline to retrieve only the nested field
    pipeline = [
        {"$match": {"teams." + query: {"$exists": True}}},
        {"$project": {query: "$teams." + query}}
    ]

    # Execute aggregation pipeline
    results = list(leaguesCollection.aggregate(pipeline))

    return jsonify(results), 200


       
############################################################################################################################################
    
############################################################################################################################################

@app.route('/api/v1.0/leaguesCollection/searchTeamsByStats', methods=['GET'])
def search_teams_by_stats():
    wins = request.args.get('wins')
    if not wins:
        return jsonify({'error': 'Query parameter "wins" is required'}), 400

    # Convert wins parameter to an integer
    try:
        wins = int(wins)
    except ValueError:
        return jsonify({'error': 'Invalid value for "wins"'}), 400

    # Construct MongoDB aggregation pipeline to retrieve teams with the specified number of wins
    pipeline = [
    {"$addFields": {"teamsArray": {"$objectToArray": "$teams"}}},
    {"$match": {"teamsArray.v.W": wins}},
    {"$project": {"team": {"$objectToArray": "$teams"}, "_id": 0}},
    {"$unwind": "$team"},
    {"$match": {"team.v.W": wins}},
    {"$replaceRoot": {"newRoot": "$team"}}
]


    # Execute aggregation pipeline
    results = list(leaguesCollection.aggregate(pipeline))

    return jsonify(results), 200



    
    
############################################################################################################################################    
    
############################################################################################################################################

@app.route('/api/v1.0/leaguesCollection/<int:_id>/reviews', methods=['GET'])
def fetch_all_reviews(_id):
    try:
        league = leaguesCollection.find_one({'_id': _id})

        if league:
            return make_response(jsonify(league.get('reviews', [])), 200)
        else:
            return make_response(jsonify({'error': 'not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'error': str(e)}), 400)
    
############################################################################################################################################ 

@app.route('/api/v1.0/leaguesCollection/<int:_id>/reviews', methods=['POST'])
def add_new_review(_id):
    try:
        league = leaguesCollection.find_one({'_id': _id})

        if league:
            username = request.form.get('username')
            comment = request.form.get('comment')
            stars = request.form.get('stars')

            if username is not None and username != '' and comment is not None and comment != '' and stars is not None:
                stars = int(stars)

                if len(league.get('reviews', [])) == 0:
                    new_review_id = 1
                else:
                    new_review_id = league['reviews'][-1]['id'] + 1

                new_review = {
                    'id': new_review_id,
                    'username': username,
                    'comment': comment,
                    'stars': stars
                }

                league.setdefault('reviews', []).append(new_review)
                leaguesCollection.update_one({'_id': _id}, {'$set': {'reviews': league['reviews']}})
                return make_response(jsonify(new_review), 200)
            else:
                return make_response(jsonify({'error': 'Invalid form data'}), 400)
        else:
            return make_response(jsonify({'error': 'Not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'error': str(e)}), 400)

############################################################################################################################################

@app.route('/api/v1.0/leaguesCollection/<int:_id>/reviews/<int:reviewID>', methods=['GET'])
def fetch_one_review(_id, reviewID):
    try:
        league = leaguesCollection.find_one({'_id': _id})

        if league:
            for review in league['reviews']:
                if review['id'] == reviewID:
                    return make_response(jsonify(review), 200)

            # If the loop completes without finding a matching review
            return make_response(jsonify({'error': 'not found'}), 404)

    except Exception as e:
        return make_response(jsonify({'error': str(e)}), 400)
    
############################################################################################################################################

@app.route('/api/v1.0/leaguesCollection/<int:_id>/reviews/<int:reviewID>', methods=['PUT'])
#@jwt_required
def edit_review(_id, reviewID):
    try:
        league = leaguesCollection.find_one({'_id': _id})

        if league:
            for review in league['reviews']:
                if review['id'] == reviewID:
                    print("Received data:", request.form)  # Add this line to log the received data

                    # form data
                    new_username = request.form.get('username')
                    new_comment = request.form.get('comment')
                    new_stars = request.form.get('stars')

                    if (
                        new_username is not None and new_username != '' and
                        new_comment is not None and new_comment != '' and
                        new_stars is not None
                    ):
                        # Convert stars to an integer
                        new_stars = int(new_stars)

                        # Update review data
                        review['username'] = new_username
                        review['comment'] = new_comment
                        review['stars'] = new_stars

                        # Save changes back to MongoDB
                        leaguesCollection.update_one({'_id': _id}, {'$set': {'reviews': league['reviews']}})

                        return make_response(jsonify(review), 200)
                    else:
                        return make_response(jsonify({'error': 'Invalid form data'}), 400)

            # If the loop completes without finding a matching review
            return make_response(jsonify({'error': 'Not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'error': str(e)}), 400)


############################################################################################################################################

@app.route('/api/v1.0/leaguesCollection/<int:_id>/reviews/<int:reviewID>', methods=['DELETE'])
#@jwt_required
#@admin_required
def delete_review(_id, reviewID):
    try:
        league = leaguesCollection.find_one({'_id': _id})

        if league:
            for review in league['reviews']:
                if review['id'] == reviewID:
                    league['reviews'].remove(review)
                    leaguesCollection.update_one({'_id': _id}, {'$set': {'reviews': league['reviews']}})
                    break

            # Return a response after the loop completes
            return make_response(jsonify({}), 200)

        # If the loop completes without finding a matching review
        return make_response(jsonify({'error': 'Not found'}), 404)
    except Exception as e:
        return make_response(jsonify({'error': str(e)}), 400)

############################################################################################################################################

@app.route('/api/v1.0/leaguesCollection/goodreviews', methods=['GET'])
def good_reviews():
    try:
        # Aggregation pipeline to match highly-rated reviews
        pipeline = [
            {
                '$unwind': '$reviews'  # Unwind the reviews array
            },
            {
                '$match': {
                    'reviews.stars': 5  # Match reviews with 5 stars
                }
            },
            {
                '$project': {
                    '_id': 1,  # Exclude _id field
                    'league_title': '$title',  # Project league title
                    'review': '$reviews'  # Project the review
                }
            }
        ]

        # Execute the aggregation pipeline
        good_reviews = list(leaguesCollection.aggregate(pipeline))

        # Return the result as JSON
        return jsonify({'highly_rated_reviews': good_reviews}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

############################################################################################################################################

@app.route('/api/v1.0/login', methods =  ['GET'])
def login():
    auth = request.authorization
    if auth:
        user = users.find_one( { "username" : auth.username} )
        if user is not None:
            if bcrypt.checkpw( bytes( auth.password, 'UTF-8' ), user['password'] ):
                token = jwt.encode( {
                        'user' : auth.username,
                        'admin' : user["admin"],
                        'exp' : datetime.datetime.utcnow() + datetime.timedelta( minutes = 30 )
                    }, app.config['SECRET_KEY'])
                return make_response( jsonify( { 'token' : token}), 200)
            else:
                return make_response( jsonify( {'message' : 'bad password'}), 401)
        else: 
            return make_response( jsonify( { 'message' : 'bad username'}), 401)
    
    return make_response( jsonify( { 'message' : 'authentication required'}), 401)

###############################################################################################################################
       
@app.route('/api/v1.0/logout', methods=['GET'])
@jwt_required
def logout():
    token = request.headers['x-access-token']
    blacklist.insert_one( { "token" : token} )
    return make_response( jsonify( { 'message' : 'Logout successful'}), 200)
        



    

if __name__ == '__main__':
    app.run(debug=True)
