import pandas as pd

def _join_and_rename_columns(df, df_2, how='inner'):
    if df is None:
        df_2.columns = [f'place_{i+1}' for i in range(len(df_2.columns))]
        return df_2
    column_count = len(df.columns)
    df_2.columns = [f'place_{i+1}' for i in range(column_count, column_count + len(df_2.columns))]
    return df.join(df_2, how=how)

def _merge_place_frames(place_dfs, how='inner'):
    df = None
    for i, place_df in enumerate(place_dfs):
        place_df = place_df['place'].to_frame()
        place_df.columns = [f'place_{i+1}']
        df = _join_and_rename_columns(df, place_df, how=how)
    return df

def _build_best_n_frame(place_dfs, n):
    base_df = _merge_place_frames(place_dfs, how='outer')
    df = pd.DataFrame(columns=[f'place_{i+1}' for i in range(n)])
    for competitor in base_df.index:
        sorted_places = sorted(base_df.loc[competitor].T.dropna())
        if len(sorted_places) >= n:
            df.loc[competitor] = sorted_places[:n]
    return df

def extract_section_ids(section_id_or_rules):
    section_ids = []
    for section_id_or_rule in section_id_or_rules:
        if isinstance(section_id_or_rule, dict):
            for rule_name in section_id_or_rule:
                rule = section_id_or_rule[rule_name]
                if 'sections' in rule:
                    section_ids += rule['sections']
        elif isinstance(section_id_or_rule, str):
            section_ids.append(section_id_or_rule)
    return section_ids

def get_award_results(section_id_or_rules, place_dfs_per_section_id):
    df = None
    for section_id_or_rule in section_id_or_rules:
        if isinstance(section_id_or_rule, dict):
            rule_name = list(section_id_or_rule)[0]
            rule = section_id_or_rule[rule_name]
            if rule_name == 'BEST':
                section_ids = rule['sections']
                if 'n' in rule:
                    n = rule['n']
                else:
                    n = len(section_ids)
                place_dfs = []
                for section_id in section_ids:
                    if section_id not in place_dfs_per_section_id:
                        return pd.DataFrame() # since section isn't finished
                    place_dfs.append(place_dfs_per_section_id[section_id])
                df = _join_and_rename_columns(df, _build_best_n_frame(place_dfs, n))
        elif isinstance(section_id_or_rule, str):
            if section_id_or_rule not in place_dfs_per_section_id:
                return pd.DataFrame() # since section isn't finished
            df = _join_and_rename_columns(df, place_dfs_per_section_id[section_id_or_rule])
    df['total'] = sum([df[x] for x in df.columns])
    df['place'] = 0
    n = 0
    current_place = 1
    current_sum = 0
    for competitor, row in df.sort_values(by='total').iterrows():
        n += 1
        if row['total'] > current_sum:
            current_sum = row['total']
            current_place = n
        df.at[competitor, 'place'] = current_place
    return df.astype('int64')
