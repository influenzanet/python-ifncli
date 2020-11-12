import json
import requests


class ManagementAPIClient:
    def __init__(self, management_api_url, login_credentials=None, participant_api_url=None):
        self.management_api_url = management_api_url
        self.participant_api_url = participant_api_url

        self.token = None
        self._refresh_token = None
        self.auth_header = None
        print('Initilize client')
        if login_credentials is not None:
            self.login(login_credentials)

    def login(self, credentials):
        r = requests.post(
            self.management_api_url + '/v1/auth/login-with-email', data=json.dumps(credentials))
        if r.status_code != 200:
            print(r.content)
            exit()
        resp = r.json()
        if 'secondFactorNeeded' in resp.keys() and resp['secondFactorNeeded']:
            verification_code = input('Enter verification code:')
            credentials['verificationCode'] = verification_code
            r = requests.post(
                self.management_api_url + '/v1/auth/login-with-email', data=json.dumps(credentials))
            if r.status_code != 200:
                print(r.content)
                exit()
            resp = r.json()

        self.token = resp['token']['accessToken']
        self._refresh_token = resp['token']['refreshToken']
        self.auth_header = {'Authorization': 'Bearer ' + self.token}
        print('Successfully logged in.')

    def renew_token(self):
        """
        export const renewTokenURL = '/v1/auth/renew-token';
        export const renewTokenReq = (refreshToken: string) => authApiInstance.post<TokenResponse>(renewTokenURL, { refreshToken: refreshToken });
        :return:
        """
        if self.auth_header is None:
            raise ValueError('need to login first')
        if self.participant_api_url is None:
            raise ValueError('missing common api url')
        r = requests.post(self.participant_api_url + '/v1/auth/renew-token',
                          headers=self.auth_header, data=json.dumps({"refreshToken": self._refresh_token}))
        if r.status_code != 200:
            raise ValueError(r.content)
        resp = r.json()
        self.token = resp['accessToken']
        self._refresh_token = resp['refreshToken']
        self.auth_header = {'Authorization': 'Bearer ' + self.token}

    def create_study(self, study_obj):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(self.management_api_url + '/v1/studies',
                          headers=self.auth_header, data=json.dumps(study_obj))
        if r.status_code != 200:
            raise ValueError(r.content)
        print('study created succcessfully')

    def get_studies(self):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.get(self.management_api_url + '/v1/studies',
                          headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        data = r.json()
        if 'studies' in data:
            return data['studies']
        return []

    def update_study_props(self, study_key, props):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(self.management_api_url + '/v1/study/' + study_key + '/props', headers=self.auth_header,
                          data=json.dumps({
                              'studyKey': study_key,
                              'props': props
                          }))
        if r.status_code != 200:
            raise ValueError(r.content)
        print('study props updated succcessfully')

    def update_study_rules(self, study_key, rules):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(self.management_api_url + '/v1/study/' + study_key + '/rules', headers=self.auth_header,
                          data=json.dumps({
                              'studyKey': study_key,
                              'rules': rules
                          }))
        if r.status_code != 200:
            raise ValueError(r.content)
        print('study rules updated succcessfully')

    def delete_study(self, study_key):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.delete(self.management_api_url + '/v1/study/' +
                            study_key, headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        print('study deleted succcessfully')

    def add_study_member(self, study_key, user_id, user_name, role='maintainer'):
        if self.auth_header is None:
            raise ValueError('need to login first')
        self.post = requests.post(self.management_api_url + '/v1/study/' + study_key + '/save-member',
                                  headers=self.auth_header,
                                  data=json.dumps({
                                      'studyKey': study_key,
                                      'member': {
                                          "userId": user_id,
                                          "role": role,
                                          "username": user_name
                                      }
                                  }))
        r = self.post
        if r.status_code != 200:
            raise ValueError(r.content)
        print('user successfully added to study')

    def remove_study_member(self, study_key, user_id):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(self.management_api_url + '/v1/study/' + study_key + '/remove-member',
                          headers=self.auth_header,
                          data=json.dumps({
                              'studyKey': study_key,
                              'member': {
                                  "userId": user_id,
                              }
                          })
                          )
        if r.status_code != 200:
            raise ValueError(r.content)
        print('user successfully removed from study')

    def save_survey_to_study(self, study_key, survey_object):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(self.management_api_url + '/v1/study/' + study_key +
                          '/surveys', headers=self.auth_header, data=json.dumps(survey_object))
        if r.status_code != 200:
            raise ValueError(r.content)
        print('survey saved succcessfully')

    def get_surveys_in_study(self, study_key):
        """
            Get Surveys list in studies
            return list() of object empty if unknown study of no survey
        """
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.get(self.management_api_url + '/v1/study/' +
                         study_key + '/surveys', headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        data = r.json()
        if 'infos' in data:
            return data['infos']
        return []
        
    def get_survey_definition(self, study_key, survey_key):
        if self.auth_header is None:
            raise ValueError('need to login first')
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.get(
            self.management_api_url + '/v1/study/' + study_key + '/survey/' + survey_key,
            headers={'Authorization': 'Bearer ' + self.token})
        if r.status_code != 200:
            print(r.content)
            return None
        return r.json()

    def remove_survey_from_study(self, study_key, survey_key):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.delete(
            self.management_api_url + '/v1/study/' + study_key + '/survey/' + survey_key,
            headers={'Authorization': 'Bearer ' + self.token})
        if r.status_code != 200:
            raise ValueError(r.content)
        print("survey successfully removed")

    def get_response_statistics(self, study_key, start=None, end=None):
        if self.auth_header is None:
            raise ValueError('need to login first')
        params = {}
        if start is not None:
            params["from"] = int(start)
        if end is not None:
            params["until"] = int(end)
        r = requests.get(
            self.management_api_url + '/v1/data/' + study_key + '/statistics',
            headers={'Authorization': 'Bearer ' + self.token}, params=params)
        if r.status_code != 200:
            raise ValueError(r.content)
        return r.json()

    def get_survey_responses(self, study_key, survey_key=None, start=None, end=None):
        if self.auth_header is None:
            raise ValueError('need to login first')
        if self.token is None:
            raise ValueError('need to login first')
        params = {}
        if survey_key is not None:
            params["surveyKey"] = survey_key
        if start is not None:
            params["from"] = int(start)
        if end is not None:
            params["until"] = int(end)
        r = requests.get(
            self.management_api_url + '/v1/data/' + study_key + '/responses', headers=self.auth_header, params=params)
        if r.status_code != 200:
            print(r.content)
            return None
        return r.json()

    def get_all_templates(self):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.get(
            self.management_api_url + '/v1/messaging/email-templates', headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        return r.json()

    def save_email_template(self, template_object):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(self.management_api_url + '/v1/messaging/email-templates',
                          data=json.dumps({'template': template_object}), headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        return r.json()

    def delete_email_template(self, message_type, study_key=None):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(self.management_api_url + '/v1/messaging/email-templates/delete',
                          data=json.dumps({
                              'messageType': message_type,
                              'studyKey': study_key,
                          }), headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        print('email template deleted successfully')

    def delete_auto_message(self, auto_message_id):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.delete(self.management_api_url + '/v1/messaging/auto-message/' +
                            auto_message_id, headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        print('auto message deleted successfully')

    def get_auto_messages(self):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.get(
            self.management_api_url + '/v1/messaging/auto-messages', headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        return r.json()

    def save_auto_message(self, auto_message_object):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(
            self.management_api_url + '/v1/messaging/auto-messages', data=json.dumps(auto_message_object),
            headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        print('auto message saved successfully')

    def send_message_to_all_users(self, template_object):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(
            self.management_api_url + '/v1/messaging/send-message/all-users',
            data=json.dumps({"template": template_object}), headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        print('message sending triggered')

    def send_message_to_study_participants(self, study_key, condition, template_object):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(
            self.management_api_url + '/v1/messaging/send-message/study-participants', data=json.dumps({
                "studyKey": study_key,
                "condition": condition,
                "template": template_object
            }), headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.content)
        print('message sending triggered')

    def migrate_user(self, user_object):
        if self.auth_header is None:
            raise ValueError('need to login first')
        r = requests.post(
            self.management_api_url + '/v1/user/migrate', data=json.dumps(user_object), headers=self.auth_header)
        if r.status_code != 200:
            raise ValueError(r.json())
        print('user created for ' + user_object['accountId'])
