#!/usr/bin/env python3
import os, requests
import configparser
import pexpect
import getpass
import time 
from subprocess import Popen, PIPE

class IdepAutodelegation():
    def __init__( self, config_file='config.ini' ):
        # obtain the host name
        self.name = os.uname()[1]

        # read the config and setup the telegram
        self.read_config( config_file )
        self.setup_telegram()
        self.setup_idep_info()

        # send the hello message
        self.send( f'Hello from IDEP Autodelegation Bot on {self.name}!' )
        
    def read_config( self, config_file ):
        '''
        Read the configuration file
        '''
        config = configparser.ConfigParser()
        if os.path.exists( config_file ):
            print( f"Using Configuration File: { config_file }")
            config.read( config_file )
        else:
            print( f"Configuration File Does Not Exist: { config_file }")

        # save the config
        self.config = config

    def setup_telegram( self ):
        '''
        Setup telegram
        '''
        if "TELEGRAM_TOKEN" in os.environ:
            self.telegram_token = os.environ['TELEGRAM_TOKEN']
        elif 'Telegram' in self.config and 'telegram_token' in self.config['Telegram']:
            self.telegram_token = self.config['Telegram']['telegram_token']
        else:
            self.telegram_token = None
        
        if "TELEGRAM_CHAT_ID" in os.environ:
            self.telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']
        elif 'Telegram' in self.config and 'telegram_chat_id' in self.config['Telegram']:
            self.telegram_chat_id = self.config['Telegram']['telegram_chat_id']
        else:
            self.telegram_chat_id = None

    def setup_idep_info( self ):
        '''
        Setup idep info
        '''

        # sleep time between delegation cycles
        if "SLEEP_TIME" in os.environ:
            self.sleep_time = int(os.environ['SLEEP_TIME'])
        elif 'sleep_time' in self.config['IDEP']:
            self.sleep_time = int(self.config['IDEP']['sleep_time'])
        else:
            self.sleep_time = 600

        # Prompt for the password if not in environment
        if "IDEP_PASSWORD" in os.environ:
            self.password = os.environ['IDEP_PASSWORD']
        elif 'password' in self.config['IDEP']:
            self.password = self.config['IDEP']['password']
        else:
            self.password = getpass.getpass("Enter the wallet password: ")

        # chain id
        if "CHAIN_ID" in os.environ:
            self.chain_id = os.environ['CHAIN_ID']
        else:
            self.chain_id = self.config['IDEP']['chain_id']

        # wallet name
        if "WALLET_NAME" in os.environ:
            self.wallet_name = os.environ['WALLET_NAME']
        elif "WALLETNAME" in os.environ:
            self.wallet_name = os.environ['WALLETNAME']
        else:
            self.wallet_name = self.config['IDEP']['wallet_name']
        
        # wallet and validator keys
        if "WALLET_KEY" in os.environ:
            self.wallet_key = os.environ['WALLETKEY']
        else:
            self.wallet_key = self.config['IDEP']['wallet_key']

        if "VALIDATOR_KEY" in os.environ:
            self.validator_key = os.environ['VALIDATORKEY']
        else:
            self.validator_key = self.config['IDEP']['validator_key']

    def send( self, msg ):
        '''
        Print the message and send telegram message, if available
        '''
        if self.telegram_token != None and self.telegram_chat_id != None:
            requests.post( f'https://api.telegram.org/bot{self.telegram_token}/sendMessage?chat_id={self.telegram_chat_id}&text={msg}' )
        print( msg )

    def parse_subprocess( self, response, keyword ):
        '''
        Parse and return the line
        '''
        for line in response.decode("utf-8").split('\n'):
            if keyword in line:
                return line

    def get_balance( self ):
        '''
        Obtain the IDEP balance
        '''
        proc = Popen([ f"iond q bank balances {self.wallet_key}" ], stdout=PIPE, shell=True)
        (out, err) = proc.communicate()
        line = self.parse_subprocess( out, 'amount' )
        balance = line.split('"')[1]
        return balance

    def distribute_rewards( self ):
        '''
        Distribute the rewards from the validator and return the hash
        '''
        child = pexpect.spawn(f"iond tx distribution withdraw-rewards { self.validator_key } --chain-id={ self.chain_id } --from {self.wallet_name} -y", timeout=10)
        child.expect( b'Enter keyring passphrase:' ) 
        child.sendline( self.password )   
        child.expect( pexpect.EOF )                                                                                                                                     
        child.close()
        line = self.parse_subprocess( child.before, 'txhash:' )
        txhash = line.split('txhash: ')[1]
        return txhash

    def distribute_rewards_commission( self ):
        '''
        Distribute the comission for the validator and return the hash
        '''
        child = pexpect.spawn(f"iond tx distribution withdraw-rewards { self.validator_key } --chain-id={ self.chain_id } --from {self.wallet_name} --commission -y", timeout=10)
        child.expect( b'Enter keyring passphrase:' ) 
        child.sendline( self.password )   
        child.expect( pexpect.EOF )                                                                                                                                     
        child.close()
        line = self.parse_subprocess( child.before, 'txhash:' )
        txhash = line.split('txhash: ')[1]
        return txhash

    def delegate( self, amount ):
        '''
        Delegate the amount to the validator
        '''
        child = pexpect.spawn( f'iond tx staking delegate { self.validator_key } { amount }idep --from { self.wallet_name } --chain-id { self.chain_id } -y', timeout=10)
        child.expect( b'Enter keyring passphrase:' ) 
        child.sendline( self.password )   
        child.expect( pexpect.EOF )                                                                                                                                     
        child.close()
        line = self.parse_subprocess( child.before, 'txhash:' )
        txhash = line.split('txhash: ')[1]
        return txhash
    
    def get_delegations( self ):
        '''
        Obtain the delegation amount for the validator
        '''
        proc = Popen([ f"iond q staking delegations-to {self.validator_key} --chain-id={self.chain_id}" ], stdout=PIPE, shell=True)
        (out, err) = proc.communicate()
        line = self.parse_subprocess( out, 'shares' )
        balance = float(line.split('"')[1].split(".")[0]) * (1/100000000)
        return balance

    def delegation_cycle( self ):
        '''
        Delegation cycle for distributing rewards and sending them out
        '''
        self.send( f"Start Delegation Cycle!" )
        curr_delegations = self.get_delegations()
        self.send( f" - Current Delegation: { curr_delegations } " )

        self.send( f" - Distribution Tx Hash: { self.distribute_rewards() }" )
        time.sleep( 10 )

        self.send( f" - Commission Tx Hash: { self.distribute_rewards_commission() }" )
        time.sleep( 10 )
        
        balance = self.get_balance()
        self.send( f" - Current Balance (post distribution): { float( balance ) * (1/100000000) } " )
        self.send( f" - Delegation Tx Hash: { self.delegate( balance ) }" )
        time.sleep( 10 )

        new_delegations = self.get_delegations()
        self.send( f" - New Delegation: { new_delegations } ( Delta: { new_delegations - curr_delegations } )" )
        self.send( f"End Delegation Cycle" )

        self.send( f"Sleeping { self.sleep_time } Seconds\n" )
        time.sleep( self.sleep_time )

def parse_arguments( ):
    '''
    Parse the arguments passed in
    '''
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', type=str, required=False, default='config.ini', help='Configuration File')
    return parser.parse_args()

# Parse arguments
args = parse_arguments()

# Create the object
idep_bot = IdepAutodelegation( args.config )

# run periodic delegation cycle
while True:
    idep_bot.delegation_cycle()
