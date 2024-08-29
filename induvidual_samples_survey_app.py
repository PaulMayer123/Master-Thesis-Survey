import os
import streamlit as st
import pandas as pd
import dropbox
import random
import requests
from dropbox.exceptions import AuthError

def play_wav(sound_file):
    st.write(f"### Sample {st.session_state.sample_index}: Evaluate the sample")

    # Instructions
    st.write("After listening to the audio, rate it from 1 to 5.")

    st.write(f"**It snowed, rained and hailed the same morning.**")

    if st.session_state.ratings["rating"][st.session_state.sample_index] != 0:
        index = int(st.session_state.ratings["rating"][st.session_state.sample_index]) - 1
    else:
        index = 2
    
    audio_bytes = open(sound_file, 'rb').read()
    st.audio(audio_bytes, format="audio/wav")
    
    rating = st.radio(f"Rate Sample {st.session_state.sample_index}", index=index, options=[1, 2, 3, 4, 5], key=f"radio_{st.session_state.sample_index}", horizontal=True)

    col1, col2 = st.columns(2)

    with col2:
        
        # Submit rating button
        st.button(f"✔️ Submit Rating", on_click=update_rating, args=(sound_file, rating))

    # go back a sample
    if st.session_state.sample_index > 0:
        with col1:
            st.button("⮪ Go back a sample", on_click=go_back)
    

def go_back():
    # remove the last rating from the session state
    if st.session_state.sample_index < len(st.session_state.ratings["rating"]):
        st.session_state.ratings["model"][st.session_state.sample_index] = 0
        st.session_state.ratings["rating"][st.session_state.sample_index] = 0
    # Decrement the sample index to move to the previous sample
    
    st.session_state.sample_index -= 1

def update_rating(sample, rating):
    # Append the rating to the session state
    st.session_state.ratings["model"][st.session_state.sample_index] = sample
    st.session_state.ratings["rating"][st.session_state.sample_index] = rating
    
    # Increment the sample index to move to the next sample
    if not st.session_state.sample_index == len(st.session_state.ratings["rating"]) - 1:
        if st.session_state.ratings["rating"][st.session_state.sample_index + 1] != 0:
            st.session_state.sample_index = len(st.session_state.ratings["rating"])
        else:
            st.session_state.sample_index += 1
    else:
        st.session_state.sample_index += 1

def update_version(version):   
    st.session_state.version = version

def jump_to_sample():
    if st.session_state.selected_option == "Results":
        return
    st.session_state.sample_index = int(st.session_state.selected_option.split(" ")[1])

def refresh_access_token():
    token_url = 'https://api.dropboxapi.com/oauth2/token'
    
    # Dropbox expects the client_id and client_secret as part of basic auth, not in the body
    app_key = st.secrets["dropbox"]["app_key"]
    app_secret = st.secrets["dropbox"]["app_secret"]
    refresh_access_token = st.secrets["dropbox"]["refresh_token"]
    auth = (app_key, app_secret)
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_access_token
    }
    
    response = requests.post(token_url, data=data, auth=auth)
    response_data = response.json()
    
    if response.status_code == 200:
        # Return the new access token
        return response_data.get('access_token')
    else:
        # Handle errors, print out the response for debugging
        print(f"Error refreshing token: {response.status_code}")
        print(response_data)
        return None


def submit_ratings(df):
    # Save ratings to CSV
    file_path = f"ratings_{st.session_state.version}.csv"
    df.to_csv(file_path, index=False)

    if 'access_token' not in st.session_state:
        st.session_state.access_token = refresh_access_token()
    try:
        dbx = dropbox.Dropbox(st.session_state.access_token)
    # catch error because expired token
    except AuthError as e:
        # make sure that it is a token expired error
        if e.error.is_token_expired():
            st.session_state.access_token = refresh_access_token()
            dbx = dropbox.Dropbox(st.session_state.access_token)
        else:
            st.error(f"Error connecting to Dropbox: {e}")
            return
    
    try:
        with open(file_path, "rb") as f:
            dbx.files_upload(f.read(), "/" + file_path)
        st.success(f"File uploaded to Dropbox as {file_path}")
    except Exception as e:
        st.error(f"Error uploading file to Dropbox: {e}")

    st.session_state.done = True
    

# Main function to handle sampleed self-test
def sample_self_test():
    # Initialize session state variables if they don't exist
    if 'ratings' not in st.session_state:
        st.session_state.ratings = {"model": [0 for _ in range(len(st.session_state.sample_order))], "rating": [0 for _ in range(len(st.session_state.sample_order))]}
    sample_index = st.session_state.sample_index

    if sample_index < len(st.session_state.sample_order):
        play_wav(st.session_state.sample_order[sample_index])    
    else:
        if  'done' not in st.session_state:
            st.write("### All samples have been rated!")
            st.write("Please confirm your ratings before submitting.")
            
            # Save ratings to CSV
            df = pd.DataFrame(st.session_state.ratings)
            df_names = df.copy()
            # change df["model"] to model1, model2, model3, etc
            models = ["sample" + str(i) for i in range(len(st.session_state.sample_order))] 
            
            df_names["model"] = models
            
            df_names.set_index('model', inplace=True)
            st.table(df_names)
            
            # Create the dropdown menu using st.selectbox
            st.write("Remember to only change the rating if you made a mistake.")
            st.selectbox("Choose which sample to listen/rate again:",  ["Results"] + ["sample " + str(i) for i in range(len(models))], on_change=jump_to_sample, key="selected_option")


            col1, col2 = st.columns(2)
            with col1:
                st.button("⮪ Go back a sample", on_click=go_back)
            
            with col2:
                st.button("✔️ Confirm Ratings", on_click=submit_ratings, args=(df,))
        else:
            st.write("Ratings have been successfully submitted!")
            st.write("Thank you for participating!")
        

# Streamlit App
st.title("Audio Rating Survey")
# Initialize session state variables
if 'sample_index' not in st.session_state:
    st.session_state.sample_index = 0

# create random order of samples
if 'sample_order' not in st.session_state:
    # files are in subfoleder of audio/name_of_model
    # need to shuffle all from all subfolders into one list
    path_to_audio = "audios/test/"
    models = [model for model in os.listdir(path_to_audio) if os.path.isdir(os.path.join(path_to_audio, model))]
    all_files = []
    for model in models:
        all_files += [os.path.join(path_to_audio, model, f) for f in os.listdir(os.path.join(path_to_audio, model)) if f.endswith('.wav') or f.endswith('.mp3')]
    st.session_state.sample_order = random.sample(all_files, len(all_files))
    st.session_state.total_samples = len(all_files)

# Display progress bar
progress = st.session_state.sample_index / st.session_state.total_samples
st.progress(progress)

# Check if the version is already stored in session state
if 'version' not in st.session_state:
    # Starting "page"
    st.write("### Welcome to the Audio Rating Survey!")
    st.write("Here are the instructions:")
    st.write("- First you will listen to a very good and a very bad audio sample.  \n Those will be the reference points for the rest of the survey.")
    st.write("Good Sample:")
    st.audio(open("audios/test/epd/epd_new-0.wav", 'rb').read(), format="audio/wav")
    st.write("Bad Sample:")
    st.audio(open("audios/test/ped2/ped_log_drop_c8-29.wav", 'rb').read(), format="audio/wav")
    
    st.write("- You will then listen to samples of audio samples and rate them on a scale of 1 to 5.")
    st.write("- Rate the sample based on how human-like the variance is.")
    st.write("- Stick to the first reaction and only change the rating if you made a mistake.")
    # create random string that identifies user
    version = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=7))
    st.button("Start Survey", on_click=update_version, args=(version,))
else:
    sample_self_test()
