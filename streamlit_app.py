import streamlit as st # type: ignore
import pandas as pd # type: ignore
import psycopg2 # type: ignore
from dotenv import load_dotenv # type: ignore
from openai import OpenAI # type: ignore
import os
import re
import bcrypt


# Load environment variables
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
HASHED_PASSWORD = os.getenv("HASHED_PASSWORD").encode("utf-8")
DATABASE_SCHEMA = """
Database Schema:

LOOKUP TABLES:
- genders (gender_id SERIAL PRIMARY KEY, gender_desc TEXT)
- races (race_id SERIAL PRIMARY KEY, race_desc TEXT)
- marital_statuses (marital_status_id SERIAL PRIMARY KEY, marital_status_desc TEXT)
- languages (language_id SERIAL PRIMARY KEY, language_desc TEXT)
- lab_units (unit_id SERIAL PRIMARY KEY, unit_string TEXT)
- lab_tests (lab_test_id SERIAL PRIMARY KEY, lab_name TEXT, unit_id INTEGER)
- diagnosis_codes (diagnosis_code TEXT PRIMARY KEY, diagnosis_description TEXT)

CORE TABLES: 
- patients (
    patient_id TEXT PRIMARY KEY,
    patient_gender INTEGER (FK to genders), 
    patient_dob TIMESTAMP,
    patient_race INTEGER (FK to races),
    patient_marital_status INTEGER (FK to marital_statuses), 
    patient_language INTEGER (FK to languages), 
    patient_population_pct_below_poverty REAL
)
- admissions (
    patient_id TEXT,
    admission_id INTEGER, 
    admission_start TIMESTAMP, 
    admission_end TIMESTAMP,
    PRIMARY KEY (patient_id, admission_id)
)
- admission_primary_diagnoses (
    patient_id TEXT, 
    admission_id INTEGER,
    diagnosis_code TEXT (FK to diagnosis_codes),
    PRIMARY KEY (patient_id, admission_id)
)
- admission_lab_results ( 
    patient_id TEXT, 
    admission_id INTEGER,
    lab_test_id INTEGER (FK to lab_tests), 
    lab_value REAL, 
    lab_datetime TIMESTAMP
)
IMPORTANT NOTES:
- Use JOINs to get descriptive values from lookup tables
- patient_dob, admission_start, admission_end, and lab_datetime are TIMESTAMPs
- To calculate age: EXTRACT(YEAR FROM AGE(patient_dob))
- To calculate length of stay: EXTRACT(EPOCH FROM (admission_end - admission_start)) / 86400 (gives days)
- Always use proper JOINs for foreign key relationships
"""

# --------------------- DATABASE CONNECTION --------------------- #

def login_screen():
    """Display login screen and authenticate user."""
    st.title("🔒 Secure Login")
    st.markdown("---")
    st.write("Enter your password to access the AI SQL Query Assistant.")

    password = st.text_input("Password", type="password", key="login_password")
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        login_btn = st.button("Login", type="primary", use_container_width=True)

    if login_btn:
        if password:
            try:
                # bcrypt password check
                if bcrypt.checkpw(password.encode("utf-8"), HASHED_PASSWORD):
                    st.session_state.logged_in = True
                    st.success("✅ Authentication successful. Redirecting...")
                    st.rerun()
                else:
                    st.error("❌ Incorrect Password")
            except Exception as e:
                st.error(f"Authentication error: {e}")
        else:
            st.warning("⚠️ Please enter a password")

    st.markdown("---")
    st.info("""
        **Security Notice:**
        - Passwords are protected using bcrypt hashing  
        - Your session is secure and isolated  
        - You will remain logged in until you close the browser or click logout
    """)

def require_login():
    """Enforce login before showing main app"""
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_screen()
        st.stop()

@st.cache_resource
def get_db_url():
    POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_SERVER = os.getenv("POSTGRES_SERVER")
    POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")
    return f"postgresql://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DATABASE}"

DATABASE_URL = get_db_url()

@st.cache_resource
def get_db_connection():
    """Create and cache database connection."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None


def run_query(sql):
    """Execute SQL query and return results as DataFrame."""
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        df = pd.read_sql_query(sql, conn)
        return df
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None


# --------------------- OPENAI LOGIC --------------------- #

def extract_sql_from_response(response_text: str) -> str:
    """
    Extract SQL from GPT response, whether or not it's wrapped in code fences.
    Returns clean SQL string.
    """
    if not response_text:
        return None

    # Try to match fenced SQL ```sql ... ```
    sql_pattern = r"```sql\s*(.*?)\s*```"
    matches = re.findall(sql_pattern, response_text, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[0].strip()

    # Try to match any code block ``` ... ```
    code_pattern = r"```\s*(.*?)\s*```"
    matches = re.findall(code_pattern, response_text, re.DOTALL)
    if matches:
        return matches[0].strip()

    # Fallback: if no fences, look for "SELECT", "WITH", or "CREATE"
    sql_start = re.search(r"\b(SELECT|WITH|CREATE|INSERT|UPDATE|DELETE)\b", response_text, re.IGNORECASE)
    if sql_start:
        return response_text[sql_start.start():].strip()

    # If still nothing found, return entire text (just in case)
    return response_text.strip()



def generate_sql_with_gpt(user_question):
    """Send question and schema to GPT and return extracted SQL."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a PostgreSQL expert. Here is the database schema:\n{DATABASE_SCHEMA}"},
                {"role": "user", "content": user_question}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        raw_response = response.choices[0].message.content
        sql_query = extract_sql_from_response(raw_response)
        return sql_query, raw_response
    except Exception as e:
        st.error(f"Error calling OpenAI API: {e}")
        return None, None


# --------------------- STREAMLIT APP --------------------- #

def main():
    require_login()
    st.title("🤖 AI-Powered SQL Query Assistant")
    st.markdown("Ask questions in natural language, and I will generate SQL queries for you to review and run!")
    st.markdown("---")

    st.sidebar.title("💡 Example Questions")
    st.sidebar.markdown("""
    - How many patients do we have by gender?  
    - What is the average length of stay?  
    - Which lab tests are most common?  
    - What’s the age distribution of patients?
    """)
    st.sidebar.info("""
    **How it works:**
    1. Enter your question in plain English  
    2. AI generates a SQL query  
    3. Review and edit if needed  
    4. Click "Run Query" to execute
    """)
    # Add a logout button in the sidebar
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.success("You have been logged out.")
        st.rerun()

    # Initialize session state
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'generated_sql' not in st.session_state:
        st.session_state.generated_sql = None
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None

    user_question = st.text_area(
        "💬 What would you like to know?",
        height=100,
        placeholder="e.g., What is the average length of stay?"
    )

    col1, col2, _ = st.columns([1, 1, 4])

    with col1:
        generate_button = st.button("Generate SQL", type="primary", use_container_width=True)

    with col2:
        if st.button("Clear History", use_container_width=True):
            st.session_state.query_history = []
            st.session_state.generated_sql = None
            st.session_state.current_question = None

    if generate_button and user_question:
        user_question = user_question.strip()

        # Always reset and store question
        st.session_state.current_question = user_question
        st.session_state.generated_sql = None

        with st.spinner("🤖 AI is generating SQL..."):
            sql_query, raw_response = generate_sql_with_gpt(user_question)

        if sql_query:
            # ✅ Store the new query persistently
            st.session_state.generated_sql = sql_query
            st.session_state.raw_response = raw_response
            st.success("✅ Query generated successfully!")
        else:
            st.error("⚠️ No SQL query found in GPT response or an error occurred.")

    # ✅ Always render review/run if we have a query (even after reruns)
    if st.session_state.generated_sql:
        st.markdown("---")
        st.subheader("🧾 Review and Run Query")
        st.info(f"**Question:** {st.session_state.current_question}")

        edited_sql = st.text_area(
            "Review and edit the SQL query if needed:",
            value=st.session_state.generated_sql,
            height=200,
            key=f"sql_editor_{st.session_state.current_question}"
        )

        run_button = st.button("▶️ Run Query", type="primary", use_container_width=True)
        if run_button:
            with st.spinner("Executing query..."):
                df = run_query(edited_sql)
                if df is not None:
                    st.session_state.query_history.append({
                        'question': st.session_state.current_question,
                        'sql': edited_sql,
                        'rows': len(df)
                    })
                    st.markdown("---")
                    st.subheader("Query Results")
                    st.success(f"✅ Query returned {len(df)} rows")
                    st.dataframe(df, use_container_width=True)

    # ✅ Query history
    if st.session_state.query_history:
        st.markdown("---")
        st.subheader("🕘 Query History")
        for idx, item in enumerate(reversed(st.session_state.query_history[-5:])):
            with st.expander(f"Query {len(st.session_state.query_history)-idx}: {item['question'][:60]}..."):
                st.markdown(f"**Question:** {item["question"]}")
                st.code(item["sql"], language="sql")
                st.caption(f"Returned {item["rows"]} rows")
                if st.button(f"Re-run this query", key=f"rerun_{idx}"):
                    df=run_query(item["sql"])
                    if df is not None:
                        st.dataframe(df, width="stretch")
                        



if __name__ == "__main__":
    main()
