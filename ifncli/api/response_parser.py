
class ResponseParser:
    def __init__(self, survey_def):
        print('init structure')
        self.survey_key = None
        self.questions = self.parse_definition(survey_def)

    def parse_response(self, response):
        if self.survey_key != response['key']:
            raise ValueError('wrong survey key')
        if 'responses' not in response.keys():
            raise ValueError('no responses')

        parsed_response = {
            'key': response['key'],
            'participantID': response['participantId'],
            'submittedAt': int(response['submittedAt']),
            'engine': response['context']['engineVersion']
        }

        for q in self.questions:
            q_response = self._find_and_process_response(
                q, response['responses'])
            parsed_response = {**parsed_response, **q_response}

        return parsed_response

    def parse_definition(self, survey_def):
        current_survey_def = survey_def['current']['surveyDefinition']

        # check if corrent survey key:
        if self.survey_key is None:
            self.survey_key = current_survey_def['key']
        elif self.survey_key != current_survey_def['key']:
            raise ValueError('wrong survey key')

        return self._process_survey_group_item(current_survey_def)

    def _process_survey_group_item(self, survey_item):
        questions = []
        for innerSurveyItem in survey_item['items']:
            if 'items' in innerSurveyItem.keys():
                questions.extend(
                    self._process_survey_group_item(innerSurveyItem))
            else:
                q = self._process_survey_single_item(innerSurveyItem)
                if q is not None:
                    questions.append(q)
        return questions

    def _process_survey_single_item(self, survey_item):
        # ignore page breaks:
        if 'type' in survey_item.keys() and survey_item['type'] == 'pageBreak':
            return None

        rg = self._accessResponseGroup(survey_item['components'])
        if rg is None:
            return None

        for rg_item in rg['items']:
            q_type = self._get_question_type(rg_item)
            if q_type is None or q_type == 'text':
                continue

            response_options = self._get_response_options(rg)
            return {
                'key': survey_item['key'],
                'type': q_type,
                'response_options': response_options
            }
        return None

    # access ItemGroupComponent with role responseGroup
    def _accessResponseGroup(self, components):
        for itemGroupComponent in components['items']:
            if itemGroupComponent['role'] == 'responseGroup':
                return itemGroupComponent
        return None

    def _get_question_type(self, responseGroup):
        try:
            return responseGroup['role']
        except KeyError:
            print('warning: response group has no items')
            return None

    def _get_response_options(self, responseGroup, root_key=None):
        key = responseGroup['key']
        if root_key is not None:
            key = root_key + '.' + responseGroup['key']

        options = []
        for item in responseGroup['items']:
            if item['role'] in ['text', 'label']:
                continue

            if 'items' in item.keys():
                options.extend(
                    self._get_response_options(item, key)
                )
            else:
                options.append(
                    {
                        "key": key + '.' + item['key'],
                        "role": item['role']
                    }
                )
        return options

    def _find_and_process_response(self, question, responses):
        for r in responses:
            if r['key'] == question['key']:
                answers = {}
                if 'response' not in r.keys():
                    return {}

                if question['type'] == 'singleChoiceGroup':
                    answers = self._process_single_choice(question, r)
                elif question['type'] == 'multipleChoiceGroup':
                    answers = self._process_multiple_choice(question, r)
                elif question['type'] == 'dateInput':
                    answers = self._process_date_input(question, r)
                elif question['type'] == 'matrix':
                    answers = self._process_matrix(question, r)
                elif question['type'] == 'input':
                    answers = self._process_input(question, r)
                elif question['type'] == 'dropDownGroup':
                    answers = self._process_dropdown_group(question, r)
                else:
                    print('warning: question type not processed: ',
                          question['type'])

                return answers
        return {}

    def _process_single_choice(self, question, response):
        current_response = {}
        # print(response['response'])
        for option in question['response_options']:
            resp = self._get_response_option_value(
                response['response'], option['key'])

            target_key = question['key'] + '-' + option['key']

            if resp is None:
                current_response[target_key] = False
            else:
                current_response[target_key] = resp

        return current_response

    def _process_multiple_choice(self, question, response):
        current_response = {}
        # print(response['response'])
        for option in question['response_options']:
            resp = self._get_response_option_value(
                response['response'], option['key'])

            target_key = question['key'] + '-' + option['key']

            if resp is None:
                current_response[target_key] = False
            else:
                current_response[target_key] = resp

        return current_response

    def _process_date_input(self, question, response):
        current_response = {}
        # print(response['response'])
        for option in question['response_options']:
            resp = self._get_response_option_value(
                response['response'], option['key'])

            target_key = question['key'] + '-' + option['key']

            if resp is None:
                current_response[target_key] = False
            else:
                current_response[target_key] = float(resp)

        return current_response

    def _process_input(self, question, response):
        current_response = {}
        # print(response['response'])
        for option in question['response_options']:
            resp = self._get_response_option_value(
                response['response'], option['key'])

            target_key = question['key'] + '-' + option['key']

            if resp is None:
                current_response[target_key] = False
            else:
                current_response[target_key] = resp

        return current_response

    def _process_matrix(self, question, response):
        current_response = {}
        # print(response['response'])

        for option in question['response_options']:
            resp = self._get_response_option_value(
                response['response'], option['key'])

            target_key = question['key'] + '-' + option['key']

            if resp is None:
                current_response[target_key] = False
            else:
                current_response[target_key] = resp

        return current_response

    def _process_dropdown_group(self, question, response):
        current_response = {}

        for option in question['response_options']:
            resp = self._get_response_option_value(
                response['response'], option['key'])

            target_key = question['key'] + '-' + option['key']

            if resp is None:
                current_response[target_key] = False
            else:
                current_response[target_key] = resp
        return current_response

    def _get_response_option_value(self, response, key):
        key_parts = key.split('.')
        current_item = response

        for kp in key_parts[1:]:
            if current_item['key'] == kp:
                # found directly
                break
            elif 'items' in current_item.keys():
                for it in current_item['items']:
                    try:
                        if kp == it['key']:
                            current_item = it
                            break
                    except KeyError:
                        # print("unexpected response in ", response)
                        return None


        if current_item['key'] == key_parts[-1]:
            # found it:
            if 'value' in current_item.keys():
                return current_item['value']
            else:
                return True
        return None
