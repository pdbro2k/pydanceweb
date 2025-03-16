from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect, render

from .pydance_objects import *
from .pydance_tables import *
from .models import *

# generic helpers
def render_frame(frame):
    if frame is not None:
        if 'place' in frame.columns:
            return frame.reset_index().sort_values(by=['place', 'index']).set_index('index').to_dict('index')
        return frame.to_dict('index')

def show_competitor_overview(request):
    conf = Conf.get()
    table = CompetitorStartTables.get()
    section_ids = table.get_sections()
    unstarted_sections = Sections.get_running() + Sections.get_finished()
    context = {
        'conf': conf,
        'title': 'Teilnehmer',
        'competitor_table': render_frame(table.to_frame()),
        'section_ids': section_ids,
        'unstarted_sections': unstarted_sections
    }
    return render(request, 'pydanceweb/competitor_overview.html', context)


def register_new_competitor(request):
    return register_competitor(request, CompetitorStartTables.get().get_new_id())


def register_competitor(request, competitor=""):
    if not competitor.isdigit():
        return HttpResponse(f'Die Startnummer {competitor} ist ungültig!')

    conf = Conf.get()
    table = CompetitorStartTables.get()
    uneditable_sections = Sections.get_uneditable()

    if request.POST:
        context = {
            'conf': conf,
            'competitor': competitor
        }
        #try:
        if True:
            lead = Person(competitor, request.POST['lead_name'], request.POST['lead_first_name'], request.POST['lead_team'])
            follow = Person(competitor, request.POST['follow_name'], request.POST['follow_first_name'], request.POST['follow_team'])
            registered_sections = []
            for section in conf.sections:
                if section not in uneditable_sections:
                    if section.id in request.POST:
                        registered_sections.append(section)
            CompetitorStartTables.set(table, competitor, registered_sections, lead, follow)
        #except Exception as e:
        #    print(e)
        #    context['error'] = True

        return render(request, 'pydanceweb/registration_reaction.html', context)

    registered_sections = [Section(section_id) for section_id in table.get_participations(int(competitor))]
    preregistered_sections = [Section(section_id) for section_id in table.get_preregistrations(int(competitor))]
    context = {
        'conf': conf,
        'title': f'Paar {competitor} Registrierung',
        'competitor_id': competitor,
        'lead': CompetitorStartTables.get_lead(table, competitor),
        'follow': CompetitorStartTables.get_follow(table, competitor),
        'ungrouped_sections': conf.get_ungrouped_sections(),
        'registered_sections': registered_sections,
        'preregistered_sections': preregistered_sections,
        'uneditable_sections': uneditable_sections
    }
    return render(request, 'pydanceweb/competitor_registration.html', context)

def show_adjudicator_overview(request):
    conf = Conf.get()
    table = AdjudicatorStartTables.get()
    section_ids = table.get_sections()
    context = {
        'conf': conf,
        'title': 'Wertungsrichter',
        'adjudicator_table': render_frame(table.to_frame()),
        'section_ids': section_ids,
        'base_url': request.build_absolute_uri('/')[:-1]
    }
    return render(request, 'pydanceweb/adjudicator_overview.html',context)


# admin views
def show_tournament_desk_index(request):
    conf = Conf.get()
    dance_rounds_per_section = {}
    for i, section in enumerate(conf.sections):
        initiated_section = Sections.get(section.id)
        if initiated_section:
            conf.sections[i] = initiated_section
            for j, section_group in enumerate(conf.section_groups):
                for k, grouped_section in enumerate(conf.section_groups[j].sections):
                    if grouped_section == initiated_section:
                        conf.section_groups[j].sections[k] = initiated_section
            dance_rounds_per_section[initiated_section.id] = DanceRounds.get_all(section.id)
    context = {
        'conf': conf,
        'title': 'Gesamtübersicht',
        'ungrouped_sections': conf.get_ungrouped_sections(),
        'dance_rounds_per_section': dance_rounds_per_section
    }
    return render(request, 'pydanceweb/index_for_tournament_desk.html', context)

def handle_section(request, section_id):
    section = Sections.get(section_id)
    if not section:
        section = Sections.create(section_id)
    if len(section.dances) == 0:
        section.is_finished = True
        Sections.save(section)
    dance_rounds = DanceRounds.get_all(section_id)
    last_round = dance_rounds[-1] if dance_rounds else None
    next_round_id = last_round.id + 1 if last_round else 1
    context = {
        'conf': Conf.get(),
        'title': section_id,
        'section': section,
        'dance_rounds': dance_rounds,
        'last_round': last_round,
        'next_round_id': next_round_id
    }
    return render(request, 'pydanceweb/section.html', context)

def _prepare_round(request, section_id, round_id):
    section = Sections.get(section_id)
    conf = Conf.get()
    max_heat_size = conf.max_heat_size
    if round_id == 1:
        # init new first round
        dance_round = DanceRounds.create_first(section_id)
    else:
        # init next round
        current_dance_round =  DanceRounds.get(section_id, round_id - 1)
        if not current_dance_round:
            return HttpResponse("Runde nicht gefunden")
        callback_count = int(request.POST["callback_count"])
        dance_round = DanceRounds.create_next(current_dance_round, callback_count)

    if not dance_round:
        return HttpResponse('Runde nicht gefunden')
    context = {
        'conf': conf,
        'section': section,
        'dance_round': dance_round,
        'heat_counts_per_size': dance_round.get_min_heat_counts_per_size(max_heat_size)
    }
    return render(request, 'pydanceweb/dance_round_preparation.html', context)

def handle_round(request, section_id, round_id):
    if request.POST and 'reset' in request.POST and request.POST['reset'] == 'true':
        DanceRounds.remove(DanceRounds.get(section_id, round_id))
        if round_id > 1:
            return redirect('handle_round', section_id = section_id, round_id = round_id - 1)

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
            section.is_running = True
            Sections.save(section)
            dance_round.is_running = True
            _add_additional_dances(dance_round, section, request.POST.getlist("add_dances"))
            DanceRounds.save(dance_round)

    final_tables = []
    for dance in dance_round.dances:
        final_tables.append( render_frame(SkatingTables.create(section.id, dance_round.id, dance.id).to_frame()) )

    context = {
        'conf': Conf.get(),
        'title': f'{section.id} Endrunde',
        'section': section,
        'dance_round': dance_round,
        'final_tables_per_dance': zip(dance_round.dances, final_tables),
    }
    if len(dance_round.dances) > 1:
        final_summary = FinalSummaries.create(section.id)
        context['final_summary'] = render_frame(final_summary.to_frame())
    return render(request, 'pydanceweb/final_round.html', context)

def _handle_preliminary_round(request, dance_round, section):
    if request.POST:
        dance_round.callback_wish = int(request.POST['callback_wish'])
        dance_round.max_heat_size = int(request.POST['heat_size'])
        _add_additional_dances(dance_round, section, request.POST.getlist("add_dances"))        
        DanceRounds.save(dance_round)
    callback_table = CallbackMarkTables.create(section.id, dance_round.id)
    context = {
        'conf': Conf.get(),
        'title': f'{section.id} {dance_round.name}',
        'section': section,
        'dance_round': dance_round,
        'callback_table': render_frame(callback_table.to_frame()),
        'callback_options': callback_table.get_callback_options(),
    }
    return render(request, 'pydanceweb/preliminary_round.html', context)

def _add_additional_dances(dance_round, section, added_dance_ids):
    if len(added_dance_ids) > 0:
        # remove added dance from additional dance list
        section.additional_dances = [dance for dance in section.additional_dances if dance.id not in added_dance_ids]
        Sections.save(section)

        # add dance to dances
        additional_dance_ids = [additional_dance.id for additional_dance in section.additional_dances]
        dance_round.dances = [dance for dance in section.dances if dance.id not in additional_dance_ids]

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
        if "DelayStart" in request.POST:
            competitors = [int(x) for x in request.POST.getlist('competitors')]
            HeatTables.move_to_last_heat(heat_table, section_id, round_id, dance_id, competitors)
        elif "RemoveCompetitor" in request.POST:
            competitors = [int(x) for x in request.POST.getlist('competitors')]
            # Tranformation to update the section
            section_dict = section.to_dict()
            _tmp_competitors = section_dict['competitors']
            #Remove Competitor from Heats
            HeatTables.remove_competitor(heat_table,section_id,round_id,dance_id,competitors)
            for competitor in competitors:
                _tmp_competitors.remove(competitor)
            section_dict['competitors'] = _tmp_competitors
            section = Section.from_dict(section_dict)
            Sections.save(section)
            #Remove Competitor from DanceRound
            dance_round_dict = dance_round.to_dict()
            dance_round_dict['competitors'] = _tmp_competitors
            dance_round = DanceRound.from_dict(dance_round_dict)
            DanceRounds.save(dance_round)

    context = {
        'conf': Conf.get(),
        'title': f'{section.id} {dance_round.name}',
        'section': section,
        'dance_round': dance_round,
        'dance_id': dance_id,
        'first_dance_id': dance_round.dances[0].id,
        'last_dance_id': dance_round.dances[-1].id,
        'preceding_dance_id': DanceRounds.get_preceding_dance_id(dance_round, dance_id),
        'following_dance_id': DanceRounds.get_following_dance_id(dance_round, dance_id),
        'heats': Heats.from_table(heat_table, dance_id),
    }
    return render(request, 'pydanceweb/heats_for_tournament_desk.html', context)

# => finish current section
def finalize_section(request, section_id):
    final_round = DanceRounds.get_final(section_id)
    if request.POST and 'reset' in request.POST and request.POST['reset'] == 'true':
        Sections.remove_results(Sections.get(section_id))
        return redirect('handle_round', section_id = final_round.section_id, round_id = final_round.id)

    if final_round and not final_round.is_finished:
        # create final summary and finish final
        final_summary = FinalSummaries.create(section_id)
        #final_round = DanceRounds.get_final(section_id)
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
    return show_results(request, section_id, resetable=True)

# => calc awards
def handle_award(request, award_id):
    award = Awards.get(award_id)
    if not award:
        return HttpResponse('Sonderwertung nicht gefunden')
    results = Awards.create_results(award_id)
    return show_award_results(request, award_id)

def finalize(request):
    results_table = OverallResults.create()
    context = {
        'conf': Conf.get(),
        'title': 'Ergebnisübersicht',
        'results_table': results_table.to_html(),
    }
    return render(request, 'pydanceweb/overall_results.html', context)

# adjudicator views
def show_current_adjudicator_rounds(request, adjudicator_id):
    adjudicator_id = adjudicator_id.upper() # ignore case
    context = {
        'conf': Conf.get(),
        'title': f'Wertungsrichter {adjudicator_id}',
        'adjudicator_id': adjudicator_id,
        'current_rounds': DanceRounds.get_running(adjudicator_id),
    }
    return render(request, 'pydanceweb/index_for_adjudicator.html', context)

def show_current_adjudicator_sheets(request):
    current_rounds = []
    adjudicators_per_section = { section.id: section.adjudicators for section in Sections.get_running() }
    heat_dict = {}
    for dance_round in DanceRounds.get_running():
        section_id = dance_round.section_id
        current_rounds.append(dance_round)

        current_heat_dict = {}
        for dance in dance_round.dances:
            if dance_round.is_final:
                continue
            current_heat_dict[str(dance.id)] = Heats.from_table(HeatTables.get(section_id, dance_round.id), dance.id)
        heat_dict[str(section_id)] = { 
            str(dance_round.id): current_heat_dict
        }
    context = {
        'conf': Conf.get(),
        'title': 'Wertungsrichterbögen',
        'current_rounds': current_rounds,
        'adjudicators_per_section': adjudicators_per_section,
        'heat_dict': heat_dict,
    }
    return render(request, 'pydanceweb/scoresheets_for_adjudicator.html', context)

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
        'title': f'{section_id} {dance_round.name} | Wertungsrichter {adjudicator_id}',
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
        'title': f'{section_id} {dance_round.name} | Wertungsrichter {adjudicator_id}',
        'adjudicator_id': adjudicator_id,
        'section_id': section_id,
        'dance_round': dance_round,
        'dance_id': dance_id,
        'final_marks': final_marks
    }
    return render(request, 'pydanceweb/final.html', context)

# chair views
def show_index_for_chair(request):
    context = {
        'conf': Conf.get(),
        'title': 'Laufende Runden',
        'current_rounds': DanceRounds.get_running(),
    }
    return render(request, 'pydanceweb/index_for_chair.html', context)

def show_heats_for_chair(request, section_id, round_id, dance_id=""):
    return show_heats(request, section_id, round_id, dance_id, True)

# "open" views
def show_index(request):
    conf = Conf.get()
    current_rounds = DanceRounds.get_running()
    all_section_groups = conf.section_groups
    ungrouped_sections = conf.get_ungrouped_sections()
    section_groups = []
    current_rounds_per_group = {}
    for dance_round in current_rounds:
        section = Sections.get(dance_round.section_id)
        if section in ungrouped_sections:
            section_group = SectionGroup("Weitere", "Weitere", [section])
            if section_group in section_groups:
                current_rounds_per_group[str(section_group.id)].append(dance_round)
            else:
                section_groups.append(section_group)
                current_rounds_per_group[str(section_group.id)] = [dance_round]
            if section_group in section_groups:
                section_groups[section_groups.index(section_group)].sections.append(section)
            else:
                section_groups.append(section_group)
            continue
        for section_group in all_section_groups:
            if section in section_group.sections:
                if section_group in section_groups:
                    current_rounds_per_group[str(section_group.id)].append(dance_round)
                else:
                    section_groups.append(section_group)
                    current_rounds_per_group[str(section_group.id)] = [dance_round]
                break
    heat_tables_per_group = {}
    for section_group in section_groups:
        section_ids = [section.id for section in section_group.sections]
        heat_table = HeatTables.merge_running(section_ids)
        if heat_table is not None:
            heat_tables_per_group[str(section_group.id)] = [heat_table.to_html()]
    context = {
        'conf': Conf.get(),
        'title': conf.name,
        'section_groups': section_groups,
        'heat_tables_per_group': heat_tables_per_group,
        'current_rounds_per_group': current_rounds_per_group,
        'finished_sections': Sections.get_finished()
    }
    return render(request, 'pydanceweb/index.html', context)

def show_heats(request, section_id, round_id, dance_id="", is_chair=False):
    section = Sections.get(section_id)
    dance_round = DanceRounds.get(section_id, round_id)
    if not dance_round:
        return HttpResponse('Runde nicht gefunden.')
    if not dance_id:
        dance_id = dance_round.dances[0].id

    if dance_round.is_final:
        if is_chair:
            context = {
                'conf': Conf.get(),
                'section': section,
                'dance_round': dance_round,
                'dance_id': dance_id,
                'preceding_dance_id': DanceRounds.get_preceding_dance_id(dance_round, dance_id),
                'following_dance_id': DanceRounds.get_following_dance_id(dance_round, dance_id),
                'first_dance_id': dance_round.dances[0].id,
                'last_dance_id': dance_round.dances[-1].id
            }
            return render(request, 'pydanceweb/final_for_chair.html', context)
        return HttpResponse('Runde nicht gefunden.')

    heat_table = HeatTables.get(section_id, round_id)
    context = {
        'conf': Conf.get(),
        'title': f'{section_id} {dance_round.name}',
        'section': section,
        'dance_round': dance_round,
        'dance_id': dance_id,
        'preceding_dance_id': DanceRounds.get_preceding_dance_id(dance_round, dance_id),
        'following_dance_id': DanceRounds.get_following_dance_id(dance_round, dance_id),
        'first_dance_id': dance_round.dances[0].id,
        'last_dance_id': dance_round.dances[-1].id,
        'heats': Heats.from_table(heat_table, dance_id),
        'is_chair': is_chair
    }
    return render(request, 'pydanceweb/heats.html', context)

def show_results(request, section_id, resetable=False):
    section = Sections.get(section_id)
    place_table = Sections.get_results(section)

    context = {
        'conf': Conf.get(),
        'title': f'{section.id} Ergebnisse',
        'section': section,
        'resetable': resetable
    }

    if place_table is not None:
        preliminary_rounds = [dance_round for dance_round in DanceRounds.get_all(section_id) if not dance_round.is_final]
        callback_tables = [render_frame(table.to_frame()) for table in CallbackMarkTables.get_all(section_id)]
        final_round = DanceRounds.get_final(section.id)
        context['callback_tables_per_round'] = zip(preliminary_rounds, callback_tables)
        context['place_table'] = render_frame(place_table)
        context['final_round'] = final_round

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
    award_table = Awards.get_results(award_id)
    context = {
        'conf': Conf.get(),
        'title': f'{award.id} Ergebnisse',
        'award': award,
        'award_table': render_frame(award_table),
    }
    return render(request, 'pydanceweb/award_results.html', context)
