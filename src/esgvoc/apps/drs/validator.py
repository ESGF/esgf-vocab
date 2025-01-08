from typing import cast
from esgvoc.api.models import ProjectSpecs, DrsType, DrsPart, DrsSpecification, DrsPartType, DrsCollection, DrsConstant
import esgvoc.api.projects as projects

class DrsValidator:
    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        project_specs: ProjectSpecs = projects.get_project_specs(project_id)
        for specs in project_specs.drs_specs:
            match specs.type:
                case DrsType.directory:
                    self.directory_specs = specs
                case DrsType.file_name:
                    self.filename_specs = specs
                case DrsType.dataset_id:
                    self.dataset_id_specs = specs
                case _:
                    raise ValueError(f'unsupported DRS specs type {specs.type}')
    
    def tokenize(self, drs_expression: str, separator: str) -> list[str]:
        return drs_expression.split(separator)
    
    def clean_expression(drs_expression: str, separator) -> str:
        return drs_expression.strip().strip(separator)

    def validate_token(self, token: str, part: DrsPart) -> bool:
        match part.kind:
            case DrsPartType.collection:
                    part: DrsCollection = cast(DrsCollection, part)
                    # TODO: handle exceptions?
                    try:
                        matching_terms = projects.valid_term_in_collection(token,
                                                                           self.project_id,
                                                                           part.collection_id)
                    except Exception as e:
                        # DEBUG
                        print(f'problem while validating token: {e}. Pass.')
                        return True
                    return len(matching_terms) > 0
            case DrsPartType.constant:
                part: DrsConstant = cast(DrsConstant, part)
                return part.value != token
            case _:
                raise ValueError(f'unsupported DRS specs part type {part.kind}')

    def validate(self,
                 drs_expression: str,
                 specs: DrsSpecification):
        drs_expression = DrsValidator.clean_expression(drs_expression, specs.separator)
        tokens = self.tokenize(drs_expression, specs.separator)
        token_index = 0
        token_max_index = len(tokens)
        part_index = 0
        part_max_index = len(specs.parts)
        while part_index < part_max_index:
            token = tokens[token_index]
            part = specs.parts[part_index]
            print(f'{token=} part={part}') # DEBUG
            if self.validate_token(token, part):
                token_index += 1
                part_index += 1
                print('OK') # DEBUG
            elif part.kind == DrsPartType.constant or \
                 cast(DrsCollection, part).is_required:
                # TODO: create error
                print(f'error on token {token} concerning collection {part}') # DEBUG
                token_index += 1
                part_index += 1
            else: # The part is not required so try to match the token with the next part.
                part_index += 1
                print('try to match token with the next part') # DEBUG
            if token_index == token_max_index:
                break
        if part_index < part_max_index:
            # Not enough token.
            for index in range(part_index, part_max_index):
                part = specs.parts[index]
                # TODO: create error
                print(f'missing token for collection {part}') # DEBUG
        elif token_index < token_max_index:
            # Extra tokens.
            for index in range(token_index, token_max_index):
                token = tokens[index]
                # TODO: create error
                print(f'extra token {token}') # DEBUG

    def validate_directory(self, drs_expression: str):
        return self.validate(drs_expression, self.directory_specs)


if __name__ == "__main__":
    project_id = 'cmip6plus'
    validator = DrsValidator(project_id)
    drs_expressions = [
            "CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923",
            " CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923  ",
            "CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/",
            "/CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923/",
            "//CMIP6Plus/CMIP/NCC/MIROC6/amip/r2i2p1f2/ACmon/od550aer/gn/v20190923//"
        ]
    for drs_expression in drs_expressions:
        validator.validate_directory(drs_expression)
    