class GreenData():
    def __init__(self):
        self.values = []
        self.lat = []
        self.long = []
        self.timestamp = []

    def extend(self, new_data):
        if isinstance(new_data, GreenData):
            self.values.extend(new_data.values)
            self.lat.extend(new_data.lat)
            self.long.extend(new_data.long)
            self.timestamp.extend(new_data.timestamp)
        elif isinstance(new_data, BasePanorama):
            self.values.append(new_data.green_res)
            self.lat.append(new_data.latitude)
            self.long.append(new_data.longitude)
            self.timestamp.append(new_data.timestamp)
        else:
            raise TypeError("Green data needs either panorama or Green data to"
                            "append.")
