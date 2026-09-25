from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///players.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    coins = db.Column(db.Integer, default=1000)


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/save-player", methods=["POST"])
def save_player():
    data = request.get_json()
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400

    player = Player.query.filter_by(name=name).first()

    if not player:
        player = Player(name=name, coins=1000)
        db.session.add(player)
        db.session.commit()

    return jsonify({
        "name": player.name,
        "coins": player.coins
    })


@app.route("/player/<name>")
def get_player(name):
    player = Player.query.filter_by(name=name).first()

    if not player:
        return jsonify({"error": "Player not found"}), 404

    return jsonify({
        "name": player.name,
        "coins": player.coins
    })


@app.route("/update-coins", methods=["POST"])
def update_coins():
    data = request.get_json()

    name = data.get("name", "").strip()
    coins = data.get("coins")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    if coins is None:
        return jsonify({"error": "Coins are required"}), 400

    player = Player.query.filter_by(name=name).first()

    if not player:
        return jsonify({"error": "Player not found"}), 404

    player.coins = int(coins)
    db.session.commit()

    return jsonify({
        "name": player.name,
        "coins": player.coins
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)