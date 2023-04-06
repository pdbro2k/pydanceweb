from django.urls import path

from . import views

urlpatterns = [
    # index pages
    # admin overview
    path('desk', views.show_tournament_desk_index, name='show_tournament_desk_index'),
    path('desk/', views.show_tournament_desk_index, name='show_tournament_desk_index'),
    path('desk/competitors', views.show_competitor_overview, name='show_competitor_overview'),
    path('desk/competitors/', views.show_competitor_overview, name='show_competitor_overview'),
    path('desk/competitors/<competitor>', views.register_competitor, name='register_competitor'),

    # admin results/awards views
    path('desk/<section_id>/results', views.finalize_section, name='finalize_section'),
    path('desk/results', views.finalize, name='finalize'),
    path('desk/awards/<award_id>', views.handle_award, name='handle_award'),

    # adjudicator overview => current rounds
    path('judge_<adjudicator_id>', views.show_current_adjudicator_rounds, name='show_current_adjudicator_rounds'),
    path('judge_<adjudicator_id>/', views.show_current_adjudicator_rounds, name='show_current_adjudicator_rounds'),
    # open index => merged heat table and results
    path('', views.show_index, name='show_index'),

    # section views
    # admin section view => init rounds
    path('desk/<section_id>', views.handle_section, name='handle_section'),

    # dance round views
    # admin round overview/analysis
    path('desk/<section_id>/<int:round_id>', views.handle_round, name='handle_round'),
    # admin heats view => move_to_last_heat
    path('desk/<section_id>/<int:round_id>/heats', views.handle_heats, name='handle_heats'),
    path('desk/<section_id>/<int:round_id>/heats/<dance_id>', views.handle_heats, name='handle_heats'),

    # adjudicator heats view => set_callback_marks
    path('judge_<adjudicator_id>/<section_id>/<int:round_id>', views.judge_heats, name='judge_heats'),
    path('judge_<adjudicator_id>/<section_id>/<int:round_id>/<dance_id>', views.judge_heats, name='judge_heats'),
    # adjudicator final view => set_final_marks
    path('judge_<adjudicator_id>/<section_id>/final', views.judge_final, name='judge_final'),
    path('judge_<adjudicator_id>/<section_id>/final/<dance_id>', views.judge_final, name='judge_final'),

    # open heats view
    path('<section_id>/<int:round_id>', views.show_heats, name='show_heats'),
    path('<section_id>/<int:round_id>/<dance_id>', views.show_heats, name='show_heats'),
    # MEMO: nice to have: adjudicator sheets for all current rounds

    # open results/ awards views
    path('<section_id>/results', views.show_results, name='show_results'),
    path('awards/<award_id>', views.show_award_results, name='show_award_results'),
]
