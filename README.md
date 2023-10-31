# DB and Cache Manager

This package consists of a database connector class and an abstract cache manager class, which can be used to perform database operations and caching of computed results in a user-friendly way and with support for fingerprinting and automatic lookup of similar elements in the cache.

## Installation
To install the package, run:

```
pip install db-cache-manager
```

## Features

This package contains two classes, `DB` and `DBCachingManagerBase`, and a variety of helper functions (mostly for escaping characters in strings that are to be inserted into a database). 

`DB` is a standard database connector that allows you to query MySQL with ease.

`DBCachingManagerBase` is an abstract caching manager that supports a cache with a main cache table (where results are stored) and a similarity table (where for each row, the most similar pre-existing row can be stored). It supports fingerprints for each cache row, and allows the user to use their own fingerprinting logic in order to populate the similarity table. The logic of the cache is as follows:

* Each cache row has an id, contained in the column `id_token`, which is how cache rows are identified in the similarity table as well.
* Each row optionally has a `fingerprint` column and a `date_added` column, which can be used to perform fingerprint lookups and populate the similarity table.
* The similarity table expects its contents to form a directed acyclic graph (DAG), except it allows for self-loops and handles them as if they do not exist. When looking for the most similar element to a given element, it always resolves the former's chain of similarities to the end.
* When performing a fingerprint lookup, if there are multiple matches, it sorts the results by their `date_added`, returning the oldest row first. This makes it very easy to respect the DAG constraint of the similarity table.
* When a lookup operation is performed for the results of an `id_token` value, the caching manager looks both at the results of the id token itself, as well as the results of its most similar token, after resolving the chain of similarities. It returns both results: first the results of the id token itself, then the results of its closest match.
* The cache table supports an `origin_token` column, which allows for multiple child classes (i.e. caches) that reference each other. For example, if you have a cache table for videos and a cache table for the audio extracted from those videos, you can add an `origin_token` column to the audio cache table that is a foreign key for the video cache table, allowing you to perform lookups (using the native methods) in the audio table using both video and audio ids.
* The caching logic assumes that each row's results are invariant. Therefore, extra care must be taken to ensure that each token's results never change.
* If a hashing algorithm is used to generate the id tokens and a perceptual hashing algorithm is used for the fingerprints, the cache can effectively allow for two fingerprint lookups: one exact and one approximate.

## Usage

### Using the database connector

To use the database connector, import the `DB` class, like in the following example:

```
from db_cache_manager.db import DB

db_connector = DB({
  'host': 'localhost',
  'port': 3306,
  'user': 'yourusername',
  'pass': 'yourpassword'
})

res = db_connector.execute_query("SELECT column1, column2 FROM someschema.sometable")
```

### Using the cache manager

To use the abstract cache manager, import the following:

```
from db_cache_manager.db import DBCachingManagerBase
```

Sinc `DBCachingManagerBase` is an abstract class, you need to first create a child class. The class `ExampleDBCachingManager` provides an example of how the base class should be extended. Here is an example of how the example class can be used:

```
token = 'sometoken'
new_token = 'anothertoken'
out = None
db_manager = ExampleDBCachingManager()
# Performing a cache lookup
existing = db_manager.get_details(token, ['input', 'output', 'fingerprint'])
# Returning the row's own results if they are not null, then looking at the results of the closest match
for existing_row in existing:
    if existing_row is not None and existing_row['output'] is not None:
        input_str = existing_row['input']
        output_str = existing_row['output']
        target_fingerprint = existing_row['fingerprint']

# Inserting the same results into the table with another token
if output_str is not None:
    dt = datetime.now()
    current_datetime = dt.strftime("%Y-%m-%d %H:%M:%S")
    # Constructing the column_name: value dictionary that we will insert into the table
    values = {
        'fingerprint': target_fingerprint,
        'input': input_str,
        'output': output_str
        'date_added': current_datetime
    }
    db_manager.insert_or_update_details(new_token, values_to_insert=values)
else:
    return

# Now, performing a fingerprint lookup for the new token

# This line sets up the condition of the fingerprint lookup: that the fingerprint should be equal to the new token's fingerprint
equality_conditions = {'fingerprint': target_fingerprint}

# Performing a fingerprint lookup
# `exclude_token` is a string or a list of strings, indicating the tokens that are to be excluded from the lookup
# Here, the new token itself must be excluded in order not to trivially get a self-match
# The equality conditions turn this retrieval operation into a fingerprint lookup
tokens_and_fingerprints = db_manager.get_all_details(
  ['fingerprint', 'date_added'], start=0, limit=-1, exclude_token=new_token,
  allow_nulls=False, equality_conditions=equality_conditions
)

if tokens_and_fingerprints is not None:
    # insertion order is preserved in Python > 3.7, and the results are inserted in order of their `date_added` (ascending)
    all_tokens = list(tokens_and_fingerprints.keys())
    all_fingerprints = [tokens_and_fingerprints[key]['fingerprint'] for key in all_tokens]
    all_dates = [tokens_and_fingerprints[key]['date_added'] for key in all_tokens]

    # Since the results are ordered by `date_added`, the first element is the earliest match
    closest_token, closest_fingerprint, closest_date = all_tokens[0], all_fingerprints[0], all_dates[0]

    # Inserting the results. The method automatically resolves the chain of similarities before insertion.
    db_manager.insert_or_update_closest_match(
        new_token,
        {
            'most_similar_token': closest_token
        }
    )
```
