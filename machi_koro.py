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
    def __init__(self, winner, snaplist, turncount):
        self.winner = winner
        self.snaplist = snaplist
        self.turncount = turncount


class Agent:
    def __init__(self, *args, **kwargs):
        self.n = len(Policy.get_labels())

    def get_policy(self, vector=[]):
        if isinstance(vector, Snapshot):
            vector = vector.vector
        return [random.random() for i in range(self.n)]
        # override this method

    def export(self, filename="default_agent.txt"):
        pass


class Player:
    def __init__(self, name:str, agent:Agent, starting_money:int=3):
        self.name = name
        self.agent = agent
        self.money = starting_money
        self.cardcounts = {card:card.starting_count for card in ALL_CARDS}

    @classmethod
    def from_gamestate(cls, gamestate_vector):
        p1 = Player.__new__(cls)
        p2 = Player.__new__(cls)
        p1.cardcounts = {card:0 for card in ALL_CARDS}
        p2.cardcounts = {card:0 for card in ALL_CARDS}
        for i in range(len(ALL_CARDS)):
            p1.cardcounts[ALL_CARDS[i]] = gamestate_vector[i]
        p1.money = gamestate_vector[i+1]
        for i in range(len(ALL_CARDS)):
            p2.cardcounts[ALL_CARDS[i]] = gamestate_vector[i]
        p2.money = gamestate_vector[i+1]
        return p1, p2

    def __repr__(self):
        return self.name


class Snapshot:
    def __init__(self, turnplayer:Player, opponent:Player):
        self.turnplayer = turnplayer
        self.did_player_win = None
        self.choice = None
        self.vector = ( [turnplayer.cardcounts[card] for card in ALL_CARDS] + [turnplayer.money]
              + [opponent.cardcounts[card] for card in ALL_CARDS] + [opponent.money] )

    @staticmethod
    def get_labels():
        v = []
        for card in ALL_CARDS:
            v += f"Turnplayer {card}",
        v += "Turnplayer money",
        for card in ALL_CARDS:
            v += f"Opponent {card}",
        v += "Oppponent money",
        return v


class Policy:
    def __init__(self, vector):
        assert (max(vector) <= 1 and min(vector) >= 0), "Policy elements must start bounded between 0 and 1."
        assert len(vector) == len(self.get_labels()), "Policy is the wrong shape!"
        self.vector = vector
        
    def make_choice(self, deterministic=True):
        if deterministic:
            return argmax(self.vector)
        else:
            if max(self.vector) == 0:
                return random.choice([i for i in range(len(self.vector)) if self.vector[i] == 0])
            else:
                v = [i if i >=0 else 0 for i in self.vector]
                return random.choices(list(range(len(self.vector))), weights=v)[0]

    @staticmethod
    def get_labels():
        v = []
        for card in ALL_CARDS:
            v += f"Buy {card}",
        v += "Do Nothing",
        return v
    
    def __repr__(self):
        return str(self.vector)


class Game:
    def __init__(self, verbose=False, deterministic=True):
        self.verbose = verbose
        self.deterministic_agents = True
        self.snapshots: list[Snapshot] = []

    def get_input_length(self):
        return 2*(len(ALL_CARDS) + 1)

    def produce_income(self, player:Player, n:int):
        player.money += n
        self.print_event(f"{player} gets ${n}, up to ${player.money}.")

    def player_can_buy_card(self, player:Player, opponent:Player, cardtype:CardType):
        if player.money >= cardtype.cost:
            if cardtype.unique:
                if player.cardcounts[cardtype] == 0:
                    return True
            else:
                boughtcards = player.cardcounts[cardtype] + opponent.cardcounts[cardtype] - 2*cardtype.starting_count
                if boughtcards < 6:
                    return True
        return False
    
    def simplify_policy(self, policy:Policy, turnplayer:Player, opponent:Player):
        for i in range(len(ALL_CARDS)):            
            if not self.player_can_buy_card(turnplayer, opponent, ALL_CARDS[i]):
                policy.vector[i] = -1  # let's just reduce the work the agent needs to do
        money_to_win = sum([card.cost*(not turnplayer.cardcounts[card]) for card in ALL_CARDS if card.landmark])
        if money_to_win and (turnplayer.money >= money_to_win):
            policy.vector[len(ALL_CARDS)] = -1  # c'mon, don't pass the turn if you have a win
        return policy

    def buy_card(self, player:Player, opponent:Player, cardtype:CardType):
        assert self.player_can_buy_card(player, opponent, cardtype), f"{player} unsuccessfully attempts to buy a {cardtype}."
        player.money -= cardtype.cost
        player.cardcounts[cardtype] += 1
        self.print_event(f"{player} buys a {cardtype}.")   

    def roll_dice(self, n=1):
        return [random.randint(1,6) for i in range(n)]
    
    def print_event(self, s):
        if self.verbose:
            print(s)

    def get_policy_and_take_snapshot(self, turnplayer:Player, opponent:Player):
        snap = Snapshot(turnplayer, opponent)
        policy = turnplayer.agent.get_policy(snap.vector)
        self.snapshots += snap,
        return policy
    
    def setup_game(self):
        self.snapshots = []

    def playgame(self, agent1:Agent, agent2:Agent, randomizep1=True) -> tuple[Player, list[Snapshot], int]: 
        players = (Player("Player 1", agent1), Player("Player 2", agent2))
        turncount = 1
        if randomizep1 and random.randint(0,1):
            opponent, turnplayer = players
        else:
            turnplayer, opponent = players
        try:
            self.setup_game()
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
                policy = Policy(self.get_policy_and_take_snapshot(turnplayer, opponent))
                policy = self.simplify_policy(policy, turnplayer, opponent)
                choice = policy.make_choice(self.deterministic_agents)
                self.snapshots[-1].choice = choice
                if choice == len(ALL_CARDS):
                    pass # buy nothing
                else:
                    try:
                        self.buy_card(turnplayer, opponent, ALL_CARDS[choice])
                    except AssertionError as e:
                        print(f"{policy.vector=}, {turnplayer.money=}, {turnplayer.cardcounts=}")
                        raise e

                # check for winner
                # we are making the assumption that you can only gain a landmark on your turn.
                # if you modify the cardset, I still like this added rule that you can only win on your turn.
                # it's very simple and disallows ties.
                if all([turnplayer.cardcounts[card] for card in victory_cards]):
                    # edit the snapshots to show who won
                    for snap in self.snapshots:
                        snap.did_player_win = (snap.turnplayer == turnplayer)
                    raise Winner(turnplayer, self.snapshots, turncount)


                # pass the turn
                turncount += 1
                turnplayer, opponent = opponent, turnplayer

        except Winner as winner:
            return winner.winner, winner.snaplist, winner.turncount


if __name__ == "__main__":
    agents = Agent()
    g = Game()
    winner, snaplist, turncount = g.playgame(agents, agents)
    print(f"Sample game: {winner} wins in {turncount} turns.")
    labels = Snapshot.get_labels()
    for i in range(len(labels)):
        print(f"{labels[i]}: {snaplist[-1].vector[i]}")