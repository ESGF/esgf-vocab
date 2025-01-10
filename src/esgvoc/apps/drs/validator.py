from typing import cast
from esgvoc.api.models import ProjectSpecs, DrsType, DrsPart, DrsSpecification, DrsPartType, DrsCollection, DrsConstant
import esgvoc.api.projects as projects
import esgvoc.apps.drs.constants as constants


class DrsValidator:
    # dict[project_id: dict[collection_id: set[token]]]
    _validated_token_cache: dict[str, dict[str, set[str]]] = dict()
    
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
        if self.project_id not in DrsValidator._validated_token_cache:
            DrsValidator._validated_token_cache[self.project_id] = dict()
    
    def parse(self,
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
                    if part.collection_id not in DrsValidator._validated_token_cache[self.project_id]:
                        DrsValidator._validated_token_cache[self.project_id][part.collection_id] = set()
                    if token in DrsValidator._validated_token_cache[self.project_id][part.collection_id]:
                        return True
                    else:
                        # TODO: handle exceptions?
                        try:
                            matching_terms = projects.valid_term_in_collection(token,
                                                                               self.project_id,
                                                                               part.collection_id)
                        except Exception as e:
                            print(f'problem while validating token: {e}. Pass.') # DEBUG
                            return True # DEBUG
                        if len(matching_terms) > 0:
                            DrsValidator._validated_token_cache[self.project_id][part.collection_id].add(token)
                            return True
                        else:
                            return False
            case DrsPartType.constant:
                part: DrsConstant = cast(DrsConstant, part)
                return part.value != token
            case _:
                raise ValueError(f'unsupported DRS specs part type {part.kind}')

    def validate(self,
                 drs_expression: str,
                 specs: DrsSpecification):
        tokens = self.parse(drs_expression, specs.separator, specs.type)
        if not tokens:
            # TODO: forward error.
            pass
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
        return self.validate(drs_expression, self.directory_specs)
    
    def validate_dataset_id(self, drs_expression: str):
        return self.validate(drs_expression, self.dataset_id_specs)

    def validate_file_name(self, drs_expression: str):
        specs = self.file_name_specs
        full_extension = specs.properties[constants.FILE_NAME_EXTENSION_SEPARATOR_KEY] + \
                         specs.properties[constants.FILE_NAME_EXTENSION_KEY]
        if drs_expression.endswith(full_extension):
            drs_expression = drs_expression.replace(full_extension, '')
            return self.validate(drs_expression, self.file_name_specs)
        else:
            # TODO: create error
            print(f"filename error: filename extension missing or not compliant ('{full_extension}')") # DEBUG


if __name__ == "__main__":
    project_id = 'cmip6plus'
    validator = DrsValidator(project_id)
    drs_expressions = [
"od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_202211-202212.nc",
"od550aer_ACmon_MIROC6_amip_r2i2p1f2_gn_202111-202112.nc",
        ]
    import time
    for drs_expression in drs_expressions:
        start_time = time.perf_counter_ns()
        validator.validate_file_name(drs_expression)
        stop_time = time.perf_counter_ns()
        print(f'elapsed time: {(stop_time-start_time)/1000000}')
    