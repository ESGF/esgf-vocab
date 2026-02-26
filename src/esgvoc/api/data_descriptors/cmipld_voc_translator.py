'''
A pydantic class used to translate from the CMIP JSON-ld to esgvoc for validation.  
This is to be used as a wrapper in the validation of form input and repository contents ensuring compliance to both standards. 

'''


from typing import TypeVar, Generic, Type
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

class pycmipld(BaseModel, Generic[T]):
    '''
    A wrapper class to translate CMIP JSONLD format to the ESGVOC compatible pydantic models. 

    Usage:
      model = pycmipld(HorizontalGridCells, **data_dictionary)

      # Get a fromatted table for issue updates:
      validation = model.validation_md
      
      # Optional print the table to console.
      if validation: print(validation)
    '''
  
    data: T | None = None
    _model: Type[T]
    validation_md: str | None = None  # Stores validation warnings/errors as Markdown

    def __init__(self, model: Type[T], **cmip_ld_data):
        self._model = model
        translated = self._prepare_dict(cmip_ld_data)
        # Attempt validation
        try:
            validated_data = self._model.model_validate(translated)
            super().__init__(data=validated_data)
        except ValidationError as e:
            # Capture errors as Markdown instead of raising
            super().__init__(data=None, _model=model, validation_md=self._errors_to_md(e))


  
    def _prepare_dict(self, values: dict) -> dict:
        """Translate JSON-LD to model dict; convert empty strings to None."""
        # Always a list for @type
        raw_type = values.get("@type", [])
        type_value = next((t.replace('esgvoc:', '') for t in raw_type if 'esgvoc:' in t), None)

        # Build translated dict
        translated = {
            k: (v if v != '' else None)  # convert empty strings to None
            for k, v in {
                "id": values.get("@id"),
                "type": type_value,
                "context": values.get("@context"),
                "drs_name": values.get("validation_key"),
                **{k: v for k, v in values.items() if not k.startswith("@")}
            }.items()
        }
        return translated

    def _errors_to_md(self, err: ValidationError) -> str:
        """Convert ValidationError into a pretty Markdown table."""
        headers = ["Field", "Error Type", "Input Value", "Input Type", "Message"]
        rows = []

        for e in err.errors():
            loc = ".".join(str(x) for x in e.get("loc", ["unknown"]))
            err_type = e.get("type", "")
            input_value = e.get("ctx", {}).get("given", e.get("input_value", None))
            input_type = type(input_value).__name__ if input_value is not None else "None"
            msg = e.get("msg", "").replace("\n", "<br>")
            rows.append([loc, err_type, f"`{input_value}`", input_type, msg])

        md = "| " + " | ".join(f"**{h}**" for h in headers) + " |\n"
        md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        for row in rows:
            md += "| " + " | ".join(str(c) for c in row) + " |\n"
        return md

