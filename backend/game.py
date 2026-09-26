import random


SUITS = [
    "♠",
    "♥",
    "♦",
    "♣"
]


RANKS = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 10,
    "Q": 10,
    "K": 10,
    "A": 11
}


def create_deck():

    deck = []

    for suit in SUITS:

        for rank in RANKS:

            deck.append({
                "rank": rank,
                "suit": suit
            })

    random.shuffle(deck)

    return deck


def card_value(card):

    return RANKS[card["rank"]]


def hand_score(hand):

    score = 0
    aces = 0

    for card in hand:

        score += card_value(card)

        if card["rank"] == "A":
            aces += 1

    while score > 21 and aces > 0:

        score -= 10
        aces -= 1

    return score


def card_text(card):

    return card["rank"] + card["suit"]