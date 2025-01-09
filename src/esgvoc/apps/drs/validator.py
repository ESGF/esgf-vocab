from typing import cast
from esgvoc.api.models import ProjectSpecs, DrsType, DrsPart, DrsSpecification, DrsPartType, DrsCollection, DrsConstant
import esgvoc.api.projects as projects
import esgvoc.apps.drs.constants as constants

class DrsValidator:
    def __init__(self, project_id: str, pedantic: bool = False) -> None:
        self.project_id = project_id
        self.pedantic = pedantic
        project_specs: ProjectSpecs = projects.get_project_specs(project_id)
        for specs in project_specs.drs_specs:
            match specs.type:
                case DrsType.directory:
                    self.directory_specs = specs
                case DrsType.file_name:
                    self.file_name_specs = specs
                case DrsType.dataset_id:
                    self.dataset_id_specs = specs
                case _:
                    raise ValueError(f'unsupported DRS specs type {specs.type}')
    
    def tokenize(self,
                 drs_expression: str,
                 separator: str,
                 drs_type: DrsType) -> list[str]|None:
        cursor_offset = 0
        # Spaces at the beginning/end of expression:
        start_with_space = drs_expression[0].isspace()
        end_with_space = drs_expression[-1].isspace()
        if start_with_space or end_with_space:
            if self.pedantic:
                # TODO: create error
                print('tokenizer error: the expression is surrounded by white space[s]') # DEBUG
            else:
                # TODO: create warning
                print('tokenizer warning: the expression is surrounded by white space[s]') # DEBUG
            if start_with_space:
                previous_len = len(drs_expression)
                drs_expression = drs_expression.lstrip()
                cursor_offset = previous_len - len(drs_expression)
            if end_with_space:
                drs_expression = drs_expression.rstrip()
        tokens = drs_expression.split(separator)
        if len(tokens) < 2:
            # TODO: early exit
            print(f'unable to parse this expression {drs_expression}. Is it a DRS {drs_type} expression?') # DEBUG
            return None
        max_token_index = len(tokens)
        cursor_position = initial_cursor_position = len(drs_expression) + 1
        has_white_token = False
        for index in range(max_token_index-1, -1, -1):
            token = tokens[index]
            if (is_white_token := token.isspace()) or (not token):
                has_white_token = has_white_token or is_white_token
                cursor_position -= len(token) + 1
                del tokens[index]
                continue
            else:
                break
        if cursor_position != initial_cursor_position:
            max_token_index = len(tokens)
            if (drs_type == DrsType.directory) and (not has_white_token):
                print('tokenizer warning: extra / at the end of the expression')
            else:
                # TODO: create error
                print(f'tokenizer error: extra token at column {cursor_position+cursor_offset}')
        for index in range(max_token_index-1, -1, -1):
            token = tokens[index]
            len_token = len(token)
            if not token:
                column = cursor_position + cursor_offset
                if (drs_type != DrsType.directory) or self.pedantic or (index == 0):
                    # TODO: create error
                    print(f'tokenizer error: extra separator at column {column}')
                else:
                    # TODO: create warning
                    print(f'tokenizer warning: extra separator at column {column}')
                del tokens[index]
            if token.isspace():
                column = cursor_position + cursor_offset - len_token
                # TODO: create error
                print(f'tokenizer error: white token at position {column}')
                del tokens[index]
            cursor_position -= len_token + 1
        return tokens
    
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
                 specs: DrsSpecification,
                 has_to_remove_extension: bool):
        if has_to_remove_extension:
            # + 1 for the character dot.
            last_char_position = -1 * (len(specs.properties[constants.FILE_NAME_EXTENSION_KEY]) + 1)
            drs_expression = drs_expression[0:last_char_position]
        tokens = self.tokenize(drs_expression, specs.separator, specs.type)
        token_index = 0
        token_max_index = len(tokens)
        part_index = 0
        part_max_index = len(specs.parts)
        matching_code_mapping = dict()
        while part_index < part_max_index:
            token = tokens[token_index]
            part = specs.parts[part_index]
            print(f'{token=} part={part}') # DEBUG
            if self.validate_token(token, part):
                token_index += 1
                part_index += 1
                matching_code_mapping[part.__str__()] = 0
                print('OK') # DEBUG
            elif part.kind == DrsPartType.constant or \
                 cast(DrsCollection, part).is_required:
                # TODO: create error
                print(f'error on token {token} concerning collection {part}') # DEBUG
                matching_code_mapping[part.__str__()] = 1
                token_index += 1
                part_index += 1
            else: # The part is not required so try to match the token with the next part.
                part_index += 1
                print('try to match token with the next part') # DEBUG
                matching_code_mapping[part.__str__()] = -1
            if token_index == token_max_index:
                break
        # Cases:
        # - All tokens and collections have been processed.
        # - Not enough token to process all collections.
        # - Extra tokens left whereas all collections have been processed:
        #   + The last collections are required => report extra tokens.
        #   + The last collections are not required and these tokens were not validated by them.
        #     => Should report error even if the collections are not required.
        if part_index < part_max_index: # Not enough token.
            for index in range(part_index, part_max_index):
                part = specs.parts[index]
                if part.is_required:
                    # TODO: create error
                    print(f'error: missing token for collection {part}') # DEBUG
                else:
                    # TODO: create a warning
                    print(f'warning: missing token for collection {part}') # DEBUG
        elif token_index < token_max_index: # Extra tokens.
            part_index -= token_max_index - token_index
            for index in range(token_index, token_max_index):
                token = tokens[token_index]
                part = specs.parts[part_index]
                if part.is_required:
                    # TODO: create error extra token
                    print(f'error: extra token {token}') # DEBUG
                else:
                    if matching_code_mapping[part.__str__()] < 0:
                        # TODO: create error extra token or invalidated token by an optional collection.
                        print(f'error: extra token {token} or invalidated token by an optional ' +
                              f'collection {part}') # DEBUG
                    else:
                        # TODO: create error extra token
                        print(f'error: extra token {token}') # DEBUG
                part_index += 1

    def validate_directory(self, drs_expression: str):
        return self.validate(drs_expression, self.directory_specs, False)
    
    def validate_dataset_id(self, drs_expression: str):
        return self.validate(drs_expression, self.dataset_id_specs, False)

    def validate_file_name(self, drs_expression: str):
        return self.validate(drs_expression, self.file_name_specs, True)


if __name__ == "__main__":
    project_id = 'cmip6plus'
    validator = DrsValidator(project_id)
    drs_expressions = [
            "  CMIP6Plus/CMIP/NCC/MIROC6/amip//r2i2p1f2/ACmon/od550aer/gn/v20190923/ // "
        ]
    for drs_expression in drs_expressions:
        validator.validate_directory(drs_expression)
    