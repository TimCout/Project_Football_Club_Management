from pymongo import MongoClient
from bson import ObjectId
import random

client = MongoClient('mongodb://localhost:27017')
db = client['database']

clubs_collection = db['clubs']
teams_collection = db['teams']
players_collection = db['players']
users_collection = db['users']

def generate_name(prefix, index):
    return f"{prefix} {index}"

NUM_CLUBS = 5
NUM_TEAMS_PER_CLUB = 10
NUM_PLAYERS_PER_TEAM = 1000
NUM_USERS = 5

def create_data():
    clubs_collection.delete_many({})
    teams_collection.delete_many({})
    players_collection.delete_many({})

    for i in range(NUM_CLUBS):
        club_name = generate_name("Club", i+1)
        club_id = clubs_collection.insert_one({
            "name": club_name,
            "teams": []
        }).inserted_id

        team_ids = []
        for j in range(NUM_TEAMS_PER_CLUB):
            team_name = generate_name("Team", j+1)
            team_id = teams_collection.insert_one({
                "name": team_name,
                "club_id": club_id,
                "players": []
            }).inserted_id
            team_ids.append(team_id)

            player_ids = []
            for k in range(NUM_PLAYERS_PER_TEAM):
                player_name = generate_name("Player", k+1)
                player_id = players_collection.insert_one({
                    "name": player_name,
                    "club_id": club_id,
                    "team_id": team_id
                }).inserted_id
                player_ids.append(player_id)

            teams_collection.update_one(
                {"_id": team_id},
                {"$set": {"players": player_ids}}
            )

        clubs_collection.update_one(
            {"_id": club_id},
            {"$set": {"teams": team_ids}}
        )

    print("Database populated with clubs, teams, and players.")

def add_users(num_users):
    for i in range(num_users):
        user_data = {
            "_id": ObjectId(),
            "username": f"user_{i + 1}",
            "password": "1234",
            "role": "user"
        }
        users_collection.insert_one(user_data)
    print(f"{num_users} users added to the database.")

if __name__ == "__main__":
    create_data()
    add_users(NUM_USERS)