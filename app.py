from quart import Quart, request, jsonify, render_template
import os
from load_songs_files import load_songs_from_files_list 
from functionality import *

UPLOAD_FOLDER = "static/songs"
app = Quart(__name__)

@app.route('/delete-group/<group_name>', methods=['DELETE'])
async def delete_group_route(group_name):
    try:
        # הנח שהשגת את שם הקבוצה לפי ה-ID מתוך ה-Database
        # לדוגמה: `group_name = await db.get_group_name_by_id(group_id)`

        print("group_name", group_name)
        result = await delete_group(group_name)
        print("result", result)

        if result == 1:
            return jsonify({"status": "success", "message": result}), 200
        else:
            return jsonify({"status": "error", "message": result}), 400

    except Exception as e:
        print(f"Error in delete route: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500


@app.route("/get-rhymes")
async def get_rhymes():
    print("jhjh")
    
    try:
        # שליפת הפרמטר word מתוך ה-Query String
        word = request.args.get("word")
        print(word)
        if not word:
            return jsonify({"status": "error", "message": "Missing 'word' parameter"}), 400

        rhymes_df = await get_rhymes_for_word_df(word)
        print(rhymes_df)
        return jsonify({"status": "success", "words": rhymes_df})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/expressions")
async def expressions_page():
    songs = await fetch_songs()
    words = await fetch_words()
    return await render_template("expressions.html", songs=songs, words=words, active_page='expressions')


@app.route("/rhymes")
async def rhymes_page():
    songs = await fetch_songs()
    words = await fetch_words()
    return await render_template("rhymes.html", songs=songs, words=words, active_page='rhymes')



@app.route("/stat")
async def stat_page():
    words_stat_in_songs = await words_statistics_in_song_df()
    words_stat = await words_statistics_in_db_df()
    songs = await fetch_songs()
    line_stat = await lines_statistics_in_song_df()
    pars_stat = await pars_statistics_in_song_df()
    songs_stat = await songs_statistics_df()

    return await render_template("stat.html", songs=songs, words_stat_in_songs=words_stat_in_songs, words_stat=words_stat, line_stat=line_stat, pars_stat=pars_stat, songs_stat=songs_stat, active_page='stat')


@app.route("/search")
async def search_page():
    songs = await fetch_songs()
    words = await fetch_words_in_songs()
    pars = await word_shows_in_par_df(None)

    return await render_template("search.html", songs=songs, words=words, pars = pars, active_page='search')

@app.route("/indexing")
async def indexing_page():
    index = await words_index_df()
    groups = await fetch_groups()
    songs = await fetch_songs()
    words_in_group = await fetch_words_in_groups()
    return await render_template("indexing.html", index_data=index, groups=groups, songs=songs, words_in_group=words_in_group,active_page='indexing')

@app.route("/group")
async def group_page():
    groups = await fetch_groups()
    words = await fetch_words()
    words_in_group = await fetch_words_in_groups()
    return await render_template("group.html", groups=groups, words = words, words_in_group = words_in_group, active_page='group')

@app.route('/add_group', methods=['POST'])
async def add_group():
    data = await request.get_json()
    group_name = data.get('group_name')
    group_purpose = data.get('group_purpose', '')
    
    # Call the Python function
    new_group = await insert_new_group(group_name, group_purpose)
    
    if new_group is None:
            return jsonify({
                "success": False,
                "message": "Group already exists."
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

@app.route("/get-words-in-group", methods=["GET"])
async def get_words__group():
    try:
        # שליפת רשימת מילים מהקבוצה
        words = await fetch_words_in_groups(None)
        return jsonify({"status": "success", "words": words})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    

@app.route("/add-word-to-group", methods=["POST"])
async def add_word_to_group():
    try:
        data = await request.json
        group_name = data["group_name"]
        word_str = data["word_str"]

        # הוספת המילה לקבוצה
        await insert_to_words_in_group(group_name, word_str)

        # הדפסה לצורכי דיבאגינג
        print(f"Word '{word_str}' added to group '{group_name}'.")

        return jsonify({"status": "success", "message": f"Word '{word_str}' added to group '{group_name}'."})
    except Exception as e:
        print(f"Error adding word to group: {e}")
        return jsonify({"status": "error", "message": str(e)})


@app.route("/remove-word-from-group", methods=["POST"])
async def remove_word_from_group():
    data = await request.json
    group_name = data["group_name"]
    word_str = data["word_str"]
    print(group_name)
    print(word_str)
    await delete_word_from_group(group_name, word_str)
    return jsonify({"status": "success"})

@app.route("/")
async def upload_page():
    songs = await fetch_songs()
    details = await get_search_details_df()
    return await render_template("upload.html", songs=songs, details=details, active_page='songs')


@app.route("/songs-list", methods=["GET"])
async def get_songs_list():
    try:
        songs = await fetch_songs()  # פונקציה שמחזירה את רשימת השירים מה-DB
        return jsonify(songs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/upload", methods=["POST"])
async def upload_files():
    try:
        files = await request.files  # ImmutableMultiDict
        if not files:
            return jsonify({"error": "No files provided"}), 400

        file_list = []
        for file in files.getlist("files"):  # קבלת כל הקבצים תחת המפתח "files"
            if file.filename == "":
                return jsonify({"error": "One of the files has no filename"}), 400
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            await file.save(file_path)
            file_list.append(file_path)
            print(f"Saved: {file.filename}")

        # קריאה לפונקציה שתטפל בקבצים
        await load_songs_from_files_list(file_list)
        return jsonify({"message": f"{len(file_list)} files uploaded successfully"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/save-song-details", methods=["POST"])
async def save_song_details_route():
    try:
        data = await request.get_json()

        # קבלת הנתונים
        song_name = data.get("song_name", "")
        poet = data.get("poet", "")
        composer = data.get("composer", "")
        creation_year = data.get("creation_year", "")
        video_link = data.get("video_link", "")
        performer_name = data.get("performer_name", "")

        # קריאה לפונקציה שמכניסה את הנתונים ל-DB
        await insert_song_details(
            song_name,
            poet=poet,
            composer=composer,
            creation_year=creation_year,
            video_link=video_link,
            performer_name=performer_name,
        )

        return jsonify({"message": "Song details saved successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True)
