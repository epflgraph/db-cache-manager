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

Sinc `DBCachingManagerBase` is an abstract class, you need to first create a child class. The class `ExampleDBCachingManager` provides an example of how the base class should be extended:

```
class ExampleDBCachingManager(DBCachingManagerBase):
    # This class demonstrates how to extend the DBCachingManagerBase class for a concrete case
    # For most purposes, the default methods defined in the parent class should be appropriate for any and all tasks.
    # Feel free to overwrite any if you have special mechanisms (e.g. if some results expire after a certain amount
    # of time, you may have to overwrite `get_details`, `get_details_using_origin`, etc.)
    def __init__(self):
        """
        db_config: Parameters for the database connection
        cache_table: Name of the main cache table, where the actual results are stored
        most_similar_table: Name of the similarity table, where the similarity relationships between different rows
            of the cache table are stored
        schema: Name of the database schema
        """
        super().__init__(
            db_config={
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'pass': ''
            },
            cache_table='Example_Main', most_similar_table='Example_Most_Similar',
            schema='cache_graphai'
        )

    def init_db(self):
        # This method implements an abstract method in the parent.
        # This example demonstrates the general layout of this method, and generally these are all the lines you need.
        # All you have to do is to add your own columns to the definition of the cache table. See more below.

        # Making sure the schema exists
        self.db.execute_query(
            f"""
            CREATE DATABASE IF NOT EXISTS `{self.schema}`
            DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
            DEFAULT ENCRYPTION='N';
            """
        )

        # Creating the cache table if it does not exist
        # The columns "id_token" and "date_added" should not have their names changed, since the
        # methods in the parent class rely on their names.
        # The types of "id_token" and "date_added" should not be changed, but "fingerprint" can be LONGTEXT if need be.
        # Aside from these three columns, add any columns you need. For this example, the task could be text
        # classification: there is an "input" and an "output" column, where "output" is the name of the class that
        # "input" has been classified as. "fingerprint" is the fingerprint of "input", and can be null.
        self.db.execute_query(
            f"""
            CREATE TABLE IF NOT EXISTS `{self.schema}`.`{self.cache_table}` (
              `id_token` VARCHAR(255),
              `fingerprint` VARCHAR(255) DEFAULT NULL,
              `input` LONGTEXT DEFAULT NULL,
              `output` VARCHAR(255) DEFAULT NULL,
              `date_added` DATETIME DEFAULT NULL,
              PRIMARY KEY id_token (id_token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )

        # To speed up fingerprint lookups, it is advisable to create a fingerprint index
        try:
            self.db.execute_query(
                f"""
                CREATE INDEX `example_main_fp_index` ON `{self.schema}`.`{self.cache_table}` (`fingerprint`(64));
                """
            )
        except Exception:
            pass

        # Creating the closest match table. This table represents a DAG of most-similar relationships (although it
        # can also have self-loops), where the row with "id_token" as its id is found to be (almost or exactly)
        # identical to the row with "most_similar_token" as its id.
        self.db.execute_query(
            f"""
            CREATE TABLE IF NOT EXISTS `{self.schema}`.`{self.most_similar_table}` (
              `id_token` VARCHAR(255),
              `most_similar_token` VARCHAR(255) DEFAULT NULL,
              PRIMARY KEY id_token (id_token),
              KEY most_similar_token (most_similar_token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )
```

The names `id_token`, `most_similar_token`, and `date_added` should be left as-is. Other column names can be changed (even `fingerprint`).

Here is an example of how the example class can be used:

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
