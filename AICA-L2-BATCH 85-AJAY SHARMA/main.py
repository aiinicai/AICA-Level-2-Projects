import streamlit as st

# Configure the Streamlit page before running any views code
st.set_page_config(page_title="LitigationAI Dashboard", page_icon="⚖️", layout="wide")

from views.dashboard import DashboardUI

def main():
    # Instantiate and render the production UI architecture
    app = DashboardUI()
    user_key = app.render_sidebar()
    app.render_body(user_key)

if __name__ == "__main__":
    main()
