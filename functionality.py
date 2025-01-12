import asyncio

from text_processing import get_last_syllable
from sql_via_code import get_query_from_db, exec_procedure_from_db
from queries_bank import *

"""
    Retrieves the ID of a song based on its name.

    Args:
        song_name (str): The name of the song to search for.

    Returns:
        int: The ID of the song if found.

    Raises:
        Exception: If the song is not found.
"""
async def get_song_id(song_name):
    get_song_id_query = "SELECT id FROM songs WHERE song_name = :song_name"
    params = {'song_name': song_name}
    song_id_query_df = await get_query_from_db(get_song_id_query, None, params=params)
    if not song_id_query_df.empty:
        return int(song_id_query_df.iloc[0, 0])
    else:
        raise Exception(f"Inside function 'get_song_id':\nSong with name '{song_name}' was not found.")

"""
    Inserts details of a song into the song_details table.

    Args:
        song_name (str): The name of the song.
        poet (str, optional): The name of the poet. Defaults to "".
        composer (str, optional): The name of the composer. Defaults to "".
        creation_year (str, optional): The creation year of the song. Defaults to "".
        video_link (str, optional): The performance video link. Defaults to "".
        performer_name (str, optional): The name of the performer. Defaults to "".

    Raises:
        Exception: If no details are provided.
"""
async def insert_song_details(song_name, poet = "", composer = "", creation_year = "", video_link = "", performer_name = ""):
    if not any([poet, composer, creation_year, video_link, performer_name]):
        raise Exception("Inside function 'insert_song_details':\nNo details provided")
    song_id = await get_song_id(song_name)
    insert_song_details_query = """
        INSERT INTO song_details (song_id, [Poet’s_Name], [Composer’s_Name], Creation_Year, Performance_Video_Link, [Performer’s_Name])
        VALUES (:song_id, :Poets_Name, :Composers_Name, :Creation_Year, :Performance_Video_Link, :Performers_Name)
        """
    params = {
        'song_id': song_id,
        'Poets_Name': poet,
        'Composers_Name': composer,
        'Creation_Year': creation_year,
        'Performance_Video_Link': video_link,
        'Performers_Name': performer_name
        }
    await get_query_from_db(insert_song_details_query, None, params=params)

"""
    Removes a specific song detail entry based on its ID.

    Args:
        details_line_id (int): The ID of the detail entry to remove.
"""
async def remove_song_details_line(details_line_id):
    params = {'details_line_id': details_line_id}
    await get_query_from_db(remove_details_line, None, params=params)

"""
    Retrieves song details based on search parameters.

    Args:
        song_name (str, optional): Name of the song. Defaults to None.
        poet (str, optional): Name of the poet. Defaults to None.
        composer (str, optional): Name of the composer. Defaults to None.
        creation_year (str, optional): Year of creation. Defaults to None.
        performer_name (str, optional): Name of the performer. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame containing the search results.
"""
async def get_search_details_df(song_name = None, poet = None, composer = None, creation_year = None, performance_video_link = None, performer_name = None):
    params = {
        'song_name': song_name,
        'poet': poet,
        'composer': composer,
        'creation_year': creation_year,
        'Performance_Video_Link': performance_video_link,
        'performer_name': performer_name
        }
    song_id_query_df = await get_query_from_db(search_details, None, params=params)
    if song_id_query_df.empty:
        return []
    return list(song_id_query_df.itertuples(index=False, name=None))

"""
    Inserts a new group into the database if it does not already exist.

    Args:
        group_name (str): The name of the group.
        group_purpose (str, optional): The purpose of the group. Defaults to "".

    Returns:
        int or None: The ID of the inserted group, or None if it already exists.
"""
async def insert_new_group(group_name, group_purpose = ''):
    params = {
        'group_name': group_name,
        'group_purpose': group_purpose
        }

    existing_group_df = await get_query_from_db(get_group_id, None, params=params)
    if existing_group_df.empty:
        group_id = await get_query_from_db(insert_new_group_query, None, params=params)
        return int(group_id.iloc[0, 0])
    return None

"""
    Updates the details of an existing group.

    Args:
        old_group_name (str): The current name of the group.
        new_group_name (str): The new name for the group.
        new_group_purpose (str, optional): The new purpose of the group. Defaults to "".
        
    Raises:
        Exception: If the new group name already exists or the old group does not exist.
"""
async def update_group(old_group_name, new_group_name, new_group_purpose = ''):
    params = {'group_name': new_group_name}
    existing_group_df = await get_query_from_db(get_group_id, None, params=params)

    if old_group_name != new_group_name and not existing_group_df.empty:
        exception_str = f"\n\tInside function 'update_group':\n\t\tA group with the name \"{new_group_name}\" already exists."
        raise Exception(exception_str)
    else:
        new_params = {
            'old_group_name': old_group_name,
            'new_group_name': new_group_name,
            'new_group_purpose': new_group_purpose
        }
        try:
            await get_query_from_db(get_group_details, None, params=new_params)
        except Exception:
            raise Exception(f"Inside function 'update_group':\ngroup does not exist.")

"""
    Deletes a group and its relationships from the database.

    Args:
        group_name (str): The name of the group to delete.

    Returns:
        int: 1 if group with the given name was found and deleted.
"""
async def delete_group(group_name):
    search_params = {
        'group_name': group_name,
    }
    existing_group_df = await get_query_from_db(get_group_id, None, params=search_params)
    if not existing_group_df.empty:
        group_id = int(existing_group_df.iloc[0, 0])
        params = {
            'group_id': group_id,
            'group_name': group_name
        }
        await get_query_from_db(delete_group_query, None, params=params)
        return 1

"""
    Inserts a word into a group if both exist and their relationship does not already exist.

    Args:
        group_name (str): The name of the group.
        word_str (str): The word to insert into the group.

    Raises:
        Exception: If the group or word does not exist.
"""
async def insert_to_words_in_group(group_name, word_str):
    search_params = {
        'group_name': group_name,
        'word_str': word_str
    }
    existing_group_df = await get_query_from_db(get_group_id, None, params=search_params)
    existing_word_df = await get_query_from_db(get_word_id, None, params=search_params)

    if not existing_group_df.empty and not existing_word_df.empty:
        group_id = int(existing_group_df.iloc[0, 0])
        word_id = int(existing_word_df.iloc[0, 0])
        params = {
            'group_id': group_id,
            'word_id': word_id
        }
        await get_query_from_db(insert_to_words_in_group_query, None, params=params)
    else:
        raise Exception(f"Inside function 'insert_word_to_group':\ngroup/word does not exist.")

"""
    Deletes a word from a group.

    Args:
        group_name (str): The name of the group.
        word_str (str): The word to delete from the group.
"""
async def delete_word_from_group(group_name, word_str):
    search_params = {
        'group_name': group_name,
        'word_str': word_str
    }
    existing_group_df = await get_query_from_db(get_group_id, None, params=search_params)
    existing_word_df = await get_query_from_db(get_word_id, None, params=search_params)

    if not existing_group_df.empty and not existing_word_df.empty:
        group_id = int(existing_group_df.iloc[0, 0])
        word_id = int(existing_word_df.iloc[0, 0])
        params = {
            'group_id': group_id,
            'word_id': word_id
        }
        await get_query_from_db(delete_word_from_group_query, None, params=params)
    return 1

"""
    Retrieves an index of words and their positions.

    Returns:
        list: A list of tuples containing words and their positions.
"""
async def words_index_df():
    query_df = await get_query_from_db(words_index, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves paragraphs containing a specific word.

    Args:
        word (str): The word to search for in paragraphs.

    Returns:
        list: A list of tuples containing paragraphs with the specified word.
"""
async def word_shows_in_par_df(word):
    params = {'word': word}
    res = await get_query_from_db(word_shows_in_par, None, params=params)
    return list(res.itertuples(index=False, name=None))


"""
    Retrieves word statistics for a specific song.

    Returns:
        list: A list of tuples containing word statistics for the song.
"""
async def words_statistics_in_song_df():
    query_df = await get_query_from_db(words_statistics_in_song, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves word statistics for all songs in the database.

    Returns:
        list: A list of tuples containing word statistics for all songs.
"""
async def words_statistics_in_db_df():
    query_df = await get_query_from_db(words_statistics_in_db, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves paragraph statistics for a specific song.

    Returns:
        list: A list of tuples containing paragraph statistics for the song.
"""
async def pars_statistics_in_song_df():
    query_df = await get_query_from_db(pars_statistics_in_song, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves line statistics for a specific song.

    Returns:
        list: A list of tuples containing line statistics for the song.
"""
async def lines_statistics_in_song_df():
    query_df = await get_query_from_db(lines_statistics_in_song, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves overall statistics for all songs in the database.

        Returns:
        list: A list of tuples containing overall statistics for songs.
"""
async def songs_statistics_df():
    query_df = await get_query_from_db(songs_statistics, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves words that rhyme with a specific word.

    Args:
        word_str (str): The word to find rhymes for.

    Returns:
        list: A list of tuples containing words that rhyme with the specified word.
"""
async def get_rhymes_for_word_df(word_str):
    last_syllable = get_last_syllable(word_str)
    params = {'last_syllable': last_syllable}
    query_df = await get_query_from_db(rhymes_for_word, None, params=params)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))


# Clears all data from the database.
async def clear_db():
    await exec_procedure_from_db('DeleteAllData', None)

"""
    Fetches table data based on a given query.

    Args:
        query (str): The query to execute.
        params (dict, optional): Parameters for the query. Defaults to None.

    Returns:
        list: A list of tuples containing the query results.
"""
async def fetch_table_df(query, params = None):
    query_df = await get_query_from_db(query, None, params=params)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

# Fetches a list of expressions with their IDs and names from the 'songs' table.
async def fetch_expressions():
    return await fetch_table_df(expression_table_query)

# Fetches a list of songs with their IDs and names from the 'songs' table.
async def fetch_songs():
    return await fetch_table_df(songs_table_query)

# Fetches a list of words associated with songs, including their IDs, word IDs, clean words, and song IDs.
async def fetch_words_in_songs():
    return await fetch_table_df(words_in_songs_main_columns_table_query)

# Fetches a list of groups with their IDs, names, and purposes from the 'groups' table.
async def fetch_groups():
    return await fetch_table_df(groups_table_query)

# Fetches a list of words associated with groups, including their IDs, word IDs, group IDs and clean words.
async def fetch_words_in_groups(group_name = None):
    params = {'group_name': group_name}
    return await fetch_table_df(get_words_in_group, params=params)

# Fetches a list of words with their IDs and the word itself.
async def fetch_words():
    return await fetch_table_df(words_table_query)

# Fetches a list of words with their IDs and the word itself and last syllable.
async def fetch_whole_words():
    return await fetch_table_df(whole_words_table_query)

"""
    Inserts a new expression into the database.

    Args:
        expression (str): The expression to insert.
"""
async def insert_new_expression(expression):
    params = {'expression_str': expression}
    await get_query_from_db(insert_expression, None, params=params)

"""
    Deletes an expression from the database.

    Args:
        expression_str (str): The expression to delete.
"""
async def delete_expression(expression_str):
    delete_query = "DELETE FROM expression WHERE expression_str = :expression_str"
    params = {'expression_str': expression_str}
    await get_query_from_db(delete_query, None, params=params)

