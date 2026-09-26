from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, date
import random
import os

# =========================================================
# WHITE JACK - COMPLETE APP
# =========================================================

app = Flask(__name__)
CORS(app)

# =========================================================
# DATABASE
# =========================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

DATABASE_FILE = os.path.join(INSTANCE_DIR, "players.db")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DATABASE_FILE
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================================================
# MODELS
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
    result = db.Column(db.String(30), nullable=False)
    player_score = db.Column(db.Integer, default=0)
    dealer_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


# =========================================================
# GAME
# =========================================================

active_games = {}

VALID_BETS = [10, 50, 100, 500]


def new_deck():
    suits = ["♠", "♥", "♦", "♣"]
    ranks = [
        "2", "3", "4", "5", "6", "7", "8",
        "9", "10", "J", "Q", "K", "A"
    ]

    deck = []

    for suit in suits:
        for rank in ranks:
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
    score = 0
    aces = 0

    for card in cards:
        score += card_value(card)

        if card["rank"] == "A":
            aces += 1

    while score > 21 and aces > 0:
        score -= 10
        aces -= 1

    return score


def is_blackjack(cards):
    return len(cards) == 2 and calculate_score(cards) == 21


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

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;
    font-family: Arial, sans-serif;
    color: white;
    background:
        radial-gradient(
            circle at top,
            #123c30,
            #06130f 55%,
            #020706
        );
}

.container {
    width: 94%;
    max-width: 1200px;
    margin: auto;
    padding: 25px 0 50px;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 25px;
}

.logo {
    font-size: 38px;
    font-weight: 900;
    color: #35e58c;
    letter-spacing: 2px;
}

.card-box {
    background: rgba(25, 47, 41, 0.95);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 22px;
    padding: 25px;
    margin-bottom: 20px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.25);
}

input,
select {
    width: 100%;
    padding: 15px;
    border: none;
    border-radius: 12px;
    margin-bottom: 12px;
    font-size: 16px;
}

button {
    border: none;
    cursor: pointer;
    font-weight: 900;
}

.primary {
    width: 100%;
    padding: 16px;
    border-radius: 12px;
    background: #35e58c;
    color: #04110b;
    font-size: 17px;
}

.primary:hover {
    background: #55f0a0;
}

.primary:disabled {
    opacity: 0.6;
    cursor: wait;
}

.theme-btn {
    padding: 12px 18px;
    border-radius: 12px;
    background: #17352c;
    color: white;
}

.hidden {
    display: none !important;
}

.stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

.stat {
    background: rgba(0,0,0,0.2);
    padding: 18px;
    border-radius: 15px;
    text-align: center;
}

.stat-title {
    opacity: 0.7;
    font-size: 13px;
}

.stat-value {
    font-size: 25px;
    font-weight: 900;
    color: #35e58c;
    margin-top: 7px;
}

.game-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.cards {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    min-height: 100px;
}

.playing-card {
    width: 70px;
    height: 95px;
    background: white;
    color: #111;
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    font-weight: 900;
    font-size: 23px;
}

.red-card {
    color: #d72626;
}

.hidden-card {
    background: #183d32;
    color: #35e58c;
    border: 2px solid #35e58c;
}

.game-buttons {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 20px;
}

.game-buttons button {
    flex: 1;
    min-width: 120px;
    padding: 14px;
    border-radius: 12px;
}

.deal {
    background: #35e58c;
    color: #04110b;
}

.hit {
    background: #2d7dd2;
    color: white;
}

.stand {
    background: #e09b35;
    color: #111;
}

.result {
    margin-top: 20px;
    padding: 16px;
    border-radius: 12px;
    background: rgba(53,229,140,0.12);
    border: 1px solid rgba(53,229,140,0.3);
    font-size: 18px;
}

.notice {
    padding: 13px;
    border-radius: 12px;
    background: rgba(53,229,140,0.1);
    margin-bottom: 15px;
}

.profile-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
}

.table {
    width: 100%;
    border-collapse: collapse;
}

.table th,
.table td {
    padding: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    text-align: left;
}

.history-item {
    padding: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

.danger {
    width: 100%;
    margin-top: 15px;
    padding: 13px;
    border-radius: 10px;
    background: #a93d3d;
    color: white;
}

.small {
    font-size: 13px;
    opacity: 0.75;
}

hr {
    border: 0;
    border-top: 1px solid rgba(255,255,255,0.15);
    margin: 25px 0;
}

@media (max-width: 800px) {

    .game-layout {
        grid-template-columns: 1fr;
    }

    .stats {
        grid-template-columns: repeat(2, 1fr);
    }

    .profile-grid {
        grid-template-columns: 1fr;
    }

    .logo {
        font-size: 28px;
    }
}

@media (max-width: 500px) {

    .container {
        width: 96%;
        padding-top: 15px;
    }

    .card-box {
        padding: 17px;
    }

    .playing-card {
        width: 58px;
        height: 80px;
        font-size: 19px;
    }
}

</style>

</head>

<body>

<div class="container">

<header>

<div class="logo">
WHITE JACK
</div>

<button
    id="themeBtn"
    class="theme-btn"
    type="button">
🌙 Theme
</button>

</header>


<!-- LOGIN -->

<section
    id="loginSection"
    class="card-box">

<h1>Welcome to White Jack</h1>

<p>
Virtual coins only. No real-money betting.
</p>

<input
    id="usernameInput"
    type="text"
    maxlength="50"
    placeholder="Enter your player name">

<button
    id="loginBtn"
    class="primary"
    type="button">
ENTER GAME
</button>

<p
    id="loginMessage"
    class="small">
</p>

</section>


<!-- GAME -->

<section
    id="gameSection"
    class="hidden">

<div class="notice">
🎁 Daily Bonus:
<b>100 virtual coins</b>
once per day.
</div>


<div class="card-box">

<div class="stats">

<div class="stat">
<div class="stat-title">COINS</div>
<div
    id="coins"
    class="stat-value">
0
</div>
</div>

<div class="stat">
<div class="stat-title">WINS</div>
<div
    id="wins"
    class="stat-value">
0
</div>
</div>

<div class="stat">
<div class="stat-title">LOSSES</div>
<div
    id="losses"
    class="stat-value">
0
</div>
</div>

<div class="stat">
<div class="stat-title">GAMES</div>
<div
    id="games"
    class="stat-value">
0
</div>
</div>

</div>

</div>


<div class="game-layout">


<!-- GAME TABLE -->

<div class="card-box">

<h2>🎰 Blackjack Table</h2>

<label>Bet Coins</label>

<select id="betSelect">

<option value="10">10 Coins</option>
<option value="50">50 Coins</option>
<option value="100">100 Coins</option>
<option value="500">500 Coins</option>

</select>


<h3>Dealer</h3>

<div
    id="dealerCards"
    class="cards">
</div>

<p>
Dealer Score:
<b id="dealerScore">?</b>
</p>


<hr>


<h3>Player</h3>

<div
    id="playerCards"
    class="cards">
</div>

<p>
Player Score:
<b id="playerScore">0</b>
</p>


<div class="game-buttons">

<button
    id="dealBtn"
    class="deal"
    type="button">
DEAL
</button>

<button
    id="hitBtn"
    class="hit"
    type="button"
    disabled>
HIT
</button>

<button
    id="standBtn"
    class="stand"
    type="button"
    disabled>
STAND
</button>

</div>


<div
    id="resultBox"
    class="result hidden">
</div>

</div>


<!-- PROFILE -->

<div class="card-box">

<h2>👤 Profile</h2>

<div class="profile-grid">

<div>
<b>Username</b>
<p id="profileName">-</p>
</div>

<div>
<b>Win Rate</b>
<p id="winRate">0%</p>
</div>

<div>
<b>Rank</b>
<p id="rank">-</p>
</div>

</div>


<h2>🏆 Leaderboard</h2>

<div id="leaderboard">
Loading...
</div>


<button
    id="logoutBtn"
    class="danger"
    type="button">
LOGOUT
</button>

</div>

</div>


<!-- HISTORY -->

<div class="card-box">

<h2>📜 Game History</h2>

<div id="history">
No games yet.
</div>

</div>

</section>

</div>


<script>

"use strict";


// ========================================================
// VARIABLES
// ========================================================

let currentPlayer =
    localStorage.getItem("whiteJackPlayer");

let gameActive = false;


// ========================================================
// DOM
// ========================================================

const loginSection =
    document.getElementById("loginSection");

const gameSection =
    document.getElementById("gameSection");

const usernameInput =
    document.getElementById("usernameInput");

const loginBtn =
    document.getElementById("loginBtn");

const loginMessage =
    document.getElementById("loginMessage");

const coinsEl =
    document.getElementById("coins");

const winsEl =
    document.getElementById("wins");

const lossesEl =
    document.getElementById("losses");

const gamesEl =
    document.getElementById("games");

const profileName =
    document.getElementById("profileName");

const winRate =
    document.getElementById("winRate");

const rankEl =
    document.getElementById("rank");

const betSelect =
    document.getElementById("betSelect");

const dealBtn =
    document.getElementById("dealBtn");

const hitBtn =
    document.getElementById("hitBtn");

const standBtn =
    document.getElementById("standBtn");

const dealerCardsEl =
    document.getElementById("dealerCards");

const playerCardsEl =
    document.getElementById("playerCards");

const dealerScoreEl =
    document.getElementById("dealerScore");

const playerScoreEl =
    document.getElementById("playerScore");

const resultBox =
    document.getElementById("resultBox");

const leaderboardEl =
    document.getElementById("leaderboard");

const historyEl =
    document.getElementById("history");

const logoutBtn =
    document.getElementById("logoutBtn");

const themeBtn =
    document.getElementById("themeBtn");


// ========================================================
// API FUNCTION
// ========================================================

async function api(url, options = {}) {

    try {

        const response = await fetch(
            url,
            {
                ...options,
                headers: {
                    "Content-Type":
                        "application/json",
                    ...(options.headers || {})
                }
            }
        );

        const text = await response.text();

        let data = {};

        try {
            data = text ? JSON.parse(text) : {};
        } catch (e) {
            throw new Error(
                "Server returned invalid response."
            );
        }

        if (!response.ok) {

            throw new Error(
                data.error || "Server error."
            );
        }

        return data;

    } catch (error) {

        console.error(
            "API ERROR:",
            error
        );

        throw error;
    }
}


// ========================================================
// LOGIN
// ========================================================

async function login() {

    const name =
        usernameInput.value.trim();

    loginMessage.textContent = "";

    if (!name) {

        loginMessage.textContent =
            "Please enter your player name.";

        usernameInput.focus();

        return;
    }

    loginBtn.disabled = true;

    loginBtn.textContent =
        "CONNECTING...";

    try {

        const data = await api(
            "/api/player",
            {
                method: "POST",

                body: JSON.stringify({
                    name: name
                })
            }
        );

        currentPlayer =
            data.player.name;

        localStorage.setItem(
            "whiteJackPlayer",
            currentPlayer
        );

        showGame();

        await refreshAll();

    } catch (error) {

        loginMessage.textContent =
            error.message ||
            "Unable to connect to server.";

    } finally {

        loginBtn.disabled = false;

        loginBtn.textContent =
            "ENTER GAME";
    }
}


// ========================================================
// SHOW GAME
// ========================================================

function showGame() {

    loginSection.classList.add(
        "hidden"
    );

    gameSection.classList.remove(
        "hidden"
    );
}


// ========================================================
// LOGOUT
// ========================================================

function logout() {

    localStorage.removeItem(
        "whiteJackPlayer"
    );

    currentPlayer = null;

    gameActive = false;

    location.reload();
}


// ========================================================
// DEAL
// ========================================================

async function deal() {

    if (!currentPlayer) {

        showResult(
            "ERROR",
            "Please enter your name first."
        );

        return;
    }

    const bet =
        Number(betSelect.value);

    dealBtn.disabled = true;

    try {

        const data = await api(
            "/api/game/start",
            {
                method: "POST",

                body: JSON.stringify({
                    name: currentPlayer,
                    bet: bet
                })
            }
        );

        renderCards(
            dealerCardsEl,
            data.dealer_cards,
            !data.game_over
        );

        renderCards(
            playerCardsEl,
            data.player_cards,
            false
        );

        dealerScoreEl.textContent =
            data.dealer_score ?? "?";

        playerScoreEl.textContent =
            data.player_score;

        resultBox.classList.add(
            "hidden"
        );

        if (data.game_over) {

            gameActive = false;

            hitBtn.disabled = true;

            standBtn.disabled = true;

            showResult(
                data.result,
                data.message
            );

            await refreshAll();

        } else {

            gameActive = true;

            hitBtn.disabled = false;

            standBtn.disabled = false;
        }

    } catch (error) {

        showResult(
            "ERROR",
            error.message
        );

    } finally {

        dealBtn.disabled = false;
    }
}


// ========================================================
// HIT
// ========================================================

async function hit() {

    if (!gameActive) {
        return;
    }

    hitBtn.disabled = true;

    try {

        const data = await api(
            "/api/game/hit",
            {
                method: "POST",

                body: JSON.stringify({
                    name: currentPlayer
                })
            }
        );

        renderCards(
            dealerCardsEl,
            data.dealer_cards,
            !data.game_over
        );

        renderCards(
            playerCardsEl,
            data.player_cards,
            false
        );

        dealerScoreEl.textContent =
            data.dealer_score ?? "?";

        playerScoreEl.textContent =
            data.player_score;

        if (data.game_over) {

            gameActive = false;

            standBtn.disabled = true;

            showResult(
                data.result,
                data.message
            );

            await refreshAll();

        } else {

            hitBtn.disabled = false;
        }

    } catch (error) {

        showResult(
            "ERROR",
            error.message
        );

        hitBtn.disabled = false;
    }
}


// ========================================================
// STAND
// ========================================================

async function stand() {

    if (!gameActive) {
        return;
    }

    hitBtn.disabled = true;
    standBtn.disabled = true;

    try {

        const data = await api(
            "/api/game/stand",
            {
                method: "POST",

                body: JSON.stringify({
                    name: currentPlayer
                })
            }
        );

        renderCards(
            dealerCardsEl,
            data.dealer_cards,
            false
        );

        renderCards(
            playerCardsEl,
            data.player_cards,
            false
        );

        dealerScoreEl.textContent =
            data.dealer_score;

        playerScoreEl.textContent =
            data.player_score;

        gameActive = false;

        showResult(
            data.result,
            data.message
        );

        await refreshAll();

    } catch (error) {

        showResult(
            "ERROR",
            error.message
        );

        hitBtn.disabled = true;
        standBtn.disabled = true;
    }
}


// ========================================================
// CARD RENDER
// ========================================================

function renderCards(
    container,
    cards,
    hideSecond
) {

    container.innerHTML = "";

    if (!cards) {
        return;
    }

    cards.forEach(
        function(card, index) {

            const div =
                document.createElement("div");

            div.className =
                "playing-card";

            if (
                card.suit === "♥" ||
                card.suit === "♦"
            ) {

                div.classList.add(
                    "red-card"
                );
            }

            if (
                hideSecond &&
                index === 1
            ) {

                div.classList.add(
                    "hidden-card"
                );

                div.textContent = "🂠";

            } else {

                div.innerHTML =
                    "<div>" +
                    escapeHtml(card.rank) +
                    "</div>" +

                    "<div>" +
                    escapeHtml(card.suit) +
                    "</div>";
            }

            container.appendChild(div);
        }
    );
}


// ========================================================
// RESULT
// ========================================================

function showResult(
    result,
    message
) {

    resultBox.classList.remove(
        "hidden"
    );

    resultBox.innerHTML =
        "<strong>" +
        escapeHtml(result) +
        "</strong><br>" +
        escapeHtml(message);
}


// ========================================================
// PLAYER
// ========================================================

async function loadPlayer() {

    if (!currentPlayer) {
        return;
    }

    const data = await api(
        "/api/player/" +
        encodeURIComponent(currentPlayer)
    );

    coinsEl.textContent =
        data.coins;

    winsEl.textContent =
        data.wins;

    lossesEl.textContent =
        data.losses;

    gamesEl.textContent =
        data.games_played;

    profileName.textContent =
        data.name;

    let rate = 0;

    if (data.games_played > 0) {

        rate =
            data.wins /
            data.games_played *
            100;
    }

    winRate.textContent =
        rate.toFixed(1) + "%";
}


// ========================================================
// LEADERBOARD
// ========================================================

async function loadLeaderboard() {

    const data = await api(
        "/api/leaderboard"
    );

    if (
        !data.players ||
        data.players.length === 0
    ) {

        leaderboardEl.innerHTML =
            "No players yet.";

        rankEl.textContent = "-";

        return;
    }

    let html =
        "<table class='table'>" +
        "<tr>" +
        "<th>#</th>" +
        "<th>Player</th>" +
        "<th>Coins</th>" +
        "<th>Wins</th>" +
        "</tr>";

    data.players.forEach(
        function(player, index) {

            html +=
                "<tr>" +
                "<td>" +
                (index + 1) +
                "</td>" +
                "<td>" +
                escapeHtml(player.name) +
                "</td>" +
                "<td>" +
                player.coins +
                "</td>" +
                "<td>" +
                player.wins +
                "</td>" +
                "</tr>";
        }
    );

    html += "</table>";

    leaderboardEl.innerHTML =
        html;

    const myRank =
        data.players.findIndex(
            function(player) {
                return player.name ===
                    currentPlayer;
            }
        );

    if (myRank >= 0) {

        rankEl.textContent =
            "#" + (myRank + 1);

    } else {

        rankEl.textContent =
            "Not in Top 20";
    }
}


// ========================================================
// HISTORY
// ========================================================

async function loadHistory() {

    if (!currentPlayer) {
        return;
    }

    const data = await api(
        "/api/history/" +
        encodeURIComponent(currentPlayer)
    );

    if (
        !data.history ||
        data.history.length === 0
    ) {

        historyEl.innerHTML =
            "No games played yet.";

        return;
    }

    let html = "";

    data.history.forEach(
        function(item) {

            html +=
                "<div class='history-item'>" +

                "<b>" +
                escapeHtml(item.result) +
                "</b>" +

                " — Bet: " +
                item.bet +

                " | Player: " +
                item.player_score +

                " | Dealer: " +
                item.dealer_score +

                "<br>" +

                "<span class='small'>" +
                escapeHtml(
                    item.created_at
                ) +
                "</span>" +

                "</div>";
        }
    );

    historyEl.innerHTML =
        html;
}


// ========================================================
// REFRESH
// ========================================================

async function refreshAll() {

    try {

        await Promise.all([
            loadPlayer(),
            loadLeaderboard(),
            loadHistory()
        ]);

    } catch (error) {

        console.error(
            "Refresh error:",
            error
        );
    }
}


// ========================================================
// ESCAPE HTML
// ========================================================

function escapeHtml(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value == null ? "" : value;

    return div.innerHTML;
}


// ========================================================
// THEME
// ========================================================

function toggleTheme() {

    document.body.classList.toggle(
        "light"
    );

    const light =
        document.body.classList.contains(
            "light"
        );

    localStorage.setItem(
        "whiteJackTheme",
        light ? "light" : "dark"
    );

    themeBtn.textContent =
        light ? "☀️ Theme" : "🌙 Theme";
}


// ========================================================
// BUTTONS
// ========================================================

loginBtn.onclick = function() {
    login();
};

dealBtn.onclick = function() {
    deal();
};

hitBtn.onclick = function() {
    hit();
};

standBtn.onclick = function() {
    stand();
};

logoutBtn.onclick = function() {
    logout();
};

themeBtn.onclick = function() {
    toggleTheme();
};


// ========================================================
// ENTER KEY
// ========================================================

usernameInput.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            login();
        }
    }
);


// ========================================================
// START
// ========================================================

const savedTheme =
    localStorage.getItem(
        "whiteJackTheme"
    );

if (savedTheme === "light") {

    document.body.classList.add(
        "light"
    );

    themeBtn.textContent =
        "☀️ Theme";
}


if (currentPlayer) {

    showGame();

    refreshAll();
}

</script>

</body>
</html>
"""


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


# =========================================================
# HEALTH
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "app": "White Jack",
        "message": "Server is running"
    })


# =========================================================
# CREATE / LOGIN PLAYER
# =========================================================

@app.route("/api/player", methods=["POST"])
def create_player():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    if not name:

        return jsonify({
            "error":
                "Player name is required."
        }), 400

    if len(name) > 50:

        return jsonify({
            "error":
                "Player name is too long."
        }), 400

    player = Player.query.filter_by(
        name=name
    ).first()

    created = False
    bonus = 0

    if not player:

        player = Player(
            name=name,
            coins=1000,
            wins=0,
            losses=0,
            games_played=0,
            last_bonus=""
        )

        db.session.add(player)

        created = True

    today = date.today().isoformat()

    if player.last_bonus != today:

        player.coins += 100
        player.last_bonus = today
        bonus = 100

    db.session.commit()

    return jsonify({

        "message":
            "Player ready.",

        "created":
            created,

        "bonus":
            bonus,

        "player": {

            "name":
                player.name,

            "coins":
                player.coins,

            "wins":
                player.wins,

            "losses":
                player.losses,

            "games_played":
                player.games_played
        }
    })


# =========================================================
# PLAYER PROFILE
# =========================================================

@app.route("/api/player/<name>", methods=["GET"])
def get_player(name):

    player = Player.query.filter_by(
        name=name
    ).first()

    if not player:

        return jsonify({
            "error":
                "Player not found."
        }), 404

    return jsonify({

        "name":
            player.name,

        "coins":
            player.coins,

        "wins":
            player.wins,

        "losses":
            player.losses,

        "games_played":
            player.games_played
    })


# =========================================================
# START GAME
# =========================================================

@app.route("/api/game/start", methods=["POST"])
def start_game():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    try:
        bet = int(
            data.get("bet", 0)
        )
    except (TypeError, ValueError):
        bet = 0

    if bet not in VALID_BETS:

        return jsonify({
            "error":
                "Invalid bet."
        }), 400

    player = Player.query.filter_by(
        name=name
    ).first()

    if not player:

        return jsonify({
            "error":
                "Player not found."
        }), 404

    if player.coins < bet:

        return jsonify({
            "error":
                "Not enough coins."
        }), 400

    if name in active_games:

        return jsonify({
            "error":
                "You already have an active game."
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

    player.coins -= bet

    player_score = calculate_score(
        player_cards
    )

    dealer_score = calculate_score(
        dealer_cards
    )

    active_games[name] = {
        "deck": deck,
        "player_cards": player_cards,
        "dealer_cards": dealer_cards,
        "bet": bet
    }

    # Blackjack
    if is_blackjack(player_cards):

        payout = bet + int(
            bet * 1.5
        )

        player.coins += payout
        player.wins += 1
        player.games_played += 1

        history = GameHistory(
            player_name=name,
            bet=bet,
            result="BLACKJACK",
            player_score=player_score,
            dealer_score=dealer_score
        )

        db.session.add(history)
        db.session.commit()

        del active_games[name]

        return jsonify({

            "game_over": True,

            "result": "BLACKJACK",

            "message":
                "Blackjack! You won.",

            "player_cards":
                player_cards,

            "dealer_cards":
                dealer_cards,

            "player_score":
                player_score,

            "dealer_score":
                dealer_score
        })

    db.session.commit()

    return jsonify({

        "game_over": False,

        "player_cards":
            player_cards,

        "dealer_cards":
            dealer_cards,

        "player_score":
            player_score,

        "dealer_score":
            None,

        "message":
            "Game started."
    })


# =========================================================
# HIT
# =========================================================

@app.route("/api/game/hit", methods=["POST"])
def hit_game():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    game = active_games.get(name)

    if not game:

        return jsonify({
            "error":
                "No active game."
        }), 400

    player = Player.query.filter_by(
        name=name
    ).first()

    if not player:

        return jsonify({
            "error":
                "Player not found."
        }), 404

    card = game["deck"].pop()

    game["player_cards"].append(card)

    player_score = calculate_score(
        game["player_cards"]
    )

    if player_score > 21:

        bet = game["bet"]

        dealer_score = calculate_score(
            game["dealer_cards"]
        )

        player.losses += 1
        player.games_played += 1

        history = GameHistory(
            player_name=name,
            bet=bet,
            result="LOSS - BUST",
            player_score=player_score,
            dealer_score=dealer_score
        )

        db.session.add(history)
        db.session.commit()

        player_cards = game["player_cards"]
        dealer_cards = game["dealer_cards"]

        del active_games[name]

        return jsonify({

            "game_over": True,

            "result": "BUST",

            "message":
                "You busted.",

            "player_cards":
                player_cards,

            "dealer_cards":
                dealer_cards,

            "player_score":
                player_score,

            "dealer_score":
                dealer_score
        })

    db.session.commit()

    return jsonify({

        "game_over": False,

        "result": "CONTINUE",

        "message":
            "Hit again or stand.",

        "player_cards":
            game["player_cards"],

        "dealer_cards": [
            game["dealer_cards"][0]
        ],

        "player_score":
            player_score,

        "dealer_score":
            None
    })


# =========================================================
# STAND
# =========================================================

@app.route("/api/game/stand", methods=["POST"])
def stand_game():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    game = active_games.get(name)

    if not game:

        return jsonify({
            "error":
                "No active game."
        }), 400

    player = Player.query.filter_by(
        name=name
    ).first()

    if not player:

        return jsonify({
            "error":
                "Player not found."
        }), 404

    while calculate_score(
        game["dealer_cards"]
    ) < 17:

        game["dealer_cards"].append(
            game["deck"].pop()
        )

    player_score = calculate_score(
        game["player_cards"]
    )

    dealer_score = calculate_score(
        game["dealer_cards"]
    )

    bet = game["bet"]

    if dealer_score > 21:

        result = "WIN"

        message = "Dealer busted. You won."

        player.wins += 1
        player.coins += bet * 2

    elif player_score > dealer_score:

        result = "WIN"

        message = "You won."

        player.wins += 1
        player.coins += bet * 2

    elif player_score < dealer_score:

        result = "LOSS"

        message = "You lost."

        player.losses += 1

    else:

        result = "DRAW"

        message = "Draw. Bet returned."

        player.coins += bet

    player.games_played += 1

    history = GameHistory(
        player_name=name,
        bet=bet,
        result=result,
        player_score=player_score,
        dealer_score=dealer_score
    )

    db.session.add(history)
    db.session.commit()

    player_cards = game["player_cards"]
    dealer_cards = game["dealer_cards"]

    del active_games[name]

    return jsonify({

        "game_over": True,

        "result": result,

        "message": message,

        "player_cards":
            player_cards,

        "dealer_cards":
            dealer_cards,

        "player_score":
            player_score,

        "dealer_score":
            dealer_score
    })


# =========================================================
# LEADERBOARD
# =========================================================

@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():

    players = Player.query.order_by(
        Player.coins.desc()
    ).limit(20).all()

    return jsonify({

        "players": [

            {
                "name": player.name,
                "coins": player.coins,
                "wins": player.wins,
                "losses": player.losses,
                "games_played":
                    player.games_played
            }

            for player in players
        ]
    })


# =========================================================
# HISTORY
# =========================================================

@app.route("/api/history/<name>", methods=["GET"])
def history(name):

    records = GameHistory.query.filter_by(
        player_name=name
    ).order_by(
        GameHistory.created_at.desc()
    ).limit(30).all()

    return jsonify({

        "history": [

            {
                "bet": item.bet,
                "result": item.result,
                "player_score":
                    item.player_score,
                "dealer_score":
                    item.dealer_score,
                "created_at":
                    item.created_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
            }

            for item in records
        ]
    })


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "error":
            "The requested URL was not found."
    }), 404


@app.errorhandler(500)
def server_error(error):

    return jsonify({
        "error":
            "Internal server error."
    }), 500


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )