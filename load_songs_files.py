from sql_via_code.engine_manager import EngineManager
from text_processing import *
from functionality import *
from queries_bank import *
import aiofiles
import asyncio
import time
import os
import re

engine_manager = EngineManager()
IS_LAST_IN_LINE_FALSE = 0
IS_LAST_IN_LINE_TRUE = 1

"""
    Inserts a word into the words_in_songs table.

    Args:
        unclean_word (str): Original word with punctuation.
        clean_word (str): Cleaned version of the word.
        song_id (int): ID of the song.
        paragraphs_num (int): Paragraph number.
        line_num_in_par (int): Line number in the paragraph.
        word_num_in_line (int): Word's position in the line.
        word_index_in_song (int): Word's global index in the song.

    Returns:
        None
"""
async def insert_to_words_in_songs(unclean_word, clean_word , song_id, paragraphs_num,  line_num_in_par, word_num_in_line, word_index_in_song):
    insert_words_in_songs_query = """ 
        INSERT INTO words_in_songs 
            (unclean_word,  clean_word,  song_id,  par_num,  line_num_in_par,  word_num_in_line,  is_last_in_line,  word_num,  chars_count,  last_syllable) VALUES  
            (:unclean_word, :clean_word, :song_id, :par_num, :line_num_in_par, :word_num_in_line, :is_last_in_line, :word_num, :chars_count, :last_syllable)
        """
    params = {
        'clean_word': clean_word,
        'unclean_word': unclean_word,
        'song_id': song_id,
        'par_num': paragraphs_num,
        'line_num_in_par': line_num_in_par,
        'word_num_in_line': word_num_in_line,
        'is_last_in_line': IS_LAST_IN_LINE_TRUE if unclean_word.endswith("\n") else IS_LAST_IN_LINE_FALSE,
        'word_num': word_index_in_song,
        'chars_count': len(clean_word),
        'last_syllable': get_last_syllable(clean_word)
        }
    await get_query_from_db(insert_words_in_songs_query, None, params=params)

"""
    Updates the words table with unique words from words_in_songs.

    Args:
        None

    Returns:
        None
"""
async def update_words():
    await get_query_from_db(update_words_query, None)

"""
    Inserts words from a paragraph into the words_in_songs table in bulk.

    This function builds a single SQL query to insert all words in a paragraph 
    into the `words_in_songs` table to improve performance and reduce database calls.

    Args:
        song_id (int): The ID of the song.
        paragraphs_num (int): The paragraph number in the song.
        par_words_list (list): List of words in the paragraph.
        start_par_index (int): The starting index for the paragraph's words in the song.

    Returns:
        None
"""
async def insert_par_words(song_id, paragraphs_num, par_words_list, start_par_index):
    curr_line = 1
    curr_word_num_in_line = 1
    word_index_in_song = start_par_index
    insert_to_words_in_songs_query = """
        INSERT INTO words_in_songs 
        (unclean_word, clean_word, song_id, par_num, line_num_in_par, word_num_in_line, is_last_in_line, word_num, chars_count, last_syllable) 
        VALUES 
    """
    values = []
    words_variables_values = {}
    for idx, word in enumerate(par_words_list):
        clean_word = re.sub(r'^[\W_]+|[\W_]+$', '', word).lower()
        cur_word_variables = f"(:unclean_word_{idx}, :clean_word_{idx}, :song_id_{idx}, :par_num_{idx}, :line_num_in_par_{idx}, :word_num_in_line_{idx}, :is_last_in_line_{idx}, :word_num_{idx}, :chars_count_{idx}, :last_syllable_{idx})"
        values.append(cur_word_variables)
        words_variables_values.update({
            f"unclean_word_{idx}": word,
            f"clean_word_{idx}": clean_word,
            f"song_id_{idx}": song_id,
            f"par_num_{idx}": paragraphs_num,
            f"line_num_in_par_{idx}": curr_line,
            f"word_num_in_line_{idx}": curr_word_num_in_line,
            f"is_last_in_line_{idx}": 1 if word.endswith("\n") else 0,
            f"word_num_{idx}": word_index_in_song,
            f"chars_count_{idx}": len(clean_word),
            f"last_syllable_{idx}": get_last_syllable(clean_word),
        })
        word_index_in_song += 1
        curr_word_num_in_line += 1
        if word.endswith("\n"):
            curr_line += 1
            curr_word_num_in_line = 1
    insert_to_words_in_songs_query += ", ".join(values)
    await get_query_from_db(insert_to_words_in_songs_query, None, params=words_variables_values)


"""
    Inserts a new paragraph into the paragraphs table.

    Args:
        song_id (int): ID of the song.
        paragraphs_num (int): Paragraph number.
        start_index (int): Starting word index.
        end_index (int): Ending word index.

    Returns:
        None
"""
async def insert_new_par(song_id, paragraphs_num, start_index, end_index):
    insert_par_query = """
        INSERT INTO paragraphs (song_id, par_num, first_word_index, last_word_index)
        OUTPUT INSERTED.id
        VALUES (:song_id, :paragraph_num, :first_word_index, :last_word_index)
        """
    params = {
        'song_id': song_id,
        'paragraph_num': paragraphs_num,
        'first_word_index': start_index,
        'last_word_index': end_index
    }
    await get_query_from_db(insert_par_query, None, params=params)

"""
    Inserts a new song into the songs table.

    Args:
        song_name (str): Name of the song.

    Returns:
        int: ID of the inserted song.
"""
async def insert_to_songs(song_name):
    insert_song_query = "INSERT INTO songs (song_name) OUTPUT INSERTED.id VALUES (:song_name)"
    params = {'song_name': song_name}
    song_id_df = await get_query_from_db(insert_song_query, None , params=params)
    if not song_id_df.empty:
        return song_id_df.iloc[0, 0]
    else:
        raise Exception(f"Inside function 'insert_to_songs':\nFailed to insert song '{song_name}' into songs table.\nQuery did not return a valid ID.")

"""
    Inserts a new song and its paragraphs and words into the database.

    Args:
        song_name (str): Name of the song.
        curr_song_path (str): Path to the song file.

    Returns:
        None
"""
async def insert_new_song(song_name, curr_song_path):
    song_id = int(await insert_to_songs(song_name))
    async with aiofiles.open(curr_song_path, 'r', encoding='utf-8') as file:
        song_text = await file.read()

        paragraphs = song_text.split('\n\n')
        paragraphs = [paragraph for paragraph in paragraphs if paragraph.strip() != ""]

        par_start_word_index = 1
        tasks = []
        for paragraphs_num, paragraph in enumerate(paragraphs, start=1):
            par_words_list = split_par(paragraph)
            end_par_index = par_start_word_index + len(split_par(paragraph)) - 1
            tasks.append(insert_new_par(song_id, paragraphs_num, par_start_word_index, end_par_index))
            tasks.append(insert_par_words(song_id, paragraphs_num, par_words_list, par_start_word_index))
            par_start_word_index = end_par_index + 1
        await asyncio.gather(*tasks)

"""
    Removes a song from the database by name.

    Args:
        song_name (str): Name of the song.

    Returns:
        None
"""
async def remove_song(song_name):
    song_id = int(await get_song_id(song_name))
    params = {'song_id': song_id}
    await exec_procedure_from_db('RemoveSong', None, params=params)

"""
    Loads songs from a list of file paths into the database.

    This function iterates over a list of file paths, extracts song names from the file names, 
    checks whether the song already exists in the database, and if not, inserts the song, 
    its paragraphs, and words into the respective tables.

    Args:
        files_path_list (list): A list of file paths for song files.

    Returns:
        bool: True if the operation completes successfully.

    Raises:
        Exception: If any error occurs during the process.
"""
async def load_songs_from_files_list(files_path_list):
    async def load_songs():
        tasks = []
        for curr_song_path in files_path_list:
                song_name = os.path.splitext(os.path.basename(curr_song_path))[0]
                is_exist_song_result = await get_query_from_db(is_exist_song_query, None, params={'song_name': song_name})
                if not is_exist_song_result.empty and is_exist_song_result.iloc[0, 0] > 0:
                    continue
                else: # new song
                    tasks.append(insert_new_song(song_name, curr_song_path))

        await asyncio.gather(*tasks)
        await update_words()
        await get_query_from_db(update_word_id_query, None) # Updates the word_id field in the words_in_songs table.
    await load_songs()
    return True

"""
    Loads songs from text files in a predefined directory.

    Args:
        None

    Returns:
        bool: True if operation was successful.
"""
async def load_songs_from_files():
    path_list = []
    directory_path = "./static/songs"
    for file_name in os.listdir(directory_path):
        if file_name.endswith(".txt"):
            curr_song_path = f"{directory_path}/{file_name}"
            path_list.append(curr_song_path)
    return await load_songs_from_files_list(path_list)

"""
    Main function to load songs from files and close the database connection.

    Args:
        None

    Returns:
        None
"""
async def main():
    start_time = time.time()
    try:
        await load_songs_from_files()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await engine_manager.close_engines()
        end_time = time.time()
        print(f"Total time for async execution: {end_time - start_time} seconds")

if __name__ == "__main__":
    asyncio.run(main())