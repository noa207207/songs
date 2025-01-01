import pandas as pd

from text_processing import get_last_syllable
from sql_via_code import get_query_from_db, exec_procedure_from_db
from datetime import datetime
from queries_bank import *
import aiofiles
import asyncio
import os

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

    Returns:
        None

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
async def get_search_details_df(song_name = None, poet = None, composer = None, creation_year = None, performer_name = None):
    params = {
        'song_name': song_name,
        'poet': poet,
        'composer': composer,
        'creation_year': creation_year,
        'performer_name': performer_name
        }
    song_id_query_df = await get_query_from_db(search_details, None, params=params)
    if song_id_query_df.empty:
        return []
    return list(song_id_query_df.itertuples(index=False, name=None))

"""
    Reads the content of a song file from the directory.

    Args:
        song_name (str): The name of the song file to read.

    Returns:
        tuple: The song name and its content.

    Raises:
        FileNotFoundError: If the song file does not exist.
"""
async def read_song(song_name):
    directory_path = "./static/songs"
    full_song_path = os.path.join(directory_path, song_name + ".txt")
    if not os.path.exists(full_song_path):
        raise FileNotFoundError(f"The song {song_name} was not found.")
    async with aiofiles.open(full_song_path, 'r', encoding='utf-8') as file:
        return song_name, await file.read()

"""
    Retrieves the content of multiple song files as a dictionary.

    Args:
        song_names_list (list): A list of song names to retrieve.

    Returns:
        dict: A dictionary where keys are song names and values are their contents.
"""
async def songs_words_dict(song_names_list):
    songs_contents_dict = dict(await asyncio.gather(*(read_song(song_name) for song_name in song_names_list)))
    return songs_contents_dict

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
        int: 1 if the operation was successful.
"""
async def delete_group(group_name):
    search_params = {
        'group_name': group_name,
    }
    existing_group_df = await get_query_from_db(get_group_id, None, params=search_params)
    
    if not existing_group_df.empty:
        group_id = int(existing_group_df.iloc[0, 0])
        print(group_id)
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

    Returns:
        None

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

    Returns:
        int: 1 if the operation was successful.
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
    Retrieves an index of words.

    Args:
        None

    Returns:
        pd.DataFrame: DataFrame containing words and their positions.
"""
async def words_index_df():
    query_df = await get_query_from_db(words_index, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves all words in a group as a list.

    Args:
        group_id (int): The ID of the group.

    Returns:
        list: List of words in the group.
"""
async def get_group_words_as_list(group_id):
    params = {'group_id': group_id}
    words_list_df = await get_query_from_db(get_group_words, None, params=params)
    return words_list_df['word_str'].to_list()

"""
    Retrieves an index of words in a group.

    Args:
        group_name (str): The name of the group.

    Returns:
        pd.DataFrame or None: DataFrame containing the index of words in the group, or None if not found.
"""
async def group_words_index_df(group_name):
    search_params = {'group_name': group_name}
    existing_group_df = await get_query_from_db(get_group_id, None, params=search_params)
    if not existing_group_df.empty:
        group_id = int(existing_group_df.iloc[0, 0])
        group_words_list = await get_group_words_as_list(group_id)
        index_df = await words_index_df()
        if not index_df.empty and len(group_words_list) > 0:
            group_index_df = index_df[index_df['word_str'].isin(group_words_list)]
            return group_index_df
    return None

async def export_df_to_csv(df , report_name):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    df.to_csv(f"{report_name}_{timestamp}.csv", index=False)

"""
    Retrieves songs that contain a specific expression.

    Args:
        expression_str (str): The expression to search for in songs.

    Returns:
        pd.DataFrame: A DataFrame containing songs that match the expression.
"""
async def songs_with_expression_df(expression_str):
    params = {'expression': expression_str}
    return await get_query_from_db(songs_with_expression, None, params=params)

"""
    Retrieves paragraphs containing a specific word.

    Args:
        word (str): The word to search for in paragraphs.

    Returns:
        pd.DataFrame: A DataFrame containing paragraphs with the specified word.
"""
async def word_shows_in_par_df(word):
    params = {'word': word}
    res = await get_query_from_db(word_shows_in_par, None, params=params)
    return list(res.itertuples(index=False, name=None))

"""
    Retrieves words based on their position in a song.

    Args:
        song_name (str, optional): The name of the song. Defaults to None.
        par_num (int, optional): The paragraph number. Defaults to None.
        line_num_in_par (int, optional): The line number in the paragraph. Defaults to None.
        word_num_in_line (int, optional): The word's position in the line. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame containing words matching the specified position.
"""
async def words_by_place_df(song_name = None, par_num = None, line_num_in_par = None, word_num_in_line = None):
    params = {
        'song_name': song_name,
        'par_num': par_num,
        'line_num_in_par': line_num_in_par,
        'word_num_in_line': word_num_in_line
        }
    return await get_query_from_db(words_by_place, None, params=params)

"""
    Retrieves word statistics for a specific song.

    Args:
        song_name (str, optional): The name of the song. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame containing word statistics for the song.
"""
async def words_statistics_in_song_df():
    query_df = await get_query_from_db(words_statistics_in_song, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves word statistics in the whole DB.

    Returns:
        pd.DataFrame: A DataFrame containing word statistics in the whole DB.
"""
async def words_statistics_in_db_df():
    query_df = await get_query_from_db(words_statistics_in_db, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves paragraph statistics for a specific song.

    Args:
        song_name (str, optional): The name of the song. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame containing paragraph statistics for the song.
"""
async def pars_statistics_in_song_df():
    query_df = await get_query_from_db(pars_statistics_in_song, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves line statistics for a specific song.

    Args:
        song_name (str, optional): The name of the song. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame containing line statistics for the song.
"""
async def lines_statistics_in_song_df():
    query_df = await get_query_from_db(lines_statistics_in_song, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves overall statistics for songs.

    Args:
        song_name (str, optional): The name of the song. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame containing overall statistics for songs.
"""
async def songs_statistics_df():
    query_df = await get_query_from_db(songs_statistics, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

"""
    Retrieves words that rhyme with a specific word in a song.

    Args:
        word_str (str): The word to find rhymes for.
        song_name (str, optional): The name of the song to limit the search. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame containing words that rhyme with the specified word.
"""
async def get_rhymes_for_word_df(word_str):
    last_syllable = get_last_syllable(word_str)
    params = {'last_syllable': last_syllable}
    print("last_syllable", last_syllable)
    query_df = await get_query_from_db(rhymes_for_word, None, params=params)
    print(query_df)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

async def clear_db():
    await exec_procedure_from_db('DeleteAllData', None)

# A utility function to fetch data from the database and return it as a list of tuples.
# If the result is empty, it returns an empty list.
async def fetch_table_df(query):
    query_df = await get_query_from_db(query, None)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

# Fetches a list of songs with their IDs and names from the 'songs' table.
async def fetch_songs():
    return await fetch_table_df("SELECT id, song_name FROM songs")

# Fetches distinct words associated with songs, including their IDs, word IDs, clean words, and song IDs.
async def fetch_words_in_songs():
    return await fetch_table_df("SELECT distinct id, word_id, clean_word, song_id FROM words_in_songs")

# Fetches distinct groups with their IDs, names, and purposes from the 'groups' table.
async def fetch_groups():
    return await fetch_table_df("SELECT distinct id, group_name, group_purpose FROM groups")

# Fetches words in groups by joining 'words_in_group' and 'words' tables,
# if group_name is given, it will return only the words in this group.
async def fetch_words_in_groups(group_name = None):
    params = {'group_name': group_name}
    query_df = await get_query_from_db(get_words_in_group, None, params=params)
    if query_df.empty:
        return []
    return list(query_df.itertuples(index=False, name=None))

# Fetches distinct words with their IDs and string representations from the 'words' table.
async def fetch_words():
    return await fetch_table_df("SELECT distinct id, word_str FROM words")
