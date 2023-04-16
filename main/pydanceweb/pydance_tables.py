import math
import pandas as pd
import random

# tables
class StartTable:
    """A simple competitor Start Table"""
    def __init__(self, section_ids=[]):
        self._df = pd.DataFrame(index=[], columns=section_ids)
        self.person_columns = [
            'first_name', 'surname', 'team',
            'lead_first_name', 'lead_surname', 'lead_team',
            'follow_first_name', 'follow_surname', 'follow_team']

    def _get_section_columns(self):
        return [x for x in self._df.columns if x not in self.person_columns]

    def get_ids(self, section_id=""):
        if not section_id:
            return sorted(self._df.index)
        if section_id in self._df.columns:
            return sorted(self._df.loc[self._df[section_id] != 0].index)
        return []

    def get_preregistrations(self, competitor):
        if competitor in self._df.index:
            row = self._df.loc[competitor]
            return list(row.loc[row == -1].index)
        return []

    def get_participations(self, competitor):
        if competitor in self._df.index:
            row = self._df.loc[competitor]
            return list(row.loc[row != 0].index)
        return []

    def add_section(self, section_id):
        if section_id not in self._df.columns:
            self._df[section_id] = 0

    def remove_section(self, section_id):
        if section_id:
            assert section_id in self._df.columns, f"section '{section_id}' not found"
        self._df.drop([section_id], axis=1, inplace=True)

    def add_participation(self, competitor, section_id):
        assert section_id in self._df.columns, f"section '{section_id}' not found"
        self._df.at[competitor, section_id] = 1
        self._df[self._get_section_columns()] = self._df[self._get_section_columns()].fillna(0).astype(int)
        self._df = self._df.fillna("")

    def remove_participation(self, competitor, section_id):
        assert section_id in self._df.columns, f"section '{section_id}' not found"
        self._df.at[competitor, section_id] = 0

    def add_preregistration(self, competitor, section_id):
        assert section_id in self._df.columns, f"section '{section_id}' not found"
        self._df.at[competitor, section_id] = -1
        self._df[self._get_section_columns()] = self._df[self._get_section_columns()].fillna(0).astype(int)
        self._df = self._df.fillna("")

    def remove_preregistration(self, competitor, section_id):
        assert section_id in self._df.columns, f"section '{section_id}' not found"
        self._df.at[competitor, section_id] = 0

    def _reset_index(self, min_id=0):
        if min_id == 0:
            min_id = 1
        self._df.set_index(pd.RangeIndex(min_id, len(self._df) + min_id), inplace=True)

    def randomize(self, min_id=0):
        self._df = self._df.sample(frac = 1).reset_index(drop=True) # shuffle
        self._reset_index(min_id)

    def get_new_competitor_id(self):
        # REturning a String representation of this for further usage (because isDigit() is used in the code)
        return str(self._df.shape[0] + 1)

    def to_frame(self):
        return self._df.copy()

    def to_csv(self, path_or_buf=None, sep=','):
        self._df.to_csv(path_or_buf, sep=sep)

    @staticmethod
    def read_csv(path_or_buf, sep=',', encoding='utf8'):
        table = StartTable()
        table._df = pd.read_csv(path_or_buf, sep=sep, encoding=encoding)
        if 'Unnamed: 0' in table._df.columns:
            table._df.set_index('Unnamed: 0', inplace=True)
            table._df.index.name = None
        else:
            table._reset_index()
        return table

class AdjudicatorStartTable(StartTable):
    """A simple adjudicator Start Table"""
    def _reset_index(self):
        adjudicator_ids = []
        for i in range(len(self._df)):
            adjudicator_id = chr(i%26 + 65) # [A-Z]
            if i//26 > 0:
                adjudicator_id = chr(i//26%26 + 64) + adjudicator_id # [A-Z][A-Z]
            adjudicator_ids.append(adjudicator_id)
        self._df.set_index([adjudicator_ids], inplace=True)

    @staticmethod
    def read_csv(path_or_buf, sep=',', encoding='utf8'):
        table = AdjudicatorStartTable()
        table._df = pd.read_csv(path_or_buf, sep=sep, encoding=encoding)
        if 'Unnamed: 0' in table._df.columns:
            table._df.set_index('Unnamed: 0', inplace=True)
            table._df.index.name = None
        else:
            table._reset_index()
        return table

class HeatTable:
    """A simple Heat Table"""
    def __init__(self, competitors=[], dances=[]):
        self._df = pd.DataFrame(index=competitors, columns=dances)

    def get_competitors(self):
        return sorted(self._df.index)

    def get_dances(self):
        return list(self._df.columns)

    def randomize(self, heat_count=1):
        assert heat_count > 0, "heat_no must be a positive integer"

        competitors = self.get_competitors()
        for dance in self.get_dances():
            # draw random heats
            random.shuffle(competitors)
            for i, competitor in enumerate(competitors):
                self._df.at[competitor, dance] = (i % heat_count) + 1

    def get_heat_count(self):
        return max(list(self._df.max()))

    def get_heat(self, dance, heat_no):
        assert dance in self.get_dances(), f"dance '{dance}' not found"
        assert heat_no in range(1, self.get_heat_count() + 1), f"heat_no must be an integer between 1 and {self.get_heat_count()}"

        return sorted(self._df.loc[self._df[dance] == heat_no].index)

    def change_heat(self, competitor, dance, new_heat):
        assert competitor in self.get_competitors(), f"competitor {competitor} not found"
        assert dance in self.get_dances(), f"dance '{dance}' not found"
        assert new_heat in range(1, self.get_heat_count() + 1), f"new_heat must be an integer between 1 and {self.get_heat_count()}"

        self._df.at[competitor, dance] = new_heat

    def remove_competitor(self, competitor, dance):
        assert competitor in self.get_competitors(), f"competitor {competitor} not found"
        assert dance in self.get_dances(), f"dance '{dance}' not found"

        self._df.drop(competitor,inplace=True)

    def to_frame(self):
        return self._df.copy()

    def to_csv(self, path_or_buf=None, sep=','):
        self.to_frame().to_csv(path_or_buf, sep=sep)

    @staticmethod
    def read_csv(path_or_buf, sep=',', encoding='utf8'):
        heat_table = HeatTable()
        heat_table._df = pd.read_csv(path_or_buf, sep=sep, encoding=encoding, index_col=0, dtype='Int64')
        return heat_table

class CallbackOption:
    """A wrapper object for a possible result of any preliminary round: namely which competitors should be called back together and whether this results in a final round or not"""
    def __init__(self, competitors, is_final):
        self.competitors = competitors
        self.is_final = is_final

class CallbackMarkTable:
    """The table used to tabulate the results of preliminary rounds in order to find the competitors that should called back for the next round"""
    def __init__(self, competitors=[], adjudicators=[]):
        self._df = pd.DataFrame(index=competitors, columns=adjudicators).fillna(0)
        self._calculation_column = "total"
        self._place_column = "place"
        self._clear_calculations()
        self._clear_places()

    def get_competitors(self):
        return sorted(self._df.index)

    def get_adjudicators(self):
        return list(self._df.columns)

    def get_place(self, competitor):
        assert competitor in self.get_competitors(), f"competitor {competitor} not found"

        return self._place_df.at[competitor, self._place_column]

    def get_mark(self, competitor, adjudicator):
        assert competitor in self.get_competitors(), f"competitor {competitor} not found"
        assert adjudicator in self.get_adjudicators(), f"adjudicator '{adjudicator}' not found"

        return self._df.at[competitor, adjudicator]

    def set_mark(self, competitor, adjudicator):
        assert competitor in self.get_competitors(), f"competitor {competitor} not found"
        assert adjudicator in self.get_adjudicators(), f"adjudicator '{adjudicator}' not found"

        self._df.at[competitor, adjudicator] = 1

    def add_mark(self, competitor, adjudicator):
        assert competitor in self.get_competitors(), f"competitor {competitor} not found"
        assert adjudicator in self.get_adjudicators(), f"adjudicator '{adjudicator}' not found"

        self._df.at[competitor, adjudicator] += 1

    def remove_mark(self, competitor, adjudicator):
        assert competitor in self.get_competitors(), f"competitor {competitor} not found"
        assert adjudicator in self.get_adjudicators(), f"adjudicator '{adjudicator}' not found"

        self._df.at[competitor, adjudicator] = 0

    def _clear_calculations(self):
        self._calculation_df = pd.DataFrame(index=self._df.index, columns=[self._calculation_column])

    def _clear_places(self):
        self._place_df = pd.DataFrame(index=[], columns=[self._place_column])

    def _set_place(self, competitor, place):
        self._place_df.loc[competitor] = place

    def analyze(self):
        self._df = self._df.fillna(0)
        # clear calculated columns
        self._clear_calculations()
        self._clear_places()

        # fill sum column
        self._calculation_df[self._calculation_column] = sum([self._df[x] for x in self._df.columns])

        # fill place column
        n = 0
        current_place = 1
        current_sum = max(self._calculation_df[self._calculation_column])
        for competitor, row in self._calculation_df.sort_values(by=self._calculation_column, ascending=False).iterrows():
            n += 1
            if row[self._calculation_column] < current_sum:
                current_sum = row[self._calculation_column]
                current_place = n
            self._place_df.loc[competitor] = current_place

    def get_callback_options(self, min_callback = 3):
        assert min_callback > 0 and min_callback <= len(self.get_competitors()), f"invalid min_callback {min_callback}"

        callback_options = []
        last_callback = 0
        for place in range(1, len(self._place_df) + 1):
            # get competitors that will procede if the current place is selected as a cut-off point
            competitors = sorted(self._place_df.loc[self._place_df[self._place_column] <= place].index)
            callback = len(competitors)

            # get distinct callback options
            if callback >= min_callback and callback > last_callback:
                last_callback = callback

                # build CallBackOption (and check if it results in a Final)
                is_final = (place <= 6 and len(competitors) <= 8)
                callback_options.append(CallbackOption(competitors, is_final))
        return callback_options

    def to_frame(self):
        df = self._df.copy()
        if len(self._place_df) > 0:
            df = df.join(self._calculation_df)
            df = df.join(self._place_df)
        return df

    def to_csv(self, path_or_buf=None, sep=','):
        self.to_frame().to_csv(path_or_buf, sep=sep)

    @staticmethod
    def read_csv(path_or_buf, sep=',', encoding='utf8'):
        table = CallbackMarkTable()
        df = pd.read_csv(path_or_buf, sep=sep, encoding=encoding, index_col=0, dtype='Int64').fillna(0)
        columns = list(df.columns)
        if table._calculation_column in columns:
            table._calculation_df = df[table._calculation_column].to_frame()
            columns.remove(table._calculation_column)
        if table._place_column in columns:
            table._place_df = df[table._place_column].to_frame()
            columns.remove(table._place_column)
        table._df = df[columns]
        return table


class SkatingTable(CallbackMarkTable):
    """The table used to tabulate the results of a single dance final"""

    def __init__(self, competitors=[], adjudicators=[]):
        self._df = pd.DataFrame(index=competitors, columns=adjudicators).fillna(0)
        self._calculation_columns = [SkatingTable.build_calculation_column(x+1) for x in range(len(competitors))]
        self._place_column = "place"
        self._clear_calculations()
        self._clear_places()

    def _clear_calculations(self):
        self._calculation_df = pd.DataFrame(index=self._df.index, columns=self._calculation_columns)

    def set_mark(self, competitor, adjudicator, mark):
        assert competitor in self.get_competitors(), f"competitor {competitor} not found"
        assert adjudicator in self.get_adjudicators(), f"adjudicator '{adjudicator}' not found"
        assert mark > 0 and mark <= len(self.get_competitors()), f"mark cannot be '{adjudicator}'"

        self._df.at[competitor, adjudicator] = mark

    def _get_marks_per_competitor(self, competitors, max_mark=0):
        relevant_df = self._df.loc[competitors].T

        marks_per_competitor = {}
        for competitor in competitors:
            marks = list(relevant_df[competitor])
            if set(marks) == {0}:
                continue
            if max_mark > 0 and max_mark < len(self.get_competitors()):
                marks = [x for x in marks if x <= max_mark and x > 0]
            marks_per_competitor[competitor] = marks
        return marks_per_competitor

    def _get_min_majority(self):
        return len(self.get_adjudicators()) // 2 + 1

    def _get_max_place(self):
        return len(self._place_df) + 1

    def _skate(self, competitors, min_place):
        min_majority = self._get_min_majority()
        current_place = self._get_max_place()
        current_calculation_column = SkatingTable.build_calculation_column(min_place)

        marks_per_competitor = self._get_marks_per_competitor(competitors, min_place)
        competitors_per_mark_count = SkatingTable.get_competitors_per_mark_count(marks_per_competitor)
        # Rule 6: Handle multiple majorities
        for mark_count in reversed(sorted(competitors_per_mark_count)):
            current_competitors = competitors_per_mark_count[mark_count]
            if mark_count < min_majority:
                # Rule 8: Handle no majority => fill only calculation column
                for competitor in current_competitors:
                    self._calculation_df.at[competitor, current_calculation_column] = str(mark_count)
                if len(competitors) > 0:
                    self._skate(competitors, min_place + 1)
            else:
                if len(current_competitors) == 1:
                    # Rule 5: Handle single majority
                    competitor = current_competitors[0]
                    self._set_place(competitor, current_place)
                    self._calculation_df.at[competitor, current_calculation_column] = str(mark_count)
                    current_place = self._get_max_place()
                    competitors.remove(competitor)
                else:
                    # Rule 7: Try to break a majority tie by looking at the sum of the associated place marks
                    current_marks_per_competitor = {competitor: marks_per_competitor[competitor] for competitor in current_competitors}
                    competitors_per_mark_sum = SkatingTable.get_competitors_per_mark_sum(current_marks_per_competitor)
                    for mark_sum in sorted(competitors_per_mark_sum):
                        tied_competitors = competitors_per_mark_sum[mark_sum]
                        if len(tied_competitors) == 1:
                            competitor = tied_competitors[0]
                            self._set_place(competitor, current_place)
                            self._calculation_df.at[competitor, current_calculation_column] = f"{mark_count} ({mark_sum})"
                            current_place = self._get_max_place()
                            competitors.remove(competitor)
                            current_competitors.remove(competitor)
                            #tied_competitors.remove(competitor)
                        else:
                            for competitor in tied_competitors:
                                self._calculation_df.at[competitor, current_calculation_column] = f"{mark_count} ({mark_sum})"
                                competitors.remove(competitor)
                                current_competitors.remove(competitor)
                            if min_place < len(self.get_competitors()):
                                # look at next column(s)
                                self._skate(tied_competitors, min_place + 1)
                            else:
                                # tie => TODO: calc tied_place
                                for competitor in tied_competitors:
                                    self._set_place(competitor, current_place)

                            current_place = self._get_max_place()
        # fill irrelevant cells
        self._calculation_df.fillna("-", inplace=True)

    def analyze(self):
        self._df = self._df.fillna(0)
        # clear calculated columns
        self._clear_calculations()
        self._clear_places()

        self._skate(self.get_competitors(), 1)

    def validate(self):
        expected_marks = [x+1 for x in range(len(self.get_competitors()))]
        issues = []
        for adjudicator in self.get_adjudicators():
            marks = list(self._df[adjudicator])
            if sorted(marks) != expected_marks:
                issues.append(f"invalid marks found for adjudicator '{adjudicator}': {marks}")
        assert len(issues) == 0, f"{len(issues)} issue(s) found: {issues}"
        return True

    @staticmethod
    def read_csv(path_or_buf, sep=',', encoding='utf8'):
        table = SkatingTable()
        df = pd.read_csv(path_or_buf, sep=sep, encoding=encoding, index_col=0)
        columns = list(df.columns)

        calculation_columns = [SkatingTable.build_calculation_column(x+1) for x in range(len(df))]
        table._calculation_df = pd.DataFrame(index=df.index, columns=calculation_columns)
        for column in calculation_columns:
            if column in columns:
                table._calculation_df[column] = df[column].to_frame()
                columns.remove(column)

        if table._place_column in columns:
            table._place_df = df[table._place_column].to_frame()
            columns.remove(table._place_column)
        table._df = df[columns]
        return table

    @staticmethod
    def build_calculation_column(max_place):
        if max_place > 1:
            return f"1-{max_place}"
        return "1"

    @staticmethod
    def get_competitors_per_mark_count(marks_per_competitor):
        competitors_per_mark_count = {}
        for competitor in marks_per_competitor:
            mark_count = len(marks_per_competitor[competitor])
            if mark_count in competitors_per_mark_count:
                competitors_per_mark_count[mark_count].append(competitor)
            else:
                competitors_per_mark_count[mark_count] = [competitor]
        return competitors_per_mark_count

    @staticmethod
    def get_competitors_per_mark_sum(marks_per_competitor):
        competitors_per_mark_sum = {}
        for competitor in marks_per_competitor:
            mark_sum = sum(marks_per_competitor[competitor])
            if mark_sum in competitors_per_mark_sum:
                competitors_per_mark_sum[mark_sum].append(competitor)
            else:
                competitors_per_mark_sum[mark_sum] = [competitor]
        return competitors_per_mark_sum

class FinalSummary(CallbackMarkTable):
    """The table(s) used to tabulate the results of a multi-dance section final"""
    def __init__(self, skating_tables=[]):
        self.skating_tables = skating_tables
        self._rule_9_calculation_column = 'total'
        self._place_column = 'place'

        self._df = pd.DataFrame()
        self._rule_10_df = pd.DataFrame()
        self._rule_11_df = pd.DataFrame()
        self._place_df = pd.DataFrame()

    def analyze(self):
        self._apply_rule_9()
        self._apply_rule_10()
        self._apply_rule_11()

    def _apply_rule_9(self):
        if self._df.empty:
            # build basic df with columns for the places from the individual dances
            self._df = pd.DataFrame()
            for i, skating_table in enumerate(self.skating_tables):
                # fill place columns per dance
                place_df = skating_table._place_df.copy()
                column = f'{self._place_column}_{i+1}'
                place_df.columns = [column]

                # calculate mean for tied competitors
                for current_place, tied_competitors in FinalSummary._get_competitors_per_place(place_df[column]).items():
                    if len(tied_competitors) > 1:
                        mean_place = current_place + (len(tied_competitors) - 1) * .5
                        for competitor in tied_competitors:
                            place_df.at[competitor, column] = mean_place
                self._df = self._df.join(place_df, how='outer')

        # add sum column
        self._df[self._rule_9_calculation_column] = 0
        self._df[self._rule_9_calculation_column] = sum([self._df[x] for x in self._df.columns])

        # rule 9: set places by sorting the sums in descending order
        self._place_df = pd.DataFrame(index=self._df.index)
        self._place_df[self._place_column] = 0
        n = 0
        current_place = 1
        current_sum = 0
        for competitor, row in self._df.sort_values(by=self._rule_9_calculation_column).iterrows():
            n += 1
            if row[self._rule_9_calculation_column] > current_sum:
                current_sum = row[self._rule_9_calculation_column]
                current_place = n
            self._place_df[self._place_column].loc[competitor] = current_place

    def _apply_rule_10(self):
        df = pd.DataFrame(columns=[SkatingTable.build_calculation_column(x + 1) for x in range(len(self._df))])
        for current_place in sorted(set(self._place_df[self._place_column])):
            tied_competitors = FinalSummary._get_competitors_per_place(self._place_df[self._place_column])[current_place]
            if len(tied_competitors) > 1:
                relevant_places_per_competitor = {}
                for competitor in tied_competitors:
                    relevant_places = [x for x in self._df.loc[competitor] if x > 0 and x <= current_place]
                    relevant_places_per_competitor[competitor] = relevant_places
                    df.at[competitor, SkatingTable.build_calculation_column(current_place)] = str(len(relevant_places))

                competitors_per_place_count = SkatingTable.get_competitors_per_mark_count(relevant_places_per_competitor)
                max_place_count = sorted(competitors_per_place_count)[-1]
                if len(competitors_per_place_count[max_place_count]) == 1:
                    best_competitor = competitors_per_place_count[max_place_count][0]
                    for competitor in tied_competitors:
                        if competitor != best_competitor:
                            self._place_df.at[competitor, self._place_column] = current_place + 1
                else:
                    current_tied_competitors = competitors_per_place_count[max_place_count]
                    current_relevant_places_per_competitor = {competitor: relevant_places_per_competitor[competitor] for competitor in current_tied_competitors}
                    for competitor in current_relevant_places_per_competitor:
                        df.at[competitor, SkatingTable.build_calculation_column(current_place)] = f'{len(current_relevant_places_per_competitor[competitor])} ({sum(current_relevant_places_per_competitor[competitor])})'

                    competitors_per_place_sum = SkatingTable.get_competitors_per_mark_sum(current_relevant_places_per_competitor)
                    min_place_sum = sorted(competitors_per_place_sum)[0]
                    if len(competitors_per_place_sum[min_place_sum]) == 1:
                        best_competitor = competitors_per_place_sum[min_place_sum][0]
                        for competitor in tied_competitors:
                            if competitor != best_competitor:
                                self._place_df.at[competitor, self._place_column] = current_place + 1
                    else:
                        best_competitors = competitors_per_place_sum[min_place_sum]
                        for competitor in tied_competitors:
                            if competitor not in best_competitors:
                                self._place_df.at[competitor, self._place_column] = current_place + len(best_competitors)
                        # break tie with rule 11
            if len(df) > 0:
                self._rule_10_df = df.fillna('-')

    def _apply_rule_11(self):
        df = pd.DataFrame()
        if len(self.skating_tables) == 0:
            return

        for current_place, tied_competitors in FinalSummary._get_competitors_per_place(self._place_df[self._place_column]).items():
            if len(tied_competitors) > 1:
                current_df = SkatingTable()
                current_df._df = pd.DataFrame(index=self.get_competitors())
                for i, skating_table in enumerate(self.skating_tables):
                    current_df._df = current_df._df.join(skating_table._df.loc[tied_competitors].add_prefix(f'.{i+1}'), how='outer').fillna(0).astype(int)
                current_df.analyze()
                current_df._df = current_df._df.loc[tied_competitors]
                for competitor in tied_competitors:
                    place = current_df._place_df.at[competitor, self._place_column] + current_place - 1
                    current_df._place_df.at[competitor, self._place_column] = place
                    self._place_df.at[competitor, self._place_column] = place
                df = df.join(current_df._calculation_df.loc[tied_competitors].T, how='outer')#.fillna('-')
        self._rule_11_df = df.T.fillna('-')

    def _get_competitors_per_place(place_column):
        place_per_competitor = place_column.sort_values().to_dict()
        competitors_per_place = {}
        for competitor in place_per_competitor:
            place = place_per_competitor[competitor]
            if place in competitors_per_place:
                competitors_per_place[place].append(competitor)
            else:
                competitors_per_place[place] = [competitor]
        return competitors_per_place


    def to_frame(self):
        df = self._df.join(self._place_df, how='outer')
        df = df.join(self._rule_10_df.add_prefix('R10_'), how='outer') # TODO: prefix columns to avoid conflicts !!!
        df = df.join(self._rule_11_df.add_prefix('R11_'), how='outer') # TODO: prefix columns to avoid conflicts !!!
        return df.fillna('-').copy()
