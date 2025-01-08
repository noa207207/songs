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

"""
    Inserts a word into the words_in_songs table.

    Args:
        unclean_word (str): The original word with potential punctuation.
        word_str (str): The cleaned version of the word.
        song_id (int): The ID of the song the word belongs to.
        paragraphs_num (int): The paragraph number where the word appears.
        line_num_in_par (int): The line number in the paragraph.
        word_num_in_line (int): The word's position in the line.
        word_index_in_song (int): The word's global index in the song.

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
        'is_last_in_line': 1 if unclean_word.endswith("\n") else 0,
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
    update_words_query = """ 
        INSERT INTO words (word_str)
        SELECT DISTINCT clean_word
        FROM words_in_songs
        WHERE 
            words_in_songs.clean_word IS NOT NULL 
            AND LEN(words_in_songs.clean_word) > 0
            AND NOT EXISTS (
                SELECT 1
                FROM words
                WHERE words.word_str = words_in_songs.clean_word
            );
        """
    await get_query_from_db(update_words_query, None)

"""
    Updates the word_id field in the words_in_songs table.

    Args:
        None

    Returns:
        None
"""
async def update_word_id():
    await get_query_from_db(update_word_id_query, None)

"""
    Inserts words from a paragraph into the words_in_songs table.

    Args:
        song_id (int): The ID of the song.
        paragraphs_num (int): The paragraph number.
        par_words_list (list): List of words in the paragraph.
        start_par_index (int): The starting index for the paragraph's words.

    Returns:
        None
"""
async def insert_par_words(song_id, paragraphs_num, par_words_list , start_par_index):
    tasks = []
    curr_line = 1
    curr_word_num_in_line = 1
    clean_word_first_char_index = 1
    word_index_in_song = start_par_index
    for word in par_words_list:
        clean_word = (re.sub(r'^[\W_]+|[\W_]+$', '', word)).lower()
        clean_word_last_char_index = clean_word_first_char_index + len(clean_word) - 1
        tasks.append(insert_to_words_in_songs(word, clean_word, song_id, paragraphs_num, curr_line, curr_word_num_in_line, word_index_in_song))

        clean_word_first_char_index = clean_word_last_char_index + 1
        word_index_in_song += 1
        curr_word_num_in_line += 1
        if word.endswith("\n"):
            curr_line += 1
            curr_word_num_in_line = 1
    await asyncio.gather(*tasks)

"""
    Inserts a new paragraph into the paragraphs table.

    Args:
        song_id (int): The ID of the song.
        paragraphs_num (int): The paragraph number.
        start_index (int): The starting index of the paragraph.
        end_index (int): The ending index of the paragraph.

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
        song_name (str): The name of the song.

    Returns:
        int: The ID of the inserted song.
"""
async def insert_to_songs(song_name):
    insert_song_query = "INSERT INTO songs (song_name) OUTPUT INSERTED.id VALUES (:song_name)"
    params = {'song_name': song_name}
    song_id_df = await get_query_from_db(insert_song_query, None , params=params)
    if not song_id_df.empty:
        return song_id_df.iloc[0, 0]
    else:
        raise Exception(f"Inside function 'insert_to_songs':\nFailed to insert song.")

"""
    Inserts a new song and its paragraphs and words into the database.

    Args:
        song_name (str): The name of the song.
        curr_song_path (str): The path to the song's file.

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

async def remove_song(song_name):
    song_id = int(await get_song_id(song_name))
    params = {'song_id': song_id}
    await exec_procedure_from_db('RemoveSong', None, params=params)

async def load_songs_from_files_list(files_path_list):
    async def load_songs():
        tasks = []
        for curr_song_path in files_path_list:
                song_name = os.path.splitext(os.path.basename(curr_song_path))[0]

                is_exist_song_query = "SELECT COUNT(1) FROM songs WHERE song_name = :song_name"
                is_exist_song_result = await get_query_from_db(is_exist_song_query, None, params={'song_name': song_name})
                if not is_exist_song_result.empty and is_exist_song_result.iloc[0, 0] > 0:
                    continue
                else: # new song
                    tasks.append(insert_new_song(song_name, curr_song_path))

        await asyncio.gather(*tasks)
        await update_words()
        await update_word_id()
    await load_songs()
    return True

"""
    Loads songs from text files and inserts them into the database.

    Args:
        None

    Returns:
        bool: True if the operation was successful.
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
        # await load_songs_from_files()
        await remove_song('Aesthetic')
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await engine_manager.close_engines()
        end_time = time.time()
        print(f"Total time for async execution: {end_time - start_time} seconds")

if __name__ == "__main__":
    asyncio.run(main())