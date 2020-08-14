import numpy as np


# TODO: Fix destructive negation / addition.


class LinearMeasure():
    def __init__(self, intercept=0.0, weights={}):
        self.intercept = intercept
        self.weights = weights

    def compute(self, green_res):
        if not isinstance(green_res, dict):
            return [self.compute(x) for x in green_res]
        measure = self.intercept
        for green_class, slope in self.weights.items():
            measure += green_res[green_class]*slope
        return measure

    @property
    def name(self):
        weights_str = [f"{green_class}{slope}"
                       for green_class, slope in self.weights.items()]
        return "_".join(weights_str + [str(self.intercept)])

    @property
    def classes(self):
        return list(self.weights)


class Measure():
    def __init__(self, green_class="vegetation", _add_measures=None,
                 _mult_measures=None):
        self.green_class = green_class
        self._add_measures = _add_measures
        self._mult_measures = _mult_measures
        self.multiplier = 1
        self.adder = 0

    def compute(self, **kwargs):
        if self._add_measures is None and self._mult_measures is None:
            cur_val = kwargs[self.green_class]
        elif self._add_measures is not None:
            cur_val = sum([m.compute(**kwargs) for m in self._add_measures])
        else:
            cur_val = np.product(
                [m.compute(**kwargs) for m in self._mult_measures])
        return self.adder + self.multiplier * cur_val

    def __add__(self, rhs):
        if isinstance(rhs, Measure):
            cls = self.__class__
            return cls(_add_measures=[self, rhs])
        self.adder += rhs
        return self

    def __mul__(self, rhs):
        if isinstance(rhs, Measure):
            cls = self.__class__
            return cls(_mult_measures=[self, rhs])
        self.multiplier *= rhs
        self.adder *= rhs
        return self

    def __sub__(self, rhs):
        return self.__add__(rhs.__neg__())

    def __rsub__(self, lhs):
        self.__neg__()
        return self.__add__(lhs)

    def __neg__(self):
        self.multiplier *= -1
        self.adder *= -1

    def __rmul__(self, lhs):
        return self.__mul__(lhs)

    def __radd__(self, lhs):
        return self.__add__(lhs)

    def __str__(self):
        if self._add_measures is None and self._mult_measures is None:
            self_str = self.green_class
        elif self._add_measures is not None:
            self_str = " + ".join(str(meas) for meas in self._add_measures)
            self_str = f"({self_str})"
        else:
            self_str = " * ".join(str(meas) for meas in self._mult_measures)
            self_str = f"({self_str})"

        if self.multiplier != 1:
            self_str = str(self.multiplier) + "*" + self_str
        if self.adder != 0:
            self_str = f"({self.adder}  + {self_str})"
        return self_str
