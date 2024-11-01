from flask import Flask, jsonify,request, render_template
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["database"]
clubs_collection = db["clubs"]
teams_collection = db["teams"]
players_collection = db["players"]

@app.route('/api/clubs', methods=['GET'])
def get_clubs():
    print("API endpoint '/api/clubs' was hit.")
    clubs = clubs_collection.find({}, {"_id": 1, "name": 1})
    club_list = [{"id": str(club["_id"]), "name": club["name"]} for club in clubs]
    return jsonify(club_list)


#récupérer les équipes d'un club
@app.route('/api/teams/by-club-name/<club_name>', methods=['GET'])
def get_teams_by_club_name(club_name):
    # Recherche du club par nom
    club = clubs_collection.find_one({"name": club_name})
    
    if not club:
        return jsonify({"error": "Club not found"}), 404
    
    club_id = club["_id"]

    # Recherche des équipes liées à ce club
    teams = teams_collection.find({"club_id": club_id}, {"_id": 1, "name": 1})
    
    # Formatage de la réponse pour inclure les identifiants et noms des équipes
    team_list = [{"id": str(team["_id"]), "name": team["name"]} for team in teams]
    return jsonify(team_list)

#récupérer les joueurs d'une équipe et d'un club
@app.route('/api/players/by-club-team', methods=['GET'])
def get_players_by_club_and_team():
    club_name = request.args.get('club')
    team_name = request.args.get('team')
    

    # Trouver le club par nom pour obtenir son ID
    club = clubs_collection.find_one({"name": club_name})
    if not club:
        return jsonify({"error": "Club not found"}), 404
    

    # Trouver l'équipe par nom et club_id
    team = teams_collection.find_one({"name": team_name, "club_id": club["_id"]})
    if not team:
        return jsonify({"error": "Team not found"}), 404

    # Récupérer les joueurs de l'équipe et du club
    players = players_collection.find({"team_id": team["_id"], "club_id": club["_id"]}, {"_id": 1, "name": 1})
    player_list = [{"id": str(player["_id"]), "name": player["name"]} for player in players]
    return jsonify(player_list)

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



#récupère l'id du joueur en fonction de son nom, team et club
def get_player_id(name):
    user = players_collection.find_one({"name": name}, {"_id": 1})
    if user:
        return user["_id"]
    else:
        print(f"Aucun joueur trouvé avec le nom '{name}'.")
        return None

#récupère l'id de la team en fonction de son nom et club
def get_team_id(name):
    user = teams_collection.find_one({"name": name}, {"_id": 1})
    if user:
        return user["_id"]
    else:
        print(f"Aucune team trouvée avec le nom '{name}'.")
        return None
    
#récupère l'id du club en fonction de son nom
def get_club_id(name):
    user = clubs_collection.find_one({"name": name}, {"_id": 1})
    if user:
        return user["_id"]
    else:
        print(f"Aucun club trouvé avec le nom '{name}'.")
        return None
    

# mettre à jour le nom d'un joueur
@app.route('/update_player_name', methods=['POST'])
def update_player_name():
    data = request.json
    name = data.get('name')
    new_name = data.get('new_name')
    player_id = get_player_id(name)

    if not player_id:
        return jsonify({"error": "Player not found"}), 404

    result = players_collection.update_one(
        {"_id": player_id},
        {"$set": {"name": new_name}}
    )
    if result.matched_count > 0:
        return jsonify({"message": f"Player '{name}' updated successfully."})
    else:
        return jsonify({"error": "Update failed"}), 500

#supprimer ET ajouter un joueur dans une team
def update_player_from_team(club_id, team_id, club_id_new, team_id_new, player_name):
    try:
        
        # Rechercher le joueur dans la collection players
        player = players_collection.find_one({"name": player_name, "team_id": ObjectId(team_id), "club_id": ObjectId(club_id)})
        #player_new = players_collection.find_one({"name": player_name, "team_id": ObjectId(team_id_new), "club_id": ObjectId(club_id_new)})
        
        if not player:
            return {"error": "Player not found in the specified team."}
        

        # Mettre à jour la collection teams en retirant le joueur de la liste des joueurs de l'équipe
        teams_collection.update_one(
            {"_id": ObjectId(team_id)},
            {"$pull": {"players": player["_id"]}}
        )

        teams_collection.update_one(
            {"_id": ObjectId(team_id_new)},
            {"$push": {"players": player["_id"]}}
        )

        
        return {"message": f"Player '{player_name}' removed successfully from team '{team_id}'."}
    
    except Exception as e:
        return {"error": str(e)}



    
# mettre à jour la team d'un joueur
@app.route('/update_player_team', methods=['POST'])
def update_player_team():
    data = request.json
    name = data.get('name')
    team = data.get('from_team')
    club = data.get('from_club')
    new_team = data.get('to_team')
    new_club = data.get('to_club')

    # Obtenez les identifiants nécessaires pour les équipes et les clubs
    new_team_id = get_team_id(new_team)
    team_id = get_team_id(team)
    player_id = get_player_id(name)
    new_club_id = get_club_id(new_club)
    club_id = get_club_id(club)

    if not player_id:
        return jsonify({"error": "Player not found"}), 404
    if not team_id or not new_team_id:
        return jsonify({"error": "Team(s) not found"}), 404
    if not club_id or not new_club_id:
        return jsonify({"error": "Club(s) not found"}), 404

    # Retirer le joueur de l'équipe actuelle et l'ajouter à la nouvelle
    update_player_from_team(club_id, team_id,new_club_id, new_team_id, name)

    # Mettre à jour l'identifiant de l'équipe du joueur
    result = players_collection.update_one(
        {"_id": player_id},
        {"$set": {"team_id": new_team_id}}
    )

    if result.matched_count > 0:
        return jsonify({"message": f"Player '{name}' successfully moved to new team '{new_team}' in club '{new_club}'."})
    else:
        return jsonify({"error": "Update failed"}), 500


# mettre à jour le club d'un joueur
@app.route('/update_player_club', methods=['POST'])
def update_player_club():
    data = request.json
    name = data.get('name')
    team = data.get('from_team')
    club = data.get('from_club')
    new_team = data.get('to_team')
    new_club = data.get('to_club')

    player_id = get_player_id(name)
    if not player_id:
        return jsonify({"error": "Player not found"}), 404

    new_team_id = get_team_id(new_team)
    new_club_id = get_club_id(new_club)
    if not new_team_id or not new_club_id:
        return jsonify({"error": "New team or club not found"}), 404

    result = players_collection.update_one(
        {"_id": player_id},
        {"$set": {"team_id": new_team_id, "club_id": new_club_id}}
    )

    if result.matched_count > 0:
        return jsonify({"message": f"Player '{name}' updated successfully."})
    else:
        return jsonify({"error": "Update failed "}), 500

    # Appel de la fonction pour déplacer le joueur
    update_player_team(name, team, club, new_club, new_team)

    

# mettre à jour le nom d'une team
@app.route('/update_team_name', methods=['POST'])
def update_team_name():
    data = request.json
    team = data.get('from_team')
    new_name = data.get('to_team')

    team_id = get_team_id(team)
    if not team_id:
        return jsonify({"error": "Team not found"}), 404

    # Mettre à jour le nom de l'équipe
    result = teams_collection.update_one(
        {"_id": team_id},
        {"$set": {"name": new_name}}
    )

    if result.matched_count > 0:
        return jsonify({"message": f"Team '{team}' successfully renamed to '{new_name}'."})
    else:
        return jsonify({"error": "Update failed"}), 500

# mettre à jour le nom d'un club
@app.route('/update_club_name', methods=['POST'])
def update_club_name():
    data = request.json
    club = data.get('from_club')
    new_name = data.get('to_club')

    club_id = get_club_id(club)
    if not club_id:
        return jsonify({"error": "Club not found"}), 404

    # Mettre à jour le nom du club
    result = clubs_collection.update_one(
        {"_id": club_id},
        {"$set": {"name": new_name}}
    )

    if result.matched_count > 0:
        return jsonify({"message": f"Club '{club}' successfully renamed to '{new_name}'."})
    else:
        return jsonify({"error": "Update failed"}), 500


@app.route('/')
def index():
    return render_template('home.html')

@app.route('/modify-element.html')
def modifier():
    return render_template('modify-element.html')

if __name__ == '__main__':
    app.run(debug=True)