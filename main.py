from pydub import AudioSegment
import speech_recognition as sr
from concurrent.futures import ThreadPoolExecutor
import pygame
import time
import os
import requests
import numpy as np
from speech_recognition import AudioData


def translate_text(text, target_language='he'):
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_language}&dt=t&q={text}"
    response = requests.get(url)
    if response.status_code == 200:
        result = response.json()[0][0][0]
        return result
    else:
        return None


def process_chunk(i, chunk, last_successful_lang):
    result = {}
    temp_filename = f"temp_chunk_{i}.wav"
    chunk.export(temp_filename, format="wav")
    recognizer = sr.Recognizer()

    with sr.AudioFile(temp_filename) as source:
        audio_data = recognizer.record(source)

        # Convert AudioData to NumPy array (simulate your noise reduction here)
        audio_data_samples = np.array(audio_data.frame_data)

        # Simulated noise reduction (replace with your actual noise reduction logic)
        reduced_noise = audio_data_samples  # No real noise reduction done here

        # Convert back to AudioData
        new_audio_data = AudioData(reduced_noise.tobytes(), audio_data.sample_rate, audio_data.sample_width)

        lang_list = [last_successful_lang] if last_successful_lang else []
        lang_list.extend([lang for lang in ["ru-RU", "he-IL"] if lang != last_successful_lang])

        for lang_code in lang_list:
            try:
                text = recognizer.recognize_google(new_audio_data, language=lang_code)
                translated_text = translate_text(text)
                result['output'] = translated_text
                result['lang'] = lang_code
                return result, temp_filename
            except (sr.UnknownValueError, sr.RequestError):
                continue

    return None, temp_filename


# Initialize Pygame
pygame.init()
pygame.font.init()
pygame.mixer.init()
screen = pygame.display.set_mode((1200, 200))
pygame.display.set_caption('Subtitles')

hebrew_font = pygame.font.Font("/Users/matansheffer/Desktop/PycharmProjects/STT/hebrew.ttf", 28)
default_font = pygame.font.Font(None, 36)

# Initialize Audio and Splitting
audio = AudioSegment.from_wav("20230830183352.WAV")
chunk_length = 5 * 1000
chunks = [audio[i:i + chunk_length] for i in range(0, len(audio), chunk_length)]
last_successful_lang = None

# Process in batches
for batch_start in range(0, len(chunks), 100):
    batch_end = min(batch_start + 100, len(chunks))
    batch_chunks = chunks[batch_start:batch_end]
    results = []

    with ThreadPoolExecutor() as executor:
        future_to_chunk = {executor.submit(process_chunk, i + batch_start, chunk, last_successful_lang): i for i, chunk
                           in enumerate(batch_chunks)}

        for future in future_to_chunk:
            result, temp_filename = future.result()
            if result:
                last_successful_lang = result['lang']

                # Display Hebrew subtitle
                text_to_show = result['output']
                reversed_text = text_to_show[::-1]  # Reverse the string
                text_surface = hebrew_font.render(reversed_text, True, (255, 255, 255))
                screen.fill((0, 0, 0))

                # Existing logic for positioning
                x_position = 600 - text_surface.get_width() // 2
                y_position = 100

                screen.blit(text_surface, (x_position, y_position))
                pygame.display.flip()
                pygame.mixer.music.load(temp_filename)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    screen.fill((0, 0, 0))
                    screen.blit(text_surface, (600 - text_surface.get_width() // 2, 100))
                    pygame.display.flip()

                    for event in pygame.event.get():
                        if event.type == pygame.KEYDOWN:
                            pygame.mixer.music.stop()
                            break

                    time.sleep(0.1)

                os.remove(temp_filename)
