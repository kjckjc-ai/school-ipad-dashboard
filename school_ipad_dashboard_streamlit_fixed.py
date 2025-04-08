import streamlit as st
import pandas as pd
import json
from PIL import Image
import io
import base64

# Set page configuration
st.set_page_config(
    page_title="School iPad Implementation Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to make it look more like Apple design aesthetic
st.markdown("""
<style>
    .main {
        background-color: #f5f5f7;
        color: #1d1d1f;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    h1, h2, h3, h4 {
        font-weight: 600;
    }
    .stButton button {
        background-color: #0071e3;
        color: white;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        border: none;
    }
    .stButton button:hover {
        background-color: #0077ed;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .improvement-area {
        border-left: 4px solid #0071e3;
        background-color: #f5f5f7;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .priority-area {
        border-left: 4px solid #34c759;
        background-color: #f5f5f7;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .rating-outstanding {
        background-color: #34c759;
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 500;
    }
    .rating-good {
        background-color: #0071e3;
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 500;
    }
    .rating-requires-improvement {
        background-color: #ff9f0a;
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 500;
    }
    .rating-inadequate {
        background-color: #ff3b30;
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session states to fix button issues
if 'custom_priorities' not in st.session_state:
    st.session_state.custom_priorities = []

if 'selected_school' not in st.session_state:
    st.session_state.selected_school = None

if 'current_view' not in st.session_state:
    st.session_state.current_view = "search"  # Options: "search", "profile", "report"

if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

if 'search_results' not in st.session_state:
    st.session_state.search_results = []

if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

if 'new_priority' not in st.session_state:
    st.session_state.new_priority = ""

# Load the full dataset from CSV
@st.cache_data
def load_school_data():
    try:
        df = pd.read_csv("National datasheeet.csv")
        return df
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
        # Return sample data as fallback
        return load_sample_school_data_as_df()

# Sample data as fallback (in case CSV loading fails)
@st.cache_data
def load_sample_school_data_as_df():
    sample_data = [
        {
            "URN": "101196",
            "EstablishmentName": "Northbury Primary School",
            "Street": "Northbury Close",
            "Town": "Barking",
            "Postcode": "IG11 8JA",
            "TypeOfEstablishment (name)": "Community school",
            "PhaseOfEducation (name)": "Primary",
            "NumberOfPupils": 868,
            "PercentageFSM": 25.0
        },
        {
            "URN": "101230",
            "EstablishmentName": "Roding Primary School",
            "Street": "Hewett Road",
            "Town": "Dagenham",
            "Postcode": "RM8 2XS",
            "TypeOfEstablishment (name)": "Community school",
            "PhaseOfEducation (name)": "Primary",
            "NumberOfPupils": 1050,
            "PercentageFSM": 27.2
        },
        # Add more sample schools as needed
    ]
    return pd.DataFrame(sample_data)

# Sample Ofsted improvement areas (since these aren't in the CSV)
@st.cache_data
def get_sample_improvement_areas(urn):
    improvement_areas_map = {
        "101196": [
            "A small minority of staff do not present information clearly or provide effective support for some pupils at the point when it is needed.",
            "Some pupils with lower prior attainment and those with SEND do not receive the tools needed in lessons to fully access the learning.",
            "Leaders have identified members of staff requiring more support and development in the teaching of reading."
        ],
        "101230": [
            "Curriculum implementation in some foundation subjects is not fully developed.",
            "Assessment practices vary across subjects and year groups.",
            "Digital technology integration is inconsistent across classrooms."
        ],
        # Add more as needed
    }
    
    # Default improvement areas if URN not found
    default_areas = [
        "Improve the quality of teaching in core subjects.",
        "Develop more effective strategies for supporting pupils with special educational needs.",
        "Enhance the use of technology to support teaching and learning."
    ]
    
    return improvement_areas_map.get(str(urn), default_areas)

# Sample Ofsted ratings (since these aren't in the CSV)
@st.cache_data
def get_sample_ofsted_rating(urn):
    ratings_map = {
        "101196": {"rating": "Good", "date": "17 March 2022"},
        "101230": {"rating": "Good", "date": "10 January 2023"},
        # Add more as needed
    }
    
    # Default rating if URN not found
    default_rating = {"rating": "Good", "date": "01 January 2023"}
    
    return ratings_map.get(str(urn), default_rating)

# DfE Technology Standards focused on leadership, accessibility, and devices
@st.cache_data
def load_dfe_standards():
    return {
        "leadership": {
            "title": "Digital Leadership and Governance Standards",
            "description": "Standards for how schools should develop and implement digital technology strategy.",
            "key_points": [
                "Schools need clearly defined roles and responsibilities for digital technology",
                "A digital technology strategy should align with the school development plan",
                "The SLT digital lead should develop a longer-term vision for technology",
                "Without proper strategy, risks include disrupted learning, safeguarding issues, and budget pressures"
            ],
            "ipad_benefits": [
                "Provide a consistent platform for implementing digital strategy",
                "Offer management tools for school leaders to monitor and assess impact",
                "Support curriculum delivery with purpose-built educational apps",
                "Enable cost-effective technology implementation with predictable lifecycle",
                "Allow for centralized management and security policies"
            ]
        },
        "accessibility": {
            "title": "Digital Accessibility Standards",
            "description": "Standards for ensuring equity of access for all users in schools.",
            "key_points": [
                "Schools should provide equity of access for all users",
                "Digital accessibility features should include text-to-speech, captions, zoom settings, and translation tools",
                "Hardware and software should have accessibility features available with support provided",
                "These features remove barriers to accessing teaching and learning"
            ],
            "ipad_benefits": [
                "Built-in accessibility features including VoiceOver, Speak Screen, and Dictation",
                "Customizable display settings (text size, contrast, color filters)",
                "Assistive Touch for motor control challenges",
                "Support for external adaptive devices",
                "Consistent accessibility experience across all apps",
                "Regular updates to accessibility features"
            ]
        },
        "devices": {
            "title": "Device Standards",
            "description": "Standards for ensuring devices meet educational needs and are safe and secure.",
            "key_points": [
                "Devices should meet educational needs and support the digital technology strategy",
                "Devices should be safe and secure",
                "Hardware should be appropriate for the intended educational use",
                "Devices should support required software and applications",
                "Management systems should allow for appropriate controls"
            ],
            "ipad_benefits": [
                "Purpose-built for education with robust hardware",
                "Long battery life suitable for school day",
                "Managed device enrollment program for centralized control",
                "Regular security updates and strong privacy protections",
                "Wide range of educational apps and content",
                "Durability and reliability reducing total cost of ownership",
                "Consistent user experience across devices"
            ]
        }
    }

# Common improvement areas and how iPads can address them
@st.cache_data
def load_improvement_solutions():
    return {
        "information_presentation": {
            "keywords": ["present information", "clarity", "clear explanation", "visual aids"],
            "title": "Enhancing Information Presentation",
            "solutions": [
                "Interactive presentations with Apple Keynote allow teachers to create engaging, visual explanations",
                "Screen recording features enable teachers to create instructional videos for review",
                "AirPlay allows teachers to wirelessly display content from iPad to classroom display",
                "Split View enables teachers to reference materials while presenting information",
                "Visual and multimedia content can make complex information more accessible to all learners"
            ],
            "standards": ["accessibility", "devices"]
        },
        "send_support": {
            "keywords": ["SEND", "special educational needs", "disabilities", "additional support", "differentiation"],
            "title": "Supporting SEND Students",
            "solutions": [
                "Built-in accessibility features provide personalized support for diverse learning needs",
                "Text-to-speech and speech-to-text tools support students with reading and writing difficulties",
                "Guided Access helps students with attention difficulties stay focused on specific tasks",
                "Differentiated activities can be easily assigned to specific students through shared iPad features",
                "Apps can be selected to provide appropriate challenge and support for individual needs"
            ],
            "standards": ["accessibility", "leadership"]
        },
        "reading_instruction": {
            "keywords": ["reading", "phonics", "literacy", "books", "comprehension"],
            "title": "Improving Reading Instruction",
            "solutions": [
                "Digital reading apps with built-in assessment tools track student progress",
                "Text-to-speech features support developing readers and model fluent reading",
                "Interactive books engage reluctant readers and support comprehension",
                "Recording tools allow students to practice and review their reading",
                "Digital libraries provide access to a wide range of texts at appropriate levels"
            ],
            "standards": ["accessibility", "devices"]
        },
        "curriculum_implementation": {
            "keywords": ["curriculum", "subject knowledge", "planning", "sequencing", "knowledge building"],
            "title": "Strengthening Curriculum Implementation",
            "solutions": [
                "Curriculum planning and mapping apps help ensure systematic knowledge building",
                "Subject-specific apps provide rich, interactive content to support teaching",
                "Digital portfolios allow tracking of progress across the curriculum",
                "Collaborative tools enable subject leaders to share resources and best practices",
                "Assessment apps help identify gaps in knowledge and understanding"
            ],
            "standards": ["leadership", "devices"]
        },
        "staff_development": {
            "keywords": ["staff training", "professional development", "CPD", "teacher skills", "support"],
            "title": "Enhancing Staff Development",
            "solutions": [
                "Apple Teacher professional learning program provides structured training for staff",
                "Screen recording allows for sharing of best practices among staff",
                "Coaching and mentoring can be facilitated through collaborative apps",
                "Apple Professional Learning resources offer ongoing support for teachers",
                "Built-in guides and tutorials help staff develop confidence with technology"
            ],
            "standards": ["leadership"]
        },
        "assessment": {
            "keywords": ["assessment", "feedback", "progress", "tracking", "monitoring"],
            "title": "Improving Assessment Practices",
            "solutions": [
                "Digital assessment tools provide immediate feedback to students",
                "Formative assessment apps help teachers identify misconceptions quickly",
                "Digital portfolios enable collection of evidence over time",
                "Data analysis tools help identify patterns and trends in student performance",
                "Voice recording features allow verbal feedback for students who struggle with reading"
            ],
            "standards": ["leadership", "accessibility"]
        },
        "engagement": {
            "keywords": ["engagement", "motivation", "behavior", "attitude", "enjoyment"],
            "title": "Increasing Student Engagement",
            "solutions": [
                "Interactive, multimedia content increases student interest and motivation",
                "Creative apps allow students to demonstrate learning in diverse ways",
                "Gamified learning experiences make practice of key skills more engaging",
                "Collaborative features enable peer learning and group projects",
                "Personalized learning paths give students appropriate challenge and support"
            ],
            "standards": ["devices", "accessibility"]
        },
        "digital_technology": {
            "keywords": ["technology", "digital", "ICT", "computing", "online"],
            "title": "Enhancing Digital Technology Use",
            "solutions": [
                "1:1 iPad provision ensures consistent access to technology for all students",
                "Managed Apple IDs provide safe, controlled access to digital resources",
                "Classroom app allows teachers to guide student learning and monitor activity",
                "Shared iPad feature enables cost-effective device deployment",
                "Apple School Manager simplifies device management and app distribution"
            ],
            "standards": ["leadership", "devices"]
        }
    }

# Load data
try:
    school_data_df = load_school_data()
    dfe_standards = load_dfe_standards()
    improvement_solutions = load_improvement_solutions()
except Exception as e:
    st.error(f"Error loading data: {e}")

# Function to search schools
def search_schools(query):
    if not query or query.strip() == '':
        return []
    
    query = query.lower().strip()
    
    # Search in the dataframe
    results = school_data_df[
        school_data_df["EstablishmentName"].str.lower().str.contains(query, na=False) | 
        school_data_df["URN"].astype(str).str.contains(query, na=False) |
        school_data_df["Postcode"].str.lower().str.contains(query, na=False)
    ]
    
    return results

# Function to set search query
def set_search_query():
    query = st.session_state.search_input
    st.session_state.search_query = query
    st.session_state.search_performed = True
    
    # Perform search
    results = search_schools(query)
    st.session_state.search_results = results

# Function to select school
def select_school(urn):
    # Find the selected school in the dataframe
    school_row = school_data_df[school_data_df["URN"] == urn].iloc[0]
    
    # Create a dictionary with the school data
    school = {
        "urn": str(school_row["URN"]),
        "name": school_row["EstablishmentName"],
        "address": f"{school_row.get('Street', '')}, {school_row.get('Town', '')}, {school_row.get('Postcode', '')}",
        "type": school_row.get("TypeOfEstablishment (name)", ""),
        "phase": school_row.get("PhaseOfEducation (name)", ""),
        "pupils": school_row.get("NumberOfPupils", 0),
        "fsm": school_row.get("PercentageFSM", 0),
    }
    
    # Add Ofsted data (not in CSV, using sample data)
    ofsted_data = get_sample_ofsted_rating(urn)
    school["ofstedRating"] = ofsted_data["rating"]
    school["ofstedDate"] = ofsted_data["date"]
    
    # Add improvement areas (not in CSV, using sample data)
    school["improvementAreas"] = get_sample_improvement_areas(urn)
    
    # Set the selected school in session state
    st.session_state.selected_school = school
    st.session_state.current_view = "profile"

# Function to add priority
def add_priority():
    if st.session_state.new_priority.strip():
        st.session_state.custom_priorities.append(st.session_state.new_priority)
        st.session_state.new_priority = ""  # Clear the input

# Function to remove priority
def remove_priority(index):
    st.session_state.custom_priorities.pop(index)

# Function to generate report
def generate_report():
    st.session_state.current_view = "report"

# Function to go back to search
def back_to_search():
    st.session_state.current_view = "search"

# Function to go back to profile
def back_to_profile():
    st.session_state.current_view = "profile"

# Function to match improvement areas to solutions
def match_improvement_areas_to_solutions(improvement_areas):
    matched_solutions = []
    matched_solution_keys = set()  # To prevent duplicates
    
    # For each improvement area, find matching solutions
    for area in improvement_areas:
        area_lower = area.lower()
        
        # Check each solution category for keyword matches
        for key, solution in improvement_solutions.items():
            # Skip if we already matched this solution
            if key in matched_solution_keys:
                continue
            
            # Check if any keywords match
            has_match = any(keyword.lower() in area_lower for keyword in solution["keywords"])
            
            if has_match:
                matched_solutions.append({
                    "title": solution["title"],
                    "solutions": solution["solutions"],
                    "standards": solution["standards"]
                })
                matched_solution_keys.add(key)
    
    # If no specific matches found, add digital technology as default
    if not matched_solutions:
        matched_solutions.append({
            "title": improvement_solutions["digital_technology"]["title"],
            "solutions": improvement_solutions["digital_technology"]["solutions"],
            "standards": improvement_solutions["digital_technology"]["standards"]
        })
    
    return matched_solutions

# Function to get CSS class for Ofsted rating
def get_ofsted_rating_class(rating):
    if rating == "Outstanding":
        return "rating-outstanding"
    elif rating == "Good":
        return "rating-good"
    elif rating == "Requires Improvement":
        return "rating-requires-improvement"
    elif rating == "Inadequate":
        return "rating-inadequate"
    else:
        return ""

# Function to display school profile
def display_school_profile(school):
    st.markdown(f"<div class='card'>", unsafe_allow_html=True)
    
    # School header
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"<h2>{school['name']}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p>{school['address']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p>{school['phase']} | {school['type']}</p>", unsafe_allow_html=True)
        
        # Ofsted rating
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-top: 10px;">
            <span style="margin-right: 10px;">Ofsted Rating:</span>
            <span class="{get_ofsted_rating_class(school['ofstedRating'])}">{school['ofstedRating']}</span>
            <span style="margin-left: 10px; color: #6e6e73;">Last inspection: {school['ofstedDate']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h4>School Statistics</h4>", unsafe_allow_html=True)
        st.metric("Number of Pupils", school['pupils'])
        st.metric("FSM Percentage", f"{school['fsm']}%")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Improvement areas
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Ofsted Areas for Improvement</h3>", unsafe_allow_html=True)
    
    for area in school['improvementAreas']:
        st.markdown(f"<div class='improvement-area'>{area}</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Custom priorities
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>School Priorities</h3>", unsafe_allow_html=True)
    st.markdown("<p>Add any additional school priorities not captured in the Ofsted report:</p>", unsafe_allow_html=True)
    
    # Input for new priority
    col1, col2 = st.columns([4, 1])
    with col1:
        st.text_input("Enter school priority...", key="new_priority")
    with col2:
        st.button("Add Priority", on_click=add_priority)
    
    # Display existing priorities
    if st.session_state.custom_priorities:
        for i, priority in enumerate(st.session_state.custom_priorities):
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"<div class='priority-area'>{priority}</div>", unsafe_allow_html=True)
            with col2:
                st.button("Remove", key=f"remove_{i}", on_click=remove_priority, args=(i,))
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Generate report button
    st.button("Generate Report", key="generate_report", on_click=generate_report)

# Function to display report
def display_report(school):
    # Combine Ofsted areas and custom priorities
    all_improvement_areas = school['improvementAreas'] + st.session_state.custom_priorities
    
    # Match improvement areas to solutions
    matched_solutions = match_improvement_areas_to_solutions(all_improvement_areas)
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    
    # Report header
    st.markdown(f"<h1>iPad Implementation Report</h1>", unsafe_allow_html=True)
    st.markdown(f"<h2>{school['name']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p>{school['address']}</p>", unsafe_allow_html=True)
    
    # Ofsted rating
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-top: 10px; margin-bottom: 20px;">
        <span style="margin-right: 10px;">Ofsted Rating:</span>
        <span class="{get_ofsted_rating_class(school['ofstedRating'])}">{school['ofstedRating']}</span>
        <span style="margin-left: 10px; color: #6e6e73;">Last inspection: {school['ofstedDate']}</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Executive Summary
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Executive Summary</h3>", unsafe_allow_html=True)
    st.markdown(f"""
    <p>This report outlines how implementing 1:1 iPads at {school['name']} can address key improvement areas 
    identified in the school's latest Ofsted report while meeting the Department for Education's technology 
    standards for digital leadership, accessibility, and devices.</p>
    
    <p>The recommendations are tailored to the specific context of {school['name']} as a {school['phase'].lower()} school
    with {school['pupils']} pupils and a Free School Meals percentage of {school['fsm']}%.</p>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Key Improvement Areas
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Key Improvement Areas</h3>", unsafe_allow_html=True)
    
    for area in all_improvement_areas:
        st.markdown(f"<div class='improvement-area'>{area}</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # iPad Implementation Recommendations
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>iPad Implementation Recommendations</h3>", unsafe_allow_html=True)
    
    for solution in matched_solutions:
        with st.expander(solution["title"]):
            for item in solution["solutions"]:
                st.markdown(f"- {item}")
            
            st.markdown("**Relevant DfE Standards:**")
            for standard in solution["standards"]:
                st.markdown(f"<span style='background-color: #e8f0fe; padding: 4px 8px; border-radius: 12px; font-size: 14px;'>{dfe_standards[standard]['title']}</span>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Alignment with DfE Technology Standards
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Alignment with DfE Technology Standards</h3>", unsafe_allow_html=True)
    
    tabs = st.tabs(["Leadership", "Accessibility", "Devices"])
    
    with tabs[0]:
        st.markdown(f"<h4>{dfe_standards['leadership']['title']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p>{dfe_standards['leadership']['description']}</p>", unsafe_allow_html=True)
        st.markdown("<h5>How 1:1 iPads Support This Standard:</h5>", unsafe_allow_html=True)
        for benefit in dfe_standards['leadership']['ipad_benefits']:
            st.markdown(f"- {benefit}")
    
    with tabs[1]:
        st.markdown(f"<h4>{dfe_standards['accessibility']['title']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p>{dfe_standards['accessibility']['description']}</p>", unsafe_allow_html=True)
        st.markdown("<h5>How 1:1 iPads Support This Standard:</h5>", unsafe_allow_html=True)
        for benefit in dfe_standards['accessibility']['ipad_benefits']:
            st.markdown(f"- {benefit}")
    
    with tabs[2]:
        st.markdown(f"<h4>{dfe_standards['devices']['title']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p>{dfe_standards['devices']['description']}</p>", unsafe_allow_html=True)
        st.markdown("<h5>How 1:1 iPads Support This Standard:</h5>", unsafe_allow_html=True)
        for benefit in dfe_standards['devices']['ipad_benefits']:
            st.markdown(f"- {benefit}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Implementation Considerations
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Implementation Considerations</h3>", unsafe_allow_html=True)
    
    with st.expander("Professional Development"):
        st.markdown("""
        Staff training will be essential to maximize the impact of 1:1 iPads. Apple Professional Learning 
        resources and the Apple Teacher program provide structured support for educators at all levels of 
        technical confidence.
        """)
    
    with st.expander("Technical Infrastructure"):
        st.markdown("""
        Robust Wi-Fi coverage throughout the school is essential. A technical audit should be conducted 
        to ensure the network can support simultaneous connections from all devices.
        """)
    
    with st.expander("Deployment Strategy"):
        st.markdown("""
        Consider a phased rollout starting with specific year groups or departments. This allows for 
        evaluation and refinement of implementation strategies before full-school deployment.
        """)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Conclusion
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Conclusion</h3>", unsafe_allow_html=True)
    st.markdown(f"""
    <p>Implementing 1:1 iPads at {school['name']} would directly address the improvement areas identified 
    in the school's Ofsted report while meeting DfE technology standards for leadership, accessibility, and devices.</p>
    
    <p>The versatility, reliability, and built-in accessibility features of iPads make them an ideal platform 
    to support teaching and learning across the curriculum, particularly in addressing the specific needs 
    identified for this school.</p>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        st.button("Back to School Profile", key="back_to_profile", on_click=back_to_profile)
    with col2:
        # Simple text download instead of PDF
        report_text = f"""
        # iPad Implementation Report for {school['name']}
        
        ## School Details
        - Name: {school['name']}
        - Address: {school['address']}
        - Type: {school['type']}
        - Phase: {school['phase']}
        - Ofsted Rating: {school['ofstedRating']} (Last inspection: {school['ofstedDate']})
        - Pupils: {school['pupils']}
        - FSM: {school['fsm']}%
        
        ## Executive Summary
        This report outlines how implementing 1:1 iPads at {school['name']} can address key improvement areas 
        identified in the school's latest Ofsted report while meeting the Department for Education's technology 
        standards for digital leadership, accessibility, and devices.
        
        The recommendations are tailored to the specific context of {school['name']} as a {school['phase'].lower()} school
        with {school['pupils']} pupils and a Free School Meals percentage of {school['fsm']}%.
        
        ## Key Improvement Areas
        {chr(10).join(['- ' + area for area in all_improvement_areas])}
        
        ## iPad Implementation Recommendations
        {chr(10).join(['### ' + solution["title"] + chr(10) + chr(10).join(['- ' + item for item in solution["solutions"]]) for solution in matched_solutions])}
        
        ## Alignment with DfE Technology Standards
        
        ### Digital Leadership and Governance Standards
        {chr(10).join(['- ' + benefit for benefit in dfe_standards['leadership']['ipad_benefits']])}
        
        ### Digital Accessibility Standards
        {chr(10).join(['- ' + benefit for benefit in dfe_standards['accessibility']['ipad_benefits']])}
        
        ### Device Standards
        {chr(10).join(['- ' + benefit for benefit in dfe_standards['devices']['ipad_benefits']])}
        
        ## Conclusion
        Implementing 1:1 iPads at {school['name']} would directly address the improvement areas identified 
        in the school's Ofsted report while meeting DfE technology standards for leadership, accessibility, and devices.
        
        The versatility, reliability, and built-in accessibility features of iPads make them an ideal platform 
        to support teaching and learning across the curriculum, particularly in addressing the specific needs 
        identified for this school.
        """
        
        st.download_button(
            "Download Report as Text",
            report_text,
            file_name=f"{school['name']}_iPad_Implementation_Report.txt",
            mime="text/plain"
        )

# Main application logic
def main():
    # App header
    st.markdown("<h1 style='text-align: center;'>School iPad Implementation Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Create customized reports showing how 1:1 iPads can address Ofsted improvement areas while meeting DfE technology standards.</p>", unsafe_allow_html=True)
    
    # Sidebar for navigation and settings
    with st.sidebar:
        st.markdown("<h3>Navigation</h3>", unsafe_allow_html=True)
        
        if st.button("Search Schools", key="nav_search", on_click=lambda: setattr(st.session_state, 'current_view', 'search')):
            pass  # Action handled by on_click
        
        if st.session_state.selected_school:
            if st.button("View School Profile", key="nav_profile", on_click=lambda: setattr(st.session_state, 'current_view', 'profile')):
                pass  # Action handled by on_click
            
            if st.button("Generate Report", key="nav_report", on_click=lambda: setattr(st.session_state, 'current_view', 'report')):
                pass  # Action handled by on_click
        
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>About</h3>", unsafe_allow_html=True)
        st.markdown("""
        This dashboard helps schools create customized reports showing how 1:1 iPads can address their specific Ofsted improvement areas while meeting DfE technology standards for:
        
        - Digital Leadership and Governance
        - Digital Accessibility
        - Device Standards
        """)
    
    # Main content area based on current view
    if st.session_state.current_view == "search":
        # Search interface
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h2>Search for a School</h2>", unsafe_allow_html=True)
        
        st.text_input("Enter school name, URN, or postcode", key="search_input", on_change=set_search_query)
        
        if st.button("Search", key="search_button", on_click=set_search_query):
            pass  # Action handled by on_click
        
        # Display search results if search was performed
        if st.session_state.search_performed and len(st.session_state.search_query.strip()) > 0:
            results = st.session_state.search_results
            
            if len(results) > 0:
                st.markdown(f"<p>Found {len(results)} schools matching your search.</p>", unsafe_allow_html=True)
                
                # Create a DataFrame for display with selected columns
                display_columns = ["URN", "EstablishmentName", "Town", "Postcode", "PhaseOfEducation (name)"]
                available_columns = [col for col in display_columns if col in results.columns]
                
                results_display = results[available_columns].copy()
                
                # Rename columns for display
                column_rename = {
                    "URN": "URN",
                    "EstablishmentName": "School Name",
                    "Town": "Town",
                    "Postcode": "Postcode",
                    "PhaseOfEducation (name)": "Phase"
                }
                
                results_display = results_display.rename(columns={col: column_rename.get(col, col) for col in available_columns})
                
                # Display results in a table
                st.dataframe(results_display, use_container_width=True)
                
                # Allow user to select a school
                if len(results) > 0:
                    selected_urn = st.selectbox(
                        "Select a school to view details",
                        options=results["URN"].tolist(),
                        format_func=lambda x: f"{results[results['URN']==x]['EstablishmentName'].values[0]} (URN: {x})"
                    )
                    
                    if st.button("View School Profile", key="view_profile"):
                        select_school(selected_urn)
            else:
                st.warning("No schools found matching your search criteria.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Sample schools for quick access
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h3>Sample Schools</h3>", unsafe_allow_html=True)
        st.markdown("<p>Click on a school to view its profile:</p>", unsafe_allow_html=True)
        
        # Get first 6 schools from the dataframe for sample buttons
        sample_schools = school_data_df.head(6)
        
        # Create columns for sample schools
        cols = st.columns(3)
        for i, (_, school) in enumerate(sample_schools.iterrows()):
            with cols[i % 3]:
                if st.button(school["EstablishmentName"], key=f"sample_{i}"):
                    select_school(school["URN"])
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    elif st.session_state.current_view == "profile" and st.session_state.selected_school:
        # Display back button
        if st.button("← Back to Search", key="back_to_search", on_click=back_to_search):
            pass  # Action handled by on_click
        
        # Display school profile
        display_school_profile(st.session_state.selected_school)
    
    elif st.session_state.current_view == "report" and st.session_state.selected_school:
        # Display report
        display_report(st.session_state.selected_school)

# Run the app
if __name__ == "__main__":
    main()
