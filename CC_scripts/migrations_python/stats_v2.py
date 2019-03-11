#!/usr/bin/env python3

import re
import json
import platform
import os
import bitcoin
from bitcoin.wallet import P2PKHBitcoinAddress
from bitcoin.core import x
from bitcoin.core import CoreMainParams

class CoinParams(CoreMainParams):
    MESSAGE_START = b'\x24\xe9\x27\x64'
    DEFAULT_PORT = 7770
    BASE58_PREFIXES = {'PUBKEY_ADDR': 60,
                       'SCRIPT_ADDR': 85,
                       'SECRET_KEY': 188}

bitcoin.params = CoinParams

from slickrpc import Proxy

def colorize(string, color):
    colors = {
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'green': '\033[92m',
        'red': '\033[91m'
    }
    if color not in colors:
        return string
    else:
        return colors[color] + string + '\033[0m'

# function to accept only integers selection
def selectRangeInt(low,high, msg):
    while True:
        try:
            number = int(input(msg))
        except ValueError:
            print("integer only, try again")
            continue
        if low <= number <= high:
            return number
        else:
            print("input outside range, try again")

# fucntion to define rpc_connection
def def_credentials(chain):
    rpcport = '';
    operating_system = platform.system()
    if operating_system == 'Darwin':
        ac_dir = os.environ['HOME'] + '/Library/Application Support/Komodo'
    elif operating_system == 'Linux':
        ac_dir = os.environ['HOME'] + '/.komodo'
    elif operating_system == 'Windows':
        ac_dir = '%s/komodo/' % os.environ['APPDATA']
    if chain == 'KMD':
        coin_config_file = str(ac_dir + '/komodo.conf')
    else:
        coin_config_file = str(ac_dir + '/' + chain + '/' + chain + '.conf')
    with open(coin_config_file, 'r') as f:
        for line in f:
            l = line.rstrip()
            if re.search('rpcuser', l):
                rpcuser = l.replace('rpcuser=', '')
            elif re.search('rpcpassword', l):
                rpcpassword = l.replace('rpcpassword=', '')
            elif re.search('rpcport', l):
                rpcport = l.replace('rpcport=', '')
    if len(rpcport) == 0:
        if chain == 'KMD':
            rpcport = 7771
        else:
            print("rpcport not in conf file, exiting")
            print("check " + coin_config_file)
            exit(1)

    return (Proxy("http://%s:%s@127.0.0.1:%d" % (rpcuser, rpcpassword, int(rpcport))))

# to select assetchain at keyprompt
assetChains = []
ccids = []
ID=1
HOME = os.environ['HOME']
try:
    with open(HOME + '/StakedNotary/assetchains.json') as file:
        assetchains = json.load(file)
except Exception as e:
    print(e)
    print("Trying alternate location for file")
    with open(HOME + '/staked/assetchains.json') as file:
        assetchains = json.load(file)
print("")
for chain in assetchains:
    print(str(ID).rjust(3) + ' | ' + (chain['ac_name']+" (ccid: "+chain['ac_cc']+")").ljust(12))
    ID+=1
    assetChains.append(chain['ac_name'])
    ccids.append(chain['ac_cc'])
src_index = selectRangeInt(1,len(assetChains),"Select chain: ")
print("")
CHAIN = assetChains[src_index-1]

rpc_connection = def_credentials(CHAIN)
getinfo_result = rpc_connection.getinfo()
height = getinfo_result['blocks']
print("notarisation results are unreliable below a depth of 5")
DEPTH_input = selectRangeInt(1,int((height / 5) - 5),"Please enter notarisation depth (5 to " + str(int(height / 5)) + "):  ")
#input('Please enter notarisation depth: ')

DEPTH = (int(DEPTH_input) * 5) + 1
print("Blocks in consideration: " + str(DEPTH))
print("")
if DEPTH < 1: DEPTH == 5

#CHAIN = input('Please specify chain: ')
ADDRESS = 'RXL3YXG2ceaB6C5hfJcN4fvmLH2C34knhA'

getnotarysendmany_result = rpc_connection.getnotarysendmany()
iguana_json = rpc_connection.getiguanajson()
notary_keys = {}
score = {}

for notary in iguana_json['notaries']:
    for i in notary:
        addr = str(P2PKHBitcoinAddress.from_pubkey(x(notary[i])))
        notary_keys[addr] = i

for block in range(height - DEPTH,height):
    getblock_result = rpc_connection.getblock(str(block), 2)
    if len(getblock_result['tx'][0]['vout']) > 1:
        vouts = getblock_result['tx'][0]['vout']
        for vout in vouts[1:]:
            addr = vout['scriptPubKey']['addresses'][0]
            if addr in getnotarysendmany_result:
                getnotarysendmany_result[addr] += 1
            else:
                print('BUG in the coinbase tx, please report this.')

for i in notary_keys:
    score[notary_keys[i]] = getnotarysendmany_result[i]

getinfo_result = rpc_connection.getinfo()
if 'notaryname' in getinfo_result:
    notaryname = getinfo_result['notaryname']

s = [(k, score[k]) for k in sorted(score, key=score.get, reverse=True)]
for k, v in s:
    if k == notaryname:
        myscore = str(k) + ' ' + str(v)
        print(colorize(myscore, 'green'))
    else:
        print(k, v)
print("")