from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from typing import List

def GeneralDiagnosticsOutputParserFactory() -> PydanticOutputParser:
    class DiagnosticsPydanticObjekt(BaseModel):
        class SingleDiagnostic(BaseModel):

            location: str
            error_message: str
            severity_level: int

        class Config:
            populate_by_name = True

        diagnostics: List[SingleDiagnostic]

    return PydanticOutputParser(pydantic_object=DiagnosticsPydanticObjekt)


