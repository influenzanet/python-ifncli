from cliff.command import Command
from . import register
from ..utils import read_yaml, write_json
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

register(ParticipantSurveysStatistics)
register(ParticipantStatesStatistics)