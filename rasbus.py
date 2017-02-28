#!/usr/bin/env python
import requests
import json
import jsonpickle
import dateutil.parser
import pytz
import datetime
import time, os

"""
Shamelessly stolen from https://github.com/ianwestcott/bustime-display/blob/master/flask/bustime/stopmonitoring.py

Query the MTA BusTime stop monitoring endpoint for bus information.

Example calls:
# b70_near_me_as_json = StopMonitor(MY_API_KEY, '308100', 'B70', 2).json()
# b35_near_me_as_string = StopMonitor(MY_API_KEY, '302684', 'B35', 2)
"""

STOP_MONITORING_ENDPOINT = "http://bustime.mta.info/api/siri/stop-monitoring.json"
VEHICLE_MONITORING_ENDPOINT = "http://bustime.mta.info/api/siri/vehicle-monitoring.json"

FEET_PER_METER = 3.28084
FEET_PER_MILE = 5280

class StopMonitor(object):

  def __init__(self, api_key, stop_id, line=None, max_visits=3):
    self.api_key = api_key
    self.stop_id = stop_id
    # TODO support null line name (to match on any line)
    self.line = line
    self.max_visits = max_visits
    # TODO what if the request throws an exception?
    self.visits = self.stop_monitoring_request()
    self.name = self.visits[0].monitored_stop if len(self.visits) > 0 else None

  def bustime_request_json(self):
    blob = {
      'key': self.api_key,
      'OperatorRef': "MTA",
      'MonitoringRef': self.stop_id,
      'MaximumStopVisits': self.max_visits,
      }
    if self.line is not None:
      blob['LineRef'] =  "MTA NYCT_%s" % self.line
    # TODO define num_visits globally (or per instance of this class)
    # TODO populate these better to account for null values (see self.line above)
    return blob

  def stop_monitoring_request(self):
    payload = self.bustime_request_json()
    response = requests.get(STOP_MONITORING_ENDPOINT, params=payload)
    return self.parse_bustime_response(response.json())

  def parse_bustime_response(self, rsp):
    # self.updated_at
    parsed_visits = []
    visits_json = rsp['Siri']['ServiceDelivery']['StopMonitoringDelivery'][0]['MonitoredStopVisit']
    for raw_visit in visits_json:
      try:
        parsed_visits.append(Visit(raw_visit))
      except:
        pass
    return parsed_visits

  def __str__(self):
    output = []
    if self.name:
      output.append("{}:".format(self.name))
    for visit in self.visits:
      output.append("{}. {}".format(self.visits.index(visit)+1, visit))
    if len(self.visits) == 0:
      output.append("no buses are on the way. sad :(")
    return '\n'.join(output)

  def json(self):
    return jsonpickle.encode(self.visits)


class Visit(object):

  def __init__(self, raw_visit):
    self.route = raw_visit['MonitoredVehicleJourney']['PublishedLineName']
    call = raw_visit['MonitoredVehicleJourney']['MonitoredCall']
    distances = call['Extensions']['Distances']
    self.arrival =  call['ExpectedArrivalTime']
    self.monitored_stop = call['StopPointName']
    self.stops_away = distances['StopsFromCall']
    self.distance = round(distances['DistanceFromCall'] * FEET_PER_METER / FEET_PER_MILE, 2)

  def __str__(self):
    dt = (dateutil.parser.parse(self.arrival) - datetime.datetime.now(pytz.utc))
    dt = dt.days*24*3600 + dt.seconds
    m,s = divmod(dt,60)
    dtf = "{}:{:02d}".format(m,s)
    dtf = "{} min".format(m)
    return ("{} bus {} stops away ({} miles) in {}").format(
          self.route, self.stops_away, self.distance,dtf)

  def __getstate__(self):
    return json.dumps({
      'route': self.route,
      'stops_away': self.stops_away,
      'distance': self.distance,
    })


if __name__ == "__main__":
  with open('APIKEY') as f:
     key = f.read()

  sm = StopMonitor(key,"401094",None,max_visits=5)

  tz = pytz.timezone('US/Eastern')

  while True:
    os.system('clear')
    print datetime.datetime.now(tz)
    print sm
    time.sleep(60)
    sm = None
    while sm is None:
      try:
        sm = StopMonitor(key,"401094",None,max_visits=5)
      except:
        print "Exception loading schedule"
        time.sleep(60)
