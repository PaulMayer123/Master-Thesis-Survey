import os
import streamlit as st
import pandas as pd

# Function to display all sound files in a group and collect a single rating
def play_wav_grouped(sound_files, files_path, group):
    st.write(f"### Group {st.session_state.group_index}: Evaluate all the samples")

    # Display all sound files
    audio_bytes = {}
    for i, sound_file in enumerate(sound_files):
        st.write(f"Sample {i + 1}")
        file_path = os.path.join(files_path, sound_file)
        audio_bytes[i] = open(file_path, 'rb').read()
        st.audio(audio_bytes[i], format="audio/wav")

    # Instructions
    st.write("After listening to all samples, use the slider below to rate the group as a whole.")
    st.write("Evaluate how human-like the variance is. Are these all natural readings? And are they variable enough to cover roughly how a human would speak?")

    rating = st.radio(f"Rate Group {st.session_state.group_index}", options=[1, 2, 3, 4, 5], index=2, key=f"radio_{st.session_state.group_index}", horizontal=True)

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
    st.session_state.ratings["model"].pop()
    st.session_state.ratings["rating"].pop()
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
    st.session_state.ratings["model"].append(group)
    st.session_state.ratings["rating"].append(rating)
    
    # Increment the group index to move to the next group
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

def submit_ratings(df):
    # Save ratings to CSV
    df.to_csv(f"ratings_{st.session_state.version}.csv", index=False)
    st.write("Ratings have been successfully submitted!")
    st.write("Thank you for participating!")

# Main function to handle grouped self-test
def grouped_self_test(path_to_audio):
    models = [model for model in os.listdir(path_to_audio) if os.path.isdir(os.path.join(path_to_audio, model))]
    st.session_state.total_groups = len(models)
    # Initialize session state variables if they don't exist
    if 'ratings' not in st.session_state:
        st.session_state.ratings = {"model": [], "rating": []}
    group_index = st.session_state.group_index

    print(st.session_state)
    if group_index < len(models):
        model_name = models[group_index]
        sound_files = [f for f in os.listdir(os.path.join(path_to_audio, model_name)) if f.endswith('.wav') or f.endswith('.mp3')]
        
        # Get rating for the entire group of sound files
        play_wav_grouped(sound_files, os.path.join(path_to_audio, model_name), model_name)
            
    else:
        st.write("### All groups have been rated!")
        st.write("Please confirm your ratings before submitting.")
        
        # Save ratings to CSV
        df = pd.DataFrame(st.session_state.ratings)
        
        st.write(st.session_state.ratings)

        col1, col2 = st.columns(2)
        with col1:
            st.button("⮪ Go back a group", on_click=go_back)
        
        with col2:
            st.button("✔️ Confirm Ratings", on_click=submit_ratings, args=(df,))

        

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
