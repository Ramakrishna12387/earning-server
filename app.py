from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///players.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
CORS(app)


# =========================
# PLAYER DATABASE
# =========================

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    coins = db.Column(db.Integer, default=1000)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)


with app.app_context():
    db.create_all()


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return jsonify({
        "message": "White Jack Earning Server is running!"
    })


# =========================
# CREATE PLAYER
# =========================

@app.route("/player", methods=["POST"])
def create_player():

    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON data is required"}), 400

    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400

    player = Player.query.filter_by(name=name).first()

    if not player:

        player = Player(
            name=name,
            coins=1000,
            wins=0,
            losses=0,
            games_played=0
        )

        db.session.add(player)
        db.session.commit()

    return jsonify({
        "name": player.name,
        "coins": player.coins,
        "wins": player.wins,
        "losses": player.losses,
        "games_played": player.games_played
    })


# =========================
# GET PLAYER
# =========================

@app.route("/player/<name>")
def get_player(name):

    player = Player.query.filter_by(name=name).first()

    if not player:
        return jsonify({
            "error": "Player not found"
        }), 404

    return jsonify({
        "name": player.name,
        "coins": player.coins,
        "wins": player.wins,
        "losses": player.losses,
        "games_played": player.games_played
    })


# =========================
# UPDATE COINS
# =========================

@app.route("/update-coins", methods=["POST"])
def update_coins():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "JSON data is required"
        }), 400

    name = data.get("name", "").strip()
    coins = data.get("coins")

    if not name:
        return jsonify({
            "error": "Name is required"
        }), 400

    if coins is None:
        return jsonify({
            "error": "Coins are required"
        }), 400

    player = Player.query.filter_by(name=name).first()

    if not player:
        return jsonify({
            "error": "Player not found"
        }), 404

    try:
        coins = int(coins)
    except:
        return jsonify({
            "error": "Coins must be a number"
        }), 400

    player.coins += coins

    if player.coins < 0:
        player.coins = 0

    db.session.commit()

    return jsonify({
        "message": "Coins updated successfully",
        "name": player.name,
        "coins": player.coins
    })


# =========================
# GAME RESULT
# =========================

@app.route("/game-result", methods=["POST"])
def game_result():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "JSON data is required"
        }), 400

    name = data.get("name", "").strip()
    result = data.get("result")

    if not name:
        return jsonify({
            "error": "Name is required"
        }), 400

    if result not in ["win", "loss"]:
        return jsonify({
            "error": "Result must be win or loss"
        }), 400

    player = Player.query.filter_by(name=name).first()

    if not player:
        return jsonify({
            "error": "Player not found"
        }), 404

    player.games_played += 1

    if result == "win":

        player.wins += 1
        player.coins += 100

    else:

        player.losses += 1
        player.coins -= 50

        if player.coins < 0:
            player.coins = 0

    db.session.commit()

    return jsonify({
        "message": "Game result updated",
        "name": player.name,
        "coins": player.coins,
        "wins": player.wins,
        "losses": player.losses,
        "games_played": player.games_played
    })


# =========================
# LEADERBOARD
# =========================

@app.route("/leaderboard")
def leaderboard():

    players = Player.query.order_by(
        Player.coins.desc()
    ).limit(10).all()

    result = []

    for player in players:

        result.append({
            "name": player.name,
            "coins": player.coins,
            "wins": player.wins,
            "losses": player.losses,
            "games_played": player.games_played
        })

    return jsonify(result)


# =========================
# WHITE JACK GAME
# =========================

@app.route("/blackjack", methods=["POST"])
def blackjack():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "JSON data is required"
        }), 400

    name = data.get("name", "").strip()

    if not name:
        return jsonify({
            "error": "Name is required"
        }), 400

    player = Player.query.filter_by(name=name).first()

    if not player:
        return jsonify({
            "error": "Player not found"
        }), 404


    # Card deck

    cards = [
        2, 3, 4, 5, 6, 7, 8, 9, 10,
        10, 10, 10, 11
    ]


    player_card_1 = random.choice(cards)
    player_card_2 = random.choice(cards)

    dealer_card_1 = random.choice(cards)
    dealer_card_2 = random.choice(cards)


    player_total = player_card_1 + player_card_2
    dealer_total = dealer_card_1 + dealer_card_2


    # Simple Ace handling

    if player_total > 21:
        player_total -= 10

    if dealer_total > 21:
        dealer_total -= 10


    # Result

    if player_total > 21:

        result = "loss"

    elif dealer_total > 21:

        result = "win"

    elif player_total > dealer_total:

        result = "win"

    elif player_total < dealer_total:

        result = "loss"

    else:

        result = "draw"


    # Coins

    player.games_played += 1


    if result == "win":

        player.wins += 1
        player.coins += 100

        message = "YOU WIN! +100 COINS"

    elif result == "loss":

        player.losses += 1
        player.coins -= 50

        if player.coins < 0:
            player.coins = 0

        message = "YOU LOST! -50 COINS"

    else:

        message = "DRAW! NO COINS"


    db.session.commit()


    return jsonify({

        "name": player.name,

        "player_cards": [
            player_card_1,
            player_card_2
        ],

        "dealer_cards": [
            dealer_card_1,
            dealer_card_2
        ],

        "player_total": player_total,
        "dealer_total": dealer_total,

        "result": result,

        "message": message,

        "coins": player.coins,

        "wins": player.wins,

        "losses": player.losses,

        "games_played": player.games_played
    })


# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )