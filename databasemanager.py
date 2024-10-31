from pymongo import MongoClient
import redis
from bson.objectid import ObjectId

mongo_client = MongoClient("mongodb://localhost:27017/")
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

db = mongo_client["database"]
clubs_collection = db["clubs"]
players_collection = db["players"]
teams_collection = db["teams"]

def add_club(club_data):
    try:
        club_id = clubs_collection.insert_one(club_data).inserted_id
        return {"message": "Club added successfully", "club_id": str(club_id)}
    
    except Exception as e:
        return {"error": str(e)}
    
def add_team_to_club(club_id, team_data):
    try:
        club = clubs_collection.find_one({"_id": ObjectId(club_id)})
        
        if not club:
            return {"error": "Club not found."}
        
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

player_data = {
    "name": "Cristiano Ronaldo"
}
club_data = {"name": "Real madrid"}
response_club = add_club(club_data)
print(response_club)

team_data = {"name": "U22"}
response_team = add_team_to_club(response_club.get("club_id"), team_data)
print(response_team)

player_data = {"name": "Iniesta"}
response_player = add_player_to_team(response_club.get("club_id"), response_team.get("team_id"), player_data)
print(response_player)