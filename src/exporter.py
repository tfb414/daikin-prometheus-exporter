import subprocess
import json
import os
import logging
import datetime
import requests
from prometheus_client import make_wsgi_app, Gauge
from flask import Flask
from waitress import serve
from shutil import which

app = Flask("Diaken-Thermostat-Exporter")  # Create flask app

# Setup logging values
format_string = 'level=%(levelname)s datetime=%(asctime)s %(message)s'
logging.basicConfig(encoding='utf-8',
                    level=logging.DEBUG,
                    format=format_string)

# Disable Waitress Logs
log = logging.getLogger('waitress')
log.disabled = True

# Create Metrics
outside_humidity = Gauge('ac_humidity_outside', "AC's humidity at the unit")
fan = Gauge('ac_fan', "AC's fan setting 0: auto, 1: on")
humIndoor = Gauge('ac_humIndoor', "AC's indoor humidity")
modeLimit = Gauge('ac_modeLimit', "AC's mode; 0: none, 1: all, 2: heat only, 3: cool only")
tempOutdoor = Gauge('ac_tempOutdoor', "AC's indoor temperature in celcius")
mode = Gauge('ac_mode', "AC's Thermostate mode; 0: off, 1: heat, 2: cool, 3: auto, 4: emergencyHeat")
setpointMaximum = Gauge('ac_setpointMaximum', "AC's Maximum temperature threshold supported by the system in 0.1 degree Celsius increments")
coolSetpoint = Gauge('ac_coolSetpoint', "AC's Cooling threshold for the 'Manual' operating mode")
heatSetpoint = Gauge('ac_heatSetpoint', "AC's Heating threshold for the 'Manual' operating mode")
fanCirculateSpeed = Gauge('ac_fanCirculateSpeed', "AC's Speed at which fan should run when circulating on a schedule; 0: low, 1: medium, 2: high")
equipmentStatus = Gauge('ac_equipmentStatus', "AC's HVAC equipmentStatus; 1: cool, 2: overcool for dehum, 3: heat, 4: fan, 5: idle")
tempIndoor = Gauge('ac_tempIndoor', "AC's Current indoor temperature")
setpointDelta = Gauge('ac_setpointDelta', "AC's minimum temperature delta in 0.5 celcius increments")
equipmentCommunication = Gauge('ac_equipmentCommunication', "AC's equipment communication")
fanCirculate = Gauge('ac_fanCirculate', "AC's system fan; 0: auto, 1: on")
modeEmHeatAvailable = Gauge('ac_modeEmHeatAvailable', "AC's emergency heat is available as a system mode; 0: not available, 1: available")
geofencingEnabled = Gauge('ac_geofencingEnabled', "AC's geoFencing enabled")
scheduleEnabled = Gauge('ac_scheduleEnabled', "AC's scheduled enabled")
setpointMinimum = Gauge('ac_setpointMinimum', "AC's minimum threshold supported by the system in .1 degree C increments")
authentication_success = Gauge('ac_authentication_successful', "AC's ability to get a new accessToken")
up = Gauge('ac_up', "AC's healthCheck")

# Cache metrics for how long (seconds)
cache_seconds = int(os.environ.get('DAIKIN_CACHE_FOR', 240))
cache_until = datetime.datetime.fromtimestamp(0)

def convertFromFToC(celsius, digitsToRound):
    return round((1.8 * celsius), digitsToRound) + 32

def getAccessToken():
    print("HERE")
    print(os.getenv('X_API_KEY'))


    url = 'https://integrator-api.daikinskyport.com/v1/token'
    headers = {
        'x-api-key': os.getenv('X_API_KEY'),
        'Content-Type': 'application/json'
    }

    data = {
        "email": os.getenv('ACCOUNT_EMAIL'),
        "integratorToken": os.getenv('INTEGRATOR_TOKEN')
    }

    response = requests.post(url, headers=headers, json=data)

    print(response.status_code)
    if (response.status_code != 200):
        authentication_success.set(0)
        print("WARNING WILL ROBINSON")

    access_token = response.json()['accessToken']
    print(access_token)


#   DO SOME ERROR HANDLING HERE
    return access_token

def getMetrics(access_token):
    url = 'https://integrator-api.daikinskyport.com/v1/devices/23e0fdb2-9a4a-11ec-9913-93308a5e9c5b'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'x-api-key': os.getenv('X_API_KEY'),
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)

    print(response.status_code)
    if (response.status_code != 200):
        print("WARNING WILL ROBINSON")
        return (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    if (response.json()):
        data = response.json()
        if "error" in data:
            # Socket error
            print('Something went wrong')
            print(data['error'])
            return (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)  # Return all data as 0


        actual_fan = data['fan']
        actual_humIndoor = data['humIndoor']
        actual_modeLimit = data['modeLimit']
        actual_tempOutdoor = data['tempOutdoor']
        actual_mode = data['mode']
        actual_setpointMaximum = data['setpointMaximum']
        actual_coolSetpoint = data['coolSetpoint']
        actual_heatSetpoint = data['heatSetpoint']
        actual_fanCirculateSpeed = data['fanCirculateSpeed']
        actual_equipmentStatus = data['equipmentStatus']
        actual_humOutdoor = data['humOutdoor']
        actual_tempIndoor = data['tempIndoor']
        actual_setpointDelta = data['setpointDelta']
        actual_equipmentCommunication = data['equipmentCommunication']
        actual_fanCirculate = data['fanCirculate']
        actual_modeEmHeatAvailable = data['modeEmHeatAvailable']
        actual_geofencingEnabled = data['geofencingEnabled']
        actual_scheduleEnabled = data['scheduleEnabled']
        actual_setpointMinimum = data['setpointMinimum']


        return (actual_humOutdoor,
                actual_fan,
                actual_humIndoor,
                actual_modeLimit,
                actual_tempOutdoor,
                actual_mode,
                actual_setpointMaximum,
                actual_coolSetpoint,
                actual_heatSetpoint,
                actual_fanCirculateSpeed,
                actual_equipmentStatus,
                actual_tempIndoor,
                actual_setpointDelta,
                actual_equipmentCommunication,
                actual_fanCirculate,
                actual_modeEmHeatAvailable,
                actual_geofencingEnabled,
                actual_scheduleEnabled,
                actual_setpointMinimum)

@app.route("/metrics")
def updateResults():
    global cache_until

    if datetime.datetime.now() > cache_until:
        access_token = getAccessToken()

        r_outside_humidity, r_fan, r_humIndoor, r_modeLimit, r_tempOutdoor, r_mode, r_setpointMaximum, r_coolSetpoint, r_heatSetpoint, r_fanCirculateSpeed, r_equipmentStatus, r_tempIndoor, r_setpointDelta, r_equipmentCommunication, r_fanCirculate, r_modeEmHeatAvailable, r_geofencingEnabled, r_scheduleEnabled, r_setpointMinimum = getMetrics(access_token)
        outside_humidity.set(r_outside_humidity)
        fan.set(r_fan)
        humIndoor.set(r_humIndoor)
        modeLimit.set(r_modeLimit)
        tempOutdoor.set(convertFromFToC(r_tempOutdoor, 1))
        mode.set(r_mode)
        setpointMaximum.set(r_setpointMaximum)
        coolSetpoint.set(convertFromFToC(r_coolSetpoint, 0))
        heatSetpoint.set(convertFromFToC(r_heatSetpoint, 0))
        fanCirculateSpeed.set(r_fanCirculateSpeed)
        equipmentStatus.set(r_equipmentStatus)
        tempIndoor.set(convertFromFToC(r_tempIndoor, 1))
        setpointDelta.set(r_setpointDelta)
        equipmentCommunication.set(r_equipmentCommunication)
        fanCirculate.set(r_fanCirculate)
        modeEmHeatAvailable.set(r_modeEmHeatAvailable)
        geofencingEnabled.set(r_geofencingEnabled)
        scheduleEnabled.set(r_scheduleEnabled)
        setpointMinimum.set(r_setpointMinimum)
        up.set(1)

        cache_until = datetime.datetime.now() + datetime.timedelta(
            seconds=cache_seconds)

    return make_wsgi_app()


@app.route("/")
def mainPage():
    return ("<h1>Welcome to Daikin prometheus exporter.</h1>" +
            "Click <a href='/metrics'>here</a> to see metrics.")


if __name__ == '__main__':
    PORT = os.getenv('DAIKIN_EXPORTER_PORT', 5555)
    logging.info("Starting Daikin prometheus exporter on http://localhost:" +
                 str(PORT))
    serve(app, host='0.0.0.0', port=PORT)