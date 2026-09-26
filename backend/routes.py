from datetime import date

from flask import Blueprint, request, jsonify

from .database import db
from .models import Player, GameHistory
from .game import create_deck, hand_score, card_text
from .config import VALID_BETS, STARTING_COINS, DAILY_BONUS


api = Blueprint("api", __name__)

active_games = {}


def get_player(name):
    return Player.query.filter_by(name=name).first()


def player_data(player):
    return {
        "name": player.name,
        "coins": player.coins,
        "wins": player.wins,
        "losses": player.losses,
        "games_played": player.games_played
    }


def game_data(game, hide_dealer=True):

    dealer_cards = [
        card_text(card)
        for card in game["dealer"]
    ]

    if hide_dealer:
        dealer_cards = [
            "🂠",
            card_text(game["dealer"][1])
        ]

        dealer_score = "?"
    else:
        dealer_score = hand_score(game["dealer"])

    return {
        "player_cards": [
            card_text(card)
            for card in game["player"]
        ],

        "dealer_cards": dealer_cards,

        "player_score": hand_score(
            game["player"]
        ),

        "dealer_score": dealer_score,

        "bet": game["bet"],

        "finished": game["finished"]
    }


# =====================================================
# PLAYER
# =====================================================

@api.route("/player", methods=["POST"])
def player_login():

    try:

        data = request.get_json(silent=True) or {}

        name = str(
            data.get("name", "")
        ).strip()

        if not name:
            return jsonify({
                "error": "Username is required"
            }), 400

        if len(name) > 50:
            return jsonify({
                "error": "Username is too long"
            }), 400

        player = get_player(name)

        if player is None:

            player = Player(
                name=name,
                coins=STARTING_COINS,
                wins=0,
                losses=0,
                games_played=0,
                last_bonus=str(date.today())
            )

            db.session.add(player)
            db.session.commit()

            message = (
                "Welcome! You received "
                f"{STARTING_COINS} virtual coins."
            )

        else:

            today = str(date.today())

            if player.last_bonus != today:

                player.coins += DAILY_BONUS
                player.last_bonus = today

                db.session.commit()

                message = (
                    f"Daily bonus: +{DAILY_BONUS} "
                    "virtual coins."
                )

            else:

                message = "Welcome back."

        return jsonify({
            "message": message,
            "player": player_data(player)
        })

    except Exception as error:

        db.session.rollback()

        print("PLAYER ERROR:", error)

        return jsonify({
            "error": "Player database error",
            "details": str(error)
        }), 500


@api.route("/player/<name>", methods=["GET"])
def player_info(name):

    try:

        player = get_player(name)

        if player is None:
            return jsonify({
                "error": "Player not found"
            }), 404

        return jsonify({
            "player": player_data(player)
        })

    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


# =====================================================
# START GAME
# =====================================================

@api.route("/game/start", methods=["POST"])
def start_game():

    try:

        data = request.get_json(silent=True) or {}

        name = str(
            data.get("name", "")
        ).strip()

        try:
            bet = int(data.get("bet", 10))
        except:
            bet = 10

        if bet not in VALID_BETS:

            return jsonify({
                "error": (
                    "Invalid bet. Choose "
                    "10, 50, 100 or 500."
                )
            }), 400

        player = get_player(name)

        if player is None:

            return jsonify({
                "error": "Player not found."
            }), 404

        if player.coins < bet:

            return jsonify({
                "error": "Not enough virtual coins."
            }), 400

        if name in active_games:

            return jsonify({
                "error": "You already have an active game."
            }), 400

        deck = create_deck()

        player_cards = [
            deck.pop(),
            deck.pop()
        ]

        dealer_cards = [
            deck.pop(),
            deck.pop()
        ]

        game = {
            "deck": deck,
            "player": player_cards,
            "dealer": dealer_cards,
            "bet": bet,
            "finished": False
        }

        active_games[name] = game

        player.coins -= bet

        db.session.commit()

        # Blackjack
        if hand_score(player_cards) == 21:

            dealer_score = hand_score(
                dealer_cards
            )

            if dealer_score == 21:

                result = "Push - Tie"

                player.coins += bet

            else:

                result = "Blackjack!"

                player.coins += int(
                    bet * 2.5
                )

                player.wins += 1

            player.games_played += 1

            game["finished"] = True

            db.session.add(
                GameHistory(
                    player_name=name,
                    bet=bet,
                    result=result,
                    player_score=21,
                    dealer_score=dealer_score
                )
            )

            db.session.commit()

            active_games.pop(
                name,
                None
            )

            return jsonify({
                "game": game_data(
                    game,
                    hide_dealer=False
                ),
                "result": result,
                "finished": True
            })

        return jsonify({
            "game": game_data(game),
            "finished": False
        })

    except Exception as error:

        db.session.rollback()

        print("START GAME ERROR:", error)

        return jsonify({
            "error": str(error)
        }), 500


# =====================================================
# HIT
# =====================================================

@api.route("/game/hit", methods=["POST"])
def hit():

    try:

        data = request.get_json(silent=True) or {}

        name = str(
            data.get("name", "")
        ).strip()

        game = active_games.get(name)

        if game is None:

            return jsonify({
                "error": "No active game."
            }), 400

        if game["finished"]:

            return jsonify({
                "error": "Game already finished."
            }), 400

        game["player"].append(
            game["deck"].pop()
        )

        score = hand_score(
            game["player"]
        )

        if score > 21:

            game["finished"] = True

            player = get_player(name)

            player.losses += 1
            player.games_played += 1

            result = "Bust - You lose"

            db.session.add(
                GameHistory(
                    player_name=name,
                    bet=game["bet"],
                    result=result,
                    player_score=score,
                    dealer_score=hand_score(
                        game["dealer"]
                    )
                )
            )

            db.session.commit()

            active_games.pop(
                name,
                None
            )

            return jsonify({
                "game": game_data(
                    game,
                    hide_dealer=False
                ),
                "result": result,
                "finished": True
            })

        return jsonify({
            "game": game_data(game),
            "finished": False
        })

    except Exception as error:

        db.session.rollback()

        print("HIT ERROR:", error)

        return jsonify({
            "error": str(error)
        }), 500


# =====================================================
# STAND
# =====================================================

@api.route("/game/stand", methods=["POST"])
def stand():

    try:

        data = request.get_json(silent=True) or {}

        name = str(
            data.get("name", "")
        ).strip()

        game = active_games.get(name)

        if game is None:

            return jsonify({
                "error": "No active game."
            }), 400

        if game["finished"]:

            return jsonify({
                "error": "Game already finished."
            }), 400

        while hand_score(
            game["dealer"]
        ) < 17:

            game["dealer"].append(
                game["deck"].pop()
            )

        player_score = hand_score(
            game["player"]
        )

        dealer_score = hand_score(
            game["dealer"]
        )

        player = get_player(name)

        if dealer_score > 21:

            result = "Dealer Bust - You win"

            player.coins += (
                game["bet"] * 2
            )

            player.wins += 1

        elif player_score > dealer_score:

            result = "You Win"

            player.coins += (
                game["bet"] * 2
            )

            player.wins += 1

        elif player_score < dealer_score:

            result = "You Lose"

            player.losses += 1

        else:

            result = "Push - Tie"

            player.coins += game["bet"]

        player.games_played += 1

        game["finished"] = True

        db.session.add(
            GameHistory(
                player_name=name,
                bet=game["bet"],
                result=result,
                player_score=player_score,
                dealer_score=dealer_score
            )
        )

        db.session.commit()

        result_game = game_data(
            game,
            hide_dealer=False
        )

        active_games.pop(
            name,
            None
        )

        return jsonify({
            "game": result_game,
            "result": result,
            "finished": True
        })

    except Exception as error:

        db.session.rollback()

        print("STAND ERROR:", error)

        return jsonify({
            "error": str(error)
        }), 500


# =====================================================
# LEADERBOARD
# =====================================================

@api.route("/leaderboard", methods=["GET"])
def leaderboard():

    try:

        players = Player.query.order_by(
            Player.coins.desc()
        ).limit(50).all()

        return jsonify({
            "players": [
                {
                    "name": player.name,
                    "coins": player.coins,
                    "wins": player.wins,
                    "losses": player.losses,
                    "games_played": player.games_played
                }

                for player in players
            ]
        })

    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


# =====================================================
# HISTORY
# =====================================================

@api.route("/history/<name>", methods=["GET"])
def history(name):

    try:

        records = GameHistory.query.filter_by(
            player_name=name
        ).order_by(
            GameHistory.id.desc()
        ).limit(50).all()

        return jsonify({
            "history": [

                {
                    "bet": record.bet,
                    "result": record.result,
                    "player_score": record.player_score,
                    "dealer_score": record.dealer_score,
                    "created_at": (
                        record.created_at.isoformat()
                        if record.created_at
                        else ""
                    )
                }

                for record in records
            ]
        })

    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500