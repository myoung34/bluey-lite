import binascii
import gc
from time import sleep

import bluetooth
import machine
import network
import ujson
import ure
import urequests
from machine import UART
from microdot import Microdot
from micropython import const

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)

def fix_dump(data, is_request=False):
    data_to_dump = {}
    for k, v in data.items():
        if is_request:
            if len(v) > 0:
                data_to_dump[k] = v[0]
            else:
                data_to_dump[k] = v
        else:
            data_to_dump[k] = v
        if k == 'network_name' and len(data_to_dump[k]) == 0:
            data_to_dump[k] = 'changeme'

    return data_to_dump

def dump_and_write(filename, data, is_request=False):
    data_to_dump = fix_dump(data, is_request)
    print(f"Writing configuration data: {ujson.dumps(data_to_dump)}")
    f = open("config.json", "w")
    f.write(ujson.dumps(data_to_dump))
    f.close()
    return data_to_dump

config_data = {
    'network_name': '',
    'network_password': '',
    'webhook_url': '',
}

try:
    f = open("config.json", "r")
    config_data = ujson.loads(f.read())
    f.close()
except:
    dump_and_write('config.json', config_data)

RP2040 = UART(1, baudrate=38400, tx=7, rx=6, cts=5, rts=4)
RP2040.write('&')

TILT_DEVICES = {
    'a495bb30c5b14b44b5121370f02d74de': 'black',
    'a495bb60c5b14b44b5121370f02d74de': 'blue',
    'a495bb20c5b14b44b5121370f02d74de': 'green',
    'a495bb50c5b14b44b5121370f02d74de': 'orange',
    'a495bb80c5b14b44b5121370f02d74de': 'pink',
    'a495bb40c5b14b44b5121370f02d74de': 'purple',
    'a495bb10c5b14b44b5121370f02d74de': 'red',
    'a495bb70c5b14b44b5121370f02d74de': 'yellow',
    'a495bb90c5b14b44b5121370f02d74de': 'brown',
}

def check_for_button():
    if RP2040.read(1) == b'$':
        ble.gap_scan(None, 30000, 10000)
        ble.irq(bt_irq_nothing)
        return True
    return False

def serve_configuration():
    app = Microdot()

    htmldoc = '''<!DOCTYPE html>
    <html>
        <head>
            <title>Weather Sensor Portal</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta charset="utf8">
        </head>
        <body>
            <h2 class="title">Configure Settings</h2>
            <form action="/save">
                Network SSID: <input class="input" type="text" name="network_name" value="{{network_name}}"><br/>
                SSID Password: <input class="input" type="text" name="network_password" value="{{network_password}}"><br/>
                HTTP Webhook URL: <input class="input" type="text" name="webhook_url" value="{{webhook_url}}"><br/>
                <input type="submit" value="Save">
            </form>
            <p/><p/><p/><p/>
            <form action="/wipe">
                <input type="submit" value="Wipe Configuration Data">
            </form>
            <p/><p/><p/><p/>
            <form action="/reboot">
                <input type="submit" value="Reboot">
            </form>
        </body>
    </html>
    '''

    gc.enable()

    def render(string_data, data):
        return ure.sub(r'{{([^>]*)}}', lambda m: data[m.group(1)], string_data), 200, {'Content-Type': 'text/html'}


    class DNSQuery:
        def __init__(self, data):
            self.data = data
            self.domain = ''

            m = data[2]
            tipo = (m >> 3) & 15
            if tipo == 0:
                ini = 12
                lon = data[ini]
                while lon != 0:
                    self.domain += data[ini+1:ini+lon+1].decode("utf-8") + "."
                    ini += lon+1
                    lon = data[ini]


        def response(self, ip):
            packet = b''
            print("Response {} == {}".format(self.domain, ip))
            if self.domain:
                packet += self.data[:2] + b"\x81\x80"
                packet += self.data[4:6] + b"\x00\x00\x00\x00"
                packet += self.data[12:]
                packet += b"\xc0\x0c"
                packet += b"\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04"
                packet += bytes(map(int, ip.split(".")))
            return packet

    RP2040.write('Now Setting up AP "bluey"#')
    sleep(3)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="bluey")
    RP2040.write('Connect to SSID "bluey" and \nvisit http://' + ap.ifconfig()[0] + '#')

    @app.get('/')
    def index(req):
        return render(htmldoc, fix_dump(config_data))

    @app.get('/save')
    def save_data(request):
        dump_and_write("config.json", request.args, True)
        machine.reset()

    @app.get('/reboot')
    def reboot(request):
        machine.reset()

    @app.get('/wipe')
    def wipe(request):
        config_data = {
            'network_name': '',
            'network_password': '',
            'webhook_url': '',
        }

        dump_and_write('config.json', config_data)
        machine.reset()


    app.run(debug=True, port=80)



def connect_to_network():
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)

    while True:
        try:
            sta_if.connect(config_data.get('network_name', 'changeme'), config_data.get('network_password',''))
            break
        except OSError:
            sta_if.disconnect()
            RP2040.write(f"Connection attempt to \n{config_data.get('network_name', 'changeme')} failed...#")
            sleep(5)
            machine.reset()

    wifi_attempt = 0
    max_attempts = 15
    while not sta_if.isconnected() and wifi_attempt < max_attempts:
        RP2040.write(f"Attempt: {wifi_attempt}\nConnecting to \n{config_data.get('network_name', 'changeme')}...#")
        sleep(1)
        wifi_attempt += 1
        if check_for_button():
            sta_if.active(False)
            RP2040.write("Entering Configuration mode.#")
            sleep(1)
            serve_configuration()

    if wifi_attempt == max_attempts:
        RP2040.write(f"Failed to connect to {config_data.get('network_name', 'changeme')} .\nRebooting...#")
        sleep(5)
        machine.reset()

    RP2040.write('Wifi Connected! IP: ' + sta_if.ifconfig()[0] + '#')
    sleep(3)
    RP2040.write('&')

ble = bluetooth.BLE()
ble.active(True)

def parse_data(addr, adv_data):
    mac_raw = binascii.hexlify(addr).decode('utf-8')
    raw_data = binascii.hexlify(bytes(adv_data)).decode('ascii')
    return {
        'mac': ':'.join(mac_raw[i:i+2] for i in range(0,12,2)),
        'uuid': raw_data[18:50],
        'major': raw_data[50:54],
        'minor': raw_data[54:58],
    }

def bt_irq_nothing(event, data):
    pass

def bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, connectable, rssi, adv_data = data
        parsed_data = parse_data(addr, adv_data)
        if parsed_data['uuid'] in TILT_DEVICES:
            # Send '{color},{temp},{gravity}#'
            RP2040.write(TILT_DEVICES[parsed_data['uuid']] + "," + str(int(parsed_data['major'], 16)) + "," + str(int(parsed_data['minor'], 16)) + "#")
            if (config_data.get('webhook_url') and len(config_data.get('webhook_url')) >0):
                print(f"Sending webhook to {config_data.get('webhook_url')}")
                urequests.post(config_data.get('webhook_url'), headers = {'content-type': 'application/json'}, data = post_data).json()
        else:
            RP2040.write("No Tilt Data Found#")
            sleep(1)  # We do not want to flood the UART
    elif event == _IRQ_SCAN_DONE:
        RP2040.write("Scan complete#")

# Finally do the thing
connect_to_network()
try:
    RP2040.write("Starting Scan#")
    scan = ble.gap_scan(0, 30000, 10000)

    ble.irq(bt_irq)
except OSError as e:
    pass
