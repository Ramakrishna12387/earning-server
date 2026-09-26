from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, date
import random
import os

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///players.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================================================
# DATABASE
# =========================================================

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    coins = db.Column(db.Integer, default=1000)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)
    last_bonus = db.Column(db.String(20), default="")

class GameHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_name = db.Column(db.String(50), nullable=False)
    bet = db.Column(db.Integer, default=0)
    result = db.Column(db.String(20), nullable=False)
    player_score = db.Column(db.Integer, default=0)
    dealer_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# Active games are kept in server memory.
active_games = {}

# =========================================================
# CARD FUNCTIONS
# =========================================================

def new_deck():
    deck = []

    for suit in ["♠", "♥", "♦", "♣"]:
        for rank in [
            "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "J", "Q", "K", "A"
        ]:
            deck.append({
                "rank": rank,
                "suit": suit
            })

    random.shuffle(deck)
    return deck


def card_value(card):
    rank = card["rank"]

    if rank in ["J", "Q", "K"]:
        return 10

    if rank == "A":
        return 11

    return int(rank)


def calculate_score(cards):
    total = 0
    aces = 0

    for card in cards:
        total += card_value(card)

        if card["rank"] == "A":
            aces += 1

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


def is_blackjack(cards):
    return len(cards) == 2 and calculate_score(cards) == 21


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


# =========================================================
# PLAYER LOGIN / CREATE
# =========================================================

@app.route("/api/player", methods=["POST"])
def create_player():

    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()

    if not name:
        return jsonify({
            "success": False,
            "message": "Enter player name"
        }), 400

    if len(name) > 50:
        return jsonify({
            "success": False,
            "message": "Name is too long"
        }), 400

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

    # Daily bonus
    today = date.today().isoformat()

    bonus = False

    if player.last_bonus != today:

        player.coins += 100
        player.last_bonus = today

        db.session.commit()

        bonus = True

    return jsonify({
        "success": True,
        "message": "Welcome!",
        "bonus": bonus,
        "player": {
            "name": player.name,
            "coins": player.coins,
            "wins": player.wins,
            "losses": player.losses,
            "games": player.games_played
        }
    })


# =========================================================
# GET PLAYER
# =========================================================

@app.route("/api/player/<name>")
def get_player(name):

    player = Player.query.filter_by(name=name).first()

    if not player:
        return jsonify({
            "success": False,
            "message": "Player not found"
        }), 404

    return jsonify({
        "success": True,
        "player": {
            "name": player.name,
            "coins": player.coins,
            "wins": player.wins,
            "losses": player.losses,
            "games": player.games_played
        }
    })


# =========================================================
# START GAME
# =========================================================

@app.route("/api/game/start", methods=["POST"])
def start_game():

    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()

    try:
        bet = int(data.get("bet", 0))
    except:
        bet = 0

    allowed_bets = [10, 50, 100, 500]

    if bet not in allowed_bets:
        return jsonify({
            "success": False,
            "message": "Invalid bet"
        }), 400

    player = Player.query.filter_by(name=name).first()

    if not player:
        return jsonify({
            "success": False,
            "message": "Create player first"
        }), 404

    if player.coins < bet:
        return jsonify({
            "success": False,
            "message": "Not enough coins"
        }), 400

    deck = new_deck()

    player_cards = [
        deck.pop(),
        deck.pop()
    ]

    dealer_cards = [
        deck.pop(),
        deck.pop()
    ]

    active_games[name] = {
        "deck": deck,
        "player_cards": player_cards,
        "dealer_cards": dealer_cards,
        "bet": bet
    }

    # Immediate blackjack
    if is_blackjack(player_cards):

        player.coins += int(bet * 1.5)
        player.games_played += 1
        player.wins += 1

        db.session.add(GameHistory(
            player_name=name,
            bet=bet,
            result="blackjack",
            player_score=21,
            dealer_score=calculate_score(dealer_cards)
        ))

        db.session.commit()

        del active_games[name]

        return jsonify({
            "success": True,
            "finished": True,
            "result": "BLACKJACK!",
            "player_cards": player_cards,
            "dealer_cards": dealer_cards,
            "player_score": 21,
            "dealer_score": calculate_score(dealer_cards),
            "coins": player.coins
        })

    return jsonify({
        "success": True,
        "finished": False,
        "player_cards": player_cards,
        "dealer_cards": [
            dealer_cards[0],
            {"rank": "?", "suit": "?"}
        ],
        "player_score": calculate_score(player_cards),
        "dealer_score": "?",
        "coins": player.coins
    })


# =========================================================
# HIT
# =========================================================

@app.route("/api/game/hit", methods=["POST"])
def hit():

    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()

    game = active_games.get(name)

    if not game:
        return jsonify({
            "success": False,
            "message": "No active game"
        }), 400

    game["player_cards"].append(game["deck"].pop())

    score = calculate_score(game["player_cards"])

    if score > 21:

        player = Player.query.filter_by(name=name).first()

        bet = game["bet"]

        player.coins -= bet
        player.games_played += 1
        player.losses += 1

        db.session.add(GameHistory(
            player_name=name,
            bet=bet,
            result="loss",
            player_score=score,
            dealer_score=calculate_score(game["dealer_cards"])
        ))

        db.session.commit()

        del active_games[name]

        return jsonify({
            "success": True,
            "finished": True,
            "result": "BUST! You lose.",
            "player_cards": game["player_cards"],
            "dealer_cards": game["dealer_cards"],
            "player_score": score,
            "dealer_score": calculate_score(game["dealer_cards"]),
            "coins": player.coins
        })

    return jsonify({
        "success": True,
        "finished": False,
        "player_cards": game["player_cards"],
        "dealer_cards": [
            game["dealer_cards"][0],
            {"rank": "?", "suit": "?"}
        ],
        "player_score": score,
        "dealer_score": "?"
    })


# =========================================================
# STAND
# =========================================================

@app.route("/api/game/stand", methods=["POST"])
def stand():

    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()

    game = active_games.get(name)

    if not game:
        return jsonify({
            "success": False,
            "message": "No active game"
        }), 400

    dealer_cards = game["dealer_cards"]

    while calculate_score(dealer_cards) < 17:
        dealer_cards.append(game["deck"].pop())

    player_score = calculate_score(game["player_cards"])
    dealer_score = calculate_score(dealer_cards)

    player = Player.query.filter_by(name=name).first()

    bet = game["bet"]

    result = ""

    if dealer_score > 21:
        result = "win"
        player.coins += bet
        player.wins += 1

    elif player_score > dealer_score:
        result = "win"
        player.coins += bet
        player.wins += 1

    elif player_score < dealer_score:
        result = "loss"
        player.coins -= bet
        player.losses += 1

    else:
        result = "draw"

    player.games_played += 1

    db.session.add(GameHistory(
        player_name=name,
        bet=bet,
        result=result,
        player_score=player_score,
        dealer_score=dealer_score
    ))

    db.session.commit()

    del active_games[name]

    if result == "win":
        message = "🎉 YOU WIN!"
    elif result == "loss":
        message = "😢 YOU LOSE!"
    else:
        message = "🤝 DRAW!"

    return jsonify({
        "success": True,
        "finished": True,
        "result": message,
        "result_type": result,
        "player_cards": game["player_cards"],
        "dealer_cards": dealer_cards,
        "player_score": player_score,
        "dealer_score": dealer_score,
        "coins": player.coins
    })


# =========================================================
# LEADERBOARD
# =========================================================

@app.route("/api/leaderboard")
def leaderboard():

    players = Player.query.order_by(
        Player.coins.desc()
    ).limit(20).all()

    return jsonify([
        {
            "rank": i + 1,
            "name": p.name,
            "coins": p.coins,
            "wins": p.wins,
            "games": p.games_played
        }
        for i, p in enumerate(players)
    ])


# =========================================================
# HISTORY
# =========================================================

@app.route("/api/history/<name>")
def history(name):

    records = GameHistory.query.filter_by(
        player_name=name
    ).order_by(
        GameHistory.id.desc()
    ).limit(30).all()

    return jsonify([
        {
            "bet": r.bet,
            "result": r.result,
            "player_score": r.player_score,
            "dealer_score": r.dealer_score,
            "date": r.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for r in records
    ])


# =========================================================
# ADMIN
# =========================================================

@app.route("/api/admin")
def admin():

    key = request.args.get("key", "")

    admin_key = os.environ.get(
        "ADMIN_KEY",
        "whitejack-admin"
    )

    if key != admin_key:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    players = Player.query.order_by(
        Player.coins.desc()
    ).all()

    return jsonify({
        "success": True,
        "total_players": len(players),
        "total_games": sum(
            p.games_played for p in players
        ),
        "players": [
            {
                "name": p.name,
                "coins": p.coins,
                "wins": p.wins,
                "losses": p.losses,
                "games": p.games_played
            }
            for p in players
        ]
    })


# =========================================================
# FRONTEND
# =========================================================

HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>White Jack</title>

<style>

*{
    box-sizing:border-box;
}

body{
    margin:0;
    font-family:Arial, sans-serif;
    background:
        radial-gradient(circle at top,#173b30,#07110e 60%);
    color:white;
    min-height:100vh;
}

.container{
    width:95%;
    max-width:1100px;
    margin:auto;
    padding:20px;
}

.header{
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:15px;
    flex-wrap:wrap;
}

.logo{
    font-size:32px;
    font-weight:bold;
}

.logo span{
    color:#35e28b;
}

button{
    border:none;
    padding:12px 18px;
    border-radius:12px;
    cursor:pointer;
    font-weight:bold;
    font-size:15px;
}

.primary{
    background:#35e28b;
    color:#06110c;
}

.secondary{
    background:#182b24;
    color:white;
}

.danger{
    background:#d94b4b;
    color:white;
}

input,select{
    width:100%;
    padding:13px;
    border:none;
    border-radius:10px;
    margin-bottom:10px;
    font-size:16px;
}

.card{
    background:rgba(255,255,255,.08);
    border:1px solid rgba(255,255,255,.1);
    border-radius:20px;
    padding:20px;
    margin-top:20px;
    box-shadow:0 10px 30px rgba(0,0,0,.25);
}

.login{
    max-width:450px;
    margin:60px auto;
}

.stats{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:12px;
}

.stat{
    background:#10231c;
    border-radius:15px;
    padding:15px;
    text-align:center;
}

.stat b{
    display:block;
    font-size:25px;
    margin-top:5px;
}

.table{
    width:100%;
    border-collapse:collapse;
}

.table th,
.table td{
    padding:10px;
    border-bottom:1px solid rgba(255,255,255,.1);
    text-align:left;
}

.game{
    text-align:center;
}

.cards{
    display:flex;
    justify-content:center;
    flex-wrap:wrap;
    gap:12px;
    min-height:120px;
}

.playing-card{
    width:75px;
    height:105px;
    background:white;
    color:#111;
    border-radius:12px;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    font-size:27px;
    font-weight:bold;
    box-shadow:0 8px 15px rgba(0,0,0,.3);
}

.red{
    color:#d62f45;
}

.score{
    font-size:20px;
    margin:10px;
}

.actions{
    display:flex;
    justify-content:center;
    flex-wrap:wrap;
    gap:10px;
    margin-top:20px;
}

.message{
    font-size:23px;
    font-weight:bold;
    margin:15px;
}

.tabs{
    display:flex;
    gap:8px;
    flex-wrap:wrap;
    margin-top:20px;
}

.hidden{
    display:none;
}

.small{
    color:#9eb5aa;
    font-size:13px;
}

@media(max-width:700px){

    .stats{
        grid-template-columns:repeat(2,1fr);
    }

    .logo{
        font-size:26px;
    }

    .playing-card{
        width:62px;
        height:90px;
        font-size:22px;
    }

}

</style>

</head>

<body>

<div class="container">

<div class="header">

<div class="logo">
♠ <span>WHITE JACK</span>
</div>

<button class="secondary"
onclick="toggleTheme()">
🌙 Theme
</button>

</div>


<!-- LOGIN -->

<div id="loginBox" class="card login">

<h2>🎰 Welcome to White Jack</h2>

<p class="small">
Virtual coins only.
</p>

<input
id="nameInput"
placeholder="Enter your player name"
maxlength="50"
>

<button
class="primary"
style="width:100%"
onclick="login()">

ENTER GAME

</button>

</div>


<!-- APP -->

<div id="appBox" class="hidden">

<div class="card">

<div class="stats">

<div class="stat">
🪙 Coins
<b id="coins">0</b>
</div>

<div class="stat">
🏆 Wins
<b id="wins">0</b>
</div>

<div class="stat">
💔 Losses
<b id="losses">0</b>
</div>

<div class="stat">
🎮 Games
<b id="games">0</b>
</div>

</div>

</div>


<!-- GAME -->

<div class="card game">

<h2>🃏 Blackjack</h2>

<select id="bet">

<option value="10">Bet 10 Coins</option>
<option value="50">Bet 50 Coins</option>
<option value="100">Bet 100 Coins</option>
<option value="500">Bet 500 Coins</option>

</select>

<h3>Dealer</h3>

<div id="dealerCards" class="cards"></div>

<div class="score">
Score: <span id="dealerScore">?</span>
</div>

<hr>

<h3>You</h3>

<div id="playerCards" class="cards"></div>

<div class="score">
Score: <span id="playerScore">0</span>
</div>

<div id="message" class="message"></div>

<div class="actions">

<button
id="startBtn"
class="primary"
onclick="startGame()">

🎰 DEAL

</button>

<button
id="hitBtn"
class="secondary hidden"
onclick="hit()">

✋ HIT

</button>

<button
id="standBtn"
class="danger hidden"
onclick="stand()">

🛑 STAND

</button>

</div>

</div>


<!-- NAV -->

<div class="tabs">

<button class="secondary"
onclick="showSection('profile')">

👤 Profile

</button>

<button class="secondary"
onclick="showSection('leaderboard')">

🏆 Leaderboard

</button>

<button class="secondary"
onclick="showSection('history')">

📜 History

</button>

<button class="secondary"
onclick="logout()">

🚪 Logout

</button>

</div>


<!-- PROFILE -->

<div id="profile" class="card">

<h2>👤 Profile</h2>

<p>Name: <b id="profileName"></b></p>
<p>Coins: <b id="profileCoins"></b></p>
<p>Games: <b id="profileGames"></b></p>
<p>Wins: <b id="profileWins"></b></p>
<p>Losses: <b id="profileLosses"></b></p>

<p class="small">
🎁 Daily bonus: 100 virtual coins
</p>

</div>


<!-- LEADERBOARD -->

<div id="leaderboard" class="card hidden">

<h2>🏆 Leaderboard</h2>

<table class="table">

<thead>

<tr>
<th>#</th>
<th>Player</th>
<th>Coins</th>
<th>Wins</th>
</tr>

</thead>

<tbody id="leaderboardBody"></tbody>

</table>

</div>


<!-- HISTORY -->

<div id="history" class="card hidden">

<h2>📜 Game History</h2>

<table class="table">

<thead>

<tr>
<th>Result</th>
<th>Bet</th>
<th>You</th>
<th>Dealer</th>
<th>Date</th>
</tr>

</thead>

<tbody id="historyBody"></tbody>

</table>

</div>


</div>

</div>


<script>

let currentPlayer = "";
let gameActive = false;


// =====================================================
// LOGIN
// =====================================================

async function login(){

    const name =
        document.getElementById("nameInput")
        .value.trim();

    if(!name){

        alert("Enter player name");
        return;
    }

    const response =
        await fetch("/api/player",{

            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:JSON.stringify({
                name:name
            })

        });

    const data = await response.json();

    if(!data.success){

        alert(data.message);
        return;
    }

    currentPlayer = name;

    localStorage.setItem(
        "whitejack_player",
        name
    );

    document.getElementById("loginBox")
        .classList.add("hidden");

    document.getElementById("appBox")
        .classList.remove("hidden");

    if(data.bonus){

        alert(
            "🎁 Daily Bonus!\n\n100 virtual coins added!"
        );

    }

    updateStats(data.player);

    loadLeaderboard();

    loadHistory();

}


// =====================================================
// STATS
// =====================================================

function updateStats(player){

    document.getElementById("coins")
        .innerText = player.coins;

    document.getElementById("wins")
        .innerText = player.wins;

    document.getElementById("losses")
        .innerText = player.losses;

    document.getElementById("games")
        .innerText = player.games;

    document.getElementById("profileName")
        .innerText = player.name;

    document.getElementById("profileCoins")
        .innerText = player.coins;

    document.getElementById("profileGames")
        .innerText = player.games;

    document.getElementById("profileWins")
        .innerText = player.wins;

    document.getElementById("profileLosses")
        .innerText = player.losses;

}


// =====================================================
// REFRESH PLAYER
// =====================================================

async function refreshPlayer(){

    const response =
        await fetch(
            "/api/player/" +
            encodeURIComponent(currentPlayer)
        );

    const data = await response.json();

    if(data.success){

        updateStats(data.player);

    }

}


// =====================================================
// START GAME
// =====================================================

async function startGame(){

    const bet =
        Number(
            document.getElementById("bet").value
        );

    const response =
        await fetch("/api/game/start",{

            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:JSON.stringify({

                name:currentPlayer,
                bet:bet

            })

        });

    const data = await response.json();

    if(!data.success){

        alert(data.message);
        return;
    }

    gameActive = !data.finished;

    renderCards(
        "playerCards",
        data.player_cards
    );

    renderCards(
        "dealerCards",
        data.dealer_cards
    );

    document.getElementById("playerScore")
        .innerText = data.player_score;

    document.getElementById("dealerScore")
        .innerText = data.dealer_score;

    document.getElementById("message")
        .innerText = data.result || "";

    if(data.finished){

        finishGameUI();

        refreshPlayer();
        loadLeaderboard();
        loadHistory();

    }else{

        document.getElementById("startBtn")
            .classList.add("hidden");

        document.getElementById("hitBtn")
            .classList.remove("hidden");

        document.getElementById("standBtn")
            .classList.remove("hidden");

    }

}


// =====================================================
// HIT
// =====================================================

async function hit(){

    const response =
        await fetch("/api/game/hit",{

            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:JSON.stringify({
                name:currentPlayer
            })

        });

    const data = await response.json();

    if(!data.success){

        alert(data.message);
        return;
    }

    renderCards(
        "playerCards",
        data.player_cards
    );

    renderCards(
        "dealerCards",
        data.dealer_cards
    );

    document.getElementById("playerScore")
        .innerText = data.player_score;

    document.getElementById("dealerScore")
        .innerText = data.dealer_score;

    document.getElementById("message")
        .innerText = data.result || "";

    if(data.finished){

        finishGameUI();

        refreshPlayer();
        loadLeaderboard();
        loadHistory();

    }

}


// =====================================================
// STAND
// =====================================================

async function stand(){

    const response =
        await fetch("/api/game/stand",{

            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:JSON.stringify({
                name:currentPlayer
            })

        });

    const data = await response.json();

    if(!data.success){

        alert(data.message);
        return;
    }

    renderCards(
        "playerCards",
        data.player_cards
    );

    renderCards(
        "dealerCards",
        data.dealer_cards
    );

    document.getElementById("playerScore")
        .innerText = data.player_score;

    document.getElementById("dealerScore")
        .innerText = data.dealer_score;

    document.getElementById("message")
        .innerText = data.result;

    finishGameUI();

    refreshPlayer();
    loadLeaderboard();
    loadHistory();

}


// =====================================================
// FINISH UI
// =====================================================

function finishGameUI(){

    gameActive = false;

    document.getElementById("startBtn")
        .classList.remove("hidden");

    document.getElementById("hitBtn")
        .classList.add("hidden");

    document.getElementById("standBtn")
        .classList.add("hidden");

}


// =====================================================
// CARD DISPLAY
// =====================================================

function renderCards(elementId,cards){

    const container =
        document.getElementById(elementId);

    container.innerHTML = "";

    cards.forEach(card => {

        const div =
            document.createElement("div");

        div.className = "playing-card";

        if(
            card.suit === "♥" ||
            card.suit === "♦"
        ){

            div.classList.add("red");

        }

        if(card.rank === "?"){

            div.innerHTML = "🂠";

        }else{

            div.innerHTML =
                card.rank +
                "<br>" +
                card.suit;

        }

        container.appendChild(div);

    });

}


// =====================================================
// LEADERBOARD
// =====================================================

async function loadLeaderboard(){

    const response =
        await fetch("/api/leaderboard");

    const data =
        await response.json();

    const body =
        document.getElementById(
            "leaderboardBody"
        );

    body.innerHTML = "";

    data.forEach(player => {

        body.innerHTML += `

        <tr>

        <td>${player.rank}</td>

        <td>${escapeHtml(player.name)}</td>

        <td>🪙 ${player.coins}</td>

        <td>${player.wins}</td>

        </tr>

        `;

    });

}


// =====================================================
// HISTORY
// =====================================================

async function loadHistory(){

    if(!currentPlayer) return;

    const response =
        await fetch(
            "/api/history/" +
            encodeURIComponent(currentPlayer)
        );

    const data =
        await response.json();

    const body =
        document.getElementById(
            "historyBody"
        );

    body.innerHTML = "";

    data.forEach(item => {

        let result = item.result;

        if(result === "win"){
            result = "🎉 Win";
        }

        if(result === "loss"){
            result = "❌ Loss";
        }

        if(result === "draw"){
            result = "🤝 Draw";
        }

        if(result === "blackjack"){
            result = "🃏 Blackjack";
        }

        body.innerHTML += `

        <tr>

        <td>${result}</td>

        <td>${item.bet}</td>

        <td>${item.player_score}</td>

        <td>${item.dealer_score}</td>

        <td>${item.date}</td>

        </tr>

        `;

    });

}


// =====================================================
// SECTIONS
// =====================================================

function showSection(section){

    [
        "profile",
        "leaderboard",
        "history"
    ].forEach(id => {

        document.getElementById(id)
            .classList.add("hidden");

    });

    document.getElementById(section)
        .classList.remove("hidden");

    if(section === "leaderboard"){
        loadLeaderboard();
    }

    if(section === "history"){
        loadHistory();
    }

}


// =====================================================
// LOGOUT
// =====================================================

function logout(){

    localStorage.removeItem(
        "whitejack_player"
    );

    location.reload();

}


// =====================================================
// THEME
// =====================================================

function toggleTheme(){

    const body =
        document.body;

    if(
        body.style.background === "white"
    ){

        body.style.background =
            "radial-gradient(circle at top,#173b30,#07110e 60%)";

        body.style.color =
            "white";

    }else{

        body.style.background =
            "white";

        body.style.color =
            "#111";

    }

}


// =====================================================
// SECURITY
// =====================================================

function escapeHtml(text){

    const div =
        document.createElement("div");

    div.innerText = text;

    return div.innerHTML;

}


// =====================================================
// AUTO LOGIN
// =====================================================

window.addEventListener(
    "load",
    async () => {

        const saved =
            localStorage.getItem(
                "whitejack_player"
            );

        if(saved){

            document.getElementById(
                "nameInput"
            ).value = saved;

            await login();

        }

    }
);

</script>

</body>

</html>
"""


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )