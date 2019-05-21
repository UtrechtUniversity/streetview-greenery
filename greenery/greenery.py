'''
Models to compute a greenery measure from segmentation data.
'''


class VegetationPercentage(object):
    " Greenery as the percentage of the pixels from the vegetation class. "
    def __init__(self):
        self._id = "veg_perc"

    def test(self, seg_results):
        if 'vegetation' in seg_results:
            return seg_results['vegetation']
        else:
            return 0.0

    def id(self):
        " Identification of the measure. "
        return self._id
