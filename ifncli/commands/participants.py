from cliff.command import Command
from . import register
from ..utils import read_yaml, write_json, read_json
from ..api import STUDY_PARTICIPANT_STATUS
from influenzanet.api import ParticpantStatePaginaged

from ..stats.collector import DataCollector, CollectorBuilder, FieldCountCollector

class ParticipantStatesStatistics(Command):

    name = "participants:flags:stats"

    def get_parser(self, prog_name):
        parser = super(ParticipantStatesStatistics, self).get_parser(prog_name)
        parser.add_argument("--study", help="Study key", required=True)
        parser.add_argument("--page-size", help="page size", type=int, default=100)
        g = parser.add_mutually_exclusive_group(required=False)
        g.add_argument("--stats", help="Stats definition (using string format)")
        g.add_argument("--stats-file", help="Load stats definition from file")
        parser.add_argument("--output", help="Json output file", required=False, default=None)
        parser.add_argument("--no-print", help="Do not Print results", action="store_true", default=False)
        
        return parser  

    def take_action(self, args):
        client = self.app.get_management_api()

        study_key = args.study
        page_size = args.page_size

        pager = ParticpantStatePaginaged(client, page_size=page_size, study_key=study_key)

        collectors = None
        builder = CollectorBuilder()
        if args.stats:
            collectors = builder.from_string(args.stats)
        else:
            if args.stats_file:
                defs = read_yaml(args.stats_file)
                collectors = builder.from_list(defs)
            else:
                collectors = [ FieldCountCollector(FieldCountCollector.default_name)]
        
        collector = DataCollector()
        collector.register(*collectors)

        for r in pager:
           print("Fetching page %d with %d items" % (r.page, len(r)))
           for item in r.items:
                if 'flags' in item:
                    collector.collect(item['flags'])

        stats = collector.get_stats()
        
        if not args.no_print:
            stats.show()

        if args.output:
            d = stats.to_dict()
            write_json(args.output, d)


def expr_update_flag(name: str, value:str):
    return {
            "name": "UPDATE_FLAG",
            "data": [
                {
                    "str": name,
                    "dtype": "str"
                },
                {
                    "str": value,
                    "dtype": "str"
                }
            ]
            }
    
class ParticipantStatesSync(Command):
    """
        Synchronize flags values for participants
    """

    name = "participants:flags:sync"

    def get_parser(self, prog_name):
        parser = super(ParticipantStatesSync, self).get_parser(prog_name)
        parser.add_argument("--study", help="Study key", required=True)
        parser.add_argument("--page-size", help="page size", type=int, default=500)
        parser.add_argument("--file", help="Flags definition to update for each participants")
        parser.add_argument("--dry-run", help="Only look for sync do not update", action="store_true", default=False)
        return parser  

    def take_action(self, args):
        client = self.app.get_management_api()
        
        study_key = args.study
        page_size = args.page_size

        pager = ParticpantStatePaginaged(client, page_size=page_size, study_key=study_key)

        # Flags file is expected to be a dictionnary
        
        flags = read_json(args.file)
        if not isinstance(flags, dict):
            raise ValueError("Flags file does not contains a dictionary")        
        
        to_update = {}

        count_found = 0
        count_synced = 0
        for r in pager:
           print("Fetching page %d with %d items" % (r.page, len(r)))
           for item in r.items:
                participant_id = item['participantId']
                participant_status = item['studyStatus']
                flags_to_sync = flags.get(participant_id)
                if flags_to_sync is None:
                    continue
                if not isinstance(flags_to_sync, dict):
                    print("Warning entry for {} is not a dictionary, skipping".format(participant_id))
                    continue
                if participant_status == 'temporary':
                    print("Warning '{}' is temporary, not rules will be applied, skip".format(participant_id))
                    continue
                count_found += 1
                flags_current = item.get('flags', {})
                flags_update = {} 
                for name, value in flags_to_sync.items():
                    cur_value = flags_current.get(name)
                    if cur_value is None or cur_value != value:
                        flags_update[name] = value
                if len(flags_update) > 0:
                    to_update[participant_id] = flags_update
                else:
                    count_synced += 1 

        count_ok = 0
        count_applied = 0
        count_errors = 0         

        for participant_id, updates in to_update.items():
            rules = []
            print("Participant {}".format(participant_id), end=None)
            for flag_name, flag_value in updates.items():
                rules.append(expr_update_flag(flag_name, flag_value))
            try:
                rule_output = '?'
                if args.dry_run:
                    print("Dry run")
                else:
                    r = client.run_custom_study_rules_for_single_participant(study_key, rules, participant_id)
                    if isinstance(r, dict) and 'participantStateChangePerRule' in r:
                        changes = r['participantStateChangePerRule'][0]
                        if changes > 0:
                            rule_output = 'OK'
                            count_applied += 1
                        else:
                            rule_output = 'Not applied'
                count_ok += 1
                print(" ", rule_output)
            except Exception as e:
                print("Error ", e)
                count_errors += 1
        print("Summary")
        print("Sync file has {}".format(len(flags)))
        print("Participants found {}".format(count_found))
        print("Participants alreay synced {}, need to change for ".format(count_synced), len(to_update), )
        print("Applying changed Applied={}, OK={}, Errors={}".format(count_applied, count_ok, count_errors))


class ParticipantSurveysStatistics(Command):

    name = "participants:surveys:stats"

    def get_parser(self, prog_name):
        parser = super(ParticipantSurveysStatistics, self).get_parser(prog_name)
        parser.add_argument("--study", help="Study key", required=True)
        parser.add_argument("--page-size", help="page size", type=int, default=100)
        parser.add_argument("--status", help="Study status of participant", default='active')
        g = parser.add_mutually_exclusive_group(required=False)
        g.add_argument("--stats", help="Stats definition (using string format)")
        g.add_argument("--stats-file", help="Load stats definition from file")
        parser.add_argument("--output", help="Json output file", required=False, default=None)
        parser.add_argument("--no-print", help="Do not Print results", action="store_true", default=False)
        
        return parser  

    def take_action(self, args):
        client = self.app.get_management_api()

        study_key = args.study
        page_size = args.page_size

        study_status = args.status

        query = None
        if study_status != 'all':
            if study_status not in STUDY_PARTICIPANT_STATUS:
                print("Warning: unknown participant state")
            query={"studyStatus": study_status}

        pager = ParticpantStatePaginaged(client, page_size=page_size, study_key=study_key, query=query )

        stats = {}

        for r in pager:
           print("Fetching page %d with %d items" % (r.page, len(r)))
           for item in r.items:
                if 'assignedSurveys' in item:
                    for assigned in item['assignedSurveys']:
                        surveyKey = assigned['surveyKey']
                        category = assigned['category']
                        if surveyKey not in stats:
                            stats[surveyKey] = {}
                        if category not in stats[surveyKey]:
                            stats[surveyKey][category] = 0
                        stats[surveyKey][category] += 1
        
        if not args.no_print:
            print(stats)

        if args.output:
            write_json(args.output, stats)

register(ParticipantStatesSync)
register(ParticipantSurveysStatistics)
register(ParticipantStatesStatistics)