
import json
from typing import Optional
from influenzanet.surveys.preview.schema import SurveySchemaBuilder
from influenzanet.surveys.preview import preview_from_json
from ..database import ExportDatabase
from .version_selector import VersionSelectorRule

class SurveySchema:
    """
        Survey Schema maintain information about the target schema for a survey (how to build table columns)
    """

    def __init__(self, survey_key:str, ):
        self.survey_key = survey_key
        self.column_types: dict[str, str] = {}

    def from_export_db(self, db: ExportDatabase, versionSelector: Optional[VersionSelectorRule]=None):
        meta = db.get_meta()
        builder = SurveySchemaBuilder(separator=meta.key_separator, prefix="")
        for row in db.get_survey_info(self.survey_key):
            version = row[0]
            if versionSelector is not None:
                if not versionSelector.is_version(version):
                    continue
            data = json.loads(row[1])
            info = preview_from_json(data)
            builder.build_survey(info)
        schema = builder.schema
        self.column_types = schema.get_column_types()
        return schema

    def override(self, columns: dict[str,str]):
        for name, col_type in columns.items():
            self.column_types[name] = col_type

    def to_readable(self):
        cols = []
        for name, col_type in self.column_types.items():
            cols.append( "{}: {}".format(name, col_type))
        return cols
