from django.db import models
from .pydance_objects import *
from .pydance_tables import *
from .award_calculator import *

from glob import glob
import json
import os
import shutil

# generic helper functions
def dump_json(json_dict, filepath):
    with open(filepath, "w", encoding='utf8') as file:
        json.dump(json_dict, file, indent=4)

def read_json(filepath):
    json_dict = {}
    with open(filepath, "r", encoding='utf8') as file:
        json_dict = json.load(file)
    return json_dict

def get_or_create_dir(dir_path):
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
    return dir_path

def _get_data_path(section_id="", round_id=None):
    app_data_path = 'data'
    if section_id:
        app_data_path += f'/sections/{section_id}'
    if round_id:
        app_data_path += f'/{round_id}'
    return app_data_path

# wrapper classes
class Award(PyDanceObject):
    def __init__(self, id, name=''):
        super().__init__(id, name)

class Heat:
    """wrapper object for basic heat information (dance, no, competitors)"""
    def __init__(self, dance, no, competitors):
        self.dance = dance
        self.no = no
        self.competitors = competitors


# DAO classes
class Conf:
    def __init__(self, name=''):
        self.name = name
        self.max_heat_size = 8  # use maximum number of competitors in a final round per default
        self.dances = []
        self.sections = []
        self.section_groups = []
        self.awards = []
        self.section_id_or_rules_per_award = []

    def get_ungrouped_sections(self):
        sections = self.sections.copy()
        for section_group in self.section_groups:
            for section in section_group.sections:
                if section in sections:
                    sections.remove(section)
        return sections

    def to_dict(self):
        conf_dict = {}
        conf_dict['name'] = self.name
        conf_dict['max_heat_size'] = self.max_heat_size
        conf_dict['dances'] = {dance.to_dict() for dance in self.dances}
        conf_dict['sections'] = {section.id: section.name for section in self.sections}
        conf_dict['dances_per_section'] = {section.id: [dance.id for dance in section.dances] for section in self.sections}
        conf_dict['additional_dances_per_section'] = {section.id: [dance.id for dance in section.additional_dances] for section in self.sections}
        conf_dict['section_groups'] = {section_group.id: section_group.name for section_group in self.section_groups}
        conf_dict['sections_per_group'] = {section_group.id: [section.id for section in section_group.sections] for section_group in self.section_groups}
        conf_dict['awards'] = {award.to_dict() for award in self.awards}
        conf_dict['sections_per_award'] = self.section_id_or_rules_per_award
        return conf_dict

    def _get_dances(conf_dict):
        if 'dances' in conf_dict:
            dance_dict = conf_dict['dances']
            return [Dance(dance_id, dance_dict[dance_id]) for dance_id in dance_dict]

    @staticmethod
    def from_dict(conf_dict):
        conf = Conf(conf_dict['name'])
        if 'max_heat_size' in conf_dict:
            if isinstance(conf_dict['max_heat_size'], int):
                conf.max_heat_size = conf_dict['max_heat_size']
            else:
                print("ERR")
        conf.dances = Conf._get_dances(conf_dict)

        # get sections and add info from app/data
        competitor_start_table = CompetitorStartTables.get()
        adjudicator_start_table = AdjudicatorStartTables.get()
        section_dict = conf_dict['sections']
        for section_id in section_dict:
            name = section_dict[section_id]
            dances_per_section = conf_dict['dances_per_section']
            dances = []
            if section_id in dances_per_section:
                for dance in conf.dances:
                    if dance.id in dances_per_section[section_id]:
                        dances.append(dance)
            additional_dances = []
            if 'additional_dances_per_section' in conf_dict:
                additional_dances_per_section = conf_dict['additional_dances_per_section']
                if section_id in additional_dances_per_section:
                    for dance in conf.dances:
                        if dance.id in additional_dances_per_section[section_id]:
                            additional_dances.append(dance)
            section = Section(section_id, name, dances, additional_dances)

            # add competitors and andjudicators
            if competitor_start_table:
                section.competitors = competitor_start_table.get_ids(section.id)
            if adjudicator_start_table:
                section.adjudicators = adjudicator_start_table.get_ids(section.id)
            conf.sections.append(section)

        # get section groups
        section_group_dict = conf_dict['section_groups']
        for section_group_id in section_group_dict:
            name = section_group_dict[section_group_id]#['name']
            sections_per_group = conf_dict['sections_per_group']
            sections = []
            if section_group_id in sections_per_group:
                for section in conf.sections:
                    if section.id in sections_per_group[section_group_id]:
                        sections.append(section)
            conf.section_groups.append(SectionGroup(section_group_id, name, sections))

        if 'awards' in conf_dict:
            award_dict = conf_dict['awards']
            conf.awards = [Award(award_id, award_dict[award_id]) for award_id in award_dict]
        if 'sections_per_award' in conf_dict:
            conf.section_id_or_rules_per_award = conf_dict['sections_per_award']
        return conf

    @staticmethod
    def get():
        return Conf.from_dict(read_json(f'{_get_data_path()}/conf.json'))

    def save(self):
        dump_json(self.to_dict(), f'{_get_data_path()}/conf.json')

class CompetitorStartTables:
    def _get_filepath():
        return f'{_get_data_path()}/competitors.csv'

    def get():
        filepath = CompetitorStartTables._get_filepath()
        if os.path.exists(filepath):
            return StartTable.read_csv(filepath)

    def get_lead(competitor_start_table, competitor):
        if competitor.isdigit():
            competitor = int(competitor)
            table = competitor_start_table.to_frame()
            if competitor in table.index:
                competitor_row = table.loc[competitor]
                return Person(competitor, competitor_row['lead_surname'], competitor_row['lead_first_name'], competitor_row['lead_team'])
        return Person(competitor)

    def get_follow(competitor_start_table, competitor):
        if competitor.isdigit():
            competitor = int(competitor)
            table = competitor_start_table.to_frame()
            if competitor in table.index:
                competitor_row = table.loc[competitor]
                return Person(competitor, competitor_row['follow_surname'], competitor_row['follow_first_name'], competitor_row['follow_team'])
        return Person(competitor)

    def get_registered_sections(competitor_start_table, competitor):
        if competitor.isdigit():
            return  [Section(section_id) for section_id in competitor_start_table.get_participations(int(competitor))]
        return []

    def get_preregistered_sections(competitor_start_table, competitor):
        if competitor.isdigit():
            return  [Section(section_id) for section_id in competitor_start_table.get_preregistrations(int(competitor))]
        return []

    def set(competitor_start_table, competitor, registered_sections, lead=None, follow=None):
        if competitor.isdigit():
            competitor = int(competitor)
            for section in Conf.get().sections:
                if section not in Sections.get_uneditable():
                    if section in registered_sections:
                        competitor_start_table.add_participation(competitor, section.id)
                    else:
                        competitor_start_table.remove_participation(competitor, section.id)
            # TODO: move to pydance_tables
            if lead:
                competitor_start_table._df.at[competitor, "lead_first_name"] = lead.first_name
                competitor_start_table._df.at[competitor, "lead_surname"] = lead.name
                competitor_start_table._df.at[competitor, "lead_team"] = lead.team
            if follow:
                competitor_start_table._df.at[competitor, "follow_first_name"] = follow.first_name
                competitor_start_table._df.at[competitor, "follow_surname"] = follow.name
                competitor_start_table._df.at[competitor, "follow_team"] = follow.team
        CompetitorStartTables.save(competitor_start_table)

    def save(competitor_start_table):
        if not competitor_start_table:
            return
        competitor_start_table.to_csv(CompetitorStartTables._get_filepath())


class AdjudicatorStartTables:
    def _get_filepath():
        return f'{_get_data_path()}/adjudicators.csv'

    def get():
        filepath = AdjudicatorStartTables._get_filepath()
        if os.path.exists(filepath):
            return AdjudicatorStartTable.read_csv(filepath)

class Dances:
    def get(dance_id):
        # do not store dances separately but always read them from conf
        for dance in Conf.get().dances:
            if dance.id == dance_id:
                return dance

class Sections:
    def _get_dir(section_id):
        return f'{_get_data_path(section_id)}'

    def _get_filepath(section_id):
        return f'{Sections._get_dir(section_id)}/section.json'

    def _get_results_path(section_id):
        return f'{Sections._get_dir(section_id)}/results.csv'

    def get(section_id):
        filepath = Sections._get_filepath(section_id)
        if os.path.exists(filepath):
            return Section.from_dict(read_json(filepath))

    def get_all():
        sections = []
        for section in Conf.get().sections: # use sort order from conf
            section = Sections.get(section.id)
            if section:
                sections.append(section)
        return sections

    def get_running():
        return [section for section in Sections.get_all() if section.is_running and not section.is_finished]

    def get_finished():
        return [section for section in Sections.get_all() if section.is_finished and len(section.dances) > 0]

    def get_uneditable():
        uneditable_sections = Sections.get_running() + Sections.get_finished()
        for section in Conf.get().sections:
            if section not in uneditable_sections:
                if len(DanceRounds.get_all(section.id)) > 1:
                    uneditable_sections.append(section)
        return uneditable_sections

    def create(section_id):
        for section in Conf.get().sections:
            if section.id == section_id:
                Sections.save(section)
                return section

    def save(section):
        if not section:
            return
        get_or_create_dir(Sections._get_dir(section.id))
        dump_json(section.to_dict(), Sections._get_filepath(section.id))

    def create_results(section):
        if not section:
            return
        # create place_df by getting the place per competitor from their respective last round
        places_per_competitor = {}
        for file in glob(f'{_get_data_path(section.id)}/[1-9]/{section.id}_[1-9]_results.csv'):
            _place_column = 'place'
            df = pd.read_csv(file, index_col=0)[_place_column].to_frame() # MEMO: the results may be either a CallbackMarkTable (for preliminary rounds) or a FinalSummary (for finals)
            for competitor in df.index:
                places_per_competitor[competitor] = df.at[competitor, _place_column]
        place_df = pd.DataFrame.from_dict(places_per_competitor, orient='index', columns=[_place_column])
        get_or_create_dir(Sections._get_dir(section.id))
        place_df.to_csv(Sections._get_results_path(section.id))
        return place_df

    def get_results(section):
        if not section:
            return
        filepath = Sections._get_results_path(section.id)
        if os.path.exists(filepath):
            return pd.read_csv(filepath, index_col=0)
        # set place to 1 for all competitors if there are no results yet
        place_df = pd.DataFrame(index=section.competitors)
        place_df['place'] = 1
        return place_df

    def remove_results(section):
        if not section:
            return
        filepath = Sections._get_results_path(section.id)
        if os.path.exists(filepath):
            print(filepath)
            os.remove(filepath)
            # reactivate section
            section.is_running = True
            section.is_finished = False
            Sections.save(section)
            # set final running
            final_round = DanceRounds.get_final(section.id)
            final_round.is_finished = False
            final_round.is_running = True
            DanceRounds.save(final_round)

class DanceRounds:
    def _get_dir(section_id, round_id):
        return _get_data_path(section_id, round_id)

    def _get_filepath(section_id, round_id):
        return f'{DanceRounds._get_dir(section_id, round_id)}/{section_id}_{round_id}_round.json'

    def get(section_id, round_id):
        filepath = DanceRounds._get_filepath(section_id, round_id)
        if os.path.exists(filepath):
            return DanceRound.from_dict(read_json(filepath))

    def create_first(section_id):
        section = Sections.get(section_id)
        if not section:
            return
        dance_round = DanceRound(DanceRounds._build_id(), DanceRounds._build_name())
        dance_round.section_id = section.id
        dance_round.dances = section.dances
        dance_round.competitors = section.competitors
        DanceRounds.save(dance_round)
        return dance_round

    def create_next(current_dance_round, callback_count, added_dance_ids=[]):
        if not current_dance_round:
            return
        callback_option = CallbackMarkTables.get_callback_option(current_dance_round.section_id, current_dance_round.id, callback_count)
        dance_round = DanceRound(DanceRounds._build_id(current_dance_round.id))
        dance_round.name = DanceRounds._build_name(dance_round.id, callback_option.is_final)
        dance_round.section_id = current_dance_round.section_id
        dance_round.dances = current_dance_round.dances
        for dance_id in added_dance_ids:
            dance_round.dances.append(Dances.get(dance_id))
        dance_round.competitors = [int(competitor) for competitor in callback_option.competitors]
        if callback_option.is_final:
            dance_round.is_final = True
        DanceRounds.save(dance_round)
        current_dance_round.is_running = False
        current_dance_round.is_finished = True
        DanceRounds.save(current_dance_round)
        return dance_round

    def _build_id(last_round_id=0):
        return last_round_id + 1

    def _build_name(round_id=1, is_final=False):
        if is_final:
            return 'Endrunde'
        if round_id == 1:
            return 'Vorrunde'
        if round_id == 1:
            return 'Zwischenrunde'
        return f'{round_id - 1}. Zwischenrunde'

    def get_all(section_id):
        return [DanceRound.from_dict(read_json(filepath)) for filepath in glob(DanceRounds._get_filepath(section_id, "*"))]

    def get_final(section_id):
        for dance_round in DanceRounds.get_all(section_id):
            if dance_round.is_final:
                return dance_round

    def get_running(adjudicator_id=""):
        current_rounds = []
        for section in Sections.get_running():
            if adjudicator_id and adjudicator_id not in section.adjudicators:
                continue
            for dance_round in DanceRounds.get_all(section.id):
                if dance_round.is_running and not dance_round.is_finished:
                    current_rounds.append(dance_round)
        return current_rounds

    def save(dance_round):
        get_or_create_dir(DanceRounds._get_dir(dance_round.section_id, dance_round.id))
        dump_json(dance_round.to_dict(), DanceRounds._get_filepath(dance_round.section_id, dance_round.id))

    def remove(dance_round):
        section_id = dance_round.section_id
        round_id = dance_round.id
        shutil.rmtree(DanceRounds._get_dir(section_id, round_id))
        current_section = Sections.get(section_id)
        current_section.is_running = False
        Sections.save(current_section)
        if round_id > 1:
            previous_round = DanceRounds.get(section_id, round_id - 1)
            previous_round.is_running = True
            previous_round.is_finished = False
            DanceRounds.save(previous_round)

class CallbackMarks:
    def _get_filepath(adjudicator_id, section_id, round_id, dance_id=''):
        dance_round = DanceRounds.get(section_id, round_id)
        if not dance_round:
            return
        if not dance_id:
            dance_id = dance_round.dances[0].id
        return f'{DanceRounds._get_dir(section_id, round_id)}/{section_id}_{round_id}_{dance_id}_callback_marks_{adjudicator_id}.json'

    def get(adjudicator_id, section_id, round_id, dance_id=''):
        filepath = CallbackMarks._get_filepath(adjudicator_id, section_id, round_id, dance_id)
        if os.path.exists(filepath):
            data = read_json(filepath)
            if 'competitors' in data:
                return data['competitors']
        return []

    def save(adjudicator_id, competitors, section_id, round_id, dance_id=''):
        get_or_create_dir(DanceRounds._get_dir(section_id, round_id))
        dump_json({'competitors': competitors}, CallbackMarks._get_filepath(adjudicator_id, section_id, round_id, dance_id))

class FinalMarks:
    def _get_filepath(adjudicator_id, section_id, round_id, dance_id=''):
        dance_round = DanceRounds.get(section_id, round_id)
        if not dance_round:
            return
        if not dance_id:
            dance_id = dance_round.dances[0].id
        return f'{DanceRounds._get_dir(section_id, round_id)}/{section_id}_{round_id}_{dance_id}_final_marks_{adjudicator_id}.json'

    def get(adjudicator_id, section_id, round_id, dance_id=''):
        filepath = FinalMarks._get_filepath(adjudicator_id, section_id, round_id, dance_id)
        if os.path.exists(filepath):
            return read_json(filepath)
        return {}

    def save(adjudicator_id, final_marks, section_id, round_id, dance_id=''):
        get_or_create_dir(DanceRounds._get_dir(section_id, round_id))
        dump_json(final_marks, FinalMarks._get_filepath(adjudicator_id, section_id, round_id, dance_id))

class CallbackMarkTables:
    def _get_filepath(section_id, round_id):
        return f'{DanceRounds._get_dir(section_id, round_id)}/{section_id}_{round_id}_results.csv'

    def get(section_id, round_id):
        filepath = CallbackMarkTables._get_filepath(section_id, round_id)
        if os.path.exists(filepath):
            return CallbackMarkTable.read_csv(filepath)

    def get_all(section_id):
        callback_mark_tables = []
        for dance_round in DanceRounds.get_all(section_id):
            if not dance_round.is_final:
                callback_mark_tables.append(CallbackMarkTables.get(section_id, dance_round.id))
        return callback_mark_tables

    def create(section_id, round_id):
        section = Sections.get(section_id)
        dance_round = DanceRounds.get(section_id, round_id)
        if not section or not dance_round:
            return
        callback_table = CallbackMarkTable(dance_round.competitors, section.adjudicators)
        for dance in dance_round.dances:
            for adjudicator in section.adjudicators:
                for marked_competitor in CallbackMarks.get(adjudicator, section_id, round_id, dance.id):
                    callback_table.add_mark(marked_competitor, adjudicator)
        callback_table.analyze()
        CallbackMarkTables.save(callback_table, section_id, round_id)
        return callback_table

    def save(callback_table, section_id, round_id):
        get_or_create_dir(DanceRounds._get_dir(section_id, round_id))
        callback_table.to_csv(CallbackMarkTables._get_filepath(section_id, round_id))

    def get_callback_option(section_id, round_id, callback_count):
        dance_round = DanceRounds.get(section_id, round_id)
        callback_table = CallbackMarkTables.get(section_id, round_id)
        for callback_option in callback_table.get_callback_options():
            if len(callback_option.competitors) == callback_count:
                return callback_option

class SkatingTables:
    def _get_filepath(section_id, round_id, dance_id):
        return f'{DanceRounds._get_dir(section_id, round_id)}/{section_id}_{round_id}_{dance_id}_results.csv'

    def get(section_id, round_id, dance_id):
        filepath = SkatingTables._get_filepath(section_id, round_id, dance_id)
        if os.path.exists(filepath):
            return SkatingTable.read_csv(filepath)

    def create(section_id, round_id, dance_id):
        section = Sections.get(section_id)
        dance_round = DanceRounds.get(section_id, round_id)
        if not section or not dance_round:
            return
        skating_table = SkatingTable(dance_round.competitors, section.adjudicators)
        for adjudicator in section.adjudicators:
            final_marks = FinalMarks.get(adjudicator, section.id, dance_round.id, dance_id)
            for competitor in dance_round.competitors:
                if str(competitor) in final_marks:
                    skating_table.set_mark(competitor, adjudicator, final_marks[str(competitor)])
        skating_table.analyze()
        SkatingTables.save(skating_table, section_id, round_id, dance_id)
        return skating_table

    def save(skating_table, section_id, round_id, dance_id):
        get_or_create_dir(DanceRounds._get_dir(section_id, round_id))
        skating_table.to_csv(SkatingTables._get_filepath(section_id, round_id, dance_id))

class FinalSummaries:
    def _get_filepath(section_id, round_id):
        return f'{DanceRounds._get_dir(section_id, round_id)}/{section_id}_{round_id}_results.csv'

    def create(section_id):
        final_round = DanceRounds.get_final(section_id)
        skating_tables = []
        for dance in final_round.dances:
            skating_tables.append(SkatingTables.get(section_id, final_round.id, dance.id))
        final_summary = FinalSummary(skating_tables)
        final_summary.analyze()
        get_or_create_dir(DanceRounds._get_dir(section_id, final_round.id))
        final_summary.to_csv(FinalSummaries._get_filepath(section_id, final_round.id))
        return final_summary

    def get(section_id):
        final_round = DanceRounds.get_final(section_id)
        if not final_round:
            return
        filepath = FinalSummaries._get_filepath(section_id, final_round.id)
        if os.path.exists(filepath):
            # MEMO: FinalSummary.read_csv() is not yet implemented !!!
            return pd.read_csv(filepath, index_col=0)

class Awards:
    def _get_dir():
        return f'{_get_data_path()}/awards'

    def _get_results_path(award_id):
        return f'{Awards._get_dir()}/{award_id}.csv'

    def get(award_id):
        for award in Awards.get_all():
            if award.id == award_id:
                return award

    def get_all():
        # do not store awards separately but always read them from conf
        return Conf.get().awards

    def get_section_ids(award_id):
        section_id_or_rules = Conf.get().section_id_or_rules_per_award[award_id]
        return extract_section_ids(section_id_or_rules)

    def get_results(award_id):
        filepath = Awards._get_results_path(award_id)
        if os.path.exists(filepath):
            return pd.read_csv(filepath, sep=',', encoding='utf8', index_col=0)

    def create_results(award_id):
        section_id_or_rules = Conf.get().section_id_or_rules_per_award[award_id]
        place_dfs_per_section_id = {}
        for section_id in extract_section_ids(section_id_or_rules):
            place_df = Sections.get_results(Sections.get(section_id))
            if place_df is not None:
                place_dfs_per_section_id[section_id] = place_df
        if len(place_dfs_per_section_id) > 0:
            result_df = get_award_results(section_id_or_rules, place_dfs_per_section_id)
            if not result_df.empty:
                get_or_create_dir(Awards._get_dir())
                result_df.to_csv(Awards._get_results_path(award_id), sep=',', encoding='utf8')
            return result_df.astype('Int64')
        return pd.DataFrame()

class HeatTables:
    def _get_filepath(section_id, round_id):
        return f'{DanceRounds._get_dir(section_id, round_id)}/{section_id}_{round_id}_heats.csv'

    def get(section_id, round_id):
        filepath = HeatTables._get_filepath(section_id, round_id)
        if os.path.exists(filepath):
            return HeatTable.read_csv(filepath)

    def create(section_id, round_id):
        dance_round = DanceRounds.get(section_id, round_id)
        if not dance_round:
            return
        heat_table = HeatTable(dance_round.competitors, [dance.id for dance in dance_round.dances])
        heat_table.randomize(dance_round.calc_heat_count(dance_round.max_heat_size))
        HeatTables.save(heat_table, section_id, round_id)

        # set running
        dance_round.is_running = True
        DanceRounds.save(dance_round)
        section = Sections.get(section_id)
        section.is_running = True
        Sections.save(section)
        return heat_table

    def move_to_last_heat(heat_table, section_id, round_id, dance_id, competitors):
        for competitor in competitors:
            heat_table.change_heat(competitor, dance_id, heat_table.get_heat_count())
        HeatTables.save(heat_table, section_id, round_id)

    def merge_running():
        # TODO: add section_ids as column group
        current_rounds = [dance_round for dance_round in DanceRounds.get_running() if not dance_round.is_final]
        if len(current_rounds) < 1:
            return
        merged_table = HeatTable().to_frame()
        for dance_round in current_rounds:
            table = HeatTables.get(dance_round.section_id, dance_round.id).to_frame()
            if len(dance_round.dances) > 1:
                table.columns = [f'{dance_round.section_id}_{dance.id}' for dance in dance_round.dances]
            merged_table = merged_table.join(table, how="outer")
        return merged_table.astype(object).fillna('-')

    def save(heat_table, section_id, round_id):
        get_or_create_dir(DanceRounds._get_dir(section_id, round_id))
        heat_table.to_csv(HeatTables._get_filepath(section_id, round_id))

class Heats:
    def from_table(heat_table, dance):
        heats = []
        for heat_no in range(1, heat_table.get_heat_count() + 1):
            heats.append(Heat(dance, heat_no, heat_table.get_heat(dance, heat_no)))
        return heats

class OverallResults:
    def _get_filepath():
        return f'{_get_data_path()}/results.csv'

    def get():
        filepath = OverallResults._get_filepath()
        if os.path.exists(filepath):
            return pd.read_csv(filepath, sep=',', encoding='utf8').astype('Int64').astype(object).fillna('-')

    def create():
        df = pd.DataFrame()
        for section in Sections.get_all():
            result_df = Sections.get_results(section)
            if result_df is not None:
                result_df[section.id] = result_df['place']
                df = df.join(result_df[section.id].to_frame(), how='outer')
        for award in Awards.get_all():
            result_df = Awards.get_results(award.id)
            if result_df is not None:
                result_df[award.id] = result_df['place']
                df = df.join(result_df[award.id].to_frame(), how='outer')
        df.to_csv(OverallResults._get_filepath(), sep=',', encoding='utf8')
        return df.astype('Int64').astype(object).fillna('-')
