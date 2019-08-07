#!/usr/bin/env python

import math
from datetime import datetime
from dateutil import tz
from copy import copy

def degree_to_meter(avg_lat):
    R_earth = 6356e3  # meters]
    long_fac = math.pi/180*R_earth
    lat_fac = math.pi*math.cos(math.pi*avg_lat/180.0)/180*R_earth
    return (lat_fac, long_fac)


def fast_coor_to_dist(lat_1, long_1, lat_2, long_2):
    lat_fac, long_fac = degree_to_meter((lat_1+lat_2)/2)
    dist = math.sqrt(((lat_1-lat_2)*lat_fac)**2 + ((long_1-long_2)*long_fac)**2)
    return dist

class Sun:

    def getSunriseTime( self, coords ):
        return self.calcSunTime( coords, True )

    def getSunsetTime( self, coords ):
        return self.calcSunTime( coords, False )

    def getCurrentUTC( self ):
        now = datetime.now()
        return [ now.day, now.month, now.year ]

    def timeToDawnDusk(self, dt, time_zone='UTC', **kwargs):
        sun_rise_set = self.sunRiseSetUTC(dt=dt, **kwargs)
        sunrise = sun_rise_set["sunrise"]
        sunset = sun_rise_set["sunset"]
        sr_dt = dt.replace(hour=sunrise["hour"], minute=sunrise["minute"])
        ss_dt = dt.replace(hour=sunset["hour"], minute=sunset["minute"])
        
        utc_zone = tz.gettz('UTC')
        local_zone = tz.gettz(time_zone)

        sr_dt = sr_dt.replace(tzinfo=utc_zone)
        ss_dt = ss_dt.replace(tzinfo=utc_zone)
        sr_dt = sr_dt.astimezone(local_zone) 
        ss_dt = ss_dt.astimezone(local_zone)

#         print(sr_dt, ss_dt)
        after_sunrise = dt.hour-sr_dt.hour + (dt.minute-sr_dt.minute)/60.0
        before_sunset = ss_dt.hour-dt.hour + (ss_dt.minute-dt.minute)/60.0

        return min(after_sunrise, before_sunset)
        

    def sunRiseSetUTC(self, **kwargs):
        sunrise = self.sunTimeUTC(isRiseTime=True, **kwargs)
        sunset = self.sunTimeUTC(isRiseTime=False, **kwargs)
        return {
            "sunrise": sunrise,
            "sunset": sunset,
        }
        

    def sunTimeUTC(self, coords=None, latitude=None, longitude=None, dt=None,
                   isRiseTime=True, zenith = 90.8 ):
        "Returns sunrise/sun for a day at a location given by its coordinates."
        # isRiseTime == False, returns sunsetTime

        if dt is None:
            dt = datetime.now()
        day, month, year = (dt.day, dt.month, dt.year)

        if coords is not None:
            longitude = coords['longitude']
            latitude = coords['latitude']
        elif latitude is None or longitude is None:
            raise ValueError("Error: give coordinate for sunrise/set calculation.")

        TO_RAD = math.pi/180

        #1. first calculate the day of the year
        N1 = math.floor(275 * month / 9)
        N2 = math.floor((month + 9) / 12)
        N3 = (1 + math.floor((year - 4 * math.floor(year / 4) + 2) / 3))
        N = N1 - (N2 * N3) + day - 30

        #2. convert the longitude to hour value and calculate an approximate time
        lngHour = longitude / 15

        if isRiseTime:
            t = N + ((6 - lngHour) / 24)
        else: #sunset
            t = N + ((18 - lngHour) / 24)

        #3. calculate the Sun's mean anomaly
        M = (0.9856 * t) - 3.289

        #4. calculate the Sun's true longitude
        L = M + (1.916 * math.sin(TO_RAD*M)) + (0.020 * math.sin(TO_RAD * 2 * M)) + 282.634
        L = self.forceRange( L, 360 ) #NOTE: L adjusted into the range [0,360)

        #5a. calculate the Sun's right ascension

        RA = (1/TO_RAD) * math.atan(0.91764 * math.tan(TO_RAD*L))
        RA = self.forceRange( RA, 360 ) #NOTE: RA adjusted into the range [0,360)

        #5b. right ascension value needs to be in the same quadrant as L
        Lquadrant  = (math.floor( L/90)) * 90
        RAquadrant = (math.floor(RA/90)) * 90
        RA = RA + (Lquadrant - RAquadrant)

        #5c. right ascension value needs to be converted into hours
        RA = RA / 15

        #6. calculate the Sun's declination
        sinDec = 0.39782 * math.sin(TO_RAD*L)
        cosDec = math.cos(math.asin(sinDec))

        #7a. calculate the Sun's local hour angle
        cosH = (math.cos(TO_RAD*zenith) - (sinDec * math.sin(TO_RAD*latitude))) / (cosDec * math.cos(TO_RAD*latitude))

        if cosH > 1:
            return {'status': False,
                    'msg': 'the sun never rises on this location (on the specified date)'}

        if cosH < -1:
            return {'status': False,
                    'msg': 'the sun never sets on this location (on the specified date)'}

        #7b. finish calculating H and convert into hours

        if isRiseTime:
            H = 360 - (1/TO_RAD) * math.acos(cosH)
        else: #setting
            H = (1/TO_RAD) * math.acos(cosH)

        H = H / 15

        #8. calculate local mean time of rising/setting
        T = H + RA - (0.06571 * t) - 6.622

        #9. adjust back to UTC
        UT = T - lngHour
        UT = self.forceRange( UT, 24) # UTC time in decimal format (e.g. 23.23)

        #10. Return
        minute = int(round((UT - int(UT))*60,0)+0.5)%60
        carry = int(round((UT - int(UT))*60,0)+0.5)//60
        hr = self.forceRange(int(UT) + carry, 24)
#         print(hr, minute)

        return {
#             'status': True,
#             'decimal': UT,
            'hour': hr,
            'minute': minute 
        }

    def forceRange(self, v, maxim):
        # force v to be >= 0 and < max
        if v < 0:
            return v + maxim
        elif v >= maxim:
            return v - maxim

        return v


if __name__ == "__main__":
    dt = datetime.now()
    coors = {
        'latitude':52.106175,
        'longitude': 5.177329,
    }
    sun = Sun()
    print(sun.timeToDawnDusk(dt, coords=coors))