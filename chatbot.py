import random
import re
import os
import pandas as pd
import joblib
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.metrics.pairwise import cosine_similarity

class PathOracleBot:
    def __init__(self):
        # Greetings
        self.greetings = ["hi", "hello", "hey", "hii", "hola", "good morning", "good afternoon", "good evening", "yo", "sup", "namaste"]
        
        # Upgrade: Smart Knowledge Base for direct QA (Cosine Similarity Matching)
        self.knowledge_base = {
            "what is system design": "System design is the process of defining the architecture, modules, interfaces, and data for a system to satisfy specified requirements.",
            "how do i prepare for a backend interview": "Focus on Data Structures, Algorithms, System Design, RESTful APIs, Database Management (SQL/NoSQL), and caching mechanisms like Redis.",
            "what is the difference between sql and nosql": "SQL databases are relational and table-based with predefined schemas. NoSQL databases are non-relational, document/key-value/graph based, and have dynamic schemas.",
            "what is machine learning": "Machine learning is a subset of AI that involves training algorithms to find patterns in data and make predictions without being explicitly programmed.",
            "how to get good at problem solving": "Practice consistently on platforms like LeetCode or HackerRank. Start with arrays and strings, master hash maps, and gradually move to dynamic programming and graphs."
        }
        self.kb_questions = list(self.knowledge_base.keys())
        self.kb_vectorizer = TfidfVectorizer(stop_words='english')
        self.kb_vectors = self.kb_vectorizer.fit_transform(self.kb_questions)

        self.vectorizer_file = "vectorizer.pkl"
        self.model_file = "intent_model.pkl"

        if not os.path.exists(self.vectorizer_file) or not os.path.exists(self.model_file):
            print("Model files not found. Initiating auto-training with advanced SVC model...")
            self._train_and_save_model()

        try:
            self.vectorizer = joblib.load(self.vectorizer_file)
            self.intent_model = joblib.load(self.model_file)
            print("PathOracleBot Advanced ML Brain loaded successfully!")
        except Exception as e:
            print(f"ERROR: Failed to load models. {e}")
            self.vectorizer = None
            self.intent_model = None

    def _train_and_save_model(self):
        # Import the logic from intent_model to auto-heal if files are deleted
        import intent_model
        # The import alone triggers the training script if we run it dynamically
        self.vectorizer = joblib.load(self.vectorizer_file)
        self.intent_model = joblib.load(self.model_file)

    def predict_intent(self, text):
        if not self.vectorizer or not self.intent_model: return None
        x = self.vectorizer.transform([text])
        
        # Get probabilities to ensure confidence
        probs = self.intent_model.predict_proba(x)[0]
        max_prob = max(probs)
        
        if max_prob < 0.35: # strict confidence threshold
            return "unknown"
            
        return self.intent_model.predict(x)[0]

    def handle_profile_analysis(self, user, skills):
        """Dynamically reads the user's database to give hyper-personalized advice"""
        if not user:
            return "I need you to be fully authenticated to analyze your career matrix."
        
        target = user.get('target_role', 'an unassigned role')
        username = user.get('username', 'Explorer')
        
        if not skills:
            return f"{username}, your skill map is currently completely empty. To become a successful {target}, you need to start adding foundational skills to your BeyondU profile!"
            
        # Smart logic to find lowest and highest skills
        sorted_skills = sorted(skills, key=lambda x: x.get('current_level', 0))
        weakest = sorted_skills[0]
        strongest = sorted_skills[-1]
        
        return (f"Analyzing your profile metrics, {username}... Your designated target is **{target}**.<br><br>"
                f"📈 **Strengths:** Your strongest area right now is {strongest['skill_name']} at level {strongest['current_level']}/100. Great work maintaining that.<br><br>"
                f"🔥 **Critical Focus:** However, you must prioritize improving {weakest['skill_name']}, which is currently lagging at level {weakest['current_level']}/100. Bridging this specific gap is essential to match standard industry requirements for your role.")

    def check_knowledge_base(self, msg):
        """Uses Cosine Similarity to find the closest matching technical answer"""
        vec = self.kb_vectorizer.transform([msg])
        similarities = cosine_similarity(vec, self.kb_vectors).flatten()
        best_match_idx = similarities.argmax()
        
        # 55% similarity threshold allows for typos and rephrasing
        if similarities[best_match_idx] > 0.55: 
            return self.knowledge_base[self.kb_questions[best_match_idx]]
        return None

    def get_response(self, message, user=None, skills=None):
     msg = message.lower().strip()

    # Direct shortcut for thanks
     if msg in [
        "thanks", "thank you", "thankyou", "thx", "ty",
        "thanks a lot", "many thanks", "appreciate it",
        "much appreciated"
    ]:
        name = user.get("username") if user else "there"

        responses = [
            f"You're most welcome, {name}! 😊💖",
            f"My pleasure, {name}! Happy to help! 🚀",
            f"Anytime, {name}! Keep learning. ✨",
            f"Glad I could help, {name}! 😄",
            f"Always happy to help, {name}! 💙"
        ]

        return random.choice(responses)

     if msg in ["bye", "goodbye", "exit", "quit"]:
        return "Goodbye! Keep learning and expanding your skill graph. 👋"

    # 1. Smart Knowledge Base lookup (Cosine Similarity)
     kb_answer = self.check_knowledge_base(msg)
     if kb_answer:
        return kb_answer

    # 2. Predict Intent using SVC Machine Learning
     intent = self.predict_intent(msg)

    # 3. Dynamic Contextual Routing
     if intent == "greeting" or msg in self.greetings:
        name = user.get("username") if user else "there"
        return f"Hello {name}! 👋 I am PathOracle. I can answer technical programming questions, provide career advice, or fully analyze your skill profile. How can we optimize your trajectory today?"

     if intent == "profile_analysis":
        return self.handle_profile_analysis(user, skills)

     if intent == "programming":
        if "python" in msg:
            return "Python is a high-level, interpreted language known for rapid development. It's the industry standard for Backend APIs, AI, and Data Science. Focus on mastering Data Structures (Lists/Dicts) and Object-Oriented paradigms."

        if "javascript" in msg or "js" in msg:
            return "JavaScript is the core engine of the web. To truly master it, you must understand the DOM, the Event Loop, and asynchronous programming (Promises/Async-Await)."

        if "sql" in msg:
            return "SQL is essential for managing relational databases. Master JOINs, GROUP BY clauses, and indexing for optimal query performance."

        return "Programming is fundamentally about solving complex problems using logic. Break down your problem into smaller algorithmic steps. Which specific language or framework are you currently tackling?"

     if intent == "career":
        target = user.get('target_role', 'your dream job') if user else 'your dream job'
        return f"To excel as **{target}**, you need a mix of technical mastery and strong soft skills. Ensure your GitHub commit history is active, deploy 2-3 complex end-to-end projects, and practice mock interviews utilizing the STAR (Situation, Task, Action, Result) method."

     if intent == "math":
        return "Mathematics is the absolute foundation of computer science. If you're pursuing AI, Data Science, or Graphics, focus heavily on Linear Algebra, Calculus, and Probability Theory."

     if intent == "science":
        return "Science teaches us the scientific method—hypothesis, experimentation, observation, and analysis. This exact same structured thinking applies heavily to debugging complex software architectures."

     if intent == "technology":
        return "The technological landscape is evolving rapidly. Currently, Generative AI, Cloud Infrastructure (AWS/Azure), and Edge Computing are massive trends. Stay adaptable, read technical documentation, and never stop building."

     if intent == "thanks":
        name = user.get("username") if user else "there"
        responses = [
            f"You're most welcome, {name}! 😊💖",
            f"My pleasure, {name}! Happy to help! 🚀",
            f"Anytime, {name}! Keep learning. ✨",
            f"Glad I could help, {name}! 😄",
            f"Always happy to help, {name}! 💙"
        ]
        return random.choice(responses)

    # 4. Intelligent Extractor Fallback
     if msg.startswith("explain ") or msg.startswith("what is "):
        topic = msg.replace("explain ", "").replace("what is ", "").strip("?")
        return f"That is a great question about **{topic}**. In the context of computer science and your overall career path, mastering {topic} involves understanding its core foundational principles, thoroughly reading official documentation, and building small, isolated projects to test its behavior in real-time."

    # 5. Final Unknown Fallback
     return "That's an interesting query! My internal models are constantly learning. Could you rephrase that, or ask me to analyze your career profile, explain programming concepts, or give interview preparation tips?"

# Terminal testing block
if __name__ == "__main__":
    bot = PathOracleBot()
    print("\n[System] PathOracle ML Bot is active. Type 'quit' to exit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['quit', 'exit']:
            break
        # Testing with mock user data
        mock_user = {"username": "Admin", "target_role": "Senior AI Engineer"}
        mock_skills = [
            {"skill_name": "Python", "current_level": 80},
            {"skill_name": "Docker", "current_level": 25}
        ]
        response = bot.get_response(user_input, mock_user, mock_skills)
        print(f"PathOracle: {response}")