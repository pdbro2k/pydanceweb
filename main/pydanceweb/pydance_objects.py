class PyDanceObject:
    def __init__(self, id, name=''):
        self.id = id
        self.name = name

    def __eq__(self, other):
        return self.id == other.id

    def __str__ (self):
        return f'{self.__class__.__name__}({self.id})'

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }

class Dance(PyDanceObject):
    def __init__(self, id, name=''):
        super().__init__(id, name)

    @staticmethod
    def from_dict(data):
        dance = Dance(data['id'])
        if 'name' in data:
            dance.name = data['name']
        return dance

class Section(PyDanceObject):
    def __init__(self, id, name='', dances=[], additional_dances=[], adjudicators=[], competitors=[]):
        super().__init__(id, name)
        self.dances = dances
        self.additional_dances = additional_dances
        self.adjudicators = adjudicators
        self.competitors = competitors
        self.is_running = False
        self.is_finished = False

    def to_dict(self):
        data = super().to_dict()
        data['dances'] = [dance.to_dict() for dance in self.dances]
        data['additional_dances'] = [dance.to_dict() for dance in self.additional_dances]
        data['adjudicators'] = self.adjudicators
        data['competitors'] = self.competitors
        data['is_running'] = self.is_running
        data['is_finished'] = self.is_finished
        return data

    @staticmethod
    def from_dict(data):
        section = Section(data['id'])
        if 'name' in data:
            section.name = data['name']
        if 'dances' in data:
            section.dances = [Dance.from_dict(dance) for dance in data['dances']]
        if 'additional_dances' in data:
            section.additional_dances = [Dance.from_dict(dance) for dance in data['additional_dances']]
        if 'adjudicators' in data:
            section.adjudicators = data['adjudicators']
        if 'competitors' in data:
            section.competitors = data['competitors']
        if 'is_running' in data:
            section.is_running = data['is_running']
        if 'is_finished' in data:
            section.is_finished = data['is_finished']
        return section

class SectionGroup(PyDanceObject):
    def __init__(self, id, name='', sections=[]):
        super().__init__(id, name)
        self.sections = sections

    def to_dict(self):
        data = super().to_dict()
        data['sections'] = [section.to_dict() for section in self.sections]
        return data

    @staticmethod
    def from_dict(data):
        section_group = SectionGroup(data['id'])
        if 'name' in data:
            section_group.name = data['name']
        if 'sections' in data:
            section.sections = [Section.from_dict(section) for section in data['sections']]
        return section_group

class DanceRound(PyDanceObject):
    def __init__(self, id, name="", is_final=False, section_id='', dances=[], competitors=[], callback_wish=0):
        super().__init__(id, name)
        self.section_id = section_id
        self.is_final = is_final
        self.dances = dances
        self.competitors = competitors
        if callback_wish > 0 and callback_wish <= len(competitors):
            self.callback_wish = callback_wish
        else:
            self.callback_wish = self.suggest_callback()
        self.max_heat_size = 6
        self.is_running = False
        self.is_finished = False

    def suggest_callback(self):
        competitor_count = len(self.competitors)
        # ignore finals
        if competitor_count <= 6:
            return competitor_count

        # try to find a regular callback (= 6*2^n) that allow at least half the competitors to advance to the next round
        suggested_callback = 6
        while suggested_callback * 2 < competitor_count:
            suggested_callback *= 2
        return suggested_callback

    def calc_heat_count(self, max_heat_size = 6):
        competitor_count = len(self.competitors)
        heat_count = competitor_count // max_heat_size
        if competitor_count % max_heat_size > 0:
            return heat_count + 1
        return heat_count

    def get_min_heat_counts_per_size(self, max_heat_size = 6):
        min_heat_size = 6
        competitor_count = len(self.competitors)
        min_heat_counts_per_size = {}
        min_heat_count = competitor_count + 1
        for heat_size in range(min_heat_size, max_heat_size + 1):
            heat_count = self.calc_heat_count(heat_size)
            if heat_count < min_heat_count:
                min_heat_count = heat_count
                min_heat_counts_per_size[heat_size] = heat_count
        return min_heat_counts_per_size

    def to_dict(self):
        data = super().to_dict()
        data['section_id'] = self.section_id
        data['is_final'] = self.is_final
        data['dances'] = [dance.to_dict() for dance in self.dances]
        data['competitors'] = self.competitors
        data['callback_wish'] = self.callback_wish
        data['max_heat_size'] = self.max_heat_size
        data['is_running'] = self.is_running
        data['is_finished'] = self.is_finished
        return data

    @staticmethod
    def from_dict(data):
        dance_round = DanceRound(data['id'])
        if 'name' in data:
            dance_round.name = data['name']
        if 'section_id' in data:
            dance_round.section_id = data['section_id']
        if 'is_final' in data:
            dance_round.is_final = data['is_final']
        if 'dances' in data:
            dance_round.dances = [Dance.from_dict(dance) for dance in data['dances']]
        if 'competitors' in data:
            dance_round.competitors = data['competitors']
        if 'callback_wish' in data:
            dance_round.callback_wish = data['callback_wish']
        if 'max_heat_size' in data:
            dance_round.max_heat_size = data['max_heat_size']
        if 'is_running' in data:
            dance_round.is_running = data['is_running']
        if 'is_finished' in data:
            dance_round.is_finished = data['is_finished']
        return dance_round
