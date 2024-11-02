from flask import Flask, jsonify,request, render_template
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["database"]
clubs_collection = db["clubs"]
teams_collection = db["teams"]
players_collection = db["players"]
users_collection = db["users"]

# Création du premier administrateur
def create_admin():
    existing_admin = users_collection.find_one({"username": "Admin"})
    if not existing_admin:
        admin_data = {
            "username": "Admin",
            "password": generate_password_hash("1234"),  # Hachage du mot de passe pour plus de sécurité
            "role": "admin"
        }
        users_collection.insert_one(admin_data)
        print("Admin created successfully")
    else:
        print("Admin already exists")

create_admin()

# Endpoint pour l'inscription des utilisateurs
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
    
    # Vérification si l'utilisateur existe déjà
    if users_collection.find_one({"username": username}):
        return jsonify({"error": "Username already exists"}), 409
    
    # Insertion du nouvel utilisateur
    user_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "username": username,
        "password": generate_password_hash(password),  # Hachage du mot de passe
        "role": "user"  # Rôle utilisateur par défaut
    }
    users_collection.insert_one(user_data)
    
    return jsonify({"message": "User signed up successfully"}), 201

# Endpoint pour la connexion
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    # Recherche de l'utilisateur dans la base de données
    user = users_collection.find_one({"username": username})
    if user and check_password_hash(user["password"], password):
        return jsonify({"message": f"Welcome {user['role']}!", "role": user["role"]}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

# Endpoint pour récupérer les utilisateurs (admin seulement)
@app.route('/api/users', methods=['GET'])
def get_users():
    # Exemple d’autorisation simple pour vérifier le rôle d’admin
    role = request.args.get("role")
    if role != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    
    users = users_collection.find({}, {"password": 0})  # On exclut les mots de passe
    user_list = [{"username": user["username"], "role": user["role"]} for user in users]
    return jsonify(user_list)

#home page
@app.route('/api/clubs', methods=['GET'])
def get_clubs():
    print("API endpoint '/api/clubs' was hit.")
    clubs = clubs_collection.find({}, {"_id": 1, "name": 1})
    club_list = [{"id": str(club["_id"]), "name": club["name"]} for club in clubs]
    return jsonify(club_list)

#add page
def add_club(club_data):
    existing_club = clubs_collection.find_one({"name": club_data["name"]})
    if existing_club:
        return {"message": "Club already exists", "club_id": str(existing_club["_id"])}
    
    club_id = clubs_collection.insert_one(club_data).inserted_id
    return {"message": "Club added successfully", "club_id": str(club_id)}

def add_team_to_club(club_id, team_data):
    existing_team = teams_collection.find_one({"name": team_data["name"], "club_id": ObjectId(club_id)})
    if existing_team:
        return {"message": "Team already exists in this club", "team_id": str(existing_team["_id"])}
    
    team_data["club_id"] = ObjectId(club_id)
    team_data["players"] = []
    team_id = teams_collection.insert_one(team_data).inserted_id
    clubs_collection.update_one({"_id": ObjectId(club_id)}, {"$push": {"teams": team_id}})
    
    return {"message": "Team added successfully", "team_id": str(team_id)}

def add_player_to_team(club_id, team_id, player_data):
    existing_player = players_collection.find_one({"name": player_data["name"], "team_id": ObjectId(team_id)})
    if existing_player:
        return {"message": "Player with this name already exists in the team", "player_id": str(existing_player["_id"])}
    
    player_data["club_id"] = ObjectId(club_id)
    player_data["team_id"] = ObjectId(team_id)
    player_id = players_collection.insert_one(player_data).inserted_id
    teams_collection.update_one({"_id": ObjectId(team_id)}, {"$push": {"players": player_id}})
    
    return {"message": "Player added successfully", "player_id": str(player_id)}

# New endpoint for adding elements
@app.route('/api/add-element', methods=['POST'])
def add_element():
    data = request.json
    club_name = data.get("club")
    team_name = data.get("team")
    player_name = data.get("player")

    # Initialize response message
    response = {}

    # Step 1: Handle Club
    if not club_name:
        response["club"] = "Cannot add a team or player without specifying a club."
        return jsonify(response)
    club = clubs_collection.find_one({"name": club_name})
    if club:
        club_id = str(club["_id"])
        response["club"] = "Club already exists"
    else:
        result = add_club({"name": club_name, "teams": []})
        club_id = result["club_id"]
        response["club"] = result["message"]

    # Step 2: Handle Team
    if team_name:
        team = teams_collection.find_one({"name": team_name, "club_id": ObjectId(club_id)})
        if team:
            team_id = str(team["_id"])
            response["team"] = "Team already exists in this club"
        else:
            result = add_team_to_club(club_id, {"name": team_name})
            team_id = result["team_id"]
            response["team"] = result["message"]
    elif player_name:
        response["team"] = "Cannot add a player without specifying a team."
        return jsonify(response)
    else:
        team_id = None

    # Step 3: Handle Player
    if player_name and team_id:
        result = add_player_to_team(club_id, team_id, {"name": player_name})
        response["player"] = result["message"]
    elif player_name and not team_id:
        response["player"] = "Cannot add player without specifying a team"
    else:
        response["player"] = "No player specified"

    return jsonify(response)

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


#modify page
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
    

@app.route('/api/delete', methods=['POST'])
def delete_entity():
    data = request.json
    club_name = data.get('club')
    team_name = data.get('team')
    player_name = data.get('player')

    club = clubs_collection.find_one({"name": club_name})
    if not club:
        return jsonify({"error": "Club not found"}), 404

    club_id = club["_id"]

    if club_name and not team_name and not player_name:
        teams = teams_collection.find({"club_id": club_id})
        team_ids = [team["_id"] for team in teams]
        players_collection.delete_many({"team_id": {"$in": team_ids}})
        teams_collection.delete_many({"club_id": club_id})
        clubs_collection.delete_one({"_id": club_id})
        return jsonify({"message": f"Club '{club_name}', all associated teams and players deleted successfully."})

    team = teams_collection.find_one({"name": team_name, "club_id": club_id}) if team_name else None

    if club_name and team_name and not player_name:
        if not team:
            return jsonify({"error": "Team not found in the specified club"}), 404
        players_collection.delete_many({"team_id": team["_id"]})
        teams_collection.delete_one({"_id": team["_id"]})
        return jsonify({"message": f"Team '{team_name}' and all associated players deleted successfully."})

    player = players_collection.find_one({"name": player_name, "team_id": team["_id"]}) if player_name and team else None

    if club_name and team_name and player_name:
        if not player:
            return jsonify({"error": "Player not found in the specified team"}), 404
        players_collection.delete_one({"_id": player["_id"]})
        return jsonify({"message": f"Player '{player_name}' deleted successfully."})

    return jsonify({"error": "Invalid parameters"}), 400    

#manage pages
@app.route('/')
def index():
    return render_template('select.html')

@app.route('/home-admin.html')
def admin():
    return render_template('home-admin.html')

@app.route('/home-user.html')
def user():
    return render_template('home-user.html')

@app.route('/add-element.html')
def add():
    return render_template('add-element.html')

@app.route('/delete-element.html')
def delete():
    return render_template('delete-element.html')

@app.route('/modify-element.html')
def modify():
    return render_template('modify-element.html')

@app.route('/list-user.html')
def list():
    return render_template('list-user.html')

if __name__ == '__main__':
    app.run(debug=True)