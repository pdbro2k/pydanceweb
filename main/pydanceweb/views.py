from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render

from .pydance_objects import *
from .pydance_tables import *
from .models import *

# generic helpers
def render_frame(frame):
    if frame is not None:
        if 'place' in frame.columns:
            return frame.sort_values(by='place').to_dict('index')
        return frame.to_dict('index')

# admin views
def show_tournament_desk_index(request):
    conf = Conf.get()
    sections = conf.sections
    dance_rounds_per_section = {}
    for section in sections:
        dance_rounds_per_section[section.id] = DanceRounds.get_all(section.id)
    context = {
        'conf': conf,
        'ungrouped_sections': conf.get_ungrouped_sections(),
        'running_sections': Sections.get_running(),
        'finished_sections': Sections.get_finished(),
        'dance_rounds_per_section': dance_rounds_per_section,
    }
    return render(request, 'pydanceweb/index_for_tournament_desk.html', context)

def handle_section(request, section_id):
    section = Sections.get(section_id)
    if not section:
        section = Sections.create(section_id)
    dance_rounds = DanceRounds.get_all(section_id)
    last_round = dance_rounds[-1] if dance_rounds else None
    next_round_id = last_round.id + 1 if last_round else 1
    context = {
        'conf': Conf.get(),
        'section': section,
        'dance_rounds': dance_rounds,
        'last_round': last_round,
        'next_round_id': next_round_id
    }
    return render(request, 'pydanceweb/section.html', context)

def _prepare_round(request, section_id, round_id):
    section = Sections.get(section_id)
    max_heat_size = 8 # TODO: read from conf_dinct
    if round_id == 1:
        # init new first round
        dance_round = DanceRounds.create_first(section_id)
    else:
        # init next round
        current_dance_round =  DanceRounds.get(section_id, round_id - 1)
        if not current_dance_round:
            return HttpResponse("Runde nicht gefunden")
        callback_count = int(request.POST["callback_count"])
        added_dance_ids = request.POST.getlist("add_dances")
        dance_round = DanceRounds.create_next(current_dance_round, callback_count, added_dance_ids)
    context = {
        'conf': Conf.get(),
        'section': section,
        'dance_round': dance_round,
        'heat_counts_per_size': dance_round.get_min_heat_counts_per_size(max_heat_size)
    }
    return render(request, 'pydanceweb/dance_round_preparation.html', context)

def handle_round(request, section_id, round_id):
    dance_round = DanceRounds.get(section_id, round_id)
    if not dance_round:
        return _prepare_round(request, section_id, round_id)

    section = Sections.get(section_id)
    if dance_round.is_final:
        return _handle_final_round(request, dance_round, section)
    return _handle_preliminary_round(request, dance_round, section)

def _handle_final_round(request, dance_round, section):
    if not dance_round.is_running:
        if request.POST:
            dance_round.is_running = True
            DanceRounds.save(dance_round)

    final_tables = []
    for dance in dance_round.dances:
        final_tables.append( render_frame(SkatingTables.create(section.id, dance_round.id, dance.id).to_frame()) )

    context = {
        'conf': Conf.get(),
        'section': section,
        'dance_round': dance_round,
        'final_tables_per_dance': zip(dance_round.dances, final_tables),
    }
    if len(dance_round.dances) > 1:
        final_summary = FinalSummaries.get(section.id)
        context['final_summary'] = render_frame(final_summary)
    return render(request, 'pydanceweb/final_round.html', context)

def _handle_preliminary_round(request, dance_round, section):
    if request.POST:
        dance_round.callback_wish = int(request.POST['callback_wish'])
        dance_round.max_heat_size = int(request.POST['heat_size'])
        DanceRounds.save(dance_round)
    callback_table = CallbackMarkTables.create(section.id, dance_round.id)
    context = {
        'conf': Conf.get(),
        'section': section,
        'dance_round': dance_round,
        'callback_table': render_frame(callback_table.to_frame()),
        'callback_options': callback_table.get_callback_options(),
    }
    return render(request, 'pydanceweb/preliminary_round.html', context)


def handle_heats(request, section_id, round_id, dance_id=""):
    section = Sections.get(section_id)
    dance_round = DanceRounds.get(section_id, round_id)
    if not dance_round:
        return HttpResponse('Runde nicht gefunden.')
    if not dance_id:
        dance_id = dance_round.dances[0].id
    heat_table = HeatTables.get(section_id, round_id)
    if not heat_table:
        heat_table = HeatTables.create(section_id, round_id)
    if request.method == 'POST':
        competitors = [int(x) for x in request.POST.getlist('competitors')]
        HeatTables.move_to_last_heat(heat_table, section_id, round_id, dance_id, competitors)
    context = {
        'conf': Conf.get(),
        'section': section,
        'dance_round': dance_round,
        'dance_id': dance_id,
        'first_dance_id': dance_round.dances[0].id,
        'last_dance_id': dance_round.dances[-1].id,
        'heats': Heats.from_table(heat_table, dance_id),
    }
    return render(request, 'pydanceweb/heats_for_tournament_desk.html', context)

# => finish current section
def finalize_section(request, section_id):
    final_round = DanceRounds.get_final(section_id)
    if final_round and not final_round.is_finished:
        # create final summary and finish final
        final_summary = FinalSummaries.create(section_id)
        final_round = DanceRounds.get_final(section_id)
        final_round.is_running = False
        final_round.is_finished = True
        DanceRounds.save(final_round)

        # finish section
        section = Sections.get(section_id)
        section.is_running = False
        section.is_finished = True
        Sections.save(section)

        # create section results
        Sections.create_results(section)
    return show_results(request, section_id)

# => calc awards
def handle_award(request, award_id):
    results = Awards.create_results(award_id)
    return show_award_results(request, award_id)

def finalize(request):
    results_table = OverallResults.create().astype('Int64').astype(object).fillna('-')
    context = {
        'conf': Conf.get(),
        'results_table': results_table.to_html(),
    }
    return render(request, 'pydanceweb/overall_results.html', context)

# adjudicator views
def show_current_adjudicator_rounds(request, adjudicator_id):
    conf = Conf.get()
    # TODO: move to models
    current_rounds = []
    for section in conf.sections:
        if adjudicator_id in section.adjudicators and section.is_running:
            for dance_round in DanceRounds.get_all(section.id):
                if dance_round.is_running:
                    current_rounds.append(dance_round)
    context = {
        'conf': conf,
        'adjudicator_id': adjudicator_id,
        'current_rounds': current_rounds,
    }
    return render(request, 'pydanceweb/index_for_adjudicator.html', context)

def _judge_next(request, adjudicator_id, dance_round, dance_id, callback_marks=[], final_marks={}):
    # goto next dance or index
    next_dance = None
    dance_index = dance_round.dances.index(Dance(dance_id))
    if dance_index + 1 < len(dance_round.dances):
        next_dance = dance_round.dances[dance_index + 1]
    context = {
        'conf': Conf.get(),
        'adjudicator_id': adjudicator_id,
        'dance_round': dance_round,
        'callback_marks': callback_marks,
        'final_marks': final_marks,
        'next_dance': next_dance
    }
    return render(request, 'pydanceweb/adjudicator_reaction.html', context)

def judge_heats(request, adjudicator_id, section_id, round_id, dance_id=''):
    if adjudicator_id not in Sections.get(section_id).adjudicators:
        return HttpResponse('Keine Berechtigung!')

    dance_round = DanceRounds.get(section_id, round_id)
    if not dance_round:
        return HttpResponse('Runde nicht gefunden.')
    if not dance_id:
        dance_id = dance_round.dances[0].id

    if request.method == 'POST':
         # TODO: improve
        callback_marks = [int(x) for x in request.POST.getlist('competitors')]
        CallbackMarks.save(adjudicator_id, callback_marks, section_id, round_id, dance_id)
        return _judge_next(request, adjudicator_id, dance_round, dance_id, callback_marks=callback_marks)

    heat_table = HeatTables.get(section_id, round_id)
    marked_competitors = CallbackMarks.get(adjudicator_id, section_id, round_id, dance_id)
    context = {
        'conf': Conf.get(),
        'adjudicator_id': adjudicator_id,
        'dance_round': dance_round,
        'dance_id': dance_id,
        'heats': Heats.from_table(heat_table, dance_id),
        'marked_competitors': marked_competitors,
    }
    return render(request, 'pydanceweb/heats_for_adjudicator.html', context)

def judge_final(request, adjudicator_id, section_id, dance_id=''):
    if adjudicator_id not in Sections.get(section_id).adjudicators:
        return HttpResponse(f'Keine Berechtigung!')
    dance_round = DanceRounds.get_final(section_id)
    if not dance_round:
        return HttpResponse('Runde nicht gefunden.')
    if not dance_id:
        dance_id = dance_round.dances[0].id
    if request.method == 'POST':
        # TODO: improve
        final_marks = {}
        for competitor in dance_round.competitors:
            final_marks[competitor] = int(request.POST[str(competitor)])
        FinalMarks.save(adjudicator_id, final_marks, section_id, dance_round.id, dance_id)
        return _judge_next(request, adjudicator_id, dance_round, dance_id, final_marks=final_marks)
    final_marks = FinalMarks.get(adjudicator_id, section_id, dance_round.id, dance_id)
    context = {
        'conf': Conf.get(),
        'adjudicator_id': adjudicator_id,
        'section_id': section_id,
        'dance_round': dance_round,
        'dance_id': dance_id,
        'final_marks': final_marks
    }
    return render(request, 'pydanceweb/final.html', context)

# "open" views
def show_index(request):
    heat_table = HeatTables.merge_running()
    if heat_table is not None:
        heat_table = heat_table.to_html()
    context = {
        'conf': Conf.get(),
        'current_rounds': DanceRounds.get_running(),
        'finished_sections': Sections.get_finished(),
        'heat_table': heat_table
    }
    return render(request, 'pydanceweb/index.html', context)

def show_heats(request, section_id, round_id, dance_id=""):
    section = Sections.get(section_id)
    dance_round = DanceRounds.get(section_id, round_id)
    if not dance_round:
        return HttpResponse('Runde nicht gefunden.')
    if not dance_id:
        dance_id = dance_round.dances[0].id

    heat_table = HeatTables.get(section_id, round_id)
    context = {
        'conf': Conf.get(),
        'section': section,
        'dance_round': dance_round,
        'dance_id': dance_id,
        'first_dance_id': dance_round.dances[0].id,
        'last_dance_id': dance_round.dances[-1].id,
        'heats': Heats.from_table(heat_table, dance_id),
    }
    return render(request, 'pydanceweb/heats.html', context)

def show_results(request, section_id):
    section = Sections.get(section_id)
    place_table = Sections.get_results(section)
    preliminary_rounds = [dance_round for dance_round in DanceRounds.get_all(section_id) if not dance_round.is_final]
    callback_tables = [render_frame(table.to_frame()) for table in CallbackMarkTables.get_all(section_id)]
    final_round = DanceRounds.get_final(section.id)

    context = {
        'conf': Conf.get(),
        'section': section,
        'callback_tables_per_round': zip(preliminary_rounds, callback_tables),
        'place_table': render_frame(place_table),
        'final_round': final_round,
    }

    if final_round:
        final_tables = []
        for dance in final_round.dances:
            final_tables.append( render_frame(SkatingTables.create(section.id, final_round.id, dance.id).to_frame()) )
        context['final_tables_per_dance'] = zip(final_round.dances, final_tables)
        if len(final_round.dances) > 1:
            final_summary = FinalSummaries.get(section.id)
            context['final_summary'] = render_frame(final_summary)
    return render(request, 'pydanceweb/section_results.html', context)

# => calc awards
def show_award_results(request, award_id):
    award = Awards.get(award_id)
    award_table = Awards.get_results(award_id).astype('Int64')
    context = {
        'conf': Conf.get(),
        'award': award,
        'award_table': render_frame(award_table),
    }
    return render(request, 'pydanceweb/award_results.html', context)
