import os
import json
import base64

from cliff.command import Command
from . import register

from ifncli.utils import read_yaml, read_json

from time import sleep
import random
import string

def get_random_password_string(length):
    password_characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(password_characters)
                       for i in range(length))
    return password

class MigrateUser(Command):
    """
        Migrate user from the old platform

        This command migrate users from a previous csv file

        This command expect :
        1 - A csv file with 2 columns 'email', and 'oldParticipantID'
        2 - A yaml file to describe the context

        ````
            preferredLanguage: 'en'
            studyKeys: [] 
            use2FA: true
        ```

    """

    name = 'user:migrate'

    def get_parser(self, prog_name):
        parser = super(Email, self).get_parser(prog_name)

        parser.add_argument(
            "--sleep", type=int, help="delay in seconds", default=2)
        parser.add_argument(
            "--user_list", help="CSV file with list of email addresses and old participant IDs", required=True)
        parser.add_argument(
            "--general", help="general attributes for each user in yaml format", required=True)

        return parser
        
    def take_action(self, args):
        import pandas as pd

        client = self.app.get_management_api()

        sleep_delay = args.sleep

        migration_settings = read_yaml(args.general)

        user_batch_path = args.user_list
        new_users = pd.read_csv(user_batch_path)
        failed_users = []
        client.renew_token()

        for i, u in new_users.iterrows():
            user_object = {
                'accountId': u['email'],
                'oldParticipantID': u['oldParticipantID'],
                'initialPassword': get_random_password_string(15),
                'preferredLanguage': migration_settings['preferredLanguage'],
                'studies': migration_settings['studyKeys'],
                'use2FA': migration_settings['use2FA']
            }
            if i > 0 and i % 20 == 0:
                client.renew_token()
            print('Processing ', i + 1, ' of ', len(new_users))
            try:
                client.migrate_user(user_object)
            except ValueError as err:
                failed_users.append({
                    'email': user_object['accountId'],
                    'oldParticipantID': user_object['oldParticipantID'],
                    'error': str(err)
                })

            sleep(sleep_delay)

        print(len(new_users) - len(failed_users),
            ' out of ', len(new_users), 'created')
        if len(failed_users) > 0:
            batchname = os.path.basename(user_batch_path).split('.')[0]
            new_filename = batchname + '_failed.csv'
            pd.DataFrame(failed_users).to_csv(new_filename)
            print('failed users saved into: ', new_filename)
