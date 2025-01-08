update_word_id_query = """
    UPDATE words_in_songs
    SET word_id = words.id
    FROM words_in_songs JOIN words ON words_in_songs.clean_word = words.word_str
    WHERE words_in_songs.word_id IS NULL
    """

search_details = """
select song_details.Id, songs.song_name, song_details.[Poet’s_Name], song_details.[Composer’s_Name], song_details.Creation_Year,song_details.[Performance_Video_Link] ,song_details.[Performer’s_Name]
from song_details
join songs on song_details.song_id = songs.id
WHERE 
    (:song_name IS NULL OR songs.song_name LIKE '%' + :song_name + '%') AND
    (:poet IS NULL OR [Poet’s_Name] LIKE '%' + :poet + '%') AND
    (:composer IS NULL OR [Composer’s_Name] LIKE '%' + :composer + '%') AND
    (:creation_year IS NULL OR Creation_year = :creation_year) AND
    (:performer_name IS NULL OR [Performer’s_Name] LIKE '%' + :performer_name + '%')
order by songs.song_name
"""

insert_new_group_query = """
IF NOT EXISTS (SELECT 1 FROM groups WHERE group_name = :group_name)
INSERT INTO groups (group_name, group_purpose)
OUTPUT INSERTED.id
SELECT :group_name, :group_purpose
"""

get_group_id = "SELECT id FROM groups WHERE group_name = :group_name"

get_word_id = "SELECT id FROM words WHERE word_str = :word_str"

insert_to_words_in_group_query = """
IF 
    EXISTS (SELECT 1 FROM groups WHERE id = :group_id) AND 
    EXISTS (SELECT 1 FROM words WHERE id = :word_id) AND 
    NOT EXISTS (SELECT 1 FROM words_in_group WHERE word_id = :word_id AND group_id = :group_id)
INSERT INTO words_in_group (word_id, group_id)
SELECT :word_id, :group_id
"""

delete_group_query = """
delete from groups
where group_name = :group_name
delete from words_in_group
where group_id = :group_id
"""

delete_word_from_group_query = """
delete from words_in_group
where word_id = :word_id AND group_id = :group_id
"""

get_words_in_group = """
SELECT 
    wig.id AS wig_id, 
    wig.word_id, 
    wig.group_id, 
    w.word_str 
FROM words_in_group wig 
JOIN groups ON groups.id = wig.group_id
JOIN words w ON wig.word_id = w.id
WHERE (:group_name IS NULL OR groups.group_name = :group_name)
"""

get_group_details = """
UPDATE groups
SET 
    group_name = :new_group_name,
    group_purpose = :new_group_purpose
WHERE group_name = :old_group_name
"""

remove_details_line = """
delete from song_details
where id = :details_line_id
"""

word_shows_in_par = """
with word_pars AS(
    select distinct 
        words_in_songs.clean_word, 
        songs.song_name, 
        paragraphs.par_num, 
        wis.unclean_word , 
        wis.word_num
    FROM words_in_songs
    join paragraphs on paragraphs.par_num = words_in_songs.par_num and paragraphs.song_id = words_in_songs.song_id
    join songs on paragraphs.song_id = songs.id
    JOIN words_in_songs wis on paragraphs.par_num = wis.par_num and paragraphs.song_id = wis.song_id
)
select distinct
    clean_word, 
    song_name, 
    par_num, 
    STRING_AGG(unclean_word, '') WITHIN GROUP (ORDER BY word_num) AS par_content
from word_pars
WHERE (:word IS NULL OR clean_word = :word)
AND clean_word <> ''
group by clean_word, song_name, par_num
order by clean_word, song_name, par_num
"""

words_index = """
select distinct word_id, clean_word, song_name, par_num, line_num_in_par, word_num_in_line
from words_in_songs
join songs on songs.id = words_in_songs.song_id
WHERE clean_word <> ''
order by clean_word, song_name, par_num, line_num_in_par, word_num_in_line
"""

words_statistics_in_song = """
select song_name, clean_word WORD, chars_count, COUNT(DISTINCT wis.id) TOTAL_SHOWS,
    SUM(COUNT(wis.id)) OVER (PARTITION BY song_name) AS TOTAL_WORDS_IN_SONG,
    ROUND((CAST(COUNT(DISTINCT wis.id) AS FLOAT) / SUM(COUNT(wis.id)) OVER (PARTITION BY song_name)) , 3) AS Frequency
from words_in_songs wis
join songs on songs.id = wis.song_id
group by song_name, clean_word, chars_count
order by song_name, TOTAL_SHOWS DESC
"""

words_statistics_in_db = """
DECLARE @TOTAL_WORDS_ALL_SONGS BIGINT;

SELECT 
    @TOTAL_WORDS_ALL_SONGS = SUM(COUNT(words_in_songs.id))  OVER ()
FROM words_in_songs JOIN songs ON songs.id = words_in_songs.song_id
GROUP BY clean_word;

SELECT 
    clean_word AS WORD,
    chars_count,
    COUNT(wis.id) AS TOTAL_WORD_SHOWS,
    @TOTAL_WORDS_ALL_SONGS AS TOTAL_WORDS_ALL_SONGS,
    ROUND(CAST(COUNT(wis.id) AS FLOAT) / @TOTAL_WORDS_ALL_SONGS, 3) AS FREQUENCY
FROM words_in_songs wis
JOIN songs ON songs.id = wis.song_id
GROUP BY clean_word, chars_count
ORDER BY TOTAL_WORD_SHOWS DESC;
"""

pars_statistics_in_song = """
select 
    song_name, 
    wis.par_num, 
    MAX(line_num_in_par) AS TOTAL_PAR_LINES,
    COUNT(wis.id) TOTAL_PAR_WORDS,
    SUM(chars_count) AS TOTAL_PAR_CHARS,
    ROUND(CAST(SUM(chars_count) AS float) / COUNT(word_id) , 2)  AS PAR_AVERAGE_CHARS_PER_WORD,
    MAX(wis.par_num) OVER (PARTITION BY song_name) AS TOTAL_PARS_IN_SONG,
    SUM(COUNT(wis.id)) OVER (PARTITION BY song_name) AS TOTAL_WORDS_IN_SONG,
    ROUND((CAST(COUNT(DISTINCT wis.id) AS FLOAT) / SUM(COUNT(wis.id)) OVER (PARTITION BY song_name)) , 3) AS PAR_WORDS_RATE_IN_SONG,
    ROUND((CAST(1 AS float) / (MAX(wis.par_num) OVER (PARTITION BY song_name))) , 3) AS AVERAGE_PARAGRAPH_PROPORTION,
    ROUND((CAST(COUNT(DISTINCT wis.id) AS FLOAT) / SUM(COUNT(wis.id)) OVER (PARTITION BY song_name)) / (1.0 / (MAX(wis.par_num) OVER (PARTITION BY song_name))) , 2) AS RELATIVE_DENSITY
from words_in_songs wis
join songs on songs.id = wis.song_id
group by song_name, par_num
order by song_name, par_num
"""

lines_statistics_in_song = """
select 
    song_name, 
    line_num_in_par,
    par_num, 
    SUM(chars_count) AS TOTAL_LINE_CHARS,
    COUNT(DISTINCT wis.id) TOTAL_WORDS,
    SUM(COUNT(wis.id)) OVER (PARTITION BY song_name) AS TOTAL_WORDS_IN_SONG,
    ROUND((CAST(COUNT(DISTINCT wis.id) AS FLOAT) / SUM(COUNT(wis.id)) OVER (PARTITION BY song_name)) , 4) AS Frequency,
    ROUND((CAST(1 AS float) / (COUNT(line_num_in_par) OVER (PARTITION BY song_name))) , 4) AS AVERAGE_LINE_PROPORTION,
    ROUND((CAST(COUNT(DISTINCT wis.id) AS FLOAT) / SUM(COUNT(wis.id)) OVER (PARTITION BY song_name)) / (1.0 / (COUNT(line_num_in_par) OVER (PARTITION BY song_name))) , 2) AS RELATIVE_DENSITY
from words_in_songs wis
join songs on songs.id = song_id
group by song_name, par_num, line_num_in_par
order by song_name, par_num, line_num_in_par
"""

songs_statistics = """
select 
    song_name, 
    MAX(par_num) AS TOTAL_PARS, 
    COUNT(DISTINCT CONCAT(par_num, '-', line_num_in_par)) AS TOTAL_LINES,
    COUNT(wis.id) AS TOTAL_WORDS,
    SUM(chars_count) AS TOTAL_CHARS
from words_in_songs wis
join songs on songs.id = song_id
group by song_name
order by song_name
"""

rhymes_for_word = """
SELECT DISTINCT 
    clean_word, song_name, par_num, line_num_in_par, last_syllable
FROM words_in_songs wis
JOIN words ON words.id = wis.word_id
JOIN songs ON songs.id = wis.song_id
WHERE 
    last_syllable = :last_syllable AND
    is_last_in_line = 1
ORDER BY song_name, par_num, line_num_in_par
"""

insert_expression =  """
    IF NOT EXISTS (
        SELECT expression_str
        FROM expression
        WHERE expression_str = :expression_str
    )
    insert into expression
    select :expression_str
"""

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

is_exist_song_query = "SELECT COUNT(1) FROM songs WHERE song_name = :song_name"

expression_table_query = "SELECT * FROM expression"

songs_table_query = "SELECT * FROM songs"

groups_table_query = "SELECT * FROM groups"

words_table_query = "SELECT * FROM words"

words_in_songs_main_columns_table_query = "SELECT id, word_id, clean_word, song_id FROM words_in_songs"
