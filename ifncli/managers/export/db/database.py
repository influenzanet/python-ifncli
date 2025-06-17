##
# Export Database description
# The export database is an intermediate database containing row data export and survey info
# It aims at synchronizing data download from the platform

from ....utils.sqlite import SqliteDb
from typing import Optional

class ExportMeta:

    def __init__(self, key_separator:str):
        self.key_separator = key_separator

class ExportDatabase(SqliteDb):
    
    def __init__(self, db_path, allow_create=False):
        super().__init__(db_path, allow_create)
        self.meta: Optional[ExportMeta] = None

    def export_meta_table(self):
        return "export_meta"

    def import_log_table(self):
        return "import_log"
    
    def response_table(self, survey_key):
        table_name = "responses_{survey_key}".format(survey_key=survey_key)
        return table_name

    def get_meta(self):
        if self.meta is None:
            meta_table = self.export_meta_table()
            meta = self.fetch_one('select key_separator from {}'.format(meta_table))
            if meta is None:
                raise Exception("Meta table is empty or doesnt exist")
            self.meta = ExportMeta(meta[0])
        return self.meta

    def get_survey_info(self, survey_key:str):
        """
            Get Surveys version info for a given survey
        """
        return self.fetch_all("select version, data from survey_info where survey=:survey", {"survey": survey_key})
        
    def get_survey_versions(self, survey_key:str):
        """
            Get Survey versions
        """
        for row in self.fetch_all("select version from survey_info where survey=:survey", {"survey": survey_key}):
            yield row[0]
    