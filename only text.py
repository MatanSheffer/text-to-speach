from pydub import AudioSegment
import speech_recognition as sr
import requests
from concurrent.futures import ThreadPoolExecutor
import os

def google_translate(text, target_language='he'):
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_language}&dt=t&q={text}"
    response = requests.get(url)
    if response.status_code == 200:
        result = response.json()[0][0][0]
        return result
    else:
        return None

def process_chunk(i, chunk, last_successful_lang):
    temp_filename = f"temp_chunk_{i}.wav"
    result = {}
    chunk.export(temp_filename, format="wav")
    recognizer = sr.Recognizer()

    with sr.AudioFile(temp_filename) as source:
        audio_data = recognizer.record(source)

        lang_list = [last_successful_lang] if last_successful_lang else []
        lang_list.extend([lang for lang in ["ru-RU", "he-IL"] if lang != last_successful_lang])

        for lang_code in lang_list:
            try:
                text = recognizer.recognize_google(audio_data, language=lang_code)
                if lang_code == "ru-RU":
                    translated = google_translate(text, 'he')
                    result['output'] = f"Chunk {i + 1} | Language: {lang_code} | Transcript: {text} | Translation: {translated}"
                else:
                    result['output'] = f"Chunk {i + 1} | Language: {lang_code} | Transcript: {text}"

                result['lang'] = lang_code
                os.remove(temp_filename)
                return result

            except (sr.UnknownValueError, sr.RequestError):
                continue

    os.remove(temp_filename)
    return None

# Initialize
audio = AudioSegment.from_wav("20230830183352.WAV")
chunk_length = 7 * 1000
chunks = [audio[i:i + chunk_length] for i in range(0, len(audio), chunk_length)]
last_successful_lang = None

# Process and print in batches of 100
for batch_start in range(0, len(chunks), 100):
    batch_end = min(batch_start + 100, len(chunks))
    batch_chunks = chunks[batch_start:batch_end]
    results = []

    with ThreadPoolExecutor() as executor:
        future_to_chunk = {executor.submit(process_chunk, i + batch_start, chunk, last_successful_lang): i for i, chunk
                           in enumerate(batch_chunks)}
        for future in future_to_chunk:
            result = future.result()
            if result:
                last_successful_lang = result['lang']
                results.append(result['output'])

    print("\n".join(results))
