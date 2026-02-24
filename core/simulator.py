
class Simulator:

    def __init__(self, engine):
        self.engine = engine

    def run(self, state):
        return self.engine.analyze(state)
