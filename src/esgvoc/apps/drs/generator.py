from typing import cast, Iterable, Mapping, Any

import esgvoc.api.projects as projects

from esgvoc.api.models import (DrsSpecification,
                               DrsPartType,
                               DrsCollection,
                               DrsConstant)

from esgvoc.apps.drs.validator import DrsApplication
from esgvoc.apps.drs.report import (DrsGeneratorReport,
                                    GeneratorIssue,
                                    TooManyWordsCollection,
                                    InvalidToken,
                                    MissingToken,
                                    ConflictingCollections,
                                    AssignedWord)


def _get_first_item(items: set[Any]) -> Any:
    result = None
    for result in items:
        break
    return result


class DrsGenerator(DrsApplication):
    
    def generate_directory_from_mapping(self, mapping: Mapping[str, str]) -> DrsGeneratorReport:
        return self.generate_from_mapping(mapping, self.directory_specs)
    
    def generate_directory_from_bag_of_words(self, words: Iterable[str]) -> DrsGeneratorReport:
        return self.generate_from_bag_of_words(words, self.directory_specs)

    def generate_dataset_id_from_mapping(self, mapping: Mapping[str, str]) -> DrsGeneratorReport:
        return self.generate_from_mapping(mapping, self.dataset_id_specs)
    
    def generate_dataset_id_from_bag_of_words(self, words: Iterable[str]) -> DrsGeneratorReport:
        return self.generate_from_bag_of_words(words, self.dataset_id_specs)
    
    # Without file name extension.
    def generate_file_name_from_mapping(self, mapping: Mapping[str, str]) -> DrsGeneratorReport:
        report = self.generate_from_mapping(mapping, self.file_name_specs)
        report.computed_drs_expression = report.computed_drs_expression + self.get_full_file_name_extension()
        return report 
    
    # Without file name extension.
    def generate_file_name_from_bag_of_words(self, words: Iterable[str]) -> DrsGeneratorReport:
        report = self.generate_from_bag_of_words(words, self.file_name_specs)
        report.computed_drs_expression = report.computed_drs_expression + self.get_full_file_name_extension()
        return report 

    def generate_from_mapping(self, mapping: Mapping[str, str],
                              specs: DrsSpecification) -> DrsGeneratorReport:
        drs_expression, errors, warnings = self._generate_from_mapping(mapping, specs, True)
        return DrsGeneratorReport(mapping, mapping, drs_expression, errors, warnings)
    
    def generate_from_bag_of_words(self, words: Iterable[str], specs: DrsSpecification) \
                                                        -> DrsGeneratorReport:
        collection_words_mapping: dict[str, set[str]] = dict()
        for word in words:
            matching_terms = projects.valid_term_in_project(word, self.project_id)
            for matching_term in matching_terms:
                if matching_term.collection_id not in collection_words_mapping:
                    collection_words_mapping[matching_term.collection_id] = set()
                collection_words_mapping[matching_term.collection_id].add(word)
        collection_words_mapping, warnings = DrsGenerator._resolve_conflicts(collection_words_mapping)
        mapping, errors = DrsGenerator._check_collection_words_mapping(collection_words_mapping)
        drs_expression, errs, warns = self._generate_from_mapping(mapping, specs, False)
        errors.extend(errs)
        warnings.extend(warns)
        return DrsGeneratorReport(mapping, mapping, drs_expression, errors, warnings)

    def _generate_from_mapping(self, mapping: Mapping[str, str],
                               specs: DrsSpecification,
                               has_to_valid_terms: bool)\
                                   -> tuple[str, list[GeneratorIssue], list[GeneratorIssue]]:
        errors: list[GeneratorIssue] = list()
        warnings: list[GeneratorIssue] = list()
        drs_expression = ""
        part_position: int = 0
        for part in specs.parts:
            part_position += 1
            if part.kind == DrsPartType.collection:
                collection_part = cast(DrsCollection, part)
                collection_id = collection_part.collection_id
                if collection_id in mapping:
                    part_value = mapping[collection_id]
                    if has_to_valid_terms:
                        matching_terms = projects.valid_term_in_collection(part_value,
                                                                           self.project_id,
                                                                           collection_id)
                        if not matching_terms:
                            issue = InvalidToken(part_value, part_position, collection_id)
                            errors.append(issue)
                            part_value = DrsGeneratorReport.INVALID_TAG
                else:
                    other_issue = MissingToken(collection_id, part_position)
                    if collection_part.is_required:
                        errors.append(other_issue)
                        part_value = DrsGeneratorReport.MISSING_TAG
                    else:
                        warnings.append(other_issue)
                        continue # The for loop.
            else:
                constant_part = cast(DrsConstant, part)
                part_value = constant_part.value
            
            drs_expression += part_value + specs.separator
        
        drs_expression = drs_expression[0:len(drs_expression)-len(specs.separator)]
        return drs_expression, errors, warnings
    
    @staticmethod
    def _resolve_conflicts(collection_words_mapping: dict[str, set[str]]) \
                                            -> tuple[dict[str, set[str]], list[GeneratorIssue]]:
        warnings: list[GeneratorIssue] = list()
        conflicting_collection_ids_list: list[list[str]] = list()
        collection_ids: list[str] = list(collection_words_mapping.keys())
        len_collection_ids: int = len(collection_ids)
        
        for l_collection_index in range(0, len_collection_ids - 1):
            conflicting_collection_ids: list[str] = list()
            for r_collection_index in range(l_collection_index + 1, len_collection_ids):
                if collection_words_mapping[collection_ids[l_collection_index]].isdisjoint \
                       (collection_words_mapping[collection_ids[r_collection_index]]):
                    continue
                else:
                    not_registered = True
                    for cc_ids in conflicting_collection_ids_list:
                        if collection_ids[l_collection_index] in cc_ids and \
                           collection_ids[r_collection_index] in cc_ids:
                            not_registered = False
                            break
                    if not_registered:
                        conflicting_collection_ids.append(collection_ids[r_collection_index])
            if conflicting_collection_ids:
                conflicting_collection_ids.append(collection_ids[l_collection_index])
                conflicting_collection_ids_list.append(conflicting_collection_ids)

        # Each time a collection is resolved, we must restart the loop so as to check if others can be,
        # until no progress is made.
        while True:
            # 1. Non-conflicting collections with only one word are assigned.
            #    Non-conflicting collections with more than one word will be raise an error
            #    in the _check method.
            
            #    Nothing to do.

            # 2a. Collections with one word that are conflicting to each other will raise an error.
            #     We don't search for collection with more than one word which word sets are exactly
            #     the same, because we cannot choose which word will be removed in 2b.
            #     So stick with one word collections: those collection will be detected in method _check.
            collection_ids_with_len_eq_1_list: list[list[str]] = list()
            for collection_ids in conflicting_collection_ids_list:
                tmp_conflicting_collection_ids: list[str] = list()
                for collection_id in collection_ids:
                    if len(collection_words_mapping[collection_id]) == 1:
                        tmp_conflicting_collection_ids.append(collection_id)
                if len(tmp_conflicting_collection_ids) > 1:
                    collection_ids_with_len_eq_1_list.append(tmp_conflicting_collection_ids)
            # 2b. As it is not possible to resolve collections sharing the same unique word:
            #     raise errors, remove the faulty collections and their word.
            if collection_ids_with_len_eq_1_list:
                for collection_ids_to_be_removed in collection_ids_with_len_eq_1_list:
                    DrsGenerator._remove_ids_from_conflicts(conflicting_collection_ids_list,
                                                            collection_ids_to_be_removed)
                    DrsGenerator._remove_word_from_other_word_sets(collection_words_mapping,
                                                      collection_ids_to_be_removed)
                # Every time conflicting_collection_ids_list is modified, we must restart the loop,
                # as conflicting collections may be resolved.
                continue

            # 3.a For each collections with only one word, assign their word to the detriment of
            #    collections with more than one word.
            wining_collection_ids: list[str] = list()
            for collection_ids in conflicting_collection_ids_list:
                for collection_id in collection_ids:
                    if len(collection_words_mapping[collection_id]) == 1:
                        wining_collection_ids.append(collection_id)
                        word = _get_first_item(collection_words_mapping[collection_id])
                        issue = AssignedWord(collection_id, word)
                        warnings.append(issue)
            # 3.b Update conflicting collections.
            if wining_collection_ids:
                DrsGenerator._remove_ids_from_conflicts(conflicting_collection_ids_list,
                                                        wining_collection_ids)
                DrsGenerator._remove_word_from_other_word_sets(collection_words_mapping,
                                                  wining_collection_ids)
                # Every time conflicting_collection_ids_list is modified, we must restart the loop,
                # as conflicting collections may be resolved.
                continue

            # 4.a For each word set of the remaining conflicting collections, compute their difference.
            #    If the difference is one word, this word is assigned to the collection that owns it.
            wining_id_and_word_pairs: list[tuple[str, str]] = list()
            for collection_ids in conflicting_collection_ids_list:
                for collection_index in range(0, len(collection_ids)):
                    diff: set[str] = collection_words_mapping[collection_ids[collection_index]]\
                                         .difference(
                                                     *[collection_words_mapping[index]
                                               for index in collection_ids[collection_index + 1 :] +\
                                                        collection_ids[:collection_index]
                                                      ]
                                                    )
                    if len(diff) == 1:
                        wining_id_and_word_pairs.append((collection_ids[collection_index],
                                                         _get_first_item(diff)))
            # 4.b Update conflicting collections.
            if wining_id_and_word_pairs:
                wining_collection_ids = list()
                for collection_id, word in wining_id_and_word_pairs:
                    wining_collection_ids.append(collection_id)
                    collection_words_mapping[collection_id].clear()
                    collection_words_mapping[collection_id].add(word)
                    issue = AssignedWord(collection_id, word)
                    warnings.append(issue)
                DrsGenerator._remove_ids_from_conflicts(conflicting_collection_ids_list,
                                                        wining_collection_ids)
                DrsGenerator._remove_word_from_other_word_sets(collection_words_mapping,
                                                               wining_collection_ids)
                continue
            else:
                break # Stop the loop when no progress is made.
        return collection_words_mapping, warnings

    @staticmethod
    def _check_collection_words_mapping(collection_words_mapping: dict[str, set[str]]) \
                                                     -> tuple[dict[str, str], list[GeneratorIssue]]:
        errors: list[GeneratorIssue] = list()
        # 1. Looking for collections that share strictly the same word(s).
        collection_ids: list[str] = list(collection_words_mapping.keys())
        len_collection_ids: int = len(collection_ids)
        faulty_collections_list: list[set[str]] = list()
        for l_collection_index in range(0, len_collection_ids - 1):
            l_collection_id = collection_ids[l_collection_index]
            l_word_set = collection_words_mapping[l_collection_id]
            for r_collection_index in range(l_collection_index + 1, len_collection_ids):
                r_collection_id = collection_ids[r_collection_index]
                r_word_set = collection_words_mapping[r_collection_id]
                if not l_word_set.difference(r_word_set):
                    not_registered = True
                    for faulty_collections in faulty_collections_list:
                        if l_collection_id in faulty_collections or \
                           r_collection_id in faulty_collections:
                            faulty_collections.add(l_collection_id)
                            faulty_collections.add(r_collection_id)
                            not_registered = False
                            break
                    if not_registered:
                        faulty_collections_list.append({l_collection_id, r_collection_id})
        for faulty_collections in faulty_collections_list:
            words = collection_words_mapping[_get_first_item(faulty_collections)]
            issue = ConflictingCollections(list(faulty_collections), list(words))
            errors.append(issue)
            for collection_id in faulty_collections:
                del collection_words_mapping[collection_id]
        
        # 2. Looking for collections with more than one word.
        result: dict[str, str] = dict()
        for collection_id, word_set in collection_words_mapping.items():
            len_word_set = len(word_set)
            if len_word_set == 1:
                result[collection_id] = _get_first_item(word_set)
            elif len_word_set > 1:
                other_issue = TooManyWordsCollection(collection_id, list(word_set))
                errors.append(other_issue)
            #else: Don't add emptied collection to the result.
        return result, errors

    @staticmethod
    def _remove_word_from_other_word_sets(collection_words_mapping: dict[str, set[str]],
                                          collection_ids_to_be_removed: list[str]) -> None:
        for collection_id_to_be_removed in collection_ids_to_be_removed:
            # Should only be one word.
            word_to_be_removed: str = _get_first_item(collection_words_mapping[collection_id_to_be_removed])
            for collection_id in collection_words_mapping.keys():
                if (collection_id not in collection_ids_to_be_removed):
                    collection_words_mapping[collection_id].discard(word_to_be_removed)

    @staticmethod
    def _remove_ids_from_conflicts(conflicting_collection_ids_list: list[list[str]],
                                   collection_ids_to_be_removed: list[str]) -> None:
        for collection_id_to_be_removed in collection_ids_to_be_removed:
            for conflicting_collection_ids in conflicting_collection_ids_list:
                if collection_id_to_be_removed in conflicting_collection_ids:
                    conflicting_collection_ids.remove(collection_id_to_be_removed)


if __name__ == "__main__":
    mapping = {'c0': {'w0'}, 'c1': {'w0'}, 'c2': {'w1'}, 'c3': {'w2'}}
    print(DrsGenerator._check_collection_words_mapping(mapping))