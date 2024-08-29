import os
import streamlit as st
import pandas as pd
import dropbox
import requests
from dropbox.exceptions import AuthError

# Function to display all sound files in a group and collect a single rating
def play_wav_grouped(sound_files, files_path, group):
    st.write(f"### Group {st.session_state.group_index}: Evaluate all the samples")

    # Instructions
    st.write("After listening to all samples, use the slider below to rate the group as a whole.")
    st.write("Evaluate how human-like the variance is. Are these all natural readings? And are they variable enough to cover roughly how a human would speak?")

    # Display all sound files
    audio_bytes = {}
    for i, sound_file in enumerate(sound_files):
        st.write(f"Sample {i + 1}")
        file_path = os.path.join(files_path, sound_file)
        audio_bytes[i] = open(file_path, 'rb').read()
        st.audio(audio_bytes[i], format="audio/wav")

    if st.session_state.ratings["rating"][st.session_state.group_index] != 0:
        index = int(st.session_state.ratings["rating"][st.session_state.group_index]) - 1
    else:
        index = 2
    
    rating = st.radio(f"Rate Group {st.session_state.group_index}", index=index, options=[1, 2, 3, 4, 5], key=f"radio_{st.session_state.group_index}", horizontal=True)

    col1, col2 = st.columns(2)

    with col2:
        
        # Submit rating button
        st.button(f"✔️ Submit Rating", on_click=update_rating, args=(group, rating))

    # go back a group
    if st.session_state.group_index > 0:
        with col1:
            st.button("⮪ Go back a group", on_click=go_back)
    

def go_back():
    # remove the last rating from the session state
    if st.session_state.group_index < len(st.session_state.ratings["rating"]):
        st.session_state.ratings["model"][st.session_state.group_index] = 0
        st.session_state.ratings["rating"][st.session_state.group_index] = 0
    # Decrement the group index to move to the previous group
    
    st.session_state.group_index -= 1
    js = '''
    <script>
        var body = window.parent.document.querySelector(".main");
        console.log(body);
        body.scrollTop = 0;
    </script>
    '''
    st.components.v1.html(js)

def update_rating(group, rating):
    # Append the rating to the session state
    st.session_state.ratings["model"][st.session_state.group_index] = group
    st.session_state.ratings["rating"][st.session_state.group_index] = rating
    
    # Increment the group index to move to the next group
    if not st.session_state.group_index == len(st.session_state.ratings["rating"]) - 1:
        if st.session_state.ratings["rating"][st.session_state.group_index + 1] != 0:
            st.session_state.group_index = len(st.session_state.ratings["rating"])
        else:
            st.session_state.group_index += 1
    else:
        st.session_state.group_index += 1
    js = '''
    <script>
        var body = window.parent.document.querySelector(".main");
        console.log(body);
        body.scrollTop = 0;
    </script>
    '''

    st.components.v1.html(js)

def update_version(version):   
    st.session_state.version = version

def jump_to_group():
    if st.session_state.selected_option == "Results":
        return
    st.session_state.group_index = int(st.session_state.selected_option.split(" ")[1])
    js = '''
    <script>
        var body = window.parent.document.querySelector(".main");
        console.log(body);
        body.scrollTop = 0;
    </script>
    '''
    st.components.v1.html(js)

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
    

# Main function to handle grouped self-test
def grouped_self_test(path_to_audio):
    models = [model for model in os.listdir(path_to_audio) if os.path.isdir(os.path.join(path_to_audio, model))]
    st.session_state.total_groups = len(models)
    # Initialize session state variables if they don't exist
    if 'ratings' not in st.session_state:
        st.session_state.ratings = {"model": [0 for _ in range(len(models))], "rating": [0 for _ in range(len(models))]}
    group_index = st.session_state.group_index

    print(st.session_state)
    if group_index < len(models):
        model_name = models[group_index]
        sound_files = [f for f in os.listdir(os.path.join(path_to_audio, model_name)) if f.endswith('.wav') or f.endswith('.mp3')]
        
        # Get rating for the entire group of sound files
        play_wav_grouped(sound_files, os.path.join(path_to_audio, model_name), model_name)
            
    else:
        if  'done' not in st.session_state:
            st.write("### All groups have been rated!")
            st.write("Please confirm your ratings before submitting.")
            
            # Save ratings to CSV
            df = pd.DataFrame(st.session_state.ratings)
            df_names = df.copy()
            # change df["model"] to model1, model2, model3, etc
            models = ["model " + str(i) for i in range(len(models))] 
            
            df_names["model"] = models
            st.table(df_names.reset_index(drop=True))
            
            # Create the dropdown menu using st.selectbox
            st.selectbox("Choose which Group to jump to:",  ["Results"] + ["model " + str(i) for i in range(len(models))], on_change=jump_to_group, key="selected_option")


            col1, col2 = st.columns(2)
            with col1:
                st.button("⮪ Go back a group", on_click=go_back)
            
            with col2:
                st.button("✔️ Confirm Ratings", on_click=submit_ratings, args=(df,))
        else:
            st.write("Ratings have been successfully submitted!")
            st.write("Thank you for participating!")
        

# Streamlit App
st.title("Sound File Rating Survey")
# Initialize session state variables
if 'total_groups' not in st.session_state:
    st.session_state.total_groups = 10  # will be overwritten by the actual number of groups
    if 'group_index' not in st.session_state:
        st.session_state.group_index = 0
# Display progress bar
progress = st.session_state.group_index / st.session_state.total_groups
st.progress(progress)
# Check if the version is already stored in session state
if 'version' not in st.session_state:
    # Prompt for the version input only if it's not already set
    version_input = st.text_input("Name", "")
    st.button("Submit your Name", on_click=update_version, args=(version_input,))
else:
    # Path to audio files (You can change this to a file uploader in a real deployment)
    path_to_audio = "audios/test/"

    grouped_self_test(path_to_audio)
