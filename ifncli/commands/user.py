import os
import json
from typing import List
from cliff.command import Command

from . import register
from ..utils import read_yaml, read_json, to_json, write_content,check_password_strength
from datetime import datetime
from time import sleep
import random
import string

def get_random_password_string(length):
    password_characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(password_characters) for i in range(length))
    return password

def reorder_profiles(profiles:List):
    """
        Make sure the flagged profile as "main" is the first in the profile list
    """
    main = []
    others = []
    for p in profiles:
        if 'main' in p and p['main']:
            main.append(p)
        else:
            others.append(p)
    return main + others

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
        parser.add_argument("--dry-run", action="store_true", help="Dont insert")
        parser.add_argument("--sleep", type=int, help="delay in seconds", default=0.5)
        parser.add_argument("--users", help="JSON file with the exported list of email addresses and old participant IDs", required=True)
        parser.add_argument("--settings", help="general attribute settings for each user in yaml format", required=True)
        return parser

    def take_action(self, args):
        
        migration_settings = read_yaml(args.settings)
        user_batch_path = args.users
        sleep_delay = args.sleep
        dry_run = args.dry_run

        client = self.app.get_management_api()
        
        new_users = read_json(user_batch_path)

        failed_users = []
        skipped_users = []
        created_users = []

        skipEmptyProfiles = migration_settings['skipEmptyProfiles']

        if 'emailFilters' in migration_settings:
            emailFilters = migration_settings['emailFilters']
        else:
            emailFilters = None

        client.renew_token()

        for i, u in enumerate(new_users):
            email = u['email']

            if emailFilters is not None:
                skip = False
                for filter in emailFilters:
                    if email.endswith(filter):
                        skipped_users.append(u)
                        print("%d %s - skipped email from filter %s" % (i, email, filter))
                        skip = True
                        break
                if skip:
                    continue
            
            if skipEmptyProfiles and len(u['profiles']) == 0:
                skipped_users.append(u)
                print("%d %s - skipped empty profile" % (i, email))
                continue

            initial_password = get_random_password_string(15)
            while not check_password_strength(initial_password):
                initial_password = get_random_password_string(15)

            profiles = reorder_profiles(u['profiles'])

            
            user_object = {
                'accountId': email,
                'oldParticipantIDs': [x['gid'] for x in profiles],
                'profileNames': [x['name'] for x in profiles],
                'initialPassword': initial_password,
                'preferredLanguage': u.get('language', migration_settings['preferredLanguage']),
                'studies': migration_settings['studyKeys'],
                'use2FA': migration_settings['use2FA'],
            }

            #if 'date_joined' in u:
            #    created_at = datetime.fromisoformat(u['date_joined'])
            #    user_object['CreatedAt'] = created_at.timestamp()

            if i > 0 and i % 15 == 0:
                client.renew_token()
                print('Processing ', i + 1, ' of ', len(new_users))
            try:
                if not dry_run:
                    new_user = client.migrate_user(user_object)
                    created_users.append({
                        'id':new_user['id'],
                        'email': email,
                    })
                else:
                    print(f"[dry-run] {i} {user_object['accountId']} ")
                    created_users.append(user_object)
            except ValueError as err:
                u['error'] = str(err)
                failed_users.append(u)
                print("%d - %s : %s" % (i, email, str(err)) )
            sleep(sleep_delay)

        print("%d out of %d created, %d failed" % (len(new_users) - len(failed_users), len(new_users), len(failed_users)) )

        migration_report = {
            'failed': failed_users,
            'skipped': skipped_users,
            'created': created_users,
        }
    
        batchname = os.path.basename(user_batch_path).split('.')[0]    
        write_content(batchname + "_migration_report.json", to_json(migration_report))

register(MigrateUser)