# idep-sanford-autodelegation
IDEP Sanford Autodelegation

The script will automatically perform the calls for withdrawing the rewards and send the
necessary transactions to delegate to the validator. The bot uses telegram for notifications
and will provide information on the transaction hashes.

When executing the script, a password will be prompted and the input will be used for
the transactions for delegation and withdrawing the rewards.

Assumptions:
- iond is in the path of the user
- nominal transaction path only
- `wallet_name` and `wallet_key` and `validator_key` are all linked
  e.g. the public key for `wallet_key` has the alias `wallet_name` and owns `validator_key`

Install from the requirements file:
```pip3 install -r requirements.txt```

Copy and populate the config.ini file with the necessary information.
```cp config.ini.example config.ini```

Run the script and enter the password
```python3 ./idep-sanford-autodelegation.py```
