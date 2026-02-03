import machi_koro as mk
import numpy as np
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier, export_graphviz
import graphviz


class Snapshotbank:
    def __init__(self):
        self.game = mk.Game()
        self.policy_size = len(mk.Policy.get_labels())
        self.snap_size = len(mk.Snapshot.get_labels())
        self.xlist = [tuple() for i in range(self.policy_size)]
        self.ylist = [tuple() for i in range(self.policy_size)]

    def append(self, x, y, choice):
        assert len(x) == len(y), [x, y]
        assert all([len(i) == self.snap_size for i in x]), [len(i) for i in x]
        self.xlist[choice] += x
        self.ylist[choice] += y


class Trainer:
    def __init__(self, bank=Snapshotbank()):
        self.bank = bank
        self.game = bank.game

    def play_training_games(self, agent, N=1000, deterministic=False):
        if not deterministic:
            self.game.deterministic_agents = False
        for game in range(N):
            winner, snaplist, turncount = self.game.playgame(agent, agent)
            for snap in snaplist:
                if snap.choice is not None:
                    self.bank.append((tuple(snap.vector),), (int(snap.did_player_win),), snap.choice)
        self.game.deterministic_agents = True

    def play_test_games(self, agent, other_agent, N=1000, ndigits=2):
        totalwins = 0
        totalturns = 0
        for game in range(N):
            winner, snaplist, turncount = self.game.playgame(agent, other_agent)
            if winner.agent == agent:
                totalwins += 1
            totalturns += turncount
        return round(totalwins/N, 2), round(totalturns/N, ndigits)

    def make_agent(self, agentclass, baseline_agent:mk.Agent=mk.Agent(), 
                   N_games_per_training_round=200, N_training_rounds=10, verbose=True):
        for i in range(N_training_rounds):
            self.play_training_games(baseline_agent, N=N_games_per_training_round)
            if verbose:
                print(f"Round {i} training done")
                candidate = agentclass(self.bank)
            winrate, turns = self.play_test_games(candidate, baseline_agent, N_games_per_training_round)
            if verbose:
                print(f"Round {i}: Winrate {winrate}, {turns} turns.")
            if winrate > 0.5:
                baseline_agent = candidate
                baseline_agent.export()
        winrate, turns = self.play_test_games(baseline_agent, mk.Agent(), N_games_per_training_round)
        if verbose:
            print(f"Winrate vs random: {winrate}, {turns} turns.")
        return baseline_agent

    def make_explainer(self, explainerclass, agent_to_explain:mk.Agent,
                       baseline_agent:mk.Agent=mk.Agent(), N_rounds=200, verbose=True):
        explainer = explainerclass(agent_to_explain, self.bank)
        # export_tree(classifier.tree, "Classifier", [str(c) for c in explainer.tree.classes_])
        if verbose:
            winrate, turns = self.play_test_games(explainer, baseline_agent, N_rounds)
            print(f"Explainer vs random: Winrate {winrate}, {turns} turns.")
            winrate, turns = self.play_test_games(explainer, agent_to_explain, N_rounds)
            print(f"Explainer vs target: Winrate {winrate}, {turns} turns.")
        return explainer


class TreeAgent(mk.Agent):
    def __init__(self, bank:Snapshotbank):
        self.treelist = []
        for i in range(bank.policy_size):
            if not len(bank.ylist[i]):
                self.treelist += None,
                continue
            xtrain = np.asarray(bank.xlist[i])
            ytrain = np.asarray(bank.ylist[i])
            tree = DecisionTreeRegressor(max_depth=4, min_samples_leaf=50)
            tree.fit(xtrain, ytrain)
            self.treelist += tree,

    def get_policy(self, vector):
        predictions = [[np.float64(0)] if tree is None
                        else tree.predict(np.asarray(vector).reshape(1, -1)) 
                       for tree in self.treelist]
        return [i[0] for i in predictions]


class TreeExplainer(mk.Agent):
    def __init__(self, agent_to_explain:mk.Agent, bank:Snapshotbank):
        x_obs = []
        y_obs = []
        for move_option in bank.xlist:
            for gamestate in move_option:
                policy = mk.Policy(agent_to_explain.get_policy(gamestate))
                temp_player, temp_opponent = mk.Player.from_gamestate(gamestate)
                safer_policy = bank.game.simplify_policy(policy, temp_player, temp_opponent)
                choice = mk.Policy.get_labels()[safer_policy.make_choice()] ## should I force non-deterministic??
                ### wait why are we taking the choice label instead of the raw choice??
                x_obs += gamestate,
                y_obs += choice,
        X_train = np.asarray(x_obs)
        y_train = np.asarray(y_obs)
        self.tree = DecisionTreeClassifier(max_depth=6, class_weight="balanced")
        self.tree.fit(X_train, y_train)
        print(f"Explainer accuracy: {self.tree.score(X_train, y_train)}")


    def get_policy(self, vector):
        choice = self.tree.predict_proba(np.asarray(vector).reshape(1, -1))[0]
        return choice

    def export(self, filename):
        dot = export_graphviz(self.tree, 
            feature_names=mk.Snapshot.get_labels(), class_names=mk.Policy.get_labels(), 
            impurity=False, label="root", filled=True, rounded=True)
        graphviz.Source(dot).render(f"pdfs/{filename}", format="pdf", cleanup=True)



if __name__ == "__main__":
    print("Ready")
    bank = Snapshotbank()
    trainer = Trainer(bank)

    agent = trainer.make_agent(TreeAgent,  N_training_rounds=2, verbose=True)
    explainer = trainer.make_explainer(TreeExplainer, agent, verbose=True)
    explainer.export("explainer")