import pytest


@pytest.fixture
def basic_rows():
    dates = ['2023-09-10 11:11:11', '2023-09-12 07:08:09']
    return [
        (f'test_token_{str(i)}',
         f'test_fingerprint_{str(i // 2)}',
         '',
         '',
         0,
         1,
         dates[i // 3])
        for i in range(5)
    ]


@pytest.fixture
def id_token():
    return 'test_token_0'


@pytest.fixture
def fingerprint():
    return 'test_fingerprint_0'


@pytest.fixture
def new_fingerprint():
    return 'test_fingerprint_3'


@pytest.fixture
def eq_cond():
    return {'fingerprint': 'test_fingerprint_0'}


@pytest.fixture
def earliest_date():
    return '2023-09-11 00:01:02'
