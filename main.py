from machine import UART, idle
import machine
from random import randint
from time import sleep
import network
import urequests
import bluetooth
from micropython import const
import binascii
import json


_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)


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

def connect_to_network():
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)


    while True:
        try:
            sta_if.connect('My SSID', 'myWPAPassword')
            break
        except OSError:
            sta_if.disconnect()
            RP2040.write('Connection attempt failed...#')
            sleep(5)
    while not sta_if.isconnected():
        RP2040.write('connecting...#')
        sleep(1)

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

def bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, connectable, rssi, adv_data = data
        parsed_data = parse_data(addr, adv_data)
        if parsed_data['uuid'] in TILT_DEVICES:
            # Send '{color},{temp},{gravity}#'
            RP2040.write(TILT_DEVICES[parsed_data['uuid']] + "," + str(int(parsed_data['major'], 16)) + "," + str(int(parsed_data['minor'], 16)) + "#")
        else:
            RP2040.write("No Tilt Data Found#")
            sleep(1)  # We do not want to flood the UART
    elif event == _IRQ_SCAN_DONE:
        RP2040.write("Scan complete#")

connect_to_network()
try:
    RP2040.write("Starting Scan#")
    scan = ble.gap_scan(0, 30000, 10000)

    ble.irq(bt_irq)
except OSError as e:
    pass
