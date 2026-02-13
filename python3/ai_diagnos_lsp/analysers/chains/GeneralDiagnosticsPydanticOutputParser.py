from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from typing import List, Tuple, Union

class GeneralDiagnosticsPydanticObjekt(BaseModel):
    """This is the full diagnostics class. It is basically the root for JSON"""
    class SingleDiagnostic(BaseModel):
        """
        This is the single diagnostics item. 
        It has the location of the diagnostic, in an "Semantic anchor insdead of raw numbers" format, 
        Since in my previous versions the LLM constantly fucked the raw numbers up. 
        """

        location: Union[Tuple[str, int], str]
        error_message: str
        severity_level: int

    class Config:
        populate_by_name = True

    diagnostics: List[SingleDiagnostic]

def GeneralDiagnosticsOutputParserFactory() -> PydanticOutputParser:
    """
    This is the output parsers Factory function. 
    IDK why I made it a factory function. I could have simply made it an importable class, but I guess
    For consistansy of the codebases style ? 
    """

    return PydanticOutputParser(pydantic_object=GeneralDiagnosticsPydanticObjekt)


