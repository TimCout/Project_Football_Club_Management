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

# Exemple d'utilisation
# Ajout d'un club, d'une équipe et d'un joueur
"""
club_data = {"name": "ZOUM"}
response_club = add_club(club_data)
print(response_club)

team_data = {"name": "U79"}
response_team = add_team_to_club(response_club.get("club_id"), team_data)
print(response_team)

player_data = {"name": "JOE"}
response_player = add_player_to_team(response_club.get("club_id"), response_team.get("team_id"), player_data)
print(response_player)



response_delete_club = delete_club_by_name("ZOUM")
print(response_delete_club)
"""



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



#modifier le nom d'un joueur
def update_mongo_player_name(name,new_name):

    player_id = get_player_id(name)

    result = players_collection.update_one(
        {"_id": player_id},
        {"$set": {"name": new_name}}
    )
    
    if result.matched_count > 0:
        print(f"Le joueur avec l'id {player_id} est mis à jour.")
    else:
        print(f"Aucun joueur trouvé avec l'id {player_id}.")

#update_mongo_player_name("Pedri", "Lionel")


#supprimer un joueur d'une team
def remove_player_from_team(club_id, team_id, player_name):
    """
    Supprime un joueur d'une équipe et met à jour l'équipe dans MongoDB.
    
    :param club_id: ID du club
    :param team_id: ID de l'équipe
    :param player_name: Nom du joueur à supprimer
    :return: Message indiquant si la suppression a réussi ou échoué
    """
    try:
        # Rechercher l'équipe pour s'assurer qu'elle appartient au club spécifié
        team = teams_collection.find_one({"_id": ObjectId(team_id), "club_id": ObjectId(club_id)})
        
        if not team:
            return {"error": "Team not found in the specified club."}

        # Rechercher le joueur dans la collection players
        player = players_collection.find_one({"name": player_name, "team_id": ObjectId(team_id), "club_id": ObjectId(club_id)})
        
        if not player:
            return {"error": "Player not found in the specified team."}
        
        # Supprimer le joueur de la collection players
        players_collection.delete_one({"_id": player["_id"]})

        # Mettre à jour la collection teams en retirant le joueur de la liste des joueurs de l'équipe
        teams_collection.update_one(
            {"_id": ObjectId(team_id)},
            {"$pull": {"players": player["_id"]}}
        )

        # Supprimer le joueur du cache Redis
        redis_client.delete(f"player:{player['_id']}")
        
        return {"message": f"Player '{player_name}' removed successfully from team '{team['name']}'."}
    
    except Exception as e:
        return {"error": str(e)}


#modifier la team d'un joueur
def update_mongo_player_team(name, team ,club, new_club, new_team):

    new_team_id = get_team_id(new_team)
    team_id = get_team_id(team)

    player_id = get_player_id(name)


    new_club_id = get_club_id(new_club)
    club_id = get_club_id(club)

    remove_player_from_team(club_id, team_id, name)
    add_player_to_team(new_club_id, new_team_id, {"name": name})



    result = players_collection.update_one(
        {"_id": player_id},
        {"$set": {"team_id": new_team_id}}
    )


    
    if result.matched_count > 0:
        print(f"Le joueur avec l'id {player_id} est mis à jour.")
    else:
        print(f"Aucun joueur trouvé avec l'id {player_id}.")

#update_mongo_player_team("Pedri","U24", "PSG", "U20")

#modifier le club et la team d'un joueur
def update_mongo_player_club(name,team, club, new_team, new_club ):

    player_id = get_player_id(name)
    new_team_id = get_team_id(new_team)
    new_club_id = get_club_id(new_club)

    result = players_collection.update_one(
        {"_id": player_id},
        {"$set": {"team_id": new_team_id,
                  "club_id": new_club_id}}
    )

    update_mongo_player_team(name, team, club ,new_club_id, new_team)
    
    if result.matched_count > 0:
        print(f"Le joueur avec l'id {player_id} est mis à jour.")
    else:
        print(f"Aucun joueur trouvé avec l'id {player_id}.")

#update_mongo_player_club("Lionel","U2", "PS", "U20", "PSG" )


#modifier le nom d'une team

def update_mongo_team_name(team, new_name):

    team_id =  get_team_id(team)

    result = teams_collection.update_one(
        {"_id": team_id},
        {"$set": {"name": new_name}}
    )
    
    if result.matched_count > 0:
        print(f"La team avec l'id {team_id} est mise à jour.")
    else:
        print(f"Aucune team trouvée avec l'id {team_id}.")

#update_mongo_team_name("U20", "U40")





#modifier le nom d'un club


def update_mongo_club_name(club, new_name):

    club_id = get_club_id(club)

    result = clubs_collection.update_one(
        {"_id": club_id},
        {"$set": {"name": new_name}}
    )
    
    if result.matched_count > 0:
        print(f"Utilisateur avec user_id {club_id} mis à jour.")
    else:
        print(f"Aucun utilisateur trouvé avec user_id {club_id}.")

    
#update_mongo_club_name("PS", "SP")
