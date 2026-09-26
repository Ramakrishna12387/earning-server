from datetime import datetime
from .database import db


class Player(db.Model):

    __tablename__ = "player"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    coins = db.Column(
        db.Integer,
        default=1100
    )

    wins = db.Column(
        db.Integer,
        default=0
    )

    losses = db.Column(
        db.Integer,
        default=0
    )

    games_played = db.Column(
        db.Integer,
        default=0
    )

    last_bonus = db.Column(
        db.String(20),
        default=""
    )


class GameHistory(db.Model):

    __tablename__ = "game_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    player_name = db.Column(
        db.String(50),
        nullable=False
    )

    bet = db.Column(
        db.Integer,
        default=0
    )

    result = db.Column(
        db.String(30),
        nullable=False
    )

    player_score = db.Column(
        db.Integer,
        default=0
    )

    dealer_score = db.Column(
        db.Integer,
        default=0
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )