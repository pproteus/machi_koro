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
    CardType(name="Ranch", colour="BLUE", cost=1, triggers=(2,), effect=produce_coins(1)),
    CardType(name="Bakery", colour="GREEN", cost=1, triggers=(2,3), effect=produce_coins(1), starting_count=1),
    CardType(name="Convenience Store", colour="GREEN", cost=2, triggers=(4,), effect=produce_coins(3)),
    CardType(name="Forest", colour="BLUE", cost=3, triggers=(5,), effect=produce_coins(1)),
    CardType(name="Victory1", colour="PURPLE", cost=4, unique=True, landmark=True),
    CardType(name="Victory2", colour="PURPLE", cost=10, unique=True, landmark=True),
    CardType(name="Victory3", colour="PURPLE", cost=16, unique=True, landmark=True),
    CardType(name="Victory4", colour="PURPLE", cost=22, unique=True, landmark=True),
)

trigger_dict = {n:[card for card in ALL_CARDS if n in card.triggers] for n in range(1, 13)}
victory_cards = [card for card in ALL_CARDS if card.landmark]


class Winner(Exception):
    pass


class Agent:
    def __init__(self):
        self.n = len(ALL_CARDS) + 1
        
    def get_policy(self, vector=[]):
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


class Game:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def produce_income(self, player:Player, n:int):
        player.money += n
        self.print_event(f"{player} gets ${n}, up to ${player.money}.")

    def player_can_buy_card(self, player:Player, cardtype:CardType):
        if player.money >= cardtype.cost:
            if player.cardcounts[cardtype] == 0 or not cardtype.unique:
                return True
        return False

    def buy_card(self, player:Player, cardtype:CardType):
        if self.player_can_buy_card(player, cardtype):
                player.money -= cardtype.cost
                player.cardcounts[cardtype] += 1
                self.print_event(f"{player} buys a {cardtype}.")
        else:
            self.print_event(f"{player} unsuccessfully attempts to buy a {cardtype}.")       

    def roll_dice(self, n=1):
        return [random.randint(1,6) for i in range(n)]
    
    def get_gamestate_vector(self, turn_player:Player, opponent:Player):
        return ( [turn_player.cardcounts[card] for card in ALL_CARDS] + [turn_player.money]
              + [opponent.cardcounts[card] for card in ALL_CARDS] + [opponent.money])
    
    def parse_gamestate_vector(self, vector:list):
        d = {}
        v = vector[::]
        for card in ALL_CARDS:
            d[f"Turnplayer {card}"] = v.pop(0)
        d["Turnplayer Money"] = v.pop(0)
        for card in ALL_CARDS:
            d[f"Opponent {card}"] = v.pop(0)
        d["Oppponent Money"] = v.pop(0)
        assert len(v) == 0
        return d

    def print_event(self, s):
        if self.verbose:
            print(s)

    def playgame(self, agent1:Agent, agent2:Agent):
        players = (Player("Player 1", agent1), Player("Player 2", agent2))
        turncount = 1
        turnplayer, opponent = players
        try:
            while True:
                # roll the dice
                dice = self.roll_dice()
                self.print_event(f"{turnplayer} rolls {dice}.")
                dicetotal = sum(dice)
                triggerables = trigger_dict[dicetotal]

                # trigger all cards matching the dice
                for cardtype in triggerables:
                    if cardtype.colour in ("BLUE", "GREEN"):
                        for i in range(turnplayer.cardcounts[cardtype]):
                            cardtype.effect(self, turnplayer, opponent)
                    if cardtype.colour == "BLUE":
                        for i in range(opponent.cardcounts[cardtype]):
                            cardtype.effect(self, opponent, turnplayer)

                # player may buy one thing
                policy = turnplayer.agent.get_policy()
                for i in range(len(ALL_CARDS)):
                    if not self.player_can_buy_card(turnplayer, ALL_CARDS[i]):
                        policy[i] = 0  # let's just reduce the work the agent needs to do
                choice = argmax(policy)
                if choice == len(ALL_CARDS):
                    pass # buy nothing
                else:
                    self.buy_card(turnplayer, ALL_CARDS[choice])
                
                # check for winner
                if all([turnplayer.cardcounts[card] for card in victory_cards]):
                    raise Winner(turnplayer, self.get_gamestate_vector(turnplayer, opponent))
                # we are making the assumption that you can only gain a landmark on your turn.
                # if you modify the cardset, I still like this added rule that you can only win on your turn.
                # it's very simple and disallows ties.

                # pass the turn
                turncount += 1
                turnplayer, opponent = opponent, turnplayer

        except Winner as w:
            return w.args


if __name__ == "__main__":
    agents = Agent()
    g = Game()
    results = g.playgame(agents, agents)
    print(f"{results[0]} wins!")
    for k, v in g.parse_gamestate_vector(results[1]).items():
        print(f"{k}: {v}")