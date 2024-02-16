import pytest


DATE_1 = '2023-09-10 11:11:11'
DATE_2 = '2023-09-12 07:08:09'


@pytest.fixture
def date_2():
    return DATE_2


@pytest.fixture
def basic_rows():
    dates = [DATE_1, DATE_2]
    return {
        f'test_token_{str(i)}': {
            'fingerprint': f'test_fingerprint_{str(i // 2)}' if i != 3 else None,
            'origin_token': f'origin_token_{str(i // 3)}',
            'input': str(i),
            'output': '',
            'input_length': 0,
            'input_flag': i % 2,
            'date_added': dates[i // 3]
        }
        for i in range(5)
    }


@pytest.fixture
def id_token():
    return 'test_token_0'


@pytest.fixture
def origin_token():
    return 'origin_token_0'


@pytest.fixture
def fingerprint():
    return 'test_fingerprint_0'


@pytest.fixture
def other_fingerprint():
    return 'test_fingerprint_2'


@pytest.fixture
def new_fingerprint():
    return 'test_fingerprint_3'


@pytest.fixture
def eq_cond():
    return {'fingerprint': 'test_fingerprint_0'}


@pytest.fixture
def second_eq_cond():
    return {'input_flag': 0}


@pytest.fixture
def earliest_date():
    return '2023-09-11 00:01:02'


@pytest.fixture
def attack_token_1():
    return "test_token_0 OR 1=1"


@pytest.fixture
def attack_token_2():
    return "test_token_0' OR '1'='1"


@pytest.fixture
def attack_token_3():
    return "' or ''='"


@pytest.fixture
def attack_token_4():
    return "'test_token_0'; DROP TABLE `test_db_cache_manager`.`Example_Most_Similar`"
