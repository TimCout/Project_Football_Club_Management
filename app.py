from flask import Flask, jsonify, render_template
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["database"]
clubs_collection = db["clubs"]
teams_collection = db["teams"]

@app.route('/api/clubs', methods=['GET'])
def get_clubs():
    print("API endpoint '/api/clubs' was hit.")
    clubs = clubs_collection.find({}, {"_id": 1, "name": 1})
    club_list = [{"id": str(club["_id"]), "name": club["name"]} for club in clubs]
    return jsonify(club_list)

@app.route('/api/teams/<club_id>', methods=['GET'])
def get_teams(club_id):
    print(f"API endpoint '/api/teams/{club_id}' was hit.")
    club = db['clubs'].find_one({"_id": ObjectId(club_id)})
    if not club:
        print(f"No club found with ID: {club_id}")
        return jsonify({"error": "Club not found"}), 404
    team_ids = club.get("teams", [])
    if not team_ids:
        print(f"No teams found for club ID: {club_id}")
        return jsonify([]), 200  # Return empty list if no teams found
    teams = db['teams'].find({"_id": {"$in": team_ids}}, {"_id": 1, "name": 1})  # Adjusted to only select name and _id
    team_list = []
    for team in teams:
        if '_id' in team and 'name' in team:
            team_list.append({"id": str(team["_id"]), "name": team["name"]})

    return jsonify(team_list)

@app.route('/api/players/<team_id>', methods=['GET'])
def get_players(team_id):
    print(f"API endpoint '/api/players/{team_id}' was hit.")
    team = teams_collection.find_one({"_id": ObjectId(team_id)})
    if not team:
        print(f"No team found with ID: {team_id}")
        return jsonify({"error": "Team not found"}), 404
    player_ids = team.get("players", [])
    if not player_ids:
        print(f"No players found for team ID: {team_id}")
        return jsonify([]), 200  # Return empty list if no players found
    players = db['players'].find({"_id": {"$in": player_ids}}, {"_id": 1, "name": 1})  # Adjusted to only select name and _id
    player_list = [{"id": str(player["_id"]), "name": player["name"]} for player in players]
    return jsonify(player_list)

@app.route('/')
def index():
    return render_template('select.html')

@app.route('/home-admin.html')
def admin():
    return render_template('home-admin.html')

@app.route('/home-user.html')
def user():
    return render_template('home-user.html')

if __name__ == '__main__':
    app.run(debug=True)