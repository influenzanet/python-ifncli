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


def log_migration_events(type, users_impacted, log_file_path):
    if len(users_impacted) > 0:
        batchname = os.path.basename(log_file_path).split('.')[0]
        new_filename = batchname + '_' + str(type) + '.csv'
        pd.DataFrame(users_impacted).to_csv(new_filename)
        print(str(type) + ' users saved into: ', new_filename)


class MigrateUser(Command):
    """
        Migrate user from the old platform

        This command migrate users from a previous csv file

        This command expect :
        1 - An exported json file with user details from the old platform
        ````
            [
                {
                    "login": "user1",
                    "is_staff": false,
                    "email": "user1@user.com",
                    "profiles": [{
                            "gid": "asdasdasda-c3fc-47b6-8f26-8f2dd43df1af",
                            "name": "user1"
                        }, {
                            "gid": "kkjsdasd-12fd-4da1-876a-0de2288634f5",
                            "name": "user2"
                        }
                    ],
                    "date_joined": "10-07-2008T17:14:50"
                }
            ]

        ````
        2 - A yaml file to describe the context

        ````
            preferredLanguage: 'en'
            studyKeys: []
            skipEmptyProfiles: true
            use2FA: true
        ```

    """

    name = 'user:migrate'

    def get_parser(self, prog_name):
        parser = super(MigrateUser, self).get_parser(prog_name)
        parser.add_argument(
            "--sleep", type=int, help="delay in seconds", default=0.5)
        parser.add_argument(
            "--exported_users", help="JSON file with the exported list of email addresses and old participant IDs", required=True)
        parser.add_argument(
            "--settings", help="general attribute settings for each user in yaml format", required=True)
        return parser

    def take_action(self, args):
        import pandas as pd

        client = self.app.get_management_api()

        sleep_delay = args.sleep

        migration_settings = read_yaml(args.settings)

        user_batch_path = args.exported_users
        new_users = pd.read_json(user_batch_path)
        failed_users = []
        skipped_users = []
        client.renew_token()

        for i, u in new_users.iterrows():
            if migration_settings['skipEmptyProfiles'] and u['profiles'] == []:
                skipped_users.append({
                    'email': u['email'],
                    'oldParticipantIDs': '',
                    'error': 'Empty profiles'
                })
                continue
            user_object = {
                'accountId': u['email'],
                'oldParticipantIDs': [x['gid'] for x in u['profiles']],
                'profileNames': [x['name'] for x in u['profiles']],
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
                    'oldParticipantIDs': user_object['oldParticipantIDs'],
                    'error': str(err)
                })
            sleep(sleep_delay)

        print(len(new_users) - len(failed_users) - len(skipped_users),
              ' out of ', len(new_users), 'users created')
        print(len(failed_users),
              ' out of ', len(new_users), 'users failed')
        print(len(skipped_users),
              ' out of ', len(new_users), 'users skipped')
        log_migration_events('failed', failed_users, user_batch_path)
        log_migration_events('skipped', skipped_users, user_batch_path)
