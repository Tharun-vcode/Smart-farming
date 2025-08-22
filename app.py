import streamlit as st
import json
import os
import hashlib
import requests
import pandas as pd
import altair as alt
from datetime import datetime
from groq import Groq
from twilio.rest import Client
import tempfile
import os
from groq import Groq
#from googletrans import Translator
import time
import pickle
import torch
from PIL import Image
from transformers import AutoModelForImageClassification, AutoImageProcessor
# -----------------------------
# CONFIG
# -----------------------------
USER_DB_FILE = "users.json"
API_KEY = "API_KEY"  # <-- replace with your OpenWeather API key

# -----------------------------
# UTIL: password hash
# -----------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# -----------------------------
# USER DATA FUNCTIONS (with auto-upgrade)
# -----------------------------
def load_users():
    """Load users from JSON and auto-upgrade old string-hash format to dict format."""
    if not os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "w") as f:
            json.dump({}, f)
    with open(USER_DB_FILE, "r") as f:
        try:
            users = json.load(f)
        except json.JSONDecodeError:
            users = {}
    upgraded = False
    for uname, udata in list(users.items()):
        if isinstance(udata, str):
            # old format: username -> password_hash
            users[uname] = {"password": udata, "default_city": None}
            upgraded = True
        elif isinstance(udata, dict):
            # ensure keys exist
            if "password" not in udata:
                users[uname]["password"] = ""
                upgraded = True
            if "default_city" not in udata:
                users[uname]["default_city"] = None
                upgraded = True
    if upgraded:
        save_users(users)
    return users

def save_users(users: dict):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f, indent=2)

# -----------------------------
# AUTH: signup & login (backwards compatible)
# -----------------------------
def signup():
    # Custom CSS
    st.markdown("""
        <style>
        /* Signup box */
        .signup-box {
            background: linear-gradient(145deg, #f1f8e9, #e8f5e9);
            padding: 30px 40px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            max-width: 400px;
            margin: auto;
            margin-top: 30px;
        }

        /* Title */
        .signup-title {
            font-size: 26px !important;
            font-weight: bold;
            color: #2d6a4f;
            text-align: center;
            margin-bottom: 20px;
        }

        /* Inputs */
        input {
            border-radius: 8px !important;
            border: 1px solid #ccc !important;
            padding: 10px !important;
        }

        /* Button */
        div.stButton > button {
            width: 100%;
            border-radius: 10px;
            height: 3em;
            background-color: #2d6a4f;
            color: white;
            font-size: 16px;
            font-weight: bold;
            border: none;
            transition: 0.3s;
        }
        div.stButton > button:hover {
            background-color: #40916c;
            transform: scale(1.02);
        }
        </style>
    """, unsafe_allow_html=True)

    # Signup card
    st.markdown('<div class="signup-box">', unsafe_allow_html=True)
    st.markdown('<p class="signup-title">📝 Farmer Signup</p>', unsafe_allow_html=True)

    new_username = st.text_input("👤 Choose a username", key="signup_user")
    new_password = st.text_input("🔑 Choose a password", type="password", key="signup_pass")
    confirm_password = st.text_input("🔐 Confirm password", type="password", key="signup_confirm")

    if st.button("Create Account", key="signup_btn"):
        if not new_username:
            st.warning("⚠ Please enter a username.")
            return
        if new_password != confirm_password:
            st.warning("⚠ Passwords do not match.")
            return

        users = load_users()
        if new_username in users:
            st.warning("⚠ Username already exists. Pick another one.")
            return

        users[new_username] = {"password": hash_password(new_password), "default_city": None}
        save_users(users)
        st.success("✅ Account created successfully! You can now log in.")

    st.markdown('</div>', unsafe_allow_html=True)
def login():
    st.markdown("""
        <style>
        /* Background */
        .stApp {
            background-color: #f4f9f4;
            font-family: 'Segoe UI', sans-serif;
        }

        /* Title */
        .title {
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            color: #2d6a4f;
            margin-bottom: 20px;
        }

        /* Login card */
        .login-card {
            background: white;
            padding: 30px 40px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            max-width: 400px;
            margin: auto;
        }

        /* Inputs */
        input {
            border-radius: 8px !important;
            border: 1px solid #ccc !important;
            padding: 10px !important;
        }

        /* Button */
        div.stButton > button {
            width: 100%;
            border-radius: 10px;
            height: 3em;
            background-color: #2d6a4f;
            color: white;
            font-size: 16px;
            font-weight: bold;
            border: none;
            transition: 0.3s;
        }
        div.stButton > button:hover {
            background-color: #40916c;
            transform: scale(1.02);
        }
        </style>
    """, unsafe_allow_html=True)

    # UI layout
    #st.markdown('<div class="title">🌱 CROPCARE - Smart Farming Assistant</div>', unsafe_allow_html=True)

    # Login card
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.subheader("🔐 Farmer Login")

    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    if st.button("Login", key="login_btn"):
        if not username:
            st.error("⚠ Enter username.")
        else:
            users = load_users()
            if username in users:
                user_data = users[username]

                # handle old format
                if isinstance(user_data, str):
                    user_data = {"password": user_data, "default_city": None}
                    users[username] = user_data
                    save_users(users)

                if user_data.get("password") == hash_password(password):
                    st.session_state["user"] = username
                    st.session_state["city"] = user_data.get("default_city", "")
                    st.success(f"✅ Welcome, {username}!")
                else:
                    st.error("❌ Invalid credentials.")
            else:
                st.error("❌ Invalid credentials.")

    st.markdown('</div>', unsafe_allow_html=True)

# MAIN APP
# -----------------------------

# -----------------------------
# FORUM FUNCTIONS

# -----------------------------
# FORUM FUNCTIONS (with photo upload)
# -----------------------------
FORUM_DB_FILE = "forum.json"
IMAGE_DIR = "forum_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

def load_forum():
    """Load forum data safely, reset if file is corrupted."""
    if not os.path.exists(FORUM_DB_FILE):
        with open(FORUM_DB_FILE, "w") as f:
            json.dump({"posts": []}, f)

    try:
        with open(FORUM_DB_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        st.warning("⚠ Forum data was corrupted. Resetting to empty.")
        with open(FORUM_DB_FILE, "w") as f:
            json.dump({"posts": []}, f)
        return {"posts": []}

def save_forum(data):
    with open(FORUM_DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def save_image_file(uploaded_file):
    """Save uploaded image to local folder and return filename."""
    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1]
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{ext}"
        filepath = os.path.join(IMAGE_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getvalue())
        return filename
    return None

def discussion_forum_ui():
    st.subheader("👨‍🌾 Farmer Discussion Forum")
    forum_data = load_forum()

    st.markdown("### 📢 Join the Forum")
    if st.checkbox("I agree to participate respectfully and help fellow farmers."):
        st.session_state["joined_forum"] = True

    if not st.session_state.get("joined_forum"):
        st.info("Please agree above to participate in the discussion forum.")
        return

    st.markdown("### 📝 Ask a Question")
    question = st.text_input("Enter your question")
    tag = st.selectbox("Select a tag", ["General", "Pest", "Irrigation", "Weather", "Soil", "Harvest"])
    q_image = st.file_uploader("Upload an image for your question (optional)", type=["jpg", "jpeg", "png"])

    if st.button("Post Question"):
        if question:
            image_filename = save_image_file(q_image)
            forum_data["posts"].append({
                "user": st.session_state["user"],
                "question": question,
                "tag": tag,
                "timestamp": datetime.now().isoformat(),
                "image": image_filename,
                "replies": []
            })
            save_forum(forum_data)
            st.success("Question posted!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 💬 Questions and Replies")

    sort_option = st.radio("Sort questions by", ["Latest", "Most Replies"], horizontal=True)
    if sort_option == "Latest":
        sorted_posts = sorted(forum_data["posts"], key=lambda x: x["timestamp"], reverse=True)
    else:
        sorted_posts = sorted(forum_data["posts"], key=lambda x: len(x["replies"]), reverse=True)

    for i, post in enumerate(sorted_posts):
        st.markdown(f"**Q{i+1}. {post['question']}** — _by {post['user']}_ 🏷️ *{post['tag']}*")
        if post.get("image"):
            img_path = os.path.join(IMAGE_DIR, post["image"])
            if os.path.exists(img_path):
                st.image(img_path, width=300)

        for reply in post["replies"]:
            st.markdown(f"> 💬 {reply['reply']} — _{reply['user']}_")
            if reply.get("image"):
                img_path = os.path.join(IMAGE_DIR, reply["image"])
                if os.path.exists(img_path):
                    st.image(img_path, width=250)

        with st.expander("Reply"):
            reply_text = st.text_input(f"Your reply to Q{i+1}", key=f"reply_{i}")
            r_image = st.file_uploader(
                f"Upload an image for your reply (optional) to Q{i+1}",
                type=["jpg", "jpeg", "png"],
                key=f"reply_img_{i}"
            )
            if st.button("Submit Reply", key=f"reply_btn_{i}"):
                if reply_text:
                    image_filename = save_image_file(r_image)
                    post["replies"].append({
                        "user": st.session_state["user"],
                        "reply": reply_text,
                        "image": image_filename,
                        "timestamp": datetime.now().isoformat()
                    })
                    save_forum(forum_data)
                    st.success("Reply added!")
                    st.rerun()

def disease_detection_ui():
    st.title("🌿 Plant Disease Detection")
    st.subheader("Upload a leaf image to detect plant diseases")

    # Initialize Groq client
    client = Groq(api_key="API_KEY")  # replace with your Groq API key

    @st.cache_resource
    def load_model():
        processor = AutoImageProcessor.from_pretrained(
            "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
        )
        model = AutoModelForImageClassification.from_pretrained(
            "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
        )
        return processor, model

    processor, model = load_model()

    uploaded_file = st.file_uploader("📤 Upload a leaf image", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Uploaded Leaf", use_column_width=True)

        # Preprocess & Predict
        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            predicted_idx = logits.argmax(-1).item()
            label = model.config.id2label[predicted_idx]

        st.subheader(f"Prediction: **{label}**")

        # Generate remedy using Groq
        with st.spinner("🧪 Analyzing disease and generating remedy..."):
            prompt = f"Provide a concise 2-3 sentence remedy and few points related to it for plant disease: {label}. Only give the remedy, no introduction or conclusion."
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are a plant disease expert. Provide short, practical remedies."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            remedy = response.choices[0].message.content

        st.write("✅ *Recommended Remedy:*")
        st.info(remedy)

def home_ui():
    # Page config
    st.set_page_config(
        page_title="   CropCare",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for styling
    st.markdown("""
    <style>
        .header {
            font-size: 50px !important;
            font-weight: 700 !important;
            color: #2e8b57 !important;
            text-align: center;
            margin-bottom: 30px !important;
        }
        .subheader {
            font-size: 24px !important;
            color: #3a7d44 !important;
            text-align: center;
            margin-bottom: 40px !important;
        }
        .feature-card {
            padding: 25px;
            border-radius: 15px;
            background: linear-gradient(145deg, #f0fff0, #e6f6e6);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            border-left: 5px solid #2e8b57;
        }
        .feature-title {
            font-size: 22px !important;
            font-weight: 600 !important;
            color: #2e8b57 !important;
            margin-bottom: 15px !important;
        }
        .feature-icon {
            font-size: 30px !important;
            margin-right: 10px !important;
            vertical-align: middle !important;
        }
        .welcome-text {
            font-size: 18px !important;
            line-height: 1.6 !important;
            text-align: center;
            margin-bottom: 40px !important;
            color: #333 !important;
        }
        .divider {
            border-top: 2px dashed #2e8b57;
            margin: 30px 0;
            opacity: 0.5;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header section
    st.markdown('<p class="header">🚜 Grow Smarter, Not Harder!</p>', unsafe_allow_html=True)
    st.markdown('<p class="subheader">Smart Agricultural Solutions Powered by AI</p>', unsafe_allow_html=True)

    # Welcome text
    st.markdown("""
    <p class="welcome-text">
        Empower your farming with our AI-powered tools designed to help you identify plant diseases 
        and get expert farming advice instantly. Our solutions combine cutting-edge technology with 
        practical agricultural knowledge.
    </p>
    """, unsafe_allow_html=True)

    # Create columns for feature cards
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title"><span class="feature-icon">🧪</span> Soil Health Monitoring</div>
            <p>Monitor soil quality using real-time sensor data and AI-powered insights.</p>
            <ul>
                <li>Check soil moisture, pH, and EC</li>
                <li>Get soil health score instantly</li>
                <li>Fertilizer recommendations</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title"><span class="feature-icon">🌿</span> Plant Disease Detection</div>
            <p>Upload an image of your plant leaves to instantly detect potential diseases and get treatment recommendations.</p>
            <ul>
                <li>Fast and accurate diagnosis</li>
                <li>Visual identification of symptoms</li>
                <li>Immediate action steps</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    col3, col4 = st.columns(2, gap="large")

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title"><span class="feature-icon">🤖</span> AI Farmer Chatbot</div>
            <p>Get instant expert advice on all farming topics from crop selection to pest control.</p>
            <ul>
                <li>24/7 farming assistance</li>
                <li>Personalized recommendations</li>
                <li>Latest agricultural knowledge</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title"><span class="feature-icon">💬</span> Discussion Forum</div>
            <p>Connect with fellow farmers to ask questions, share tips, and learn together.</p>
            <ul>
                <li>Post your farming questions</li>
                <li>Upload crop/pest images</li>
                <li>Get replies from the community</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    col5, col6 = st.columns(2, gap="large")

    with col5:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title"><span class="feature-icon">💧</span> Irrigation Control (ML + SMS)</div>
            <p>AI predicts irrigation needs and notifies you via SMS for efficient water usage.</p>
            <ul>
                <li>Smart irrigation predictions</li>
                <li>Water-saving recommendations</li>
                <li>SMS alerts for farmers</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title"><span class="feature-icon">🏛</span> Government Schemes</div>
            <p>Explore the latest government schemes and support available for farmers.</p>
            <ul>
                <li>Verified scheme details</li>
                <li>Eligibility information</li>
                <li>Direct links to apply</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


    # Divider
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)



    # Footer
    st.markdown("""
    <div class="divider"></div>
    <p style="text-align: center; color: #666; font-size: 14px;">
        Developed with ❤ for farmers | Using cutting-edge AI technology
    </p>
    """, unsafe_allow_html=True)

def government_schemes_ui():
    st.markdown("<h2 style='text-align:center; color:#2e8b57;'>🏛 Government Schemes for Farmers</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#555;'>🌾 Empowering farmers with access to financial support, insurance, irrigation, and modern farming opportunities.</p>", unsafe_allow_html=True)

    schemes = [
        {
            "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
            "description": "Provides crop insurance to safeguard farmers against natural calamities, pests, and diseases. Ensures financial support in case of crop loss.",
            "eligibility": "All farmers growing notified crops in notified areas, including sharecroppers and tenant farmers.",
            "documents": ["Aadhaar Card", "Land Ownership/Lease papers", "Crop Sowing Certificate", "Bank Passbook"],
            "link": "https://pmfby.gov.in/"
        },
        {
            "name": "Kisan Credit Card (KCC)",
            "description": "Offers short-term credit at low interest rates to meet crop production needs. Farmers can withdraw funds flexibly when needed.",
            "eligibility": "All farmers (individuals or joint) who own or cultivate land.",
            "documents": ["Aadhaar Card", "Land Records", "Passport-size Photos", "Bank Account Proof"],
            "link": "https://www.myscheme.gov.in/schemes/kcc"
        },
        {
            "name": "Soil Health Card Scheme",
            "description": "Provides soil health cards with crop-wise nutrient and fertilizer recommendations to improve productivity and sustainability.",
            "eligibility": "All farmers across India.",
            "documents": ["Aadhaar Card", "Land Ownership Papers", "Soil Sample"],
            "link": "https://soilhealth.dac.gov.in/"
        },
        {
            "name": "Paramparagat Krishi Vikas Yojana (PKVY)",
            "description": "Promotes organic farming through cluster-based approaches and certification. Encourages farmers to shift towards chemical-free agriculture.",
            "eligibility": "Groups of farmers or Farmer Producer Organizations.",
            "documents": ["Aadhaar Card", "Group Registration Certificate", "Land Records", "Bank Details"],
            "link": "https://pgsindia-ncof.gov.in/"
        },
        {
            "name": "Pradhan Mantri Krishi Sinchayee Yojana (PMKSY)",
            "description": "Improves irrigation coverage and water-use efficiency to achieve 'more crop per drop'. Focus on sustainable irrigation practices.",
            "eligibility": "All farmers, with priority to small and marginal farmers.",
            "documents": ["Aadhaar Card", "Land Documents", "Irrigation Project Details", "Bank Account Proof"],
            "link": "https://pmksy.gov.in/"
        },
        {
            "name": "eNAM (National Agriculture Market)",
            "description": "An online trading platform for farmers to sell produce at better prices. Connects markets across India digitally.",
            "eligibility": "All farmers registered with local APMC mandis.",
            "documents": ["Aadhaar Card", "Bank Account Details", "Farmer Registration Certificate"],
            "link": "https://enam.gov.in/web/"
        },
        {
            "name": "PM-KISAN Samman Nidhi",
            "description": "Provides direct income support of ₹6000 per year to small and marginal farmers in three installments.",
            "eligibility": "All small and marginal farmer families owning up to 2 hectares of land.",
            "documents": ["Aadhaar Card", "Land Ownership Records", "Bank Passbook"],
            "link": "https://pmkisan.gov.in/"
        },
        {
            "name": "Rashtriya Krishi Vikas Yojana (RKVY)",
            "description": "Supports farmers through state-based agricultural projects for productivity, innovation, and infrastructure.",
            "eligibility": "Farmers selected under state-level agricultural programs.",
            "documents": ["Aadhaar Card", "Land Records", "Bank Details", "Project Approval Documents"],
            "link": "https://rkvy.nic.in/"
        },
        {
            "name": "National Mission on Sustainable Agriculture (NMSA)",
            "description": "Promotes sustainable farming practices such as efficient water use, soil health management, and organic farming.",
            "eligibility": "Farmers practicing rain-fed and vulnerable agriculture.",
            "documents": ["Aadhaar Card", "Soil Health Report", "Land Ownership Papers", "Bank Account Details"],
            "link": "https://nmsa.dac.gov.in/"
        },
        {
            "name": "Pradhan Mantri Kisan Maan Dhan Yojana (PM-KMY)",
            "description": "A pension scheme for farmers above 60 years of age ensuring social security with ₹3000/month after retirement.",
            "eligibility": "Small and marginal farmers aged 18–40 years with up to 2 hectares of land.",
            "documents": ["Aadhaar Card", "Land Records", "Bank Passbook", "Age Proof"],
            "link": "https://pmkmy.gov.in/"
        }
    ]

    for scheme in schemes:
        with st.expander(f"📌 {scheme['name']}"):
            st.write(f"**📝 Description:** {scheme['description']}")
            st.write(f"**✅ Eligibility:** {scheme['eligibility']}")
            st.write("**📂 Documents Required:**")
            for doc in scheme["documents"]:
                st.markdown(f"- {doc}")
            st.markdown(f"[🔗 More Info / Apply Here]({scheme['link']})")






# Chatbot function

def farmer_chatbot_ui():
    # Page Title
    st.markdown("<h2 style='text-align: center; color: #2e8b57;'>🤖 Farmer's Assistant Chatbot</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>🌾 Smart advice for smarter farming — Ask anything about crops, soil, pests, or irrigation!</p>", unsafe_allow_html=True)

    # Custom CSS for styling chat bubbles
    st.markdown("""
        <style>
        .user-msg {
            background-color: #e6ffe6;
            padding: 12px;
            border-radius: 10px;
            margin: 8px 0;
            color: #2e7d32;
            font-weight: 500;
        }
        .bot-msg {
            background-color: #f0f0f0;
            padding: 12px;
            border-radius: 10px;
            margin: 8px 0;
            color: #333;
            font-style: italic;
        }
        .chat-box {
            border: 2px solid #2e8b57;
            border-radius: 12px;
            padding: 15px;
            background-color: #ffffff;
            box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    # Initialize Groq client
    client = Groq(api_key="API_KEY")  # replace with real key

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {"role": "system", "content": "You are a helpful assistant for farmers. Give short, simple advice in easy language."}
        ]

    # Input box
    user_input = st.text_input("💬 Type your question below:")

    if st.button("🚀 Ask Now") and user_input:
        st.session_state["chat_messages"].append({"role": "user", "content": user_input})

        with st.spinner("🤔 Thinking..."):
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=st.session_state["chat_messages"]
            )
            reply = response.choices[0].message.content
            st.session_state["chat_messages"].append({"role": "assistant", "content": reply})

    # Chat history box
    st.markdown("<div class='chat-box'>", unsafe_allow_html=True)
    for msg in st.session_state["chat_messages"]:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-msg'>👨‍🌾 <b>You:</b> {msg['content']}</div>", unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            st.markdown(f"<div class='bot-msg'>🤖 <b>Bot:</b> {msg['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def smart_irrigation_ui():
    # File paths
    csv_file = "data.csv"
    command_file = "command.txt"

    st.title("🌱Smart Farming Dashboard")


    # ---------------- Live Data ----------------
    st.subheader("📊 Sensor Data")
    placeholder = st.empty()

    # Continuous refresh (replace while True with streamlit auto-refresh)
    for _ in range(200):  # refresh 200 times (~6 min at 2 sec interval)
        with placeholder.container():
            if os.path.exists(csv_file):
                try:
                    df = pd.read_csv(csv_file)

                    # Ensure clean headers
                    df.columns = df.columns.str.strip()

                    if not df.empty and all(col in df.columns for col in ["soil", "temperature", "humidity"]):
                        latest = df.iloc[-1]

                        # Latest metrics
                        c1, c2, c3 = st.columns(3)
                        c1.metric("🌱 Soil Moisture (%)", latest["soil"])
                        c2.metric("🌡️ Temperature (°C)", latest["temperature"])
                        c3.metric("💧 Humidity (%)", latest["humidity"])

                        # Graphs
                        st.subheader("📈 Trends")
                        st.line_chart(df[["soil", "temperature", "humidity"]])

                        # Raw table
                        st.subheader("📋 Raw Data")
                        st.dataframe(df.tail(10))
                    else:
                        st.warning("⚠ No valid sensor data in CSV yet.")
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")
            else:
                st.error("CSV file not found. Make sure logger script is running.")

        time.sleep(2)

def smart_farming_ui():
    CSV_FILE = "data.csv"
    COMMAND_FILE = "command.txt"
    MODEL_FILE = "soil_model.pkl"

    # Twilio setup
    ACCOUNT_SID = "SID"
    AUTH_TOKEN = "TOKEN"
    FROM_PHONE = "NO"
    TO_PHONE = "+NO"

    # Utilities
    def send_sms(message: str):
        try:
            client = Client(ACCOUNT_SID, AUTH_TOKEN)
            client.messages.create(body=message, from_=FROM_PHONE, to=TO_PHONE)
            st.success("📩 SMS sent to farmer!")
        except Exception as e:
            st.error(f"SMS failed: {e}")

    def write_command(cmd: str):
        if cmd in ("ON", "OFF"):
            with open(COMMAND_FILE, "w") as f:
                f.write(cmd)

    @st.cache_resource
    def load_model(path):
        if os.path.exists(path):
            with open(path, "rb") as f:
                return pickle.load(f)
        return None

    def predict_quality(model, soil, temp, hum):
        try:
            X = [[float(soil), float(temp), float(hum)]]
            return model.predict(X)[0]
        except Exception:
            return None

    # Page UI
    st.subheader("🌱 Smart Farming Dashboard — IoT + AI + SMS Alerts")

    auto_refresh = st.sidebar.checkbox("Auto-refresh every 60s", value=True)

    # Load AI model
    model = load_model(MODEL_FILE)

    # Pump Control
    st.subheader("💧 Pump Control")
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("Turn ON Pump"):
            write_command("ON")
            st.success("✅ Pump ON command queued")
    with c2:
        if st.button("Turn OFF Pump"):
            write_command("OFF")
            st.warning("🛑 Pump OFF command queued")
    with c3:
        auto_control = st.checkbox("🤖 Auto-control by AI", value=False)

    st.markdown("---")

    # Live Sensor + AI Prediction
    st.subheader("📊 Live Sensor Data + AI Soil Quality")

    if not os.path.exists(CSV_FILE):
        st.error("CSV not found. Please run logger.py.")
        return

    try:
        df = pd.read_csv(CSV_FILE)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return

    needed = {"soil", "temperature", "humidity"}
    if df.empty or not needed.issubset(set(df.columns)):
        st.warning("No valid sensor data yet.")
        return

    for c in ["soil", "temperature", "humidity"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["soil", "temperature", "humidity"])

    if df.empty:
        st.warning("No numeric rows to display yet.")
        return

    latest = df.iloc[-1]
    colA, colB, colC, colD = st.columns(4)
    colA.metric("🌱 Soil Moisture (%)", f"{latest['soil']:.1f}")
    colB.metric("🌡 Temperature (°C)", f"{latest['temperature']:.1f}")
    colC.metric("💧 Humidity (%)", f"{latest['humidity']:.1f}")

    # AI Prediction
    if model:
        pred = predict_quality(model, latest["soil"], latest["temperature"], latest["humidity"])
        colD.metric("🧠 Soil Quality", pred if pred else "—")

        if pred == "Low":
            st.error("⚠ Soil Quality: Low — Irrigation Needed")
            send_sms("⚠ Soil is too dry! Please water your crops or turn on the pump.")
            if auto_control:
                write_command("ON")
                st.info("🤖 Auto-control: Pump ON")
        elif pred == "Medium":
            st.warning("⚠ Soil Quality: Medium — Monitor closely")
        elif pred == "High":
            st.success("✅ Soil Quality: High — No irrigation needed")
        else:
            st.info("AI model did not return a prediction.")
    else:
        colD.metric("🧠 Soil Quality", "No Model")
        st.info("No trained model found. Run train_model.py first.")

     # Auto-refresh
    if auto_refresh:
        time.sleep(600)
        st.experimental_set_query_params(_=str(time.time()))



# Initialize Groq client
client = Groq(api_key="API_KEY")  # replace with your Groq API key

# -----------------------------
# Rule-based safety checks
# -----------------------------
def rule_check(crop, soil, temp, hum):
    if soil < 30:
        return f"❌ Soil too dry. Irrigate before applying fertilizer for {crop.title()}."
    elif soil > 80:
        return f"❌ Soil too wet. Wait until soil drains before applying fertilizer for {crop.title()}."
    elif temp > 35:
        return f"⚠ Too hot! Apply fertilizer in evening/morning for {crop.title()}."
    elif hum > 85:
        return f"⚠ High humidity! Delay fertilizer for {crop.title()} to avoid fungal infection."
    return None

# -----------------------------
# Groq AI Fertilizer Advice
# -----------------------------
def get_fertilizer_advice(crop, soil, temp, hum):
    messages = [
        {"role": "system", "content": 
         "You are an agricultural assistant. Suggest fertilizer type and simple instructions "
         "based on crop, soil moisture, temperature, and humidity. Keep the answer short and farmer-friendly."},
        {"role": "user", "content": f"Crop: {crop}, Soil Moisture: {soil}%, Temperature: {temp}°C, Humidity: {hum}%"}
    ]

    response = client.chat.completions.create(
        model="llama3-8b-8192",  
        messages=messages
    )
    return response.choices[0].message.content

# -----------------------------
# Main Streamlit App
# -----------------------------
def  fertilizer_ui():
    st.title("🌾 Fertilizer Recommendation System")
    st.write("Smart advice for farmers based on crop + soil + weather conditions")

    # Step 1: Crop input
    crop = st.text_input("Enter Crop Name (e.g., Rice, Wheat, Tomato, Banana)")

    # Step 2: Choose input source
    mode = st.radio("📥 How do you want to provide values?",
                    ["Take from Sensor (Auto)", "Enter Manually"])

    soil, temp, hum = None, None, None  # default

    if mode == "Take from Sensor (Auto)":
        # Example sensor values (replace with real ESP32 values)
        soil, temp, hum = 55, 28, 65
        st.info(f"📡 Sensor Data → Soil: {soil}%, Temp: {temp}°C, Humidity: {hum}%")

    elif mode == "Enter Manually":
        soil = st.slider("🌍 Soil Moisture (%)", 0, 100, 50)
        temp = st.slider("🌡 Temperature (°C)", 0, 50, 28)
        hum = st.slider("💧 Humidity (%)", 0, 100, 65)

    else:  # Upload CSV mode
        uploaded_file = st.file_uploader("📂 Upload your CSV file", type=["csv"])
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.write("✅ Data Preview:", df.head())

            # Assuming CSV has columns: "SoilMoisture", "Temperature", "Humidity"
            soil = df["SoilMoisture"].iloc[-1]  # latest value
            temp = df["Temperature"].iloc[-1]
            hum = df["Humidity"].iloc[-1]

            st.info(f"📊 From CSV → Soil: {soil}%, Temp: {temp}°C, Humidity: {hum}%")

    # Step 3: Generate Recommendation
    if st.button("Get Fertilizer Advice"):
        if crop and soil is not None:
            rule_msg = rule_check(crop, soil, temp, hum)
            if rule_msg:
                st.warning(rule_msg)
            else:
                advice = get_fertilizer_advice(crop, soil, temp, hum)
                st.success(advice)
        else:
            st.error("⚠ Please enter crop name and provide sensor/CSV values.")




def main():
    
    # Custom CSS for sidebar + title
    st.markdown("""
        <style>
        /* App background */
        .stApp {
            background-color: #f9fff9;
            font-family: 'Segoe UI', sans-serif;
        }

        /* Main title */
        .main-title {
            font-size: 36px !important;
            font-weight: bold;
            color: #2d6a4f;
            text-align: center;
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 10px;
            background: linear-gradient(90deg, #d8f3dc, #b7e4c7, #95d5b2);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #2d6a4f, #1b4332);
            padding: 20px;
        }

        /* Sidebar title */
        .css-1d391kg, .css-1lcbmhc, .css-qri22k {
            color: white !important;
            font-weight: bold;
        }

        /* Sidebar options */
        div[data-baseweb="select"] span {
            color: #2d6a4f !important;
            font-weight: bold;
        }

        /* Sidebar selectbox dropdown */
        div[data-baseweb="popover"] {
            background-color: #f1f8f5 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Title
    st.markdown('<div class="main-title">🌾 CROPCARE - Smart Farming Assistant</div>', unsafe_allow_html=True)

    # Sidebar menu
    menu = [
        "🏠 Home",
        "🔐 Login",
        "📝 Signup",
        "🌱 Soil Health Monitoring",
        "🚿 Smart Irrigation",
        "💊 Fertilizer Recommendation",
        "📷 Plant Disease Detection",
        "💬 Discussion Forum",
        "🏛 Government Schemes",
        "🤖 Farmer's Chatbot"
    ]

    choice = st.sidebar.selectbox("📌 Choose a section:", menu)





    if choice == "🔐 Login":
        if "user" not in st.session_state:
            login()
        else:
            st.success(f"You're logged in as {st.session_state['user']}")
            # show quick link to weather after login
            
    elif choice == "📝 Signup":
        signup()
    elif choice == "💬 Discussion Forum":
        if "user" in st.session_state:
            discussion_forum_ui()
        else:
            st.warning("Please login to access the discussion forum.")
    
    elif choice == "🏛 Government Schemes":
       if "user" in st.session_state:
          government_schemes_ui()
       else:
          st.warning("Please login to view government schemes.")

    elif choice == "🤖 Farmer's Chatbot":
        if "user" in st.session_state:
           farmer_chatbot_ui()
        else:
           st.warning("Please login to access the chatbot.")

    elif choice == "🌱 Soil Health Monitoring":
        if "user" in st.session_state:
            smart_irrigation_ui() 
        else:
           st.warning("Please login to access the chatbot.")

    

    elif choice == "🚿 Smart Irrigation":
        if "user" in st.session_state:
           smart_farming_ui()
        else:
           st.warning("Please login to access Smart Irrigation.")

    elif choice == "📷 Plant Disease Detection":
      if "user" in st.session_state:
        disease_detection_ui()
      else:
        st.warning("Please login to use Plant Disease Detection.")

    
    elif choice =="💊 Fertilizer Recommendation":
      if "user" in st.session_state:
          fertilizer_ui()
      else:
        st.warning("Please login to use Plant Disease Detection.")
 


    elif choice == "🏠 Home":
           home_ui()



if __name__ == "__main__":
    main()
