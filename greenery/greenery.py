'''
Models to compute a greenery measure from segmentation data.
'''


class ClassPercentage(object):
    " Greenery as the percentage of the pixels from the vegetation class. "
    def __init__(self, myclass="vegetation"):
        self.myclass = myclass
        self._id = f"perc_{myclass}"

    def test(self, seg_results):
        try:
            return seg_results[self.myclass]
        except KeyError:
            return 0.0

    def id(self):
        " Identification of the measure. "
        return self._id
