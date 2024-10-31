from pymongo import MongoClient
import redis
from bson.objectid import ObjectId

# Connexion à MongoDB et Redis
mongo_client = MongoClient("mongodb://localhost:27017/")
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

db = mongo_client["database"]
clubs_collection = db["clubs"]
players_collection = db["players"]
teams_collection = db["teams"]

def add_club(club_data):
    try:
        existing_club = clubs_collection.find_one({"name": club_data["name"]})
        if existing_club:
            return {"message": "Club already exists", "club_id": str(existing_club["_id"])}
        
        club_id = clubs_collection.insert_one(club_data).inserted_id
        return {"message": "Club added successfully", "club_id": str(club_id)}
    
    except Exception as e:
        return {"error": str(e)}
    
def add_team_to_club(club_id, team_data):
    try:
        club = clubs_collection.find_one({"_id": ObjectId(club_id)})
        if not club:
            return {"error": "Club not found."}
        
        existing_team = teams_collection.find_one({
            "name": team_data["name"],
            "club_id": ObjectId(club_id)
        })
        if existing_team:
            return {"message": "Team already exists in this club", "team_id": str(existing_team["_id"])}
        
        team_data["club_id"] = ObjectId(club_id)
        team_data["players"] = []
        team_id = teams_collection.insert_one(team_data).inserted_id
        
        clubs_collection.update_one(
            {"_id": ObjectId(club_id)},
            {"$push": {"teams": team_id}}
        )
        
        return {"message": "Team added successfully", "team_id": str(team_id)}
    
    except Exception as e:
        return {"error": str(e)}

def add_player_to_team(club_id, team_id, player_data):
    try:
        team = teams_collection.find_one({"_id": ObjectId(team_id), "club_id": ObjectId(club_id)})
        
        if not team:
            return {"error": "Team not found in the specified club."}
        
        existing_player = players_collection.find_one({
            "name": player_data["name"]
        })
        if existing_player:
            return {"error": "Player with this name already exists. Please choose a different name."}
        
        player_data["club_id"] = ObjectId(club_id)
        player_data["team_id"] = ObjectId(team_id)
        
        player_id = players_collection.insert_one(player_data).inserted_id
        
        teams_collection.update_one(
            {"_id": ObjectId(team_id)},
            {"$push": {"players": player_id}}
        )
        
        player_data_str = {k: str(v) if isinstance(v, ObjectId) else v for k, v in player_data.items()}
        player_data_str["_id"] = str(player_id)
        
        redis_client.hset(f"player:{player_id}", mapping=player_data_str)
        
        return {"message": "Player added successfully", "player_id": str(player_id)}
    
    except Exception as e:
        return {"error": str(e)}

# Fonction pour supprimer un club par son nom
def delete_club_by_name(club_name):
    try:
        club = clubs_collection.find_one({"name": club_name})
        if not club:
            return {"error": "Club not found."}

        club_id = str(club["_id"])

        # Supprimer les équipes et les joueurs associés
        teams = teams_collection.find({"club_id": ObjectId(club_id)})
        for team in teams:
            team_id = str(team["_id"])
            # Supprimer tous les joueurs de cette équipe
            players_collection.delete_many({"team_id": ObjectId(team_id)})
            redis_client.delete(f"team:{team_id}")  # Supprimer aussi du cache Redis

        # Supprimer toutes les équipes du club
        teams_collection.delete_many({"club_id": ObjectId(club_id)})
        clubs_collection.delete_one({"_id": ObjectId(club_id)})
        
        return {"message": f"Club '{club_name}' and all associated teams and players deleted successfully."}
    
    except Exception as e:
        return {"error": str(e)}

# Fonction pour supprimer une équipe par son nom
def delete_team_by_name(club_name, team_name):
    try:
        club = clubs_collection.find_one({"name": club_name})
        if not club:
            return {"error": "Club not found."}
        
        club_id = str(club["_id"])
        team = teams_collection.find_one({"name": team_name, "club_id": ObjectId(club_id)})
        if not team:
            return {"error": "Team not found in the specified club."}

        team_id = str(team["_id"])
        
        # Supprimer tous les joueurs de cette équipe
        players_collection.delete_many({"team_id": ObjectId(team_id)})
        redis_client.delete(f"team:{team_id}")  # Supprimer aussi du cache Redis
        
        # Supprimer l'équipe
        teams_collection.delete_one({"_id": ObjectId(team_id)})
        
        # Retirer l'équipe de la collection des clubs
        clubs_collection.update_one(
            {"_id": ObjectId(club_id)},
            {"$pull": {"teams": ObjectId(team_id)}}
        )
        
        return {"message": f"Team '{team_name}' deleted successfully."}
    
    except Exception as e:
        return {"error": str(e)}

# Fonction pour supprimer un joueur par son nom
def delete_player_by_name(club_name, team_name, player_name):
    try:
        club = clubs_collection.find_one({"name": club_name})
        if not club:
            return {"error": "Club not found."}
        
        club_id = str(club["_id"])
        team = teams_collection.find_one({"name": team_name, "club_id": ObjectId(club_id)})
        if not team:
            return {"error": "Team not found in the specified club."}

        team_id = str(team["_id"])
        player = players_collection.find_one({"name": player_name, "team_id": ObjectId(team_id), "club_id": ObjectId(club_id)})
        if not player:
            return {"error": "Player not found in the specified team."}

        # Supprimer le joueur
        players_collection.delete_one({"_id": ObjectId(player["_id"])})
        redis_client.delete(f"player:{player['_id']}")  # Supprimer aussi du cache Redis
        
        # Retirer le joueur de l'équipe
        teams_collection.update_one(
            {"_id": ObjectId(team_id)},
            {"$pull": {"players": ObjectId(player["_id"])}}
        )
        
        return {"message": f"Player '{player_name}' deleted successfully."}
    
    except Exception as e:
        return {"error": str(e)}
    
def get_club_with_teams_and_players(club_name):
    try:
        club = clubs_collection.find_one({"name": club_name})
        if not club:
            return {"error": "Club not found."}

        club_data = {
            "club_name": club["name"],
            "teams": []
        }

        # Retrieve teams of the club
        teams = teams_collection.find({"club_id": club["_id"]})
        for team in teams:
            team_data = {
                "name": team["name"],
                "players": []
            }

            # Retrieve players of the team
            players = players_collection.find({"team_id": team["_id"]})
            for player in players:
                player_data = {
                    "name": player["name"]
                }
                team_data["players"].append(player_data)

            club_data["teams"].append(team_data)

        return club_data

    except Exception as e:
        return {"error": str(e)}


def get_team_with_players(club_name, team_name):
    try:
        club = clubs_collection.find_one({"name": club_name})
        if not club:
            return {"error": "Club not found."}

        team = teams_collection.find_one({"name": team_name, "club_id": club["_id"]})
        if not team:
            return {"error": "Team not found in the specified club."}

        team_data = {
            "team_name": team["name"],
            "players": []
        }

        # Retrieve players of the team
        players = players_collection.find({"team_id": team["_id"]})
        for player in players:
            player_data = {
                "name": player["name"]
            }
            team_data["players"].append(player_data)

        return team_data

    except Exception as e:
        return {"error": str(e)}


# Example usage
# To get a club with its teams and players
club_info = get_club_with_teams_and_players("ZOUM")
print(club_info)

# To get the details of a team
team_info = get_team_with_players("ZOUM", "U79")
print(team_info)


# Exemple d'utilisation

club_data = {"name": "ZOUM"}
response_club = add_club(club_data)
print(response_club)

team_data = {"name": "U79"}
response_team = add_team_to_club(response_club.get("club_id"), team_data)
print(response_team)

player_data = {"name": "JOE"}
response_player = add_player_to_team(response_club.get("club_id"), response_team.get("team_id"), player_data)
print(response_player)






