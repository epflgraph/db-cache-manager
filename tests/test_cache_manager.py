import pytest
from db_cache_manager.db import ExampleDBCachingManager
from configparser import ConfigParser
from datetime import datetime


def read_config():
    parser = ConfigParser()
    parser.read('../config.ini')
    config = {section: dict(parser[section]) for section in parser.sections()}
    return config['database']


def test__creation():
    cache_manager = ExampleDBCachingManager(read_config())
    assert cache_manager.db is not None


@pytest.mark.usefixtures('basic_rows')
def test__insert(basic_rows):
    cache_manager = ExampleDBCachingManager(read_config())
    for id_token in basic_rows:
        cache_manager.insert_or_update_details(id_token, basic_rows[id_token])
    assert cache_manager.get_cache_count() == 5


@pytest.mark.usefixtures('id_token', 'fingerprint')
def test__select(id_token, fingerprint):
    cache_manager = ExampleDBCachingManager(read_config())
    results = cache_manager.get_details(id_token, ['fingerprint'])[0]
    assert len(results) == 2
    assert results['id_token'] == id_token
    assert results['fingerprint'] == fingerprint


@pytest.mark.usefixtures('origin_token')
def test__select_by_origin(origin_token):
    cache_manager = ExampleDBCachingManager(read_config())
    results = cache_manager.get_details_using_origin(origin_token, ['input'])
    assert len(results) == 3
    assert all(results[i]['input'] in ['0', '1', '2'] for i in range(len(results)))


@pytest.mark.usefixtures('eq_cond', 'second_eq_cond')
def test__count_with_condition(eq_cond, second_eq_cond):
    cache_manager = ExampleDBCachingManager(read_config())
    # With equality condition
    count = cache_manager.get_cache_count(equality_conditions=eq_cond)
    assert count == 2
    count = cache_manager.get_cache_count(equality_conditions=second_eq_cond)
    assert count == 3
    # With non-null condition
    count = cache_manager.get_cache_count(non_null_cols=['fingerprint'])
    assert count == 4
    count = cache_manager.get_cache_count()
    assert count == 5


@pytest.mark.usefixtures('id_token', 'earliest_date', 'date_2', 'fingerprint', 'other_fingerprint', 'eq_cond')
def test__select_all(id_token, earliest_date, fingerprint, date_2, other_fingerprint, eq_cond):
    cache_manager = ExampleDBCachingManager(read_config())

    # Testing exclude_token
    results = cache_manager.get_all_details(cols=['fingerprint'], exclude_token=id_token)
    assert len(results) == 4
    assert id_token not in results

    # Testing the earliest_date parameter
    results = cache_manager.get_all_details(cols=['fingerprint', 'date_added'], earliest_date=earliest_date)
    assert len(results) == 2
    assert all(datetime.strftime(results[k]['date_added'], '%Y-%m-%d %H:%M:%S') == date_2
               for k in results)

    # Testing earliest_date + allow_nulls
    results = cache_manager.get_all_details(cols=['fingerprint'], earliest_date=earliest_date,
                                            allow_nulls=False)
    assert len(results) == 1
    assert results[list(results.keys())[0]]['fingerprint'] == other_fingerprint

    # Testing earliest_date + allow_nulls + equality_conditions (which in this case should yield no results)
    results = cache_manager.get_all_details(cols=['fingerprint'], earliest_date=earliest_date,
                                            allow_nulls=False, equality_conditions=eq_cond)
    assert results is None

    # Testing start + limit
    results = cache_manager.get_all_details(cols=['fingerprint'], start=0, limit=2)
    assert len(results) == 2
    assert all(results[k]['fingerprint'] == fingerprint for k in results)

    results = cache_manager.get_all_details(cols=['fingerprint'], start=3, limit=1)
    assert len(results) == 1
    assert all(results[k]['fingerprint'] is None for k in results)


@pytest.mark.usefixtures('id_token', 'attack_token_1', 'attack_token_2',
                         'attack_token_3', 'attack_token_4', 'fingerprint')
def test__attack(id_token, attack_token_1, attack_token_2, attack_token_3, attack_token_4, fingerprint):
    cache_manager = ExampleDBCachingManager(read_config())

    # Attack #1: OR with always-true condition
    results = cache_manager.get_details(attack_token_1, ['fingerprint'])[0]
    assert results is None

    # Attack #2: Same as above but with single quotes
    results = cache_manager.get_details(attack_token_2, ['fingerprint'])[0]
    assert results is None

    # Attack #3: Always-true condition exploiting single quotes
    results = cache_manager.get_details(attack_token_3, ['fingerprint'])[0]
    assert results is None

    # Attack #4: With drop table command
    results = cache_manager.get_details(attack_token_4, ['fingerprint'])[0]
    assert results is None
    assert cache_manager.db.check_if_table_exists('test_db_cache_manager', 'Example_Most_Similar')

    # Attack #5: Update with always-true condition
    cache_manager.insert_or_update_details(attack_token_1, {'fingerprint': 'gibberish'})
    results = cache_manager.get_details(id_token, ['fingerprint'])[0]
    assert results['fingerprint'] == fingerprint
    # Checking that in fact, an insertion happened instead of an update
    results = cache_manager.get_details(attack_token_1, ['fingerprint'])[0]
    assert results['fingerprint'] == 'gibberish'
    # Deleting the new row
    cache_manager.delete_cache_rows([attack_token_1])
    # Checking that the deletion happened correctly
    count = cache_manager.get_cache_count()
    assert count == 5
