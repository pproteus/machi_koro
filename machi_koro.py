from dataclasses import dataclass
from numpy import argmax
import random



def produce_coins(n):
    def effect(game, player, opponent):
        game.produce_income(player, n)
    return effect


def null_effect(game, player, opponent):
    pass


@dataclass(frozen=True)
class CardType:
    name: str
    colour: str
    cost: int
    triggers: tuple[int] = tuple()
    effect:None = null_effect          # this will be a function of (game, player, opponent)
    starting_count: int = 0
    unique: bool = False
    landmark: bool = False      # the game ends when a player has one of each landmark. Otherwise, a landmark is identical to a major establishment

    def __repr__(self):
        return self.name


ALL_CARDS = (
    CardType(name="Wheat Field", colour="BLUE", cost=1, triggers=(1,), effect=produce_coins(1), starting_count=1),
    CardType(name="Bakery", colour="GREEN", cost=1, triggers=(2,3), effect=produce_coins(1), starting_count=1),
    CardType(name="Victory1", colour="PURPLE", cost=4, unique=True, landmark=True),
    CardType(name="Victory2", colour="PURPLE", cost=10, unique=True, landmark=True),
    CardType(name="Victory3", colour="PURPLE", cost=16, unique=True, landmark=True),
    CardType(name="Victory4", colour="PURPLE", cost=22, unique=True, landmark=True),
)

trigger_dict = {n:[card for card in ALL_CARDS if n in card.triggers] for n in range(1, 13)}
victory_cards = [card for card in ALL_CARDS if card.landmark]


class Agent:
    def __init__(self):
        self.n = len(ALL_CARDS) + 1
    def get_policy(self):
        return [random.random() for i in range(self.n)]
        # override this method


class Player:
    def __init__(self, name:str, agent:Agent, starting_money:int=3):
        self.name = name
        self.agent = agent
        self.money = starting_money
        self.cardcounts = {card:card.starting_count for card in ALL_CARDS}

    def __repr__(self):
        return self.name


class GameEngine:
    def produce_income(self, player:Player, n:int):
        player.money += n
        print(f"{player} gets ${n}, up to ${player.money}.")

    def player_can_buy_card(self, player:Player, cardtype:CardType):
        if player.money >= cardtype.cost:
            if player.cardcounts[cardtype] == 0 or not cardtype.unique:
                return True
        return False

    def buy_card(self, player:Player, cardtype:CardType):
        if self.player_can_buy_card(player, cardtype):
                player.money -= cardtype.cost
                player.cardcounts[cardtype] += 1
                print(f"{player} buys a {cardtype}.")
        else:
            print(f"{player} unsuccessfully attempts to buy a {cardtype}.")       


    def roll_dice(self, n=1):
        return [random.randint(1,6) for i in range(n)]


class Winner(Exception):
    pass

def playgame(agent1:Agent, agent2:Agent):
    g = GameEngine()
    players = (Player("Player 1", agent1), Player("Player 2", agent2))
    turncount = 1
    turnplayer, opponent = players
    try:
        while True:
            # roll the dice
            dice = g.roll_dice()
            print(f"{turnplayer} rolls {dice}.")
            dicetotal = sum(dice)
            triggerables = trigger_dict[dicetotal]

            # trigger all cards matching the dice
            for cardtype in triggerables:
                if cardtype.colour in ("BLUE", "GREEN"):
                    for i in range(turnplayer.cardcounts[cardtype]):
                        cardtype.effect(g, turnplayer, opponent)
                if cardtype.colour == "BLUE":
                    for i in range(opponent.cardcounts[cardtype]):
                        cardtype.effect(g, opponent, turnplayer)

            # player may buy one thing
            policy = turnplayer.agent.get_policy()
            for i in range(len(ALL_CARDS)):
                if not g.player_can_buy_card(turnplayer, ALL_CARDS[i]):
                    policy[i] = 0  # let's just reduce the work the agent needs to do
            choice = argmax(policy)
            if choice == len(ALL_CARDS):
                pass # buy nothing
            else:
                g.buy_card(turnplayer, ALL_CARDS[choice])
            
            # check for winner
            if all([turnplayer.cardcounts[card] for card in victory_cards]):
                raise Winner(turnplayer)

            # pass the turn
            turncount += 1
            turnplayer, opponent = opponent, turnplayer

    except Winner as w:
        print(w.args)


agents = Agent()
playgame(agents, agents)