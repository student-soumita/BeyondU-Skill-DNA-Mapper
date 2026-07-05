import os
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC

# ==========================================
# Intelligent Fallback Training Dataset
# ==========================================

fallback_data = {
    "text": [

        # ---------------- Greetings ----------------
        "hello",
        "hi",
        "hi there",
        "hey",
        "hey buddy",
        "good morning",
        "good afternoon",
        "good evening",
        "howdy",
        "greetings",
        "yo",
        "sup",
        "namaste",

        # ---------------- Thanks ----------------
        "thanks",
        "thank you",
        "thank you so much",
        "thanks a lot",
        "many thanks",
        "thx",
        "ty",
        "much appreciated",
        "appreciate it",
        "that's great thanks",

        # ---------------- Programming ----------------
        "how do i learn python",
        "python",
        "learn python",
        "explain python",
        "explain javascript",
        "javascript",
        "js",
        "what is java",
        "what is c++",
        "help me code",
        "debug this",
        "fix this code",
        "what is a compiler",
        "what is sql",
        "database",
        "api",
        "rest api",
        "backend development",
        "frontend development",
        "how to write a function",
        "what is recursion",
        "explain recursion",

        # ---------------- Career ----------------
        "career advice",
        "how to get a job",
        "job tips",
        "resume review",
        "review my resume",
        "tips for my resume",
        "interview tips",
        "mock interview",
        "placement preparation",
        "how to pass interview",
        "dream company",
        "how to get hired",

        # ---------------- Mathematics ----------------
        "what is calculus",
        "solve equation",
        "derivative",
        "integration",
        "algebra",
        "probability",
        "linear algebra",
        "math help",

        # ---------------- Science ----------------
        "physics",
        "chemistry",
        "biology",
        "quantum mechanics",
        "science help",

        # ---------------- Technology ----------------
        "what is ai",
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "cloud computing",
        "latest tech",
        "technology news",
        "blockchain",
        "cybersecurity",
        "computer science",

        # ---------------- Profile Analysis ----------------
        "profile",
        "my profile",
        "profile analysis",
        "analyse profile",
        "analyze profile",
        "analyze my profile",
        "profile report",
        "profile review",
        "review my profile",
        "evaluate my profile",
        "check profile",
        "check my profile",
        "skill analysis",
        "analyze my skills",
        "my skills",
        "show my stats",
        "show profile analysis",
        "show my profile",
        "what is my weakest skill",
        "how am i doing",
        "career analysis",
        "career report",
        "what should i learn next",
        "my dashboard"

    ],

    "intent": [

        # Greetings
        "greeting","greeting","greeting","greeting","greeting",
        "greeting","greeting","greeting","greeting","greeting",
        "greeting","greeting","greeting",

        # Thanks
        "thanks","thanks","thanks","thanks","thanks",
        "thanks","thanks","thanks","thanks","thanks",

        # Programming
        "programming","programming","programming","programming",
        "programming","programming","programming","programming",
        "programming","programming","programming","programming",
        "programming","programming","programming","programming",
        "programming","programming","programming","programming",
        "programming","programming",

        # Career
        "career","career","career","career","career",
        "career","career","career","career","career",
        "career","career",

        # Math
        "math","math","math","math",
        "math","math","math","math",

        # Science
        "science","science","science","science","science",

        # Technology
        "technology","technology","technology","technology",
        "technology","technology","technology","technology",
        "technology","technology",

        # Profile
        "profile_analysis","profile_analysis","profile_analysis",
        "profile_analysis","profile_analysis","profile_analysis",
        "profile_analysis","profile_analysis","profile_analysis",
        "profile_analysis","profile_analysis","profile_analysis",
        "profile_analysis","profile_analysis","profile_analysis",
        "profile_analysis","profile_analysis","profile_analysis",
        "profile_analysis","profile_analysis","profile_analysis",
        "profile_analysis","profile_analysis","profile_analysis"
    ]
}

# ==========================================
# Create DataFrame
# ==========================================

df = pd.DataFrame(fallback_data)

# ==========================================
# Merge custom dataset if available
# ==========================================

if os.path.exists("training_data.csv"):
    try:
        custom_df = pd.read_csv("training_data.csv")
        df = pd.concat([df, custom_df], ignore_index=True)
        print("Loaded custom training_data.csv successfully.")
    except Exception as e:
        print(f"Error loading training_data.csv: {e}")

# ==========================================
# Training Data
# ==========================================

texts = df["text"]
labels = df["intent"]

# ==========================================
# TF-IDF Vectorizer
# ==========================================

vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 3)
)

X = vectorizer.fit_transform(texts)

# ==========================================
# Train SVM
# ==========================================

print("Training Advanced Support Vector Machine...")

model = SVC(
    kernel="linear",
    probability=True
)

model.fit(X, labels)

# ==========================================
# Save Model
# ==========================================

joblib.dump(vectorizer, "vectorizer.pkl")
joblib.dump(model, "intent_model.pkl")

print("Model training completed successfully!")

# ==========================================
# Prediction Function
# ==========================================

def predict_intent(text):
    x = vectorizer.transform([text])

    probs = model.predict_proba(x)[0]
    confidence = max(probs)

    prediction = model.predict(x)[0]

    print(f"Input      : {text}")
    print(f"Prediction : {prediction}")
    print(f"Confidence : {confidence:.3f}")

    if confidence < 0.35:
        return "unknown"

    return prediction


# ==========================================
# Test Mode
# ==========================================

if __name__ == "__main__":

    print("\nIntent Model Ready!")
    print("Type 'exit' to quit.\n")

    while True:

        query = input("You : ")

        if query.lower() == "exit":
            break

        print("Intent :", predict_intent(query))