class OP:
    pass


class UnOP(OP):
    def __init__(self, t):
        self.t = t

    def __repr__(self):
        return f"{self.__class__.__name__}({self.t})"

    def __len__(self):
        out = 1

        if isinstance(self.t, OP):
            out += len(self.t)

        return out


class Not(UnOP):
    pass


class BiOP(OP):
    def __init__(self, l, r):
        self.l = l
        self.r = r

    def __repr__(self):
        return f"{self.__class__.__name__}({self.l}, {self.r})"

    def __len__(self):
        out = 1

        if isinstance(self.l, OP):
            out += len(self.l)

        if isinstance(self.r, OP):
            out += len(self.r)

        return out


class And(BiOP):
    pass


class Or(BiOP):
    pass


class Implies(BiOP):
    pass


class Iff(BiOP):
    pass
