import streamlit as st # type: ignore
import pandas as pd # type: ignore
import numpy as np # type: ignore
# Create a sample DataFrame
data = {'col1': np.random.randint(1, 100, 10),
        'col2': np.random.rand(10)}
df=pd.DataFrame(data)

st.title("Title")
st.write("Writing")
st.markdown("""##HEADING 3 
    * blah
    *blah2
            
    1. one
    2. two                  
    3. **very strong**: I am


    """)
st.badge("Home", color ="blue")
st.success("blahh, blahh")

st.error("blah")

if st.button("Click me"):
    st.write(df)

col1, col2, col3 = st.columns(3)

with col1:
    st.header("A cat")
    st.image("https://static.streamlit.io/examples/cat.jpg")

with col2:
    st.header("A dog")
    st.image("https://static.streamlit.io/examples/dog.jpg")

with col3:
    st.header("An owl")
    st.image("https://static.streamlit.io/examples/owl.jpg")

# Using object notation
add_selectbox = st.sidebar.selectbox(
    "How would you like to be contacted?",
    ("Email", "Home phone", "Mobile phone")
)

# Using "with" notation
with st.sidebar:
    add_radio = st.radio(
        "Choose a shipping method",
        ("Standard (5-15 days)", "Express (2-5 days)")
    )