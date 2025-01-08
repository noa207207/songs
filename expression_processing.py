import os
import re
import pandas as pd

"""
    This function takes a string and returns a normalized version of it. 
    The normalization process includes:
    1. Converting all characters to lowercase.
    2. Removing any non-alphanumeric characters by replacing them with a space.
       (Supports only English letters and digits.)

    :param text: The input string.
    :return: The normalized string.
"""
def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text) # Remove non-alphanumeric chars between words
    return text

# Splits text lines into paragraphs (separated by empty lines).
def split_into_paragraphs(lines):
    paragraphs = []
    current_paragraph = []

    for line in lines:
        if not line.strip(): # Check if the line is empty, indicating the end of a paragraph
            if current_paragraph:
                paragraphs.append(current_paragraph)
                current_paragraph = []
        else:
            current_paragraph.append(line)

    # Append the last paragraph if it exists
    if current_paragraph:
        paragraphs.append(current_paragraph)

    return paragraphs

# Extracts words from text and tracks their position (paragraph, line, word number).
def get_words_structure(lines):
    paragraphs = split_into_paragraphs(lines)

    words_data = []
    paragraph_index = 0

    for paragraph in paragraphs:
        paragraph_index += 1
        line_in_paragraph_index = 0

        for line in paragraph:
            line_in_paragraph_index += 1
            # Normalize the line
            cleaned_line = normalize_text(line)
            # Split into words
            words = cleaned_line.split()

            word_in_line_index = 0
            for w in words:
                word_in_line_index += 1
                words_data.append({
                    "word": w,
                    "paragraph_index": paragraph_index,
                    "line_in_paragraph_index": line_in_paragraph_index,
                    "word_in_line_index": word_in_line_index
                })

    return words_data

# Finds a phrase in a list of words with metadata and returns where it appears.
def find_phrase_in_words(words_data, phrase_words):
    results = []
    phrase_len = len(phrase_words)

    # Use a sliding window to compare sequences of words
    for i in range(len(words_data) - phrase_len + 1):
        # Extract the segment of words to compare
        segment = [wd["word"] for wd in words_data[i:i + phrase_len]]
        if segment == phrase_words:
            # If a match is found, extract metadata from the first word
            first_word_info = words_data[i]
            results.append((
                first_word_info["paragraph_index"],
                first_word_info["line_in_paragraph_index"],
                first_word_info["word_in_line_index"]
            ))

    return results

# Searches for a phrase in all text files in a folder and returns results as a DataFrame.
def get_expression_shows(search_phrase, folder_path):
    # Normalize and split the search phrase into words
    phrase_clean = normalize_text(search_phrase)
    phrase_words = phrase_clean.split()

    all_results = []  # Store all results from all files

    # Iterate through all files in the folder
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".txt"):
            filepath = os.path.join(folder_path, filename)

            # Read all lines from the file
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Generate the word structure for the file
            words_data = get_words_structure(lines)

            # Search for the phrase in the list of words
            results = find_phrase_in_words(words_data, phrase_words)

            # If results are found, store them for the DataFrame
            for result in results:
                paragraph_i, line_i, word_i = result
                all_results.append(
                    {
                    "song_name": os.path.splitext(filename)[0],
                    "par_num": paragraph_i,
                    "line_num_in_par": line_i,
                    "word_num_in_line": word_i
                    }
                )

    columns = ["song_name", "par_num", "line_num_in_par", "word_num_in_line"]
    df_results = pd.DataFrame(all_results, columns=columns).sort_values(by=columns).reset_index(drop=True)
    return df_results