// =====================================================
// WHITE JACK - FRONTEND
// =====================================================

let currentPlayer = localStorage.getItem("whiteJackPlayer") || "";
let selectedBet = 10;
let gameActive = false;


// =====================================================
// ELEMENTS
// =====================================================

const loginScreen = document.getElementById("loginScreen");
const gameScreen = document.getElementById("gameScreen");

const usernameInput = document.getElementById("usernameInput");
const loginButton = document.getElementById("loginButton");
const loginMessage = document.getElementById("loginMessage");

const logoutButton = document.getElementById("logoutButton");

const topCoins = document.getElementById("topCoins");
const coins = document.getElementById("coins");
const wins = document.getElementById("wins");
const losses = document.getElementById("losses");
const games = document.getElementById("games");

const profileName = document.getElementById("profileName");
const profileCoins = document.getElementById("profileCoins");
const profileWins = document.getElementById("profileWins");
const profileLosses = document.getElementById("profileLosses");
const profileGames = document.getElementById("profileGames");

const dealerCards = document.getElementById("dealerCards");
const playerCards = document.getElementById("playerCards");

const dealerScore = document.getElementById("dealerScore");
const playerScore = document.getElementById("playerScore");

const gameMessage = document.getElementById("gameMessage");

const startButton = document.getElementById("startButton");
const hitButton = document.getElementById("hitButton");
const standButton = document.getElementById("standButton");

const leaderboardBody = document.getElementById("leaderboardBody");
const historyBody = document.getElementById("historyBody");


// =====================================================
// API HELPER
// =====================================================

async function apiRequest(url, options = {}) {

    try {

        const response = await fetch(url, {
            headers: {
                "Content-Type": "application/json"
            },
            ...options
        });

        let data;

        try {
            data = await response.json();
        } catch {
            data = {};
        }

        if (!response.ok) {
            throw new Error(
                data.error ||
                data.message ||
                `Server error: ${response.status}`
            );
        }

        return data;

    } catch (error) {

        console.error("API Error:", error);

        throw error;
    }
}


// =====================================================
// LOGIN
// =====================================================

async function login() {

    const username = usernameInput.value.trim();

    if (!username) {

        loginMessage.textContent =
            "Please enter a username.";

        return;
    }

    if (username.length < 2) {

        loginMessage.textContent =
            "Username must contain at least 2 characters.";

        return;
    }

    loginButton.disabled = true;
    loginButton.textContent = "PLEASE WAIT...";

    loginMessage.textContent = "";

    try {

        const data = await apiRequest("/api/player", {
            method: "POST",

            body: JSON.stringify({
                name: username
            })
        });

        currentPlayer = data.player.name;

        localStorage.setItem(
            "whiteJackPlayer",
            currentPlayer
        );

        showGameScreen();

        updatePlayerUI(data.player);

        showMessage(
            data.message || "Welcome to White Jack!"
        );

    } catch (error) {

        loginMessage.textContent =
            error.message || "Login failed.";

    } finally {

        loginButton.disabled = false;
        loginButton.textContent = "ENTER GAME";
    }
}


// =====================================================
// SHOW GAME SCREEN
// =====================================================

function showGameScreen() {

    loginScreen.classList.add("hidden");
    gameScreen.classList.remove("hidden");

    showPage("gamePage");
}


// =====================================================
// LOGOUT
// =====================================================

function logout() {

    currentPlayer = "";

    localStorage.removeItem("whiteJackPlayer");

    gameActive = false;

    gameScreen.classList.add("hidden");
    loginScreen.classList.remove("hidden");

    usernameInput.value = "";
    loginMessage.textContent = "";

    resetTable();
}


// =====================================================
// PLAYER DATA
// =====================================================

async function refreshPlayer() {

    if (!currentPlayer) {
        return;
    }

    try {

        const data = await apiRequest(
            `/api/player/${encodeURIComponent(currentPlayer)}`
        );

        updatePlayerUI(data.player);

    } catch (error) {

        console.error(
            "Could not refresh player:",
            error
        );
    }
}


function updatePlayerUI(player) {

    if (!player) {
        return;
    }

    topCoins.textContent = player.coins ?? 0;

    coins.textContent = player.coins ?? 0;
    wins.textContent = player.wins ?? 0;
    losses.textContent = player.losses ?? 0;
    games.textContent = player.games_played ?? 0;

    profileName.textContent = player.name ?? currentPlayer;
    profileCoins.textContent = player.coins ?? 0;
    profileWins.textContent = player.wins ?? 0;
    profileLosses.textContent = player.losses ?? 0;
    profileGames.textContent = player.games_played ?? 0;
}


// =====================================================
// BET SELECTION
// =====================================================

document.querySelectorAll(".bet-btn").forEach(button => {

    button.addEventListener("click", () => {

        if (gameActive) {
            return;
        }

        selectedBet = Number(button.dataset.bet);

        document
            .querySelectorAll(".bet-btn")
            .forEach(btn => {
                btn.classList.remove("selected");
            });

        button.classList.add("selected");
    });

});


// =====================================================
// START GAME
// =====================================================

async function startGame() {

    if (!currentPlayer) {

        showMessage(
            "Please login first.",
            "loss"
        );

        return;
    }

    startButton.disabled = true;
    startButton.textContent = "STARTING...";

    try {

        const data = await apiRequest(
            "/api/game/start",
            {
                method: "POST",

                body: JSON.stringify({
                    name: currentPlayer,
                    bet: selectedBet
                })
            }
        );

        gameActive = !data.finished;

        renderGame(data);

        if (data.finished) {

            setActionButtons(false);

            await refreshPlayer();

            showResultMessage(data.result);

        } else {

            setActionButtons(true);

            showMessage(
                `Game started! Bet: 🪙 ${selectedBet}`
            );
        }

    } catch (error) {

        showMessage(
            error.message || "Could not start game.",
            "loss"
        );

    } finally {

        startButton.disabled = false;
        startButton.textContent = "▶ START GAME";
    }
}


// =====================================================
// HIT
// =====================================================

async function hit() {

    if (!gameActive) {
        return;
    }

    hitButton.disabled = true;

    try {

        const data = await apiRequest(
            "/api/game/hit",
            {
                method: "POST",

                body: JSON.stringify({
                    name: currentPlayer
                })
            }
        );

        renderGame(data);

        if (data.finished) {

            gameActive = false;

            setActionButtons(false);

            await refreshPlayer();

            showResultMessage(data.result);

        } else {

            hitButton.disabled = false;

            showMessage(
                "You drew another card."
            );
        }

    } catch (error) {

        showMessage(
            error.message || "Hit failed.",
            "loss"
        );

        hitButton.disabled = false;
    }
}


// =====================================================
// STAND
// =====================================================

async function stand() {

    if (!gameActive) {
        return;
    }

    standButton.disabled = true;
    hitButton.disabled = true;

    try {

        const data = await apiRequest(
            "/api/game/stand",
            {
                method: "POST",

                body: JSON.stringify({
                    name: currentPlayer
                })
            }
        );

        renderGame(data);

        gameActive = false;

        setActionButtons(false);

        await refreshPlayer();

        showResultMessage(data.result);

    } catch (error) {

        showMessage(
            error.message || "Stand failed.",
            "loss"
        );

        standButton.disabled = false;
        hitButton.disabled = false;
    }
}


// =====================================================
// RENDER GAME
// =====================================================

function renderGame(data) {

    renderCards(
        dealerCards,
        data.dealer_cards || []
    );

    renderCards(
        playerCards,
        data.player_cards || []
    );

    dealerScore.textContent =
        data.dealer_score ?? "-";

    playerScore.textContent =
        data.player_score ?? "-";
}


// =====================================================
// RENDER CARDS
// =====================================================

function renderCards(container, cards) {

    container.innerHTML = "";

    if (!cards || cards.length === 0) {

        const empty = document.createElement("div");

        empty.className = "empty-card";
        empty.textContent = "?";

        container.appendChild(empty);

        return;
    }

    cards.forEach(card => {

        const cardElement =
            document.createElement("div");

        /*
         * Backend may send:
         * {rank: "A", suit: "♠"}
         *
         * or hidden card:
         * "🂠"
         */

        if (
            typeof card === "string" &&
            card === "🂠"
        ) {

            cardElement.className =
                "card back";

            cardElement.textContent = "♠";

        } else {

            const rank = card.rank || "";
            const suit = card.suit || "";

            cardElement.className = "card";

            if (
                suit === "♥" ||
                suit === "♦"
            ) {
                cardElement.classList.add("red");
            }

            cardElement.innerHTML = `
                <div>${escapeHTML(rank)}</div>
                <div>${escapeHTML(suit)}</div>
            `;
        }

        container.appendChild(cardElement);
    });
}


// =====================================================
// RESULT MESSAGE
// =====================================================

function showResultMessage(result) {

    if (!result) {

        showMessage(
            "Game finished."
        );

        return;
    }

    const resultText =
        String(result).toLowerCase();

    if (
        resultText.includes("win") ||
        resultText.includes("blackjack")
    ) {

        showMessage(
            `🎉 ${result}`,
            "win"
        );

    } else if (
        resultText.includes("lose") ||
        resultText.includes("bust")
    ) {

        showMessage(
            `😔 ${result}`,
            "loss"
        );

    } else {

        showMessage(
            `🤝 ${result}`,
            "push"
        );
    }
}


// =====================================================
// MESSAGE
// =====================================================

function showMessage(text, type = "") {

    gameMessage.textContent = text;

    gameMessage.classList.remove(
        "win",
        "loss",
        "push"
    );

    if (type) {
        gameMessage.classList.add(type);
    }
}


// =====================================================
// GAME BUTTON STATE
// =====================================================

function setActionButtons(active) {

    hitButton.disabled = !active;
    standButton.disabled = !active;

    if (active) {
        startButton.disabled = true;
    } else {
        startButton.disabled = false;
    }
}


// =====================================================
// RESET TABLE
// =====================================================

function resetTable() {

    dealerCards.innerHTML =
        '<div class="empty-card">?</div>';

    playerCards.innerHTML =
        '<div class="empty-card">?</div>';

    dealerScore.textContent = "-";
    playerScore.textContent = "-";

    gameActive = false;

    setActionButtons(false);

    showMessage(
        "Select a bet and start the game."
    );
}


// =====================================================
// PAGE NAVIGATION
// =====================================================

document.querySelectorAll(".nav-btn[data-page]")
    .forEach(button => {

        button.addEventListener("click", () => {

            const page =
                button.dataset.page;

            showPage(page);
        });

    });


function showPage(pageId) {

    document
        .querySelectorAll(".page")
        .forEach(page => {
            page.classList.add("hidden");
        });

    const selectedPage =
        document.getElementById(pageId);

    if (selectedPage) {
        selectedPage.classList.remove("hidden");
    }

    document
        .querySelectorAll(".nav-btn[data-page]")
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.page === pageId
            );
        });

    if (pageId === "leaderboardPage") {
        loadLeaderboard();
    }

    if (pageId === "historyPage") {
        loadHistory();
    }

    if (pageId === "profilePage") {
        refreshPlayer();
    }
}


// =====================================================
// LEADERBOARD
// =====================================================

async function loadLeaderboard() {

    leaderboardBody.innerHTML = `
        <tr>
            <td colspan="5">Loading...</td>
        </tr>
    `;

    try {

        const data =
            await apiRequest("/api/leaderboard");

        const players =
            data.leaderboard || [];

        if (players.length === 0) {

            leaderboardBody.innerHTML = `
                <tr>
                    <td colspan="5">
                        No players yet.
                    </td>
                </tr>
            `;

            return;
        }

        leaderboardBody.innerHTML = "";

        players.forEach((player, index) => {

            const row =
                document.createElement("tr");

            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${escapeHTML(player.name)}</td>
                <td>🪙 ${player.coins ?? 0}</td>
                <td>${player.wins ?? 0}</td>
                <td>${player.games_played ?? 0}</td>
            `;

            leaderboardBody.appendChild(row);
        });

    } catch (error) {

        leaderboardBody.innerHTML = `
            <tr>
                <td colspan="5">
                    Failed to load leaderboard.
                </td>
            </tr>
        `;
    }
}


// =====================================================
// HISTORY
// =====================================================

async function loadHistory() {

    if (!currentPlayer) {
        return;
    }

    historyBody.innerHTML = `
        <tr>
            <td colspan="5">Loading...</td>
        </tr>
    `;

    try {

        const data =
            await apiRequest(
                `/api/history/${encodeURIComponent(currentPlayer)}`
            );

        const history =
            data.history || [];

        if (history.length === 0) {

            historyBody.innerHTML = `
                <tr>
                    <td colspan="5">
                        No games yet.
                    </td>
                </tr>
            `;

            return;
        }

        historyBody.innerHTML = "";

        history.forEach(item => {

            const row =
                document.createElement("tr");

            const result =
                String(item.result || "");

            let resultClass = "";

            if (
                result.toLowerCase().includes("win") ||
                result.toLowerCase().includes("blackjack")
            ) {
                resultClass = "result-win";

            } else if (
                result.toLowerCase().includes("lose") ||
                result.toLowerCase().includes("bust")
            ) {
                resultClass = "result-loss";

            } else {
                resultClass = "result-push";
            }

            row.innerHTML = `
                <td class="${resultClass}">
                    ${escapeHTML(result)}
                </td>

                <td>
                    🪙 ${item.bet ?? 0}
                </td>

                <td>
                    ${item.player_score ?? "-"}
                </td>

                <td>
                    ${item.dealer_score ?? "-"}
                </td>

                <td>
                    ${formatDate(item.created_at)}
                </td>
            `;

            historyBody.appendChild(row);
        });

    } catch (error) {

        historyBody.innerHTML = `
            <tr>
                <td colspan="5">
                    Failed to load history.
                </td>
            </tr>
        `;
    }
}


// =====================================================
// DATE FORMAT
// =====================================================

function formatDate(value) {

    if (!value) {
        return "-";
    }

    try {

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        return date.toLocaleString();

    } catch {

        return String(value);
    }
}


// =====================================================
// SECURITY
// =====================================================

function escapeHTML(value) {

    const div =
        document.createElement("div");

    div.textContent =
        String(value ?? "");

    return div.innerHTML;
}


// =====================================================
// ENTER KEY LOGIN
// =====================================================

usernameInput.addEventListener(
    "keydown",
    event => {

        if (event.key === "Enter") {
            login();
        }

    }
);


// =====================================================
// BUTTON EVENTS
// =====================================================

loginButton.addEventListener(
    "click",
    login
);

logoutButton.addEventListener(
    "click",
    logout
);

startButton.addEventListener(
    "click",
    startGame
);

hitButton.addEventListener(
    "click",
    hit
);

standButton.addEventListener(
    "click",
    stand
);


// =====================================================
// INITIAL LOAD
// =====================================================

async function initialize() {

    resetTable();

    if (!currentPlayer) {

        loginScreen.classList.remove("hidden");
        gameScreen.classList.add("hidden");

        return;
    }

    try {

        const data =
            await apiRequest(
                `/api/player/${encodeURIComponent(currentPlayer)}`
            );

        showGameScreen();

        updatePlayerUI(data.player);

    } catch (error) {

        console.log(
            "Saved player not found. Showing login."
        );

        localStorage.removeItem(
            "whiteJackPlayer"
        );

        currentPlayer = "";

        loginScreen.classList.remove("hidden");
        gameScreen.classList.add("hidden");
    }
}


// Start application
initialize();