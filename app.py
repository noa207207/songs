import os
import time
import asyncio
import threading
from quart import Quart, request, jsonify, render_template
from load_songs_files import load_songs_from_files_list, remove_song
from functionality import *
from expression_processing import get_expression_shows
import shutil


UPLOAD_FOLDER = "static/songs"
app = Quart(__name__)

bg_loop = asyncio.new_event_loop()

"""
    Function running in a separate thread to manage its own asyncio event loop.
"""
def bg_loop_runner():
    asyncio.set_event_loop(bg_loop)
    bg_loop.run_forever()

bg_thread = threading.Thread(target=bg_loop_runner, daemon=True)
bg_thread.start()

"""
    Allows invoking a coroutine on the background event loop (bg_loop).
    - Executes `coro(*args, **kwargs)` on bg_loop.
    - Uses `asyncio.run_coroutine_threadsafe` to send the task to the other loop.
    - Returns the result as an awaitable future.
"""
async def call_in_background(coro, *args, **kwargs):
    future = asyncio.run_coroutine_threadsafe(coro(*args, **kwargs), bg_loop)
    return await asyncio.wrap_future(future)

"""
    Deletes a specific expression from the database.
    :param expression_str: The expression to delete.
"""
@app.route('/delete-expression/<string:expression_str>', methods=['DELETE'])
async def delete_expression_route(expression_str):
    try:
        print(expression_str)
        # קריאה לפונקציה למחיקת הביטוי
        result = await call_in_background(delete_expression, expression_str)
        if result==None:
            return jsonify({"message": f"Expression '{expression_str}' deleted successfully."}), 200
        else:
            return jsonify({"error": "Expression not found."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

"""
    Deletes a song file from the server and its entry from the database.
    :param song_name: Name of the song to delete.
"""
@app.route("/delete-song/<song_name>", methods=["DELETE"])
async def delete_song_route(song_name):
    try:
        song_folder = os.path.join("static", "songs")
        song_file_path = os.path.join(song_folder, f"{song_name}.txt")  # או לפי סוג הקובץ שלך

        # מחיקת הקובץ מהשרת
        if os.path.exists(song_file_path):
            os.remove(song_file_path)
        # קריאה לפונקציה שמוחקת את השיר מהמסד נתונים
        await call_in_background(remove_song, song_name)
        return jsonify({"message": f"Song '{song_name}' deleted successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

"""
    Adds a new expression to the database.
    Expects a JSON payload with the key "expression".
"""
@app.route('/insert-expression', methods=['POST'])
async def insert_expression_route():
    try:
        data = await request.get_json()
        expression = data.get("expression")
        if not expression:
            return jsonify({"error": "Expression is required"}), 400

        await call_in_background(insert_new_expression, expression)
        return jsonify({"message": f"Expression '{expression}' added successfully"}), 200
    except Exception as e:
        print(f"Error inserting expression: {e}")
        return jsonify({"error": "Failed to insert expression"}), 500

"""
    Deletes a specific detail line from a song's metadata in the database.
    :param details_line_id: The ID of the detail line to delete.
"""
@app.route("/delete-song-details/<int:details_line_id>", methods=["DELETE"])
async def delete_song_details(details_line_id):
    try:
        await call_in_background(remove_song_details_line, details_line_id)
        return jsonify({"message": f"Details line {details_line_id} deleted successfully."}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

"""
    Deletes a group by name from the database.
    :param group_name: Name of the group to delete.
"""
@app.route('/delete-group/<group_name>', methods=['DELETE'])
async def delete_group_route(group_name):
    try:
        # הנח שהשגת את שם הקבוצה לפי ה-ID מתוך ה-Database
        # לדוגמה: `group_name = await db.get_group_name_by_id(group_id)`

        print("group_name", group_name)
        result = await call_in_background(delete_group, group_name)
        print("result", result)

        if result == 1:
            return jsonify({"status": "success", "message": result}), 200
        else:
            return jsonify({"status": "error", "message": result}), 400

    except Exception as e:
        print(f"Error in delete route: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

"""
    Clears all data from the database and deletes all files in the `static/songs` directory.
"""
@app.route("/clear-db", methods=["DELETE"])
async def clear_db_route():
    try:
        # קריאה לפונקציה לניקוי ה-DB
        await call_in_background(clear_db)

        # מחיקת כל התוכן שבתיקיית static/songs
        folder_path = os.path.join("static", "songs")
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # מחיקת קובץ או קישור
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # מחיקת תיקייה ותוכנה
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")

        return jsonify({"message": "Database and static/songs cleared successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

"""
    Retrieves data on how a given phrase appears in the specified folder.
    Query parameters:
      - `phrase`: The phrase to analyze.
      - `folder`: The folder containing files for analysis.
"""
@app.route('/get-expression-shows', methods=['GET'])
def get_expression_shows_route():
    try:
        phrase = request.args.get('phrase', '')
        folder_path = request.args.get('folder', '')

        if not phrase or not folder_path:
            return jsonify({"error": "Invalid parameters"}), 400

        df_results = get_expression_shows(phrase, folder_path)

        results = df_results.to_dict(orient="records")
        return jsonify(results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

"""
    Fetches rhyming words for a given input word from the database.
    Query parameter:
      - `word`: The word to find rhymes for.
"""
@app.route("/get-rhymes")
async def get_rhymes():
    
    try:
        # שליפת הפרמטר word מתוך ה-Query String
        word = request.args.get("word")
        if not word:
            return jsonify({"status": "error", "message": "Missing 'word' parameter"}), 400

        rhymes_df = await call_in_background(get_rhymes_for_word_df, word)
        return jsonify({"status": "success", "words": rhymes_df})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

"""
    Renders the expressions page, displaying available expressions and related data.
"""
@app.route("/expressions")
async def expressions_page():
    songs = await call_in_background(fetch_songs)
    words = await call_in_background(fetch_words)
    exp = await call_in_background(fetch_expressions)
    return await render_template("expressions.html", exp=exp, songs=songs, words=words, active_page='expressions')

"""
    Renders the rhymes page, displaying words and their rhyming counterparts.
"""
@app.route("/rhymes")
async def rhymes_page():
    songs = await call_in_background(fetch_songs)
    words = await call_in_background(fetch_words)
    return await render_template("rhymes.html", songs=songs, words=words, active_page='rhymes')

"""
    Renders the statistics page, displaying various metrics about songs and words.
"""
@app.route("/stat")
async def stat_page():
    words_stat_in_songs = await call_in_background(words_statistics_in_song_df)
    words_stat = await call_in_background(words_statistics_in_db_df)
    songs = await call_in_background(fetch_songs)
    line_stat = await call_in_background(lines_statistics_in_song_df)
    pars_stat = await call_in_background(pars_statistics_in_song_df)
    songs_stat = await call_in_background(songs_statistics_df)


    return await render_template(
        "stat.html",
        songs=songs,
        words_stat_in_songs=words_stat_in_songs,
        words_stat=words_stat,
        line_stat=line_stat,
        pars_stat=pars_stat,
        songs_stat=songs_stat,
        active_page='stat'
    )

"""
    Renders the search page, allowing users to search for words and phrases.
"""
@app.route("/search")
async def search_page():
    songs = await call_in_background(fetch_songs)
    words = await call_in_background(fetch_words_in_songs)
    pars = await call_in_background(word_shows_in_par_df, None)


    return await render_template("search.html", songs=songs, words=words, pars=pars, active_page='search')

"""
    Renders the indexing page, showing word indices, groups, and relationships.
"""
@app.route("/indexing")
async def indexing_page():
    index = await call_in_background(words_index_df)
    groups = await call_in_background(fetch_groups)
    songs = await call_in_background(fetch_songs)
    words_in_group = await call_in_background(fetch_words_in_groups)

    return await render_template(
        "indexing.html",
        index_data=index,
        groups=groups,
        songs=songs,
        words_in_group=words_in_group,
        active_page='indexing'
    )

"""
    Renders the group management page, showing existing groups and associated words.
"""
@app.route("/group")
async def group_page():
    groups = await call_in_background(fetch_groups)
    words = await call_in_background(fetch_words)
    words_in_group = await call_in_background(fetch_words_in_groups)

    return await render_template("group.html", groups=groups, words=words, words_in_group=words_in_group, active_page='group')

"""
    Adds a new group to the database.
    Expects a JSON payload with keys `group_name` and optionally `group_purpose`.
"""
@app.route('/add_group', methods=['POST'])
async def add_group():
    data = await request.get_json()
    group_name = data.get('group_name')
    group_purpose = data.get('group_purpose', '')
    
    # Call the Python function
    new_group = await call_in_background(insert_new_group, group_name, group_purpose)
    
    if new_group is None:
            return jsonify({
                "success": False,
                "message": "Group name already exists. Please choose another name"
            }), 400
    
    # Return the new group's details
    return jsonify({
        "success": True,
        "group": {
            "id": new_group,
            "name": group_name,
            "purpose": group_purpose
        }
    })

"""
    Retrieves all words associated with a group.
"""
@app.route("/get-words-in-group", methods=["GET"])
async def get_words__group():
    try:
        # שליפת רשימת מילים מהקבוצה
        words = await call_in_background(fetch_words_in_groups, None)
        return jsonify({"status": "success", "words": words})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
"""
    Adds a word to a specific group in the database.
    Expects a JSON payload with `group_name` and `word_str`.
"""
@app.route("/add-word-to-group", methods=["POST"])
async def add_word_to_group():
    try:
        data = await request.json
        group_name = data["group_name"]
        word_str = data["word_str"]

        # הוספת המילה לקבוצה
        await call_in_background(insert_to_words_in_group, group_name, word_str)

        return jsonify({"status": "success", "message": f"Word '{word_str}' added to group '{group_name}'."})
    except Exception as e:
        print(f"Error adding word to group: {e}")
        return jsonify({"status": "error", "message": str(e)})

"""
    Removes a word from a specific group in the database.
    Expects a JSON payload with `group_name` and `word_str`.
"""
@app.route("/remove-word-from-group", methods=["POST"])
async def remove_word_from_group():
    data = await request.json
    group_name = data["group_name"]
    word_str = data["word_str"]
    print(group_name)
    print(word_str)
    await call_in_background(delete_word_from_group, group_name, word_str)
    return jsonify({"status": "success"})

"""
    Renders the main upload page, showing available songs and their details.
"""
@app.route("/")
async def upload_page():
    songs = await call_in_background(fetch_songs)
    details = await call_in_background(get_search_details_df)
    return await render_template("upload.html", songs=songs, details=details, active_page='songs')

"""
    Retrieves the list of available songs from the database.
"""
@app.route("/songs-list", methods=["GET"])
async def get_songs_list():
    try:
        songs = await call_in_background(fetch_songs)
        return jsonify(songs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
"""
    Handles file uploads for new songs.
    Saves files to the `static/songs` directory and processes them into the database.
"""
@app.route("/upload", methods=["POST"])
async def upload_files():
    try:
        files = await request.files  # ImmutableMultiDict
        if not files:
            return jsonify({"error": "No files provided"}), 400

        file_list = []
        for file in files.getlist("files"):
            if file.filename == "":
                return jsonify({"error": "One of the files has no filename"}), 400
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            await file.save(file_path)
            file_list.append(file_path)

        start_time = time.time()
        await call_in_background(load_songs_from_files_list, file_list)
        end_time = time.time()
        print(f"Total time for async execution: {end_time - start_time} seconds")
        return jsonify({"message": f"{len(file_list)} files uploaded successfully"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

"""
    Saves the details of a song into the database.
    Expects a JSON payload with the following keys:
      - `song_name`: Name of the song.
      - `poet`: Name of the poet (optional).
      - `composer`: Name of the composer (optional).
      - `creation_year`: Year of creation (optional).
      - `video_link`: A link to the song's video (optional).
      - `performer_name`: Name of the performer (optional).
"""
@app.route("/save-song-details", methods=["POST"])
async def save_song_details_route():
    try:
        data = await request.get_json()

        song_name = data.get("song_name", "")
        poet = data.get("poet", "")
        composer = data.get("composer", "")
        creation_year = data.get("creation_year", "")
        video_link = data.get("video_link", "")
        performer_name = data.get("performer_name", "")

        # קריאה לפונקציה שמכניסה את הנתונים ל-DB
        await call_in_background(
            insert_song_details,
            song_name,
            poet,
            composer,
            creation_year,
            video_link,
            performer_name
        )

        return jsonify({"message": "Song details saved successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True)
