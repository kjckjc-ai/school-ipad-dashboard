import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import urllib.parse
import os

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
    .strategy-area {
        border-left: 4px solid #ff9f0a;
        background-color: #f5f5f7;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .link-button {
        display: inline-block;
        background-color: #f5f5f7;
        color: #0071e3;
        text-decoration: none;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 500;
        margin-top: 10px;
    }
    .link-button:hover {
        background-color: #e5e5e7;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session states
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.custom_priorities = []
    st.session_state.school_strategies = []
    st.session_state.ofsted_priorities = []
    st.session_state.selected_school = None
    st.session_state.current_view = "search"  # Options: "search", "profile", "report"
    st.session_state.search_performed = False
    st.session_state.search_results = pd.DataFrame()
    st.session_state.search_query = ""
    st.session_state.new_priority = ""
    st.session_state.new_strategy = ""
    st.session_state.new_ofsted_priority = ""
    st.session_state.website_data_fetched = False
    st.session_state.ofsted_url = None

# Load the dataset from CSV
@st.cache_data
def load_school_data():
    try:
        # Try multiple possible file paths
        csv_paths = [
            "National datasheeet.csv",  # Same directory
            "./National datasheeet.csv", # Explicit current directory
            "../National datasheeet.csv", # Parent directory
            "/mount/src/National datasheeet.csv", # Streamlit Cloud path
            "/app/National datasheeet.csv",  # Another Streamlit Cloud path
            "/mount/src/school-ipad-dashboard/National datasheeet.csv", # Full Streamlit Cloud path
            "/home/ubuntu/upload/National datasheeet.csv",  # Original upload path
            "schools.csv",  # Alternative filename
            "./schools.csv",
            "../schools.csv",
        ]
        
        for path in csv_paths:
            try:
                if os.path.exists(path):
                    df = pd.read_csv(path)
                    st.success(f"Successfully loaded data from {path}")
                    return df
            except Exception as e:
                continue
        
        # If CSV not found, show error
        st.error("National datasheet CSV file not found. Please ensure the file is uploaded correctly.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
        return pd.DataFrame()

# Function to get default Ofsted report URL (fallback)
def get_default_ofsted_report_url(urn):
    return f"https://reports.ofsted.gov.uk/provider/21/{urn}"

# Enhanced function to scrape school website for priorities, strategies, and Ofsted report links
def scrape_school_website(url):
    if not url or not isinstance(url, str) or not url.startswith('http'):
        return {"strategies": [], "ofsted_url": None}
    
    try:
        # Add timeout to avoid hanging
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        if response.status_code != 200:
            return {"strategies": [], "ofsted_url": None}
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for Ofsted report links
        ofsted_url = None
        ofsted_keywords = ['ofsted', 'inspection', 'report']
        
        # Check all links on the page
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().lower()
            link_href = link['href'].lower()
            
            # Check if link text or URL contains Ofsted keywords
            if any(keyword in link_text for keyword in ofsted_keywords) or any(keyword in link_href for keyword in ofsted_keywords):
                # If it's a relative URL, make it absolute
                if not link['href'].startswith('http'):
                    if link['href'].startswith('/'):
                        # Get the base URL
                        parsed_url = urllib.parse.urlparse(url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        ofsted_url = base_url + link['href']
                    else:
                        # Relative to current path
                        ofsted_url = url.rstrip('/') + '/' + link['href']
                else:
                    ofsted_url = link['href']
                
                # If we found a direct link to an Ofsted report, prioritize it
                if 'reports.ofsted.gov.uk' in ofsted_url:
                    break
        
        # Keywords to look for in headings and content for strategies
        strategy_keywords = [
            'strategy', 'strategic', 'priorities', 'priority', 'vision', 'mission', 
            'values', 'aims', 'objectives', 'goals', 'improvement', 'plan', 
            'development', 'school development plan', 'sdp'
        ]
        
        # Find relevant sections for strategies
        strategies = []
        
        # Look for headings with strategy keywords
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_text = heading.get_text().lower()
            
            if any(keyword in heading_text for keyword in strategy_keywords):
                # Get the next few paragraphs or list items
                content = []
                element = heading.find_next_sibling()
                
                # Collect up to 5 elements after the heading
                count = 0
                while element and count < 5:
                    if element.name in ['p', 'li', 'div'] and len(element.get_text().strip()) > 20:
                        content.append(element.get_text().strip())
                    count += 1
                    element = element.find_next_sibling()
                
                if content:
                    strategies.extend(content)
        
        # If no structured content found, look for paragraphs with strategy keywords
        if not strategies:
            for paragraph in soup.find_all(['p', 'li']):
                text = paragraph.get_text().strip()
                if len(text) > 50 and any(keyword in text.lower() for keyword in strategy_keywords):
                    strategies.append(text)
        
        # Deduplicate and clean strategies
        cleaned_strategies = []
        for text in strategies:
            # Clean up whitespace
            cleaned = re.sub(r'\s+', ' ', text).strip()
            
            # Skip if too short
            if len(cleaned) < 30:
                continue
                
            # Check if this is a duplicate or very similar
            is_duplicate = False
            for existing in cleaned_strategies:
                if cleaned in existing or existing in cleaned:
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                cleaned_strategies.append(cleaned)
        
        # Limit to top 5 most relevant strategies
        return {
            "strategies": cleaned_strategies[:5],
            "ofsted_url": ofsted_url
        }
        
    except Exception as e:
        st.warning(f"Could not scrape school website: {e}")
        return {"strategies": [], "ofsted_url": None}

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
            "keywords": ["present information", "clarity", "clear explanation", "visual aids", "presentation", "display", "demonstrate"],
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
            "keywords": ["SEND", "special educational needs", "disabilities", "additional support", "differentiation", "inclusive", "inclusion", "SEN", "SENCO"],
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
            "keywords": ["reading", "phonics", "literacy", "books", "comprehension", "vocabulary", "fluency", "decoding", "text"],
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
            "keywords": ["curriculum", "subject knowledge", "planning", "sequencing", "knowledge building", "subject", "topics", "content", "national curriculum"],
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
            "keywords": ["staff training", "professional development", "CPD", "teacher skills", "support", "training", "staff", "teachers", "teaching assistants", "expertise"],
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
            "keywords": ["assessment", "feedback", "progress", "tracking", "monitoring", "evaluation", "marking", "testing", "formative", "summative"],
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
            "keywords": ["engagement", "motivation", "behavior", "attitude", "enjoyment", "interest", "participation", "attention", "focus", "concentration"],
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
            "keywords": ["technology", "digital", "ICT", "computing", "online", "internet", "e-safety", "digital literacy", "coding", "programming"],
            "title": "Enhancing Digital Technology Use",
            "solutions": [
                "1:1 iPad provision ensures consistent access to technology for all students",
                "Managed Apple IDs provide safe, controlled access to digital resources",
                "Classroom app allows teachers to guide student learning and monitor activity",
                "Shared iPad feature enables cost-effective device deployment",
                "Apple School Manager simplifies device management and app distribution"
            ],
            "standards": ["leadership", "devices"]
        },
        "mathematics": {
            "keywords": ["math", "maths", "mathematics", "numeracy", "calculation", "number", "arithmetic", "problem solving", "reasoning"],
            "title": "Strengthening Mathematics Teaching",
            "solutions": [
                "Interactive math apps provide visual representations of abstract concepts",
                "Adaptive learning platforms offer personalized practice at appropriate levels",
                "Augmented reality apps help visualize 3D shapes and geometric concepts",
                "Collaborative problem-solving tools encourage mathematical discussion",
                "Assessment apps provide immediate feedback on mathematical understanding"
            ],
            "standards": ["devices", "accessibility"]
        },
        "writing": {
            "keywords": ["writing", "composition", "grammar", "spelling", "punctuation", "handwriting", "creative writing", "editing", "drafting"],
            "title": "Improving Writing Skills",
            "solutions": [
                "Word processing apps with spell check and grammar support scaffold writing",
                "Voice-to-text features help students who struggle with transcription",
                "Digital portfolios allow students to track writing progress over time",
                "Collaborative writing tools enable peer feedback and editing",
                "Publishing tools motivate students by providing authentic audiences for writing"
            ],
            "standards": ["accessibility", "devices"]
        },
        "science": {
            "keywords": ["science", "scientific", "experiment", "investigation", "hypothesis", "biology", "chemistry", "physics", "nature"],
            "title": "Enhancing Science Learning",
            "solutions": [
                "Data collection apps enable scientific measurements and analysis",
                "Video recording allows detailed observation of experiments and phenomena",
                "Augmented reality apps bring scientific concepts to life",
                "Digital notebooks help students document scientific investigations",
                "Simulation apps allow exploration of concepts that are difficult to demonstrate physically"
            ],
            "standards": ["devices", "leadership"]
        },
        "early_years": {
            "keywords": ["early years", "EYFS", "foundation stage", "reception", "nursery", "play-based", "child-initiated", "early learning"],
            "title": "Supporting Early Years Learning",
            "solutions": [
                "Age-appropriate apps develop early literacy and numeracy skills through play",
                "Photo and video tools enable documentation of child-initiated learning",
                "Simple recording features support development of speaking and listening",
                "Accessibility features provide additional support for children with developmental delays",
                "Parent communication apps strengthen home-school partnerships"
            ],
            "standards": ["accessibility", "devices"]
        },
        "parental_engagement": {
            "keywords": ["parent", "parents", "family", "families", "home", "communication", "engage", "involvement", "partnership"],
            "title": "Strengthening Parental Engagement",
            "solutions": [
                "Digital portfolios allow parents to see student work and progress in real time",
                "Communication apps facilitate regular updates between school and home",
                "Translation features help engage parents who speak different languages",
                "Parent guides provide support for continuing learning at home",
                "Digital homework can increase parental understanding of curriculum content"
            ],
            "standards": ["leadership", "accessibility"]
        },
        "behavior_management": {
            "keywords": ["behavior", "behaviour", "discipline", "conduct", "rules", "expectations", "positive", "rewards", "consequences"],
            "title": "Improving Behavior Management",
            "solutions": [
                "Behavior tracking apps help identify patterns and triggers",
                "Digital reward systems provide immediate positive reinforcement",
                "Classroom management tools help teachers maintain focus and attention",
                "Timer and visual schedule apps support students with transitions",
                "Self-regulation apps help students develop emotional awareness and control"
            ],
            "standards": ["leadership", "accessibility"]
        },
        "remote_learning": {
            "keywords": ["remote", "distance", "home learning", "online learning", "virtual", "blended", "hybrid", "covid", "pandemic"],
            "title": "Enhancing Remote Learning Capabilities",
            "solutions": [
                "Seamless transition between in-school and at-home learning with the same device",
                "Video conferencing tools maintain face-to-face connection during remote learning",
                "Cloud-based storage ensures access to learning materials from anywhere",
                "Screen recording allows teachers to create instructional videos for asynchronous learning",
                "Digital submission tools simplify assignment collection and feedback during remote periods"
            ],
            "standards": ["leadership", "devices", "accessibility"]
        }
    }

# Load data
school_data_df = load_school_data()
dfe_standards = load_dfe_standards()
improvement_solutions = load_improvement_solutions()

# Function to search schools
def search_schools():
    query = st.session_state.search_input
    if not query or query.strip() == '':
        st.session_state.search_results = pd.DataFrame()
        st.session_state.search_performed = False
        return
    
    query = query.lower().strip()
    st.session_state.search_query = query
    
    try:
        # Search in the dataframe
        if school_data_df.empty:
            st.error("No school data available. Please ensure the National datasheet CSV is properly loaded.")
            st.session_state.search_results = pd.DataFrame()
            st.session_state.search_performed = True
            return
            
        results = school_data_df[
            school_data_df["EstablishmentName"].str.lower().str.contains(query, na=False) | 
            school_data_df["URN"].astype(str).str.contains(query, na=False) |
            school_data_df["Postcode"].str.lower().str.contains(query, na=False)
        ]
        
        st.session_state.search_results = results
        st.session_state.search_performed = True
    except Exception as e:
        st.error(f"Error searching schools: {e}")
        st.session_state.search_results = pd.DataFrame()
        st.session_state.search_performed = True

# Function to select school
def select_school(urn):
    if school_data_df.empty:
        st.error("No school data available. Please ensure the National datasheet CSV is properly loaded.")
        return
        
    try:
        # Find the selected school in the dataframe
        school_rows = school_data_df[school_data_df["URN"] == urn]
        
        if school_rows.empty:
            st.error(f"School with URN {urn} not found in the dataset.")
            return
            
        school_row = school_rows.iloc[0]
        
        # Create a dictionary with the school data
        school = {
            "urn": str(school_row["URN"]),
            "name": school_row["EstablishmentName"],
            "address": f"{school_row.get('Street', '')}, {school_row.get('Town', '')}, {school_row.get('Postcode', '')}",
            "type": school_row.get("TypeOfEstablishment (name)", ""),
            "phase": school_row.get("PhaseOfEducation (name)", ""),
            "pupils": school_row.get("NumberOfPupils", 0),
            "fsm": school_row.get("PercentageFSM", 0),
            "website": school_row.get("SchoolWebsite", "")
        }
        
        # Set default Ofsted URL (will be updated if found on website)
        school["ofstedUrl"] = get_default_ofsted_report_url(urn)
        
        # Reset priorities and strategies
        st.session_state.custom_priorities = []
        st.session_state.school_strategies = []
        st.session_state.ofsted_priorities = []
        st.session_state.website_data_fetched = False
        st.session_state.ofsted_url = None
        
        # Set the selected school in session state
        st.session_state.selected_school = school
        st.session_state.current_view = "profile"
    except Exception as e:
        st.error(f"Error selecting school: {e}")

# Function to fetch website data
def fetch_website_data():
    if st.session_state.selected_school and not st.session_state.website_data_fetched:
        website_url = st.session_state.selected_school.get("website", "")
        if website_url:
            with st.spinner(f"Fetching data from school website ({website_url})..."):
                try:
                    # Get strategies and Ofsted URL from website
                    result = scrape_school_website(website_url)
                    
                    # Update strategies
                    st.session_state.school_strategies = result["strategies"]
                    
                    # Update Ofsted URL if found
                    if result["ofsted_url"]:
                        st.session_state.ofsted_url = result["ofsted_url"]
                        st.session_state.selected_school["ofstedUrl"] = result["ofsted_url"]
                    
                    st.session_state.website_data_fetched = True
                    return True
                except Exception as e:
                    st.warning(f"Could not fetch website data: {e}")
                    st.session_state.website_data_fetched = True  # Mark as fetched to avoid repeated attempts
                    return False
    return False

# Function to add priority
def add_priority():
    if st.session_state.new_priority.strip():
        st.session_state.custom_priorities.append(st.session_state.new_priority)
        st.session_state.new_priority = ""  # Clear the input

# Function to add strategy
def add_strategy():
    if st.session_state.new_strategy.strip():
        st.session_state.school_strategies.append(st.session_state.new_strategy)
        st.session_state.new_strategy = ""  # Clear the input

# Function to add Ofsted priority
def add_ofsted_priority():
    if st.session_state.new_ofsted_priority.strip():
        st.session_state.ofsted_priorities.append(st.session_state.new_ofsted_priority)
        st.session_state.new_ofsted_priority = ""  # Clear the input

# Function to remove priority
def remove_priority(index):
    st.session_state.custom_priorities.pop(index)

# Function to remove strategy
def remove_strategy(index):
    st.session_state.school_strategies.pop(index)

# Function to remove Ofsted priority
def remove_ofsted_priority(index):
    st.session_state.ofsted_priorities.pop(index)

# Function to generate report
def generate_report():
    st.session_state.current_view = "report"

# Function to go back to search
def back_to_search():
    st.session_state.current_view = "search"

# Function to go back to profile
def back_to_profile():
    st.session_state.current_view = "profile"

# Enhanced function to match improvement areas to solutions with better context awareness
def match_improvement_areas_to_solutions(improvement_areas, school_context):
    if not improvement_areas:
        return []
        
    # Extract school phase and type for context-specific matching
    school_phase = school_context.get("phase", "").lower()
    school_type = school_context.get("type", "").lower()
    
    # Create a combined text of all improvement areas for better matching
    combined_text = " ".join(improvement_areas).lower()
    
    # Score each solution based on keyword matches and context relevance
    solution_scores = {}
    
    for key, solution in improvement_solutions.items():
        # Initialize score
        score = 0
        
        # Check each improvement area for keyword matches
        for area in improvement_areas:
            area_lower = area.lower()
            
            # Score based on keyword matches
            for keyword in solution["keywords"]:
                if keyword.lower() in area_lower:
                    score += 3  # Direct keyword match
            
            # Score based on title words in the area
            title_words = solution["title"].lower().split()
            for word in title_words:
                if len(word) > 3 and word in area_lower:  # Only consider significant words
                    score += 1
        
        # Context-specific scoring
        if "early_years" in key and ("early" in school_phase or "nursery" in school_phase or "foundation" in school_phase):
            score += 5  # Boost early years solutions for early years/primary schools
        
        if "reading_instruction" in key and ("primary" in school_phase or "elementary" in school_phase):
            score += 3  # Boost reading solutions for primary schools
        
        if "curriculum_implementation" in key and ("secondary" in school_phase or "high" in school_phase or "college" in school_type):
            score += 3  # Boost curriculum solutions for secondary schools
        
        # Store the score
        solution_scores[key] = score
    
    # Sort solutions by score (highest first)
    sorted_solutions = sorted(solution_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Take top scoring solutions (max 5)
    top_solutions = []
    for key, score in sorted_solutions:
        if score > 0 and len(top_solutions) < 5:  # Only include solutions with positive scores
            top_solutions.append({
                "title": improvement_solutions[key]["title"],
                "solutions": improvement_solutions[key]["solutions"],
                "standards": improvement_solutions[key]["standards"],
                "relevance": score  # Include the relevance score for reference
            })
    
    # If no specific matches found, add digital technology as default
    if not top_solutions:
        top_solutions.append({
            "title": improvement_solutions["digital_technology"]["title"],
            "solutions": improvement_solutions["digital_technology"]["solutions"],
            "standards": improvement_solutions["digital_technology"]["standards"],
            "relevance": 1
        })
    
    return top_solutions

# Function to display school profile
def display_school_profile(school):
    # Try to fetch website data if not already done
    fetch_website_data()
    
    st.markdown(f"<div class='card'>", unsafe_allow_html=True)
    
    # School header
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"<h2>{school['name']}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p>{school['address']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p>{school['phase']} | {school['type']}</p>", unsafe_allow_html=True)
        
        # Ofsted report link
        st.markdown(f"""
        <a href="{school['ofstedUrl']}" target="_blank" class="link-button">
            View Ofsted Report
        </a>
        """, unsafe_allow_html=True)
        
        # School website link if available
        if school.get('website'):
            st.markdown(f"""
            <a href="{school['website']}" target="_blank" class="link-button">
                Visit School Website
            </a>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h4>School Statistics</h4>", unsafe_allow_html=True)
        st.metric("Number of Pupils", school['pupils'])
        st.metric("FSM Percentage", f"{school['fsm']}%")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # School strategies from website
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>School Strategy & Priorities</h3>", unsafe_allow_html=True)
    st.markdown("<p>Strategies and priorities extracted from the school website:</p>", unsafe_allow_html=True)
    
    if st.session_state.website_data_fetched and not st.session_state.school_strategies:
        st.info("No strategy information found on the school website. You can add strategies manually below.")
    
    # Display existing strategies
    if st.session_state.school_strategies:
        for i, strategy in enumerate(st.session_state.school_strategies):
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"<div class='strategy-area'>{strategy}</div>", unsafe_allow_html=True)
            with col2:
                st.button("Remove", key=f"remove_strategy_{i}", on_click=remove_strategy, args=(i,))
    
    # Input for new strategy
    col1, col2 = st.columns([4, 1])
    with col1:
        st.text_input("Enter school strategy or priority...", key="new_strategy")
    with col2:
        st.button("Add Strategy", key="add_strategy_button", on_click=add_strategy)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Ofsted improvement areas
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Ofsted Areas for Improvement</h3>", unsafe_allow_html=True)
    st.markdown("<p>Enter improvement areas from the school's Ofsted report:</p>", unsafe_allow_html=True)
    
    # Display existing Ofsted priorities
    if st.session_state.ofsted_priorities:
        for i, priority in enumerate(st.session_state.ofsted_priorities):
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"<div class='improvement-area'>{priority}</div>", unsafe_allow_html=True)
            with col2:
                st.button("Remove", key=f"remove_ofsted_{i}", on_click=remove_ofsted_priority, args=(i,))
    
    # Input for new Ofsted priority
    col1, col2 = st.columns([4, 1])
    with col1:
        st.text_input("Enter Ofsted improvement area...", key="new_ofsted_priority")
    with col2:
        st.button("Add Ofsted Area", key="add_ofsted_button", on_click=add_ofsted_priority)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Custom priorities
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Additional School Priorities</h3>", unsafe_allow_html=True)
    st.markdown("<p>Add any additional school priorities not captured above:</p>", unsafe_allow_html=True)
    
    # Display existing priorities
    if st.session_state.custom_priorities:
        for i, priority in enumerate(st.session_state.custom_priorities):
            col1, col2 = st.columns([6, 1])
            with col1:
                st.markdown(f"<div class='priority-area'>{priority}</div>", unsafe_allow_html=True)
            with col2:
                st.button("Remove", key=f"remove_priority_{i}", on_click=remove_priority, args=(i,))
    
    # Input for new priority
    col1, col2 = st.columns([4, 1])
    with col1:
        st.text_input("Enter additional priority...", key="new_priority")
    with col2:
        st.button("Add Priority", key="add_priority_button", on_click=add_priority)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Generate report button
    st.button("Generate Report", key="generate_report_button", on_click=generate_report)

# Function to display report
def display_report(school):
    # Combine all priorities and strategies
    all_improvement_areas = (
        st.session_state.ofsted_priorities + 
        st.session_state.school_strategies + 
        st.session_state.custom_priorities
    )
    
    # If no areas provided, show a message
    if not all_improvement_areas:
        st.warning("No improvement areas or strategies have been added. Please go back and add some priorities or strategies to generate a meaningful report.")
        st.button("Back to School Profile", key="back_to_profile_empty", on_click=back_to_profile)
        return
    
    # Create school context for better matching
    school_context = {
        "name": school['name'],
        "phase": school['phase'],
        "type": school['type'],
        "pupils": school['pupils'],
        "fsm": school['fsm']
    }
    
    # Match improvement areas to solutions with context awareness
    matched_solutions = match_improvement_areas_to_solutions(all_improvement_areas, school_context)
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    
    # Report header
    st.markdown(f"<h1>iPad Implementation Report</h1>", unsafe_allow_html=True)
    st.markdown(f"<h2>{school['name']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p>{school['address']}</p>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Executive Summary
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Executive Summary</h3>", unsafe_allow_html=True)
    
    # Create a more personalized executive summary
    fsm_context = ""
    if school['fsm'] > 35:
        fsm_context = f"with a high proportion of pupils eligible for Free School Meals ({school['fsm']}%)"
    elif school['fsm'] > 20:
        fsm_context = f"with {school['fsm']}% of pupils eligible for Free School Meals"
    
    size_context = ""
    if school['pupils'] > 500:
        size_context = "large"
    elif school['pupils'] < 200:
        size_context = "small"
    
    # Create a summary of key improvement areas
    area_summary = ""
    if st.session_state.ofsted_priorities:
        area_summary += "Ofsted improvement areas"
        if st.session_state.school_strategies or st.session_state.custom_priorities:
            area_summary += ", "
    
    if st.session_state.school_strategies:
        area_summary += "strategic priorities from the school website"
        if st.session_state.custom_priorities:
            area_summary += ", "
    
    if st.session_state.custom_priorities:
        area_summary += "and additional school priorities"
    
    st.markdown(f"""
    <p>This report outlines how implementing 1:1 iPads at {school['name']} can address the specific challenges and priorities 
    identified in the {area_summary} while meeting the Department for Education's technology standards for digital leadership, 
    accessibility, and devices.</p>
    
    <p>The recommendations are tailored to the specific context of {school['name']} as a {size_context} {school['phase'].lower()} school
    {fsm_context}, with a focus on how iPad technology can support the school's unique improvement journey.</p>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Key Improvement Areas
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Key Improvement Areas</h3>", unsafe_allow_html=True)
    
    # Separate areas by type
    if st.session_state.ofsted_priorities:
        st.markdown("<h4>From Ofsted Report:</h4>", unsafe_allow_html=True)
        for area in st.session_state.ofsted_priorities:
            st.markdown(f"<div class='improvement-area'>{area}</div>", unsafe_allow_html=True)
    
    if st.session_state.school_strategies:
        st.markdown("<h4>From School Strategy:</h4>", unsafe_allow_html=True)
        for area in st.session_state.school_strategies:
            st.markdown(f"<div class='strategy-area'>{area}</div>", unsafe_allow_html=True)
    
    if st.session_state.custom_priorities:
        st.markdown("<h4>Additional Priorities:</h4>", unsafe_allow_html=True)
        for area in st.session_state.custom_priorities:
            st.markdown(f"<div class='priority-area'>{area}</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # iPad Implementation Recommendations
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>iPad Implementation Recommendations</h3>", unsafe_allow_html=True)
    
    # Create personalized recommendations for each solution
    for solution in matched_solutions:
        with st.expander(solution["title"]):
            # Add context about why this solution is relevant to the school
            relevant_areas = []
            for area in all_improvement_areas:
                area_lower = area.lower()
                if any(keyword.lower() in area_lower for keyword in improvement_solutions[next(k for k, v in improvement_solutions.items() if v["title"] == solution["title"])]["keywords"]):
                    relevant_areas.append(area)
            
            if relevant_areas:
                st.markdown("**Relevant to your priorities:**")
                for area in relevant_areas[:2]:  # Show up to 2 most relevant areas
                    st.markdown(f"- *\"{area}\"*")
                st.markdown("")
            
            # Show the solutions with school context
            for item in solution["solutions"]:
                # Replace generic terms with school-specific ones where appropriate
                personalized_item = item
                if "primary" in school['phase'].lower():
                    personalized_item = personalized_item.replace("students", "pupils")
                
                st.markdown(f"- {personalized_item}")
            
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
        st.markdown("<h5>How 1:1 iPads Support This Standard at Your School:</h5>", unsafe_allow_html=True)
        for benefit in dfe_standards['leadership']['ipad_benefits']:
            # Personalize the benefit with school context
            personalized_benefit = benefit
            if "primary" in school['phase'].lower():
                personalized_benefit = personalized_benefit.replace("students", "pupils")
            
            st.markdown(f"- {personalized_benefit}")
    
    with tabs[1]:
        st.markdown(f"<h4>{dfe_standards['accessibility']['title']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p>{dfe_standards['accessibility']['description']}</p>", unsafe_allow_html=True)
        st.markdown("<h5>How 1:1 iPads Support This Standard at Your School:</h5>", unsafe_allow_html=True)
        for benefit in dfe_standards['accessibility']['ipad_benefits']:
            # Personalize the benefit with school context
            personalized_benefit = benefit
            if "primary" in school['phase'].lower():
                personalized_benefit = personalized_benefit.replace("students", "pupils")
            
            st.markdown(f"- {personalized_benefit}")
    
    with tabs[2]:
        st.markdown(f"<h4>{dfe_standards['devices']['title']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p>{dfe_standards['devices']['description']}</p>", unsafe_allow_html=True)
        st.markdown("<h5>How 1:1 iPads Support This Standard at Your School:</h5>", unsafe_allow_html=True)
        for benefit in dfe_standards['devices']['ipad_benefits']:
            # Personalize the benefit with school context
            personalized_benefit = benefit
            if "primary" in school['phase'].lower():
                personalized_benefit = personalized_benefit.replace("students", "pupils")
            
            st.markdown(f"- {personalized_benefit}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Implementation Considerations - Personalized for the school
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Implementation Considerations for Your School</h3>", unsafe_allow_html=True)
    
    with st.expander("Professional Development"):
        # Personalize based on school size
        if school['pupils'] > 500:
            st.markdown(f"""
            For a school of {school['name']}'s size ({school['pupils']} pupils), a phased approach to staff training is recommended. 
            Begin with a core team of digital champions who can then support colleagues. The Apple Teacher 
            professional learning program provides structured support for educators at all levels of technical confidence.
            """)
        else:
            st.markdown(f"""
            For a smaller school like {school['name']} ({school['pupils']} pupils), whole-staff training sessions can be effective. 
            The Apple Teacher professional learning program provides structured support for educators at all levels of 
            technical confidence, with resources specifically designed for {school['phase'].lower()} settings.
            """)
    
    with st.expander("Technical Infrastructure"):
        # Personalize based on FSM percentage (as a proxy for potential funding challenges)
        if school['fsm'] > 30:
            st.markdown(f"""
            Given {school['name']}'s FSM percentage of {school['fsm']}%, you may be eligible for additional funding or support 
            for infrastructure improvements. A technical audit should be conducted to ensure the Wi-Fi network can support 
            simultaneous connections from all devices. Consider a phased approach to implementation to manage costs effectively.
            """)
        else:
            st.markdown(f"""
            Robust Wi-Fi coverage throughout {school['name']} is essential for effective iPad implementation. A technical audit 
            should be conducted to ensure the network can support simultaneous connections from all devices, particularly 
            in areas where multiple classes may be using devices simultaneously.
            """)
    
    with st.expander("Deployment Strategy"):
        # Personalize based on school phase
        if "primary" in school['phase'].lower():
            st.markdown(f"""
            For {school['name']} as a {school['phase']} school, consider a year-group by year-group rollout starting with 
            upper KS2 classes, followed by lower KS2 and then KS1. This allows for evaluation and refinement of implementation 
            strategies before full-school deployment. Shared iPad deployments can be effective for younger year groups.
            """)
        elif "secondary" in school['phase'].lower():
            st.markdown(f"""
            For {school['name']} as a {school['phase']} school, consider a subject-based or year-group rollout starting with 
            departments that align with your improvement priorities. This allows for evaluation and refinement of implementation 
            strategies before full-school deployment. A BYOD (Bring Your Own Device) policy could be considered for older students.
            """)
        else:
            st.markdown(f"""
            Consider a phased rollout at {school['name']} starting with specific year groups or departments that align with your 
            improvement priorities. This allows for evaluation and refinement of implementation strategies before full-school deployment.
            """)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Conclusion - Personalized for the school
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3>Conclusion</h3>", unsafe_allow_html=True)
    
    # Create a personalized conclusion based on the school's context and priorities
    priority_themes = []
    for area in all_improvement_areas:
        area_lower = area.lower()
        if "curriculum" in area_lower or "subject" in area_lower:
            if "curriculum" not in priority_themes:
                priority_themes.append("curriculum")
        if "reading" in area_lower or "literacy" in area_lower:
            if "literacy" not in priority_themes:
                priority_themes.append("literacy")
        if "send" in area_lower or "special" in area_lower or "need" in area_lower:
            if "inclusion" not in priority_themes:
                priority_themes.append("inclusion")
        if "staff" in area_lower or "teacher" in area_lower or "cpd" in area_lower:
            if "staff development" not in priority_themes:
                priority_themes.append("staff development")
    
    priority_text = ""
    if priority_themes:
        priority_text = "particularly in the areas of " + ", ".join(priority_themes[:-1])
        if len(priority_themes) > 1:
            priority_text += " and "
        priority_text += priority_themes[-1]
    
    st.markdown(f"""
    <p>Implementing 1:1 iPads at {school['name']} would directly address the specific improvement areas identified 
    in your school's priorities {priority_text}. The recommendations in this report are tailored to your context 
    as a {school['phase'].lower()} school with {school['pupils']} pupils.</p>
    
    <p>The versatility, reliability, and built-in accessibility features of iPads make them an ideal platform 
    to support teaching and learning across the curriculum, while meeting the DfE's technology standards for 
    leadership, accessibility, and devices.</p>
    
    <p>By implementing these recommendations, {school['name']} can enhance teaching and learning experiences, 
    support staff in delivering the curriculum effectively, and provide pupils with the digital skills they 
    need for future success.</p>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        st.button("Back to School Profile", key="back_to_profile_button", on_click=back_to_profile)
    with col2:
        # Simple text download instead of PDF
        report_text = f"""
        # iPad Implementation Report for {school['name']}
        
        ## School Details
        - Name: {school['name']}
        - Address: {school['address']}
        - Type: {school['type']}
        - Phase: {school['phase']}
        - Pupils: {school['pupils']}
        - FSM: {school['fsm']}%
        - Ofsted Report: {school['ofstedUrl']}
        - School Website: {school.get('website', 'Not available')}
        
        ## Executive Summary
        This report outlines how implementing 1:1 iPads at {school['name']} can address the specific challenges and priorities 
        identified in the {area_summary} while meeting the Department for Education's technology standards for digital leadership, 
        accessibility, and devices.
        
        The recommendations are tailored to the specific context of {school['name']} as a {size_context} {school['phase'].lower()} school
        {fsm_context}, with a focus on how iPad technology can support the school's unique improvement journey.
        
        ## Key Improvement Areas
        """
        
        # Add Ofsted priorities
        if st.session_state.ofsted_priorities:
            report_text += "\n### From Ofsted Report:\n"
            report_text += chr(10).join(['- ' + area for area in st.session_state.ofsted_priorities])
            report_text += "\n"
        
        # Add school strategies
        if st.session_state.school_strategies:
            report_text += "\n### From School Strategy:\n"
            report_text += chr(10).join(['- ' + area for area in st.session_state.school_strategies])
            report_text += "\n"
        
        # Add custom priorities
        if st.session_state.custom_priorities:
            report_text += "\n### Additional Priorities:\n"
            report_text += chr(10).join(['- ' + area for area in st.session_state.custom_priorities])
            report_text += "\n"
        
        # Add solutions
        report_text += "\n## iPad Implementation Recommendations\n"
        
        for solution in matched_solutions:
            report_text += f"### {solution['title']}\n"
            
            # Add relevant priorities
            relevant_areas = []
            for area in all_improvement_areas:
                area_lower = area.lower()
                if any(keyword.lower() in area_lower for keyword in improvement_solutions[next(k for k, v in improvement_solutions.items() if v["title"] == solution["title"])]["keywords"]):
                    relevant_areas.append(area)
            
            if relevant_areas:
                report_text += "Relevant to your priorities:\n"
                for area in relevant_areas[:2]:
                    report_text += f"- \"{area}\"\n"
                report_text += "\n"
            
            # Add solutions
            for item in solution["solutions"]:
                personalized_item = item
                if "primary" in school['phase'].lower():
                    personalized_item = personalized_item.replace("students", "pupils")
                report_text += f"- {personalized_item}\n"
            
            report_text += "\nRelevant DfE Standards:\n"
            for standard in solution["standards"]:
                report_text += f"- {dfe_standards[standard]['title']}\n"
            
            report_text += "\n"
        
        # Add standards
        report_text += "\n## Alignment with DfE Technology Standards\n"
        
        report_text += "\n### Digital Leadership and Governance Standards\n"
        report_text += chr(10).join(['- ' + benefit for benefit in dfe_standards['leadership']['ipad_benefits']])
        
        report_text += "\n\n### Digital Accessibility Standards\n"
        report_text += chr(10).join(['- ' + benefit for benefit in dfe_standards['accessibility']['ipad_benefits']])
        
        report_text += "\n\n### Device Standards\n"
        report_text += chr(10).join(['- ' + benefit for benefit in dfe_standards['devices']['ipad_benefits']])
        
        # Add implementation considerations
        report_text += "\n\n## Implementation Considerations for Your School\n"
        
        report_text += "\n### Professional Development\n"
        if school['pupils'] > 500:
            report_text += f"For a school of {school['name']}'s size ({school['pupils']} pupils), a phased approach to staff training is recommended. "
            report_text += "Begin with a core team of digital champions who can then support colleagues. The Apple Teacher "
            report_text += "professional learning program provides structured support for educators at all levels of technical confidence."
        else:
            report_text += f"For a smaller school like {school['name']} ({school['pupils']} pupils), whole-staff training sessions can be effective. "
            report_text += "The Apple Teacher professional learning program provides structured support for educators at all levels of "
            report_text += f"technical confidence, with resources specifically designed for {school['phase'].lower()} settings."
        
        report_text += "\n\n### Technical Infrastructure\n"
        if school['fsm'] > 30:
            report_text += f"Given {school['name']}'s FSM percentage of {school['fsm']}%, you may be eligible for additional funding or support "
            report_text += "for infrastructure improvements. A technical audit should be conducted to ensure the Wi-Fi network can support "
            report_text += "simultaneous connections from all devices. Consider a phased approach to implementation to manage costs effectively."
        else:
            report_text += f"Robust Wi-Fi coverage throughout {school['name']} is essential for effective iPad implementation. A technical audit "
            report_text += "should be conducted to ensure the network can support simultaneous connections from all devices, particularly "
            report_text += "in areas where multiple classes may be using devices simultaneously."
        
        report_text += "\n\n### Deployment Strategy\n"
        if "primary" in school['phase'].lower():
            report_text += f"For {school['name']} as a {school['phase']} school, consider a year-group by year-group rollout starting with "
            report_text += "upper KS2 classes, followed by lower KS2 and then KS1. This allows for evaluation and refinement of implementation "
            report_text += "strategies before full-school deployment. Shared iPad deployments can be effective for younger year groups."
        elif "secondary" in school['phase'].lower():
            report_text += f"For {school['name']} as a {school['phase']} school, consider a subject-based or year-group rollout starting with "
            report_text += "departments that align with your improvement priorities. This allows for evaluation and refinement of implementation "
            report_text += "strategies before full-school deployment. A BYOD (Bring Your Own Device) policy could be considered for older students."
        else:
            report_text += f"Consider a phased rollout at {school['name']} starting with specific year groups or departments that align with your "
            report_text += "improvement priorities. This allows for evaluation and refinement of implementation strategies before full-school deployment."
        
        # Add conclusion
        report_text += "\n\n## Conclusion\n"
        report_text += f"Implementing 1:1 iPads at {school['name']} would directly address the specific improvement areas identified "
        report_text += f"in your school's priorities {priority_text}. The recommendations in this report are tailored to your context "
        report_text += f"as a {school['phase'].lower()} school with {school['pupils']} pupils.\n\n"
        report_text += "The versatility, reliability, and built-in accessibility features of iPads make them an ideal platform "
        report_text += "to support teaching and learning across the curriculum, while meeting the DfE's technology standards for "
        report_text += "leadership, accessibility, and devices.\n\n"
        report_text += f"By implementing these recommendations, {school['name']} can enhance teaching and learning experiences, "
        report_text += "support staff in delivering the curriculum effectively, and provide pupils with the digital skills they "
        report_text += "need for future success."
        
        st.download_button(
            "Download Report as Text",
            report_text,
            file_name=f"{school['name']}_iPad_Implementation_Report.txt",
            mime="text/plain",
            key="download_report_button"
        )

# Main application logic
def main():
    # App header
    st.markdown("<h1 style='text-align: center;'>School iPad Implementation Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Create customized reports showing how 1:1 iPads can address school priorities while meeting DfE technology standards.</p>", unsafe_allow_html=True)
    
    # Sidebar for navigation and settings
    with st.sidebar:
        st.markdown("<h3>Navigation</h3>", unsafe_allow_html=True)
        
        if st.button("Search Schools", key="nav_search"):
            st.session_state.current_view = "search"
        
        if st.session_state.selected_school:
            if st.button("View School Profile", key="nav_profile"):
                st.session_state.current_view = "profile"
            
            if st.button("Generate Report", key="nav_report"):
                st.session_state.current_view = "report"
        
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>About</h3>", unsafe_allow_html=True)
        st.markdown("""
        This dashboard helps schools create customized reports showing how 1:1 iPads can address their specific priorities while meeting DfE technology standards for:
        
        - Digital Leadership and Governance
        - Digital Accessibility
        - Device Standards
        
        The dashboard combines information from:
        - School websites
        - Ofsted reports (via links)
        - Your own input on school priorities
        """)
    
    # Main content area based on current view
    if st.session_state.current_view == "search":
        # Search interface
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h2>Search for a School</h2>", unsafe_allow_html=True)
        
        # Check if data is loaded
        if school_data_df.empty:
            st.error("National datasheet CSV file not found or empty. Please ensure the file is uploaded correctly.")
        else:
            st.text_input("Enter school name, URN, or postcode", key="search_input")
            
            if st.button("Search", key="search_button"):
                search_schools()
            
            # Display search results if search was performed
            if st.session_state.search_performed:
                results = st.session_state.search_results
                
                if len(results) > 0:
                    st.markdown(f"<p>Found {len(results)} schools matching your search.</p>", unsafe_allow_html=True)
                    
                    try:
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
                            
                            if st.button("View School Profile", key="view_profile_button"):
                                select_school(selected_urn)
                    except Exception as e:
                        st.error(f"Error displaying search results: {e}")
                else:
                    st.warning("No schools found matching your search criteria.")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    elif st.session_state.current_view == "profile" and st.session_state.selected_school:
        # Display back button
        if st.button("← Back to Search", key="back_to_search_button"):
            st.session_state.current_view = "search"
        
        # Display school profile
        display_school_profile(st.session_state.selected_school)
    
    elif st.session_state.current_view == "report" and st.session_state.selected_school:
        # Display report
        display_report(st.session_state.selected_school)

# Run the app
if __name__ == "__main__":
    main()
